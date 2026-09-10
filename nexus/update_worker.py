"""Aplicador de atualização: somente biblioteca padrão, executado fora do Hub."""
import hashlib
import ast
import re
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import socket
import subprocess
import sys
import time
import zipfile

MAX_PACKAGE = 800 * 1024 * 1024
MAX_EXPANDED = 2 * 1024 * 1024 * 1024


def development_copy(root):
    root = Path(root).resolve()
    return any((directory / '.git').exists() or (directory / '.nexus-development').exists()
               for directory in (root, *root.parents))


def version_tuple(value):
    match = re.fullmatch(r'v?(\d+)\.(\d+)(?:\.(\d+))?', str(value))
    if not match:
        raise ValueError('Versão não reconhecida; atualização bloqueada.')
    return tuple(int(part or 0) for part in match.groups())


def read_version(path):
    # Lê a constante sem executar código da instalação ou do pacote.
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'APP_VERSION' for t in node.targets):
            value = ast.literal_eval(node.value)
            version_tuple(value)
            return value
    raise ValueError('Não foi possível identificar a versão do aplicativo.')


def ensure_upgrade(root, incoming, current):
    if development_copy(root):
        raise ValueError('Cópia de desenvolvimento protegida: instalação automática desativada.')
    installed = version_tuple(current)
    local_version = Path(root) / 'nexus/version.py'
    if local_version.exists():
        installed = max(installed, version_tuple(read_version(local_version)))
    if version_tuple(incoming) <= installed:
        raise ValueError('A atualização precisa ser mais recente que a versão local. Reinstalação e regressão bloqueadas.')


def allowed_path(name):
    p = PurePosixPath(name)
    if (not name or '\\' in name or ':' in name or p.is_absolute()
            or any(part in ('..', '.', '') for part in name.split('/'))):
        return False
    return name in ('Nexus_AI_Pro.exe', 'Nexus_AI_Pro.py', 'requirements.txt') or (
        len(p.parts) > 1 and p.parts[0] == 'nexus'
        and p.suffix.lower() in ('.py', '.js', '.css', '.html', '.svg', '.png', '.jpg', '.ico')
        and '__pycache__' not in p.parts)


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def target_path(root, name):
    if not allowed_path(name):
        raise ValueError('Arquivo não permitido no pacote: ' + name)
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Destino fora da instalação.')
    return path


def stage_package(archive, stage, version):
    with zipfile.ZipFile(archive) as package:
        infos = package.infolist()
        if len(infos) > 10000 or sum(i.file_size for i in infos) > MAX_EXPANDED:
            raise ValueError('Pacote excede o limite permitido.')
        names = [i.filename for i in infos]
        if len(set(n.casefold() for n in names)) != len(names):
            raise ValueError('Pacote contém nomes duplicados.')
        if package.getinfo('manifest.json').file_size > 2 * 1024 * 1024:
            raise ValueError('Manifesto inválido.')
        manifest = json.loads(package.read('manifest.json'))
        files = manifest.get('files')
        if manifest.get('version') != version or not isinstance(files, dict) or not files:
            raise ValueError('Versão ou manifesto inválido.')
        if set(names) != set(files) | {'manifest.json'}:
            raise ValueError('Conteúdo diverge do manifesto.')
        if not {'Nexus_AI_Pro.py', 'Nexus_AI_Pro.exe', 'nexus/version.py', 'requirements.txt'} <= set(files):
            raise ValueError('Pacote incompleto.')
        for name, expected in files.items():
            path = target_path(stage, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            with package.open(name) as source, path.open('wb') as destination:
                shutil.copyfileobj(source, destination)
            if digest(path) != expected:
                raise ValueError('Integridade inválida: ' + name)
        if version_tuple(read_version(stage / 'nexus/version.py')) != version_tuple(version):
            raise ValueError('A versão do código diverge do manifesto.')
    return manifest


def atomic_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + '.update-tmp')
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def apply_files(root, stage, backup, files, current_version):
    ensure_upgrade(root, read_version(stage / 'nexus/version.py'), current_version)
    # Valida tudo antes de substituir o primeiro arquivo.
    for name, expected in files.items():
        target_path(root, name)
        if digest(target_path(stage, name)) != expected:
            raise ValueError('Pacote alterado após download: ' + name)
    changed = []
    try:
        for name in files:
            destination = target_path(root, name)
            existed = destination.exists()
            if existed:
                atomic_copy(destination, backup / name)
            changed.append((name, existed))
            atomic_copy(stage / name, destination)
    except Exception:
        for name, existed in reversed(changed):
            destination = target_path(root, name)
            if existed:
                atomic_copy(backup / name, destination)
            else:
                destination.unlink(missing_ok=True)
        raise


def wait_for_hub(pid, timeout=90):
    if os.name == 'nt':
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x100000, False, pid)
        if handle:
            try:
                if kernel.WaitForSingleObject(handle, timeout * 1000) != 0:
                    raise TimeoutError('O aplicativo não encerrou. Nenhum arquivo foi alterado.')
            finally:
                kernel.CloseHandle(handle)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', 5000))
                return
            except OSError:
                time.sleep(.25)
    raise TimeoutError('A porta do Hub continua ocupada.')


def main(plan_path):
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8'))
    root, stage = Path(plan['root']), Path(plan['stage'])
    result = root / '_updates' / 'result.json'
    success = False
    stopped = False
    try:
        wait_for_hub(plan['pid'])
        stopped = True
        apply_files(root, stage, Path(plan['backup']), plan['files'], plan['current_version'])
        success, message = True, 'Atualização instalada com sucesso.'
    except Exception as error:
        message = 'Não foi possível concluir a atualização: ' + str(error)
    result.write_text(json.dumps({'success': success, 'message': message,
                                 'version': plan['version']}, ensure_ascii=False), encoding='utf-8')
    if stopped:
        subprocess.Popen(plan['restart'], cwd=root, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


if __name__ == '__main__':
    main(sys.argv[1])
