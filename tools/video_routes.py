# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from flask import Blueprint, jsonify, request

import tools.video_services as services

logger = logging.getLogger("AiderDashboard.VideoRoutes")
video_routes = Blueprint('video_routes', __name__)

@video_routes.route("/api/video_copilot/save_paths", methods=["POST"])
def api_video_copilot_save_paths():
    data = request.json
    if not data or not data.get("video_path"):
        return jsonify({"success": False, "error": "Caminho do vídeo inválido"}), 400
        
    video_path = data.get("video_path")
    video_path_obj = Path(video_path)
    base_name = video_path_obj.stem
    
    project_folder_path = Path("C:/IA_dublagem/uploads") / f"video_{base_name}"
    project_folder_path.mkdir(parents=True, exist_ok=True)
    project_folder = str(project_folder_path.resolve())
    output_path = str((project_folder_path / f"{base_name}_editado.mp4").resolve())
    
    config_dir = services.ROOT_DIR / "scratch"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "video_editor_config.json"
    
    config_data = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except: pass
            
    duration = 0.0
    try:
        ffprobe_bin = r"C:\IA_dublagem\env\Library\bin\ffprobe.exe"
        if not os.path.exists(ffprobe_bin):
            ffprobe_bin = "ffprobe"
            
        cmd = [ffprobe_bin, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        if result.returncode == 0:
            duration = float(result.stdout.strip())
    except Exception as e:
        logger.error(f"Erro no ffprobe para obter duração: {e}")

    config_data["video_path"] = video_path
    config_data["output_path"] = output_path
    config_data["project_folder"] = project_folder
    config_data["transcribe_output_path"] = str((project_folder_path / "transcricao_video.txt").resolve())
    config_data["video_duration"] = duration
    
    if "options" in data:
        config_data["options"] = data["options"]
        
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@video_routes.route("/api/video_copilot/transcribe", methods=["POST"])
def api_video_copilot_transcribe():
    if services.transcribe_process is not None and services.transcribe_process.poll() is None:
        return jsonify({"success": False, "error": "Transcrição em andamento!"}), 400
        
    try: services.TRANSCRIBE_LOG.write_text("", encoding="utf-8")
    except: pass
    
    python_bin = sys.executable
    script_path = str(services.ROOT_DIR / "scratch" / "transcrever_video.py")
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    try:
        log_file = open(services.TRANSCRIBE_LOG, "w", encoding="utf-8")
        services.transcribe_process = subprocess.Popen(
            [python_bin, "-u", script_path],
            stdout=log_file, stderr=subprocess.STDOUT,
            creationflags=creationflags
        )
        return jsonify({"success": True, "msg": "Transcrição iniciada!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@video_routes.route("/api/video_copilot/render", methods=["POST"])
def api_video_copilot_render():
    if services.render_process is not None and services.render_process.poll() is None:
        return jsonify({"success": False, "error": "Renderização em andamento!"}), 400
        
    try: services.RENDER_LOG.write_text("", encoding="utf-8")
    except: pass
    
    python_bin = sys.executable
    script_path = str(services.ROOT_DIR / "scratch" / "editar_video_profissional.py")
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    try:
        log_file = open(services.RENDER_LOG, "w", encoding="utf-8")
        services.render_process = subprocess.Popen(
            [python_bin, "-u", script_path],
            stdout=log_file, stderr=subprocess.STDOUT,
            creationflags=creationflags
        )
        return jsonify({"success": True, "msg": "Renderização iniciada!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@video_routes.route("/api/video_copilot/stop", methods=["POST"])
def api_video_copilot_stop():
    stopped_any = False
    for name, p in [("Transcrição", services.transcribe_process), ("Renderização", services.render_process)]:
        if p is not None and p.poll() is None:
            try:
                p.terminate()
                p.wait(timeout=2)
                stopped_any = True
            except: pass
            
    services.transcribe_process = None
    services.render_process = None
    return jsonify({"success": True, "stopped": stopped_any})

@video_routes.route("/api/video_copilot/status", methods=["GET"])
def api_video_copilot_status():
    transcribe_running = services.transcribe_process is not None and services.transcribe_process.poll() is None
    render_running = services.render_process is not None and services.render_process.poll() is None
    
    config_file = services.ROOT_DIR / "scratch" / "video_editor_config.json"
    current_config = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                current_config = json.load(f)
        except: pass
            
    transcript_path = current_config.get("transcribe_output_path")
    transcript_file = Path(transcript_path) if transcript_path else services.ROOT_DIR / "scratch" / "transcricao_video.txt"
    
    job_status = {}
    project_folder = current_config.get("project_folder")
    if project_folder:
        job_status_file = Path(project_folder) / "job_status.json"
        if job_status_file.exists():
            try:
                with open(job_status_file, "r", encoding="utf-8") as f:
                    job_status = json.load(f)
            except: pass
        
    return jsonify({
        "transcribe_running": transcribe_running,
        "render_running": render_running,
        "config_exists": config_file.exists(),
        "transcript_exists": transcript_file.exists(),
        "current_config": current_config,
        "job_status": job_status
    })

@video_routes.route("/api/video_copilot/logs", methods=["GET"])
def api_video_copilot_logs():
    transcribe_lines = []
    render_lines = []
    
    if services.TRANSCRIBE_LOG.exists():
        try:
            with open(services.TRANSCRIBE_LOG, "r", encoding="utf-8", errors="replace") as f:
                transcribe_lines = f.readlines()[-150:]
        except Exception as e:
            transcribe_lines = [f"Erro transcrição: {e}"]
            
    if services.RENDER_LOG.exists():
        try:
            with open(services.RENDER_LOG, "r", encoding="utf-8", errors="replace") as f:
                render_lines = f.readlines()[-150:]
        except Exception as e:
            render_lines = [f"Erro renderização: {e}"]
            
    return jsonify({
        "transcribe_log": "".join(transcribe_lines),
        "render_log": "".join(render_lines)
    })

@video_routes.route("/api/video_copilot/transcript", methods=["GET"])
def api_video_copilot_transcript():
    config_file = services.ROOT_DIR / "scratch" / "video_editor_config.json"
    current_config = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                current_config = json.load(f)
        except: pass
            
    transcript_path = current_config.get("transcribe_output_path")
    transcript_file = Path(transcript_path) if transcript_path else services.ROOT_DIR / "scratch" / "transcricao_video.txt"
        
    if not transcript_file.exists():
        return jsonify({"success": False, "error": "Nenhuma transcrição encontrada."}), 404
        
    try:
        content = transcript_file.read_text(encoding="utf-8", errors="replace")
        return jsonify({"success": True, "content": content})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@video_routes.route("/api/video_copilot/chat_history", methods=["GET"])
def api_video_copilot_get_chat():
    config_file = services.ROOT_DIR / "scratch" / "video_editor_config.json"
    current_config = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                current_config = json.load(f)
        except: pass
            
    project_folder = current_config.get("project_folder")
    if not project_folder:
        return jsonify({"success": True, "history": []})
        
    chat_file = Path(project_folder) / "chat_history.json"
    if not chat_file.exists():
        return jsonify({"success": True, "history": []})
        
    try:
        with open(chat_file, "r", encoding="utf-8") as f:
            history = json.load(f)
        return jsonify({"success": True, "history": history})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@video_routes.route("/api/video_copilot/chat_history", methods=["POST"])
def api_video_copilot_save_chat():
    data = request.json
    if not data or "message" not in data:
        return jsonify({"success": False, "error": "Mensagem inválida"}), 400
        
    config_file = services.ROOT_DIR / "scratch" / "video_editor_config.json"
    current_config = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                current_config = json.load(f)
        except: pass
            
    project_folder = current_config.get("project_folder")
    if not project_folder:
        return jsonify({"success": False, "error": "Projeto não selecionado"}), 400
        
    chat_file = Path(project_folder) / "chat_history.json"
    history = []
    if chat_file.exists():
        try:
            with open(chat_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except: pass
            
    history.append(data["message"])
    
    try:
        with open(chat_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@video_routes.route("/api/video_copilot/clear_chat", methods=["POST"])
def api_video_copilot_clear_chat():
    config_file = services.ROOT_DIR / "scratch" / "video_editor_config.json"
    current_config = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                current_config = json.load(f)
        except: pass
            
    project_folder = current_config.get("project_folder")
    if not project_folder:
        return jsonify({"success": False, "error": "Projeto não selecionado"}), 400
        
    chat_file = Path(project_folder) / "chat_history.json"
    if chat_file.exists():
        try:
            chat_file.unlink()
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True})
