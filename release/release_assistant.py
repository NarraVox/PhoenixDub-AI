"""Preparação guiada, sem modelos de IA, instalação ou publicação."""
import argparse
import ast
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
PYTHON_TESTS = ('test_release_preparation.py', 'test_release_assistant.py', 'test_updates.py', 'test_distribution.py', 'test_setup_support.py')
JS_TESTS = ('tests/test_correction_progress.mjs', 'tests/test_correction_timing.mjs',
            'tests/test_music_source.mjs')


def version_argument(value):
    value = value.removeprefix('v')
    if not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise argparse.ArgumentTypeError('Use uma versao como 0.8.1.')
    return value


def declared_version(root):
    tree = ast.parse((root/'nexus/version.py').read_text(encoding='utf-8-sig'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'APP_VERSION' for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('APP_VERSION nao encontrada em nexus/version.py.')


class Assistant:
    def __init__(self, root, version, offline=False):
        self.root = root.resolve()
        run_id = datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8]
        self.logs = self.root/'_updates/release-assistant'/run_id
        self.logs.mkdir(parents=True, exist_ok=False)
        self.report = {'status': 'EM_ANDAMENTO', 'version': version, 'offline': offline,
                       'steps': [], 'destination': None, 'next_action': '',
                       'publication': 'Nao executada; este comando nao publica.'}

    def command(self, label, args, cwd=None):
        print('VERIFICANDO: ' + label, flush=True)
        env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1',
                   GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never')
        log = self.logs/(str(len(self.report['steps']) + 1) + '.log')
        # Arquivo direto evita buffers enormes e preserva saida mesmo em timeout.
        with log.open('wb') as stream:
            try:
                process = subprocess.run(args, cwd=cwd or self.root, env=env,
                                         stdout=stream, stderr=subprocess.STDOUT, timeout=300)
                code = process.returncode
            except subprocess.TimeoutExpired:
                code = 124
        self.report['steps'].append({'name': label, 'returncode': code, 'log': str(log)})
        if code:
            raise ValueError(f'{label}: FALHOU (codigo {code}). Consulte {log}. Pare; nao publique nem ignore a falha.')
        return log.read_text(encoding='utf-8', errors='replace').strip()

    def preflight(self):
        if sys.version_info < (3, 10):
            raise ValueError('Use Python 3.10 ou superior.')
        for executable in ('git', 'node'):
            if not shutil.which(executable):
                raise ValueError(f'{executable} nao encontrado no PATH. Configure a ferramenta e repita.')
        email = self.command('Conferir email privado do Git', ['git', 'config', 'user.email'])
        if not re.fullmatch(r'[^\s@]+@users\.noreply\.github\.com', email):
            raise ValueError('Configure user.email com o endereco noreply da sua conta GitHub antes de preparar. Nao use email pessoal.')
        policy = json.loads((self.root/'release/policy.json').read_text(encoding='utf-8'))
        remote = self.command('Conferir repositorio', ['git', 'remote', 'get-url', 'origin'])
        if remote != policy['repository']:
            raise ValueError('Origin difere de release/policy.json. Pare e revise o repositorio.')
        actual = declared_version(self.root)
        if actual != self.report['version']:
            raise ValueError(f'Versao solicitada {self.report["version"]}; nexus/version.py declara {actual}. '
                             'Reconcile a versao e as notas com o responsavel antes de preparar.')
        for name in ('README.md', 'RELEASE_NOTES.md', 'docs/NOTAS_PARA_GITHUB.md'):
            if not re.search(r'(?<![\w.])v?' + re.escape(actual) + r'(?![\w.])',
                             (self.root/name).read_text(encoding='utf-8-sig')):
                raise ValueError(f'{name} nao menciona {actual}. Consolide as notas antes de preparar.')
        self.command('Conferir base local', ['git', 'rev-parse', '--verify', 'origin/main^{commit}'])

    def prepare(self):
        if not self.report['offline']:
            self.command('Atualizar referencias remotas', ['git', 'fetch', 'origin', 'main', '--tags'])
        base = self.command('Fixar base', ['git', 'rev-parse', 'origin/main'])
        self.report['base'] = base
        destination = self.root.parent/'IA_releases'/('v' + self.report['version'] + '_' + self.logs.name)
        if destination.exists() or destination.resolve().is_relative_to(self.root):
            raise ValueError('Destino deve ser novo e fora da copia de desenvolvimento.')
        self.report['destination'] = str(destination)
        self.command('Preparar copia isolada', [sys.executable, '-B', str(self.root/'release/prepare_release.py'),
                                               '--destination', str(destination), '--base', base])
        preparation = json.loads((self.root/'_updates/release-preparation/report.json').read_text(encoding='utf-8'))
        if Path(preparation['destination']).resolve() != destination.resolve() or preparation['base'] != base:
            raise ValueError('Relatorio nao corresponde a esta execucao. Pare e revise.')
        (self.logs/'preparation.json').write_text(json.dumps(preparation, ensure_ascii=False, indent=2), encoding='utf-8')
        self.verify_hashes(destination, preparation['sha256'])
        if declared_version(destination) != self.report['version']:
            raise ValueError('Versao da copia preparada diverge da solicitada. Pare e revise o merge.')
        self.command('Espacos e marcadores no diff', ['git', 'diff', '--check'], destination)
        for pattern in PYTHON_TESTS:
            self.command(pattern, [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern], destination)
        self.command('Testes JavaScript', ['node', '--test', *JS_TESTS], destination)
        self.verify_hashes(destination, preparation['sha256'])
        self.report['verified_hashes'] = len(preparation['sha256'])

    @staticmethod
    def verify_hashes(destination, hashes):
        for name, expected in hashes.items():
            path = destination/name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('Arquivo diverge do relatorio: ' + name)

    def finish(self, status, action):
        self.report.update(status=status, next_action=action)
        data = json.dumps(self.report, ensure_ascii=False, indent=2)
        (self.logs/'result.json').write_text(data, encoding='utf-8')
        (self.logs.parent/'ULTIMO_RESULTADO.json').write_text(data, encoding='utf-8')
        text = f'{status}\n{action}\nRelatorio: {self.logs / "result.json"}\n'
        (self.logs.parent/'LEIA_PRIMEIRO.txt').write_text(text, encoding='utf-8')
        print(text.encode('ascii', errors='backslashreplace').decode('ascii'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True, type=version_argument)
    parser.add_argument('--check-only', action='store_true', help='So pre-requisitos; sem rede, worktree ou testes.')
    parser.add_argument('--offline', action='store_true', help='Usa referencias locais; resultado exige conferencia remota posterior.')
    options = parser.parse_args(argv)
    assistant = Assistant(ROOT, options.version, options.offline)
    try:
        assistant.preflight()
        if options.check_only:
            assistant.finish('PASSOU_PRE_REQUISITOS', 'Execute novamente sem --check-only para preparar. Nada foi preparado ainda.')
        else:
            assistant.prepare()
            assistant.finish('PASSOU_PREPARACAO_LOCAL',
                             'Revise preparation.json e o diff, incluindo arquivos novos. '
                             + ('Referencias offline: confira o remoto quando houver internet. ' if options.offline else '')
                             + 'Build, instalacao real e GPU continuam pendentes. Publicar exige autorizacao separada.')
        return 0
    except (ValueError, OSError, SyntaxError) as error:
        assistant.finish('FALHOU', str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
