"""Cópia da dublagem completa; layout específico de State of Decay."""
import logging
from pathlib import Path
from nexus.correction_service import CorrectionService, read_json, write_json, local_file
from nexus.correction_game_output import GAME_NAMES, declared_game, game_destination, atomic_copy


def copy_full_output(job_dir, job_id):
    job_dir = Path(job_dir).resolve()
    final = job_dir / '_saida_final'
    if not final.is_dir():
        return 0, None
    status_path = job_dir / 'job_status.json'
    status = read_json(status_path, {})
    if (declared_game(status) or '').casefold() == 'state of decay':
        service = CorrectionService(job_dir.parent.parent)
        target = game_destination(service, job_dir)
        if target is None:
            raise ValueError('Informe a pasta original do personagem antes de exportar State of Decay.')
    else:
        # Mantém o comportamento anterior para outros jogos. Não aplica
        # a organização de personagens de State of Decay a eles.
        game = Path(str(status.get('game_name') or GAME_NAMES.get(status.get('game_profile'), 'Jogo sem nome'))).name
        project = Path(str(status.get('project_name') or status.get('original_folder_name') or job_id)).name
        game = game if game not in ('', '.', '..') else 'Jogo sem nome'
        project = project if project not in ('', '.', '..') else job_id
        target = local_file(job_dir.parent, job_dir.parent / game / project)
    count = 0
    for source in final.rglob('*'):
        if not source.is_file():
            continue
        local_file(final, source)
        destination = local_file(target, target / source.relative_to(final))
        atomic_copy(source, destination)
        count += 1
    # Lê novamente para preservar atualizações de progresso durante a cópia.
    status = read_json(status_path, {})
    status.update(consolidated_output_path=str(target), consolidated_output_files=count)
    write_json(status_path, status)
    logging.info('[SAIDA_CONSOLIDADA] %s arquivo(s) copiado(s) para %s', count, target)
    return count, target
