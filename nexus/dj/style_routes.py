"""Namespaced Style API, with constrained file access and server-owned projects."""
import re
import uuid
from pathlib import Path
from flask import request, jsonify, send_file, g
from werkzeug.utils import secure_filename

from nexus.json_io import safe_json_read
from nexus.dj.arranger import build_arrangement, compile_arrangement_abc, compile_yue2_request, qwen_enrich_prompt
from nexus.dj.style_analyzer.service import StyleService, parse_options
from nexus.dj.style_analyzer.store import TARGETS, contained, write_json


def register_style_routes(app, dj, uploads):
    service = StyleService(Path(uploads).parent, dj)
    app.extensions["nexus_styles"] = service

    # Covers the legacy DJ endpoints too; prevents clearing its busy flag during Style work.
    @app.before_request
    def protect_style_worker():
        if request.path in {
            "/api/init_session", "/api/stop_job", "/api/generate_music", "/api/master_song",
            "/api/ignite_mix", "/api/scan_tracks", "/api/transcribe_tracks"}:
            service.lock.acquire()
            g.style_admission_lock = True
            if service.active_id:
                return jsonify(error="Style Analyzer ocupado. Use o cancelamento do Analyzer."), 409

    @app.teardown_request
    def release_admission_lock(error):
        if g.pop("style_admission_lock", False):
            service.lock.release()

    def project(sid):
        if not re.fullmatch(r"[a-f0-9]{24}", sid):
            raise ValueError("ID inválido")
        return contained(service.projects, sid)

    @app.get("/api/styles")
    def list_styles():
        items = []
        for p in service.projects.glob("*/source.json"):
            data = safe_json_read(p) or {}
            state = safe_json_read(p.parent / "job_status.json") or {}
            items.append({"id": p.parent.name, "name": data.get("name", "Style"), **state})
        from nexus.dj.style_analyzer.adapters.sheetsage import availability
        return jsonify(items=items, active_id=service.active_id, sheetsage=availability(service.root))

    @app.post("/api/styles/analyze")
    def analyze():
        try:
            options = parse_options(request.form)
            name = request.form.get("name", "").strip() or "Meu Style"
            # Serialize admission with legacy routes for the duration of request handling.
            with service.lock:
                if service.active_id or dj.worker_busy or dj.generating_music:
                    return jsonify(error="Nexus DJ ocupado"), 409
                upload = request.files.get("audio")
                if not upload or not upload.filename:
                    return jsonify(error="Selecione uma música"), 400
                filename = secure_filename(upload.filename)
                if Path(filename).suffix.lower() not in {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}:
                    return jsonify(error="Formato não suportado"), 400
                folder = service.projects / "incoming"
                folder.mkdir(exist_ok=True)
                source = folder / (uuid.uuid4().hex + Path(filename).suffix.lower())
                # Stream with a bounded upload; reject rather than fill disk indefinitely.
                total = 0
                try:
                    with source.open("wb") as stream:
                        for chunk in iter(lambda: upload.stream.read(1024*1024), b""):
                            total += len(chunk)
                            if total > 128*1024*1024:
                                raise ValueError("Limite de arquivo: 128 MB")
                            stream.write(chunk)
                    sid = service.start(source, name, options)
                    saved = safe_json_read(service.projects / sid / "source.json") or {}
                    if saved.get("path") != str(source.resolve()):
                        source.unlink(missing_ok=True)  # Only this redundant upload, never the stored original.
                except Exception:
                    # Preserve a source already owned by a project for retry after spawn failure.
                    owned = any((safe_json_read(p) or {}).get("path") == str(source.resolve())
                                for p in service.projects.glob("*/source.json"))
                    if not owned:
                        source.unlink(missing_ok=True)
                    raise
            return jsonify(id=sid), 202
        except (ValueError, OSError) as exc:
            return jsonify(error=str(exc)), 400
        except RuntimeError as exc:
            return jsonify(error=str(exc)), 409

    @app.get("/api/styles/<sid>")
    def status(sid):
        try:
            p = project(sid)
        except ValueError:
            return jsonify(error="ID inválido"), 400
        state = safe_json_read(p / "job_status.json")
        if state is None:
            return jsonify(error="Style não encontrado"), 404
        return jsonify(**state, style=safe_json_read(p / "style.json") if state.get("status") == "completed" else None)

    @app.post("/api/styles/<sid>/cancel")
    def cancel(sid):
        if service.active_id != sid:
            return jsonify(error="Tarefa não está ativa"), 409
        service.cancel()
        return jsonify(status="cancelling")

    @app.get("/api/styles/<sid>/audio/<target>")
    def audio(sid, target):
        try:
            p = project(sid)
            if target not in (*TARGETS, "reference"):
                raise ValueError("Faixa inválida")
            state = safe_json_read(p / "job_status.json") or {}
            if state.get("status") != "completed":
                return jsonify(error="Análise ainda não concluída"), 409
            path = contained(p, "reference.wav" if target == "reference" else f"stems/{target}.wav")
            if not path.is_file():
                return jsonify(error="Faixa ausente"), 404
            return send_file(path, mimetype="audio/wav", conditional=True)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

    @app.get("/api/styles/<sid>/style.json")
    def download(sid):
        try:
            p = project(sid)
            if (safe_json_read(p / "job_status.json") or {}).get("status") != "completed":
                return jsonify(error="Style não disponível"), 409
            return send_file(p / "style.json", as_attachment=True, download_name="style.json")
        except ValueError:
            return jsonify(error="ID inválido"), 400

    @app.post("/api/styles/<sid>/arrangement")
    def create_arrangement(sid):
        try:
            p = project(sid)
            data = request.get_json(silent=True) or {}
            if not isinstance(data, dict):
                raise ValueError("O corpo JSON deve ser um objeto")
            with service.lock:
                if service.active_id or dj.worker_busy or dj.generating_music:
                    return jsonify(error="Nexus DJ ocupado"), 409
                if (safe_json_read(p / "job_status.json") or {}).get("status") != "completed":
                    return jsonify(error="Conclua a análise Style antes de planejar o arranjo"), 409
                style = safe_json_read(contained(p, "style.json"))
                if not isinstance(style, dict):
                    return jsonify(error="style.json ausente ou inválido"), 409
                song_plan = data.get("song") or {}
                arrangement = build_arrangement(style, seed=data.get("seed"), song_plan=song_plan)
                abc_text = compile_arrangement_abc(arrangement)
                write_json(contained(p, "arrangement.json"), arrangement)
                contained(p, "arrangement.abc").write_text(abc_text, encoding="utf-8")
            return jsonify(arrangement=arrangement,
                           abc_file=f"/api/styles/{sid}/arrangement.abc",
                           file=f"/api/styles/{sid}/arrangement.json"), 201
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except OSError as exc:
            return jsonify(error=f"Falha ao salvar arrangement.json: {exc}"), 500

    @app.get("/api/styles/<sid>/arrangement.json")
    def download_arrangement(sid):
        try:
            p = project(sid)
            if (safe_json_read(p / "job_status.json") or {}).get("status") != "completed":
                return jsonify(error="Style não disponível"), 409
            path = contained(p, "arrangement.json")
            if not path.is_file():
                return jsonify(error="Gere o arrangement antes de baixá-lo"), 404
            return send_file(path, as_attachment=True, download_name="arrangement.json")
        except ValueError:
            return jsonify(error="ID inválido"), 400

    @app.get("/api/styles/<sid>/arrangement.abc")
    def download_arrangement_abc(sid):
        try:
            p = project(sid)
            path = contained(p, "arrangement.abc")
            if not path.is_file():
                return jsonify(error="Gere o arrangement antes de baixar a partitura"), 404
            return send_file(path, as_attachment=True, download_name="arrangement.abc", mimetype="text/vnd.abc")
        except ValueError:
            return jsonify(error="ID inválido"), 400

    @app.post("/api/styles/<sid>/generate")
    def generate_from_arrangement(sid):
        """Preview by default; set dry_run=false to enter the existing generation worker."""
        try:
            p = project(sid)
            data = request.get_json(silent=True) or {}
            if not isinstance(data, dict):
                raise ValueError("O corpo JSON deve ser um objeto")
            if (safe_json_read(p / "job_status.json") or {}).get("status") != "completed":
                return jsonify(error="Conclua a análise Style antes de gerar"), 409
            arrangement = safe_json_read(contained(p, "arrangement.json"))
            if not isinstance(arrangement, dict):
                return jsonify(error="Gere arrangement.json antes de preparar a música"), 409
            abc_path = contained(p, "arrangement.abc")
            if not abc_path.is_file():
                abc_path.write_text(compile_arrangement_abc(arrangement), encoding="utf-8")
            compiled = compile_yue2_request(arrangement, abc_file=str(abc_path.resolve()))
            use_qwen = bool(data.get("use_qwen", False))
            dry_run = bool(data.get("dry_run", True))
            if use_qwen and dry_run:
                compiled["style_prompt"] = qwen_enrich_prompt(arrangement, compiled["style_prompt"])
                compiled["direct_controls"]["style"] = compiled["style_prompt"]
            from nexus.dj.yu_backend import YuE2Backend
            command = YuE2Backend().prepare_command(
                compiled["lyrics"], compiled["style_prompt"], compiled["target_tokens"], seed=1,
                abc_file=str(abc_path.resolve()), cot="full"
            )
            compiled["cli_command_preview"] = command
            compiled["qwen_used"] = use_qwen
            compiled["audio_generation_started"] = False
            compiled["worker_dispatched"] = False
            with service.lock:
                if service.active_id or dj.worker_busy or dj.generating_music:
                    return jsonify(error="Nexus DJ ocupado"), 409
                write_json(contained(p, "generation_preview.json"), compiled)
                if not dry_run:
                    dj.worker_busy = True
                    dj.generating_music = True
                    import threading
                    threading.Thread(
                        target=dj.run_music_generation_flow,
                        kwargs={"title": arrangement.get("name", "Nexus Arranger"),
                                "style": compiled["style_prompt"], "lyrics": compiled["lyrics"],
                                "duration": compiled["target_duration_seconds"], "batch_count": 1,
                                "arrangement": arrangement, "use_qwen": use_qwen,
                                "abc_file": str(abc_path.resolve())},
                        daemon=True,
                    ).start()
                    compiled["worker_dispatched"] = True
                    write_json(contained(p, "generation_preview.json"), compiled)
            return jsonify(request=compiled, dry_run=dry_run,
                           file=f"/api/styles/{sid}/generation_preview.json"), 200
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except OSError as exc:
            return jsonify(error=f"Falha ao preparar geração: {exc}"), 500

    @app.get("/api/styles/<sid>/generation_preview.json")
    def download_generation_preview(sid):
        try:
            p = project(sid)
            path = contained(p, "generation_preview.json")
            if not path.is_file():
                return jsonify(error="Prepare a geração antes de baixar o preview"), 404
            return send_file(path, as_attachment=True, download_name="generation_preview.json")
        except ValueError:
            return jsonify(error="ID inválido"), 400
