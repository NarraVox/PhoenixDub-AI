"""Cria o pacote oficial, sem modelos, dados de usuário ou configurações locais."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import zipfile


def build():
    root = Path(__file__).resolve().parents[2]
    version = runpy.run_path(str(root / 'nexus/version.py'))['APP_VERSION']
    tag = os.getenv('GITHUB_REF_NAME', '')
    if os.getenv('GITHUB_REF_TYPE') == 'tag' and tag != 'v' + version:
        raise ValueError('A tag não corresponde à versão em nexus/version.py.')
    paths = {name: root / name for name in ['Nexus_AI_Pro.py', 'requirements.txt']}
    paths['Nexus_AI_Pro.exe'] = root / 'dist/Nexus_AI_Pro.exe'
    for path in (root / 'nexus').rglob('*'):
        if path.is_file() and path.suffix.lower() in ('.py', '.js', '.css', '.html', '.svg', '.png', '.jpg', '.ico') and '__pycache__' not in path.parts:
            paths[path.relative_to(root).as_posix()] = path
    output = root / 'dist/PhoenixDub_Update.zip'
    hashes = {}
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as package:
        for name, path in sorted(paths.items()):
            data = path.read_bytes()
            hashes[name] = hashlib.sha256(data).hexdigest()
            package.writestr(name, data)
        package.writestr('manifest.json', json.dumps({'version': version, 'files': hashes}))
    print(f'Pacote de atualização v{version}: {output} ({len(hashes)} arquivos)')


if __name__ == '__main__':
    build()
