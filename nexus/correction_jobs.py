"""Execução serial das correções de voz."""
import uuid
import time
from flask import jsonify
from nexus.correction_service import CorrectionError

def submit(routes, key, action, allow_queue=False, total=0):
    # Geração e exportação não concorrem entre si nem com uma dublagem ativa.
    from nexus.nexus_routes import is_engine_busy
    if any(is_engine_busy(name) for name in ("games", "video", "editor", "dj")):
        raise CorrectionError("Aguarde a tarefa de dublagem atual terminar antes de corrigir.")
    with routes.task_lock:
        active = [t for t in routes.tasks.values() if t["status"] in {"queued", "running"}]
        if active and (not allow_queue or any(not t.get("allow_queue") for t in active)):
            raise CorrectionError("Já existe uma correção em processamento. Aguarde a conclusão.")
        # Resultados concluídos ficam disponíveis para retomar o polling após fechar o painel.
        if len(routes.tasks) >= 100:
            completed = next((key for key, task in routes.tasks.items() if task["status"] not in {"queued", "running"}), None)
            if completed:
                routes.tasks.pop(completed)
            else:
                raise CorrectionError("Fila cheia. Aguarde algumas falas terminarem.")
        token = uuid.uuid4().hex
        routes.tasks[token] = {"status": "queued", "project_id": key, "allow_queue": allow_queue,
                               "progress": {'total': total, 'completed': 0, 'failed': 0, 'current': None, 'stage': 'queued'},
                               "logs": [{'sequence': 1, 'time': time.time(), 'message': 'Aguardando na fila.'}]}

    def progress(update):
        with routes.task_lock:
            task = routes.tasks[token]
            if isinstance(update, dict):
                task['progress'].update({k: v for k, v in update.items() if k != 'message'})
                message = update['message']
            else:
                message = str(update)
            task['message'] = message
            sequence = task['logs'][-1]['sequence'] + 1
            task['logs'].append({'sequence': sequence, 'time': time.time(), 'message': message})
            task['logs'] = task['logs'][-200:]

    def run():
        with routes.task_lock:
            routes.tasks[token]["status"] = "running"
        try:
            progress('Iniciando processamento do projeto.')
            result = action(progress)
            progress({'message': result.get('message', 'Processamento concluído.'), 'current': None, 'stage': 'finished'})
            with routes.task_lock:
                routes.tasks[token].update(status="done", result=result)
        except Exception as exc:
            progress({'message': 'Erro: ' + str(exc), 'current': None, 'stage': 'error'})
            with routes.task_lock:
                routes.tasks[token].update(status="error", error=str(exc))

    routes.executor.submit(run)
    return jsonify({"task_id": token, "total": total}), 202
