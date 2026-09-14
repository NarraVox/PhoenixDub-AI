"""Prepara uma release em worktree separado. Nunca faz commit, push ou cria tags."""
import argparse
import ast
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT/'release/policy.json').read_text(encoding='utf-8'))


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd)


def allowed(name):
    p = Path(name)
    if name in POLICY['exclude'] or any(part.lower() in ('uploads', 'models', 'env', 'backups', '__pycache__', '_updates', '.git') for part in p.parts):
        return False
    if name in POLICY['files']:
        return True
    return any(name.startswith(prefix) for prefix in POLICY['directories']) and p.suffix in POLICY['extensions']


def scan(name, data):
    if len(data) > POLICY['max_text_bytes']:
        raise ValueError('Arquivo de código/documentação acima do limite: ' + name)
    text = data.decode('utf-8-sig')
    patterns = [r'gh[pousr]_[A-Za-z0-9]{30,}', r'github_pat_[A-Za-z0-9_]{30,}',
                r'hf_[A-Za-z0-9]{25,}', r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
                r'AKIA[A-Z0-9]{16}', r'sk-(?:proj-)?[A-Za-z0-9_-]{35,}']
    if any(re.search(pattern, text) for pattern in patterns):
        raise ValueError('Possível credencial em ' + name + ' (conteúdo omitido).')
    if name.endswith('.py'):
        ast.parse(text, filename=name)


def names(data):
    return [p for p in data.decode('utf-8').split('\0') if p]


def prepare(destination, base, resolved_remote=()):
    if git('remote', 'get-url', 'origin').decode().strip() != POLICY['repository']:
        raise ValueError('Repositório remoto não corresponde à política.')
    destination = destination.resolve()
    if destination.exists() or destination.is_relative_to(ROOT):
        raise ValueError('Use uma pasta nova fora da cópia de desenvolvimento.')
    base_sha = git('rev-parse', base).decode().strip()
    ancestor_sha = git('merge-base', 'HEAD', base_sha).decode().strip()
    remote_files = set(names(git('ls-tree', '-r', '-z', '--name-only', base_sha)))
    changed = set(names(git('diff', '--name-only', '-z', ancestor_sha)))
    changed.update(names(git('ls-files', '--others', '--exclude-standard', '-z')))
    selected = sorted(n for n in changed if allowed(n))
    excluded = sorted(changed - set(selected))
    blobs = {}
    with tempfile.TemporaryDirectory() as temp:
        for name in selected:
            local = ROOT/name
            if not local.exists():
                blobs[name] = None
                continue
            if local.is_symlink() or not local.resolve().is_relative_to(ROOT):
                raise ValueError('Link fora da árvore: ' + name)
            data = local.read_bytes()
            if name in remote_files:
                remote = git('show', f'{base_sha}:{name}')
                try:
                    ancestor = git('show', f'{ancestor_sha}:{name}')
                except subprocess.CalledProcessError:
                    ancestor = b''
                # Git normaliza CRLF no índice; read_bytes() lê os bytes do disco.
                # Normalize apenas as entradas temporárias de arquivos de texto.
                contents = (data, ancestor, remote)
                if Path(name).suffix != '.ico':
                    contents = tuple(content.replace(b'\r\n', b'\n') for content in contents)
                if contents[2] != contents[1] and contents[0] != contents[2] and name not in resolved_remote:
                    paths = [Path(temp)/part for part in ('local', 'base', 'remote')]
                    for path, content in zip(paths, contents):
                        path.write_bytes(content)
                    merged = subprocess.run(['git','merge-file','-p', *map(str, paths)], capture_output=True)
                    if merged.returncode:
                        raise ValueError('Falha no merge de ' + name + ': returncode=' + str(merged.returncode)
                                         + '; stderr=' + merged.stderr.decode('utf-8', errors='replace')
                                         + '. Revise antes de preparar.')
                    data = merged.stdout
            if Path(name).suffix not in ('.ico',):
                scan(name, data)
            blobs[name] = data
    # Só cria a árvore após a seleção e a primeira auditoria passarem.
    git('worktree', 'add', '--detach', str(destination), base_sha)
    removed = []
    for name in sorted(remote_files):
        preserved = name in POLICY['preserve_remote'] or name.startswith(POLICY['preserve_vendor_directory'])
        if not allowed(name) and not preserved:
            (destination/name).unlink()
            removed.append(name)
    for name, data in blobs.items():
        target = destination/name
        if data is None:
            target.unlink(missing_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    hashes = {}
    candidates = (remote_files - set(removed)) | set(selected)
    for name in sorted(candidates):
        path = destination/name
        if path.is_file():
            data = path.read_bytes()
            if not name.startswith(POLICY['preserve_vendor_directory']) and path.suffix != '.ico':
                scan(name, data)
            hashes[name] = hashlib.sha256(data).hexdigest()
    report = {'base': base_sha, 'ancestor': ancestor_sha, 'destination': str(destination), 'resolved_remote': list(resolved_remote), 'included_changes': selected,
              'excluded_local': excluded, 'removed_legacy_artifacts': removed, 'sha256': hashes}
    report_dir = ROOT/'_updates/release-preparation'
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'sha256'}, ensure_ascii=True, indent=2))
    print('Preparação concluída. Nenhum commit, push ou tag foi executado.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--base', default='origin/main')
    parser.add_argument('--resolved-remote', nargs='*', default=[], help='Arquivos já reconciliados manualmente com o remoto; ficam identificados no relatório.')
    options = parser.parse_args()
    prepare(options.destination, options.base, options.resolved_remote)
