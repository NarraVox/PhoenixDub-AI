"""API do painel compartilhado de correção de dublagens."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading

from flask import Blueprint, jsonify, request, send_file
from nexus.correction_service import CorrectionService, CorrectionError
from nexus.correction_search import search_uploads

correction_blueprint = Blueprint("corrections", __name__, url_prefix="/api/corrections")
import sys
service = CorrectionService(Path(sys.executable).parent if getattr(sys, 'frozen', False)
                            else Path(__file__).resolve().parents[1])
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="correction")
tasks = {}
task_lock = threading.Lock()


def busy():
    with task_lock:
        return any(t["status"] in {"queued", "running"} for t in tasks.values())


@correction_blueprint.errorhandler(CorrectionError)
def invalid_request(exc):
    return jsonify({"error": str(exc)}), 400


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise CorrectionError("Envie um objeto JSON válido.")
    return data


def project_id(data):
    key = data.get("project_id")
    if not isinstance(key, str):
        raise CorrectionError("Selecione um projeto.")
    service.project(key)
    return key


def submit(key, action, allow_queue=False, total=0):
    import sys
    from nexus.correction_jobs import submit as submit_job
    return submit_job(sys.modules[__name__], key, action, allow_queue, total)


@correction_blueprint.get("/projects")
def projects():
    return jsonify(service.discover())


@correction_blueprint.get("/segments")
def segments():
    key = request.args.get("project_id") or None
    try:
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        raise CorrectionError("Página inválida.")
    return jsonify(search_uploads(service, request.args.get("q", ""), offset, key))


@correction_blueprint.post("/preview")
def preview():
    data = payload()
    key = project_id(data)
    sid, text = data.get("segment_id"), data.get("text")
    if not isinstance(sid, str) or not isinstance(text, str):
        raise CorrectionError("Informe a fala e a tradução corrigida.")
    service.segment(key, sid)
    return submit(key, lambda progress: service.preview(key, sid, text))


@correction_blueprint.post("/apply")
def apply():
    data = payload()
    key = project_id(data)
    token = data.get("token")
    if not isinstance(token, str):
        raise CorrectionError("Gere e ouça uma prévia antes de salvar.")
    if busy():
        raise CorrectionError("Aguarde o processamento atual terminar.")
    return jsonify(service.apply(key, token))


@correction_blueprint.post("/export")
def export():
    key = project_id(payload())
    return submit(key, lambda progress: service.export(key))


@correction_blueprint.post("/draft")
def draft():
    data = payload()
    key = project_id(data)
    sid = data.get("segment_id")
    if not isinstance(sid, str):
        raise CorrectionError("Selecione uma fala.")
    return jsonify(service.save_draft(key, sid, data.get("text"), data.get("revision")))


@correction_blueprint.get("/queue")
def queue():
    return jsonify(service.queue(project_id(request.args)))


@correction_blueprint.post("/enqueue")
def enqueue():
    data = payload()
    key = project_id(data)
    sid = data.get("segment_id")
    if not isinstance(sid, str):
        raise CorrectionError("Selecione uma fala.")
    snapshot = service.enqueue(key, sid)
    _, kind, _ = service.project(key)
    if kind == "games":
        # O texto fica em disco mesmo se houver uma tarefa incompatível na GPU.
        return submit(key, lambda progress: service.process_queue(key, sid, progress, [snapshot]), allow_queue=True, total=1)
    return jsonify({"message": "Fala salva na fila. Clique em Iniciar quando terminar as correções."})


@correction_blueprint.post("/start")
def start():
    data = payload()
    key = project_id(data)
    sid = data.get("segment_id")
    if sid is not None:
        if not isinstance(sid, str):
            raise CorrectionError("Identificador inválido.")
        service.segment(key, sid)
    _, kind, _ = service.project(key)
    folder, _, _ = service.project(key)
    pending = [d['queued'] for d in service.drafts(folder).values() if d.get('queued')
               and d['queued'].get('status') != 'done' and (sid is None or d['segment_id'] == sid)]
    return submit(key, lambda progress: service.process_queue(key, sid, progress, pending),
                  allow_queue=kind == "games", total=len(pending))


@correction_blueprint.get("/tasks/<token>")
def task_status(token):
    with task_lock:
        task = tasks.get(token)
        if not task:
            return jsonify({"error": "Tarefa não encontrada. O servidor pode ter sido reiniciado."}), 404
        return jsonify(task)


@correction_blueprint.get("/audio")
def audio():
    key = project_id(request.args)
    token = request.args.get("token")
    if token:
        path, _ = service.preview_file(key, token)
    else:
        folder, kind, seg = service.segment(key, request.args.get("segment_id", ""))
        path = service.audio(folder, kind, seg)
    return send_file(path, conditional=True, max_age=0)


from nexus.correction_batch import register_batch_routes
register_batch_routes(correction_blueprint)
