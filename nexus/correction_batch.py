"""Seleção global e envio agrupado, preservando a referência de cada fala."""
from collections import defaultdict
from flask import jsonify, request
from nexus.correction_service import CorrectionError
from nexus.correction_search import search_uploads


def register_batch_routes(blueprint):
    @blueprint.get('/selection')
    def selection():
        from nexus import correction_routes as routes
        original = request.args.get('original')
        if original is not None and not original.strip():
            raise CorrectionError('Esta fala não possui texto original.')
        return jsonify(search_uploads(routes.service, request.args.get('q', ''),
                       key=request.args.get('project_id') or None, limit=None, original=original))

    @blueprint.post('/enqueue-many')
    def enqueue_many():
        from nexus import correction_routes as routes
        items = routes.payload().get('items')
        if not isinstance(items, list) or not items:
            raise CorrectionError('Selecione ao menos uma fala.')
        grouped = defaultdict(list)
        seen = set()
        # Valida o conjunto antes de enfileirar. A revisão evita usar um rascunho
        # que foi alterado em outra janela depois da revisão do usuário.
        with routes.service.lock:
            for item in items:
                if not isinstance(item, dict):
                    raise CorrectionError('Seleção inválida.')
                key, sid = item.get('project_id'), item.get('segment_id')
                if not isinstance(key, str) or not isinstance(sid, str):
                    raise CorrectionError('Seleção inválida.')
                if (key, sid) in seen:
                    continue
                seen.add((key, sid))
                folder, _, _ = routes.service.segment(key, sid)
                draft = routes.service.drafts(folder).get(sid, {})
                if not draft.get('text', '').strip() or draft.get('revision') != item.get('revision'):
                    raise CorrectionError('Uma fala mudou. Atualize os resultados antes de enviar o grupo.')
                grouped[key].append(sid)
            snapshots = {key: [routes.service.enqueue(key, sid) for sid in ids]
                         for key, ids in grouped.items()}
        jobs, errors, staged = [], [], []
        for key, batch in snapshots.items():
            _, kind, _ = routes.service.project(key)
            if kind == 'video':
                staged.append(key)
                continue
            try:
                response, _ = routes.submit(key, lambda progress, k=key, b=batch:
                    routes.service.process_queue(k, progress=progress, snapshots=b), allow_queue=True, total=len(batch))
                jobs.append({'project_id': key, 'task_id': response.get_json()['task_id'], 'total': len(batch)})
            except CorrectionError as error:
                errors.append({'project_id': key, 'error': str(error)})
        return jsonify({'tasks': jobs, 'staged_video_projects': staged, 'errors': errors,
                        'count': len(seen), 'projects': len(grouped)})
