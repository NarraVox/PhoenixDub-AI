"""Instala arquivos do programa empacotados, preservando dados e configurações."""
from pathlib import Path
import sys
import zipfile
from nexus.update_worker import allowed_path, development_copy


def deploy_runtime(destination, overwrite=False):
    root = Path(destination).resolve()
    bundle = Path(getattr(sys, '_MEIPASS', root)) / 'runtime.zip'
    if not bundle.is_file():
        raise FileNotFoundError('Pacote de código do aplicativo não encontrado.')
    if development_copy(root):
        if overwrite:
            raise ValueError('Instalação sobre uma cópia de desenvolvimento bloqueada.')
        return
    with zipfile.ZipFile(bundle) as archive:
        for item in archive.infolist():
            name = item.filename
            is_config = name == 'nexus/core/server_config.json'
            if not allowed_path(name) and not is_config and name != 'vpk_manager.py':
                raise ValueError('Arquivo inesperado no pacote do programa.')
            target = root/name
            if not target.resolve().is_relative_to(root):
                raise ValueError('Destino fora da instalação.')
            if target.exists() and (not overwrite or is_config):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + '.install-tmp')
            temporary.write_bytes(archive.read(item))
            temporary.replace(target)
