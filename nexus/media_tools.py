"""Localiza os binários de mídia instalados junto ao ambiente, sem mudar o Windows."""
import os
from pathlib import Path


def activate(root):
    folder = Path(root)/'env/ffmpeg/bin'
    if folder.is_dir() and str(folder) not in os.environ.get('PATH', '').split(os.pathsep):
        os.environ['PATH'] = str(folder) + os.pathsep + os.environ.get('PATH', '')
    return folder
