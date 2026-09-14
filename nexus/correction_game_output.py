"""Destino adicional dentro de uploads; nunca escreve na instalação do jogo."""
import os
import shutil
import uuid
from pathlib import PureWindowsPath
from nexus.correction_service import read_json, safe_name, local_file, CorrectionError

GAME_NAMES = {'state_of_decay': 'State of Decay', 'cod': 'Call of Duty', 'xcom': 'XCOM'}


def declared_game(status):
    return status.get('game_name') or GAME_NAMES.get(status.get('game_profile'))


def game_destination(service, folder):
    status = read_json(folder / 'job_status.json', {})
    game = declared_game(status)
    source = status.get('original_folder_path')
    # Projetos antigos, como SAM, não têm game_name. Só inferimos quando
    # projetos da mesma pasta de origem concordam sobre um único jogo.
    if not game and source:
        parent = str(PureWindowsPath(source).parent).casefold()
        candidates = set()
        for path in service.uploads.glob('*/job_status.json'):
            try:
                other = read_json(path, {})
                origin = other.get('original_folder_path')
                name = declared_game(other)
                if name and origin and str(PureWindowsPath(origin).parent).casefold() == parent:
                    candidates.add(name)
            except (OSError, ValueError, TypeError):
                continue
        if len(candidates) == 1:
            game = candidates.pop()
    character = status.get('original_folder_name') or (PureWindowsPath(source).name if source else None) or status.get('project_name')
    if not game or not character:
        return None
    # Layout aprovado pelo usuário para este jogo. Outros jogos precisam
    # de sua própria regra antes de receber a cópia adicional de correções.
    if game.casefold() != 'state of decay':
        return None
    root = local_file(service.uploads, service.uploads / safe_name(game))
    if (root / 'project_data.json').exists():
        raise CorrectionError('O destino do jogo coincide com uma pasta de trabalho.')
    return local_file(service.uploads, root / safe_name(character))


def atomic_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
