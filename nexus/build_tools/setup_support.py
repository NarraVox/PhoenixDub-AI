"""Funções de instalação testáveis, sem carregar modelos ou interface gráfica."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

FFMPEG_URL = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'


def requirement_plan(root, modules):
    groups = {'BASE'}
    if modules.get('llama'):
        groups.add('LLAMA')
    if modules.get('voice') or modules.get('video'):
        groups.update(('TORCH', 'VOICE', 'DJ'))
    result, group = [], None
    for raw in (Path(root)/'requirements.txt').read_text(encoding='utf-8-sig').splitlines():
        line = raw.strip()
        match = re.fullmatch(r'# \[([A-Z]+)\]', line)
        if match:
            group = match[1]
        elif line.startswith('--extra-index-url '):
            result.extend(line.split())
        elif line and not line.startswith('#') and group in groups:
            result.append(line)
    if not any(not item.startswith(('-', 'https://')) for item in result):
        raise ValueError('Lista de dependencias vazia; confira requirements.txt.')
    # Todas as etapas respeitam a mesma matriz, inclusive dependencias transitivas.
    return result + ['-c', str(Path(root)/'requirements.txt')]


def ensure_environment(root):
    root = Path(root).resolve()
    env = root/'env'
    for candidate in (env/'Scripts/python.exe', env/'python.exe'):
        if candidate.is_file():
            python = candidate
            break
    else:
        if env.exists():
            raise ValueError('env existe sem Python valido; nao sera apagado ou recriado.')
        python = shutil.which('python')
        if not python:
            raise ValueError('Instale Python 3.10 a 3.12 e habilite seu PATH antes de continuar.')
        check_python(python)
        subprocess.run([python, '-m', 'venv', str(env)], check=True, cwd=root)
        python = env/'Scripts/python.exe'
        if not python.is_file():
            raise ValueError('Falha ao criar ambiente Windows. Nenhuma instalacao global sera feita.')
    check_python(python)
    return str(python)


def check_python(python):
    subprocess.run([str(python), '-c',
                    "import sys; assert (3,10)<=sys.version_info[:2]<(3,13), 'Use Python 3.10 a 3.12'"], check=True)


def working_tool(command):
    try:
        return subprocess.run([str(command), '-version'], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=15).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def ensure_ffmpeg(root, log=print):
    from nexus.media_tools import activate
    folder = activate(root)
    tools = [shutil.which(name) for name in ('ffmpeg', 'ffprobe')]
    if all(tool and working_tool(tool) for tool in tools):
        log('FFmpeg e ffprobe existentes verificados; download dispensado.')
        return
    log('Baixando FFmpeg e ffprobe para o ambiente local...')
    with tempfile.TemporaryDirectory(prefix='phoenix_ffmpeg_') as temp:
        archive = Path(temp)/'ffmpeg.zip'
        with urllib.request.urlopen(FFMPEG_URL + '.sha256', timeout=30) as response:
            checksum = response.read(4096).decode('ascii').split()[0]
        if not re.fullmatch(r'[a-fA-F0-9]{64}', checksum):
            raise ValueError('Checksum FFmpeg invalido; instalacao interrompida.')
        digest = hashlib.sha256()
        with urllib.request.urlopen(FFMPEG_URL, timeout=60) as response, archive.open('wb') as target:
            for chunk in iter(lambda: response.read(1024 * 1024), b''):
                digest.update(chunk)
                target.write(chunk)
        if digest.hexdigest().lower() != checksum.lower():
            raise ValueError('SHA-256 do FFmpeg diverge; nenhum binario foi instalado.')
        # Nao extrai caminhos do ZIP: copia apenas os dois binarios esperados.
        with zipfile.ZipFile(archive) as package:
            for name in ('ffmpeg.exe', 'ffprobe.exe'):
                matches = [p for p in package.namelist() if p.endswith('/bin/' + name)]
                if len(matches) != 1:
                    raise ValueError('Pacote FFmpeg incompleto: ' + name)
                target = Path(temp)/name
                with package.open(matches[0]) as source, target.open('wb') as output:
                    shutil.copyfileobj(source, output)
                if not working_tool(target):
                    raise ValueError('Binario FFmpeg nao executa neste Windows: ' + name)
        folder.mkdir(parents=True, exist_ok=True)
        for name in ('ffmpeg.exe', 'ffprobe.exe'):
            shutil.copy2(Path(temp)/name, folder/name)
    activate(root)
    log('FFmpeg e ffprobe instalados e verificados.')
