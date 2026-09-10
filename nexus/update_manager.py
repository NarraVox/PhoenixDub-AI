"""Download assíncrono e preparação; não altera a instalação em execução."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import uuid
import requests
from nexus.update_worker import MAX_PACKAGE, digest, stage_package, development_copy, ensure_upgrade
from nexus.version import APP_VERSION


class UpdateManager:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.lock = threading.RLock()
        self.state = {'status': 'idle', 'message': '', 'progress': 0}
        self.plan = None

    def status(self):
        with self.lock:
            return dict(self.state)

    def report(self, **values):
        with self.lock:
            self.state.update(values)

    def ensure_installable(self):
        # Não sobrescreve checkouts de desenvolvimento, mesmo sem alterações locais.
        if development_copy(self.root):
            raise ValueError('Cópia de desenvolvimento protegida. A instalação automática está desativada para preservar as alterações locais.')

    def start(self, release):
        with self.lock:
            self.ensure_installable()
            if self.state['status'] in ('downloading', 'ready', 'installing'):
                return dict(self.state)
            if not release['has_update'] or not release.get('package'):
                raise ValueError('Esta release ainda não oferece um pacote de atualização automática.')
            ensure_upgrade(self.root, release['latest_version'], APP_VERSION)
            self.state = {'status': 'downloading', 'progress': 0, 'message': 'Baixando atualização...'}
            threading.Thread(target=self.download, args=(release,), daemon=True).start()
            return dict(self.state)

    def download(self, release):
        try:
            ensure_upgrade(self.root, release['latest_version'], APP_VERSION)
            asset = release['package']
            expected = asset.get('digest') or ''
            if not expected.startswith('sha256:') or len(expected) != 71:
                raise ValueError('O GitHub ainda não forneceu a verificação de integridade do pacote.')
            folder = self.root / '_updates' / uuid.uuid4().hex
            folder.mkdir(parents=True)
            archive = folder / 'package.zip'
            received = 0
            with requests.get(asset['url'], stream=True, timeout=(5, 30)) as response:
                response.raise_for_status()
                with archive.open('wb') as output:
                    for chunk in response.iter_content(1024 * 1024):
                        received += len(chunk)
                        if received > MAX_PACKAGE:
                            raise ValueError('Pacote excede o limite de download.')
                        output.write(chunk)
                        self.report(progress=min(95, round(received / max(asset['size'], 1) * 95)))
            if received != asset['size'] or digest(archive) != expected[7:]:
                raise ValueError('Download incompleto ou integridade inválida.')
            stage = folder / 'staged'
            manifest = stage_package(archive, stage, release['latest_version'])
            # Mudanças de dependências precisam do instalador: não modifica env parcialmente.
            installed_requirements = self.root / 'requirements.txt'
            if (not installed_requirements.is_file()
                    or installed_requirements.read_text(encoding='utf-8-sig').splitlines()
                    != (stage / 'requirements.txt').read_text(encoding='utf-8-sig').splitlines()):
                raise ValueError('Esta versão altera as dependências. Use o instalador disponível nas notas da release.')
            self.plan = {'root': str(self.root), 'stage': str(stage), 'backup': str(folder / 'backup'),
                         'files': manifest['files'], 'version': release['latest_version'], 'current_version': APP_VERSION}
            self.report(status='ready', progress=100, message='Download verificado. Preparando reinicialização...')
        except Exception as error:
            self.report(status='error', message=str(error))

    def launch(self):
        with self.lock:
            self.ensure_installable()
            if self.state['status'] != 'ready' or not self.plan:
                raise ValueError('A atualização ainda não está pronta.')
            ensure_upgrade(self.root, self.plan['version'], APP_VERSION)
            python = sys.executable
            frozen = getattr(sys, 'frozen', False)
            if frozen:
                python = next((str(p) for p in [self.root / 'env/Scripts/python.exe', self.root / 'env/python.exe']
                               if p.is_file()), None)
                if not python:
                    raise ValueError('Ambiente Python não encontrado. Use o instalador da release.')
            folder = Path(self.plan['stage']).parent
            # Usa o aplicador desta versão, fora dos arquivos que serão substituídos.
            worker = folder / 'apply_update.py'
            shutil.copy2(Path(__file__).with_name('update_worker.py'), worker)
            self.plan.update(pid=os.getpid(), current_version=APP_VERSION, restart=[sys.executable] if frozen else
                             [sys.executable, str(self.root / 'Nexus_AI_Pro.py')])
            plan_path = folder / 'plan.json'
            plan_path.write_text(json.dumps(self.plan), encoding='utf-8')
            subprocess.Popen([python, str(worker), str(plan_path)], cwd=self.root,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.report(status='installing', message='Instalando atualização e reiniciando...')
