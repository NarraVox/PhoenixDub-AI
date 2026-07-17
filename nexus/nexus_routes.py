# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import os
import sys
import time
import logging
import json
import requests
import subprocess
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, send_from_directory, send_file, Response

import nexus.core.security as security
from nexus.core.utils import safe_json_read, safe_json_write

# Configurações de Diretório vindas do Core de Segurança
UPLOAD_FOLDER = security.UPLOAD_FOLDER
TEMP_DIR = security.BASE_DIR / "uploads" / "_NEXUS_TEMP_"
CLIENT_DIR = str((security.BASE_DIR / "client").resolve())

nexus_blueprint = Blueprint('nexus_routes', __name__)

# --- REFERÊNCIAS DE MOTORES (Compartilhados com nexus_app) ---
# Serão inicializados ou passados pelo nexus_app.py no dicionário global de motores
active_engines = {}
running_processes = []
engine_switch_lock = None

def init_routes(engines_dict, processes_list, switch_lock):
    """Inicializa as referências compartilhadas do Hub."""
    global active_engines, running_processes, engine_switch_lock
    active_engines.update(engines_dict)
    running_processes.extend(processes_list)
    engine_switch_lock = switch_lock

def is_engine_busy(name):
    engine = active_engines.get(name)
    if not engine: return False
    p = engine["process"]
    if p is None or p.poll() is not None:
        return False
    try:
        url = f"http://127.0.0.1:{engine['port']}/api/is_busy"
        res = requests.get(url, timeout=0.5)
        if res.status_code == 200:
            return res.json().get("busy", False)
    except Exception:
        pass
    return False

# --- ROTAS DO HUB ---

@nexus_blueprint.route('/stream_media')
def stream_media():
    path = request.args.get('path')
    if not path: return "Caminho ausente", 400

    # Limpeza básica do caminho para verificação
    path_clean = path.replace('file:///', '').replace('file://', '').replace('/', os.sep)
    if path_clean.startswith(os.sep) and len(path_clean) > 2 and path_clean[2] == ':':
        path_clean = path_clean[1:]
    path_clean = path_clean.replace('"', '').replace("'", "").strip()

    # [v2026.PATH_SMART] Se for apenas um nome de arquivo, tenta achar na pasta de uploads
    if os.sep not in path_clean and ':' not in path_clean:
        potential_path = UPLOAD_FOLDER / path_clean
        if potential_path.exists():
            path_clean = str(potential_path.absolute())

    # --- PROTEÇÃO CONTRA PATH TRAVERSAL (SEGURANÇA CRÍTICA) ---
    if not security.is_safe_path(path_clean):
        logging.warning(f"❌ [SEGURANÇA] Bloqueado acesso a caminho não autorizado: {path_clean}")
        return "Acesso negado: Caminho não autorizado.", 403

    if not os.path.exists(path_clean):
        # Tenta procurar recursivamente em uploads se ainda não achou
        found = False
        if UPLOAD_FOLDER.exists():
             for root, dirs, files in os.walk(UPLOAD_FOLDER):
                  if path_clean in files:
                      path_clean = os.path.join(root, path_clean)
                      found = True
                      break
        if not found:
             # Tenta decodificar espaços
             import urllib.parse
             path_clean = urllib.parse.unquote(path_clean)
             if not os.path.exists(path_clean):
                 logging.error(f"❌ [STREAM] Arquivo NÃO encontrado: {path_clean}")
                 return f"Arquivo inexistente: {path_clean}", 404

    # Detecta Mime Type dinamicamente
    import mimetypes
    mime, _ = mimetypes.guess_type(path_clean)
    if not mime: mime = 'video/mp4' # Fallback

    file_size = os.path.getsize(path_clean)
    range_header = request.headers.get('Range', None)

    if range_header:
        try:
            byte_range = range_header.replace('bytes=', '').split('-')
            start = int(byte_range[0])
            end = int(byte_range[1]) if byte_range[1] else file_size - 1

            length = end - start + 1
            if length > 1024 * 1024 * 2: # Max 2MB por chunk
                length = 1024 * 1024 * 2
                end = start + length - 1

            with open(path_clean, 'rb') as f:
                f.seek(start)
                data = f.read(length)

            rv = Response(data, 206, mimetype=mime, content_type=mime)
            rv.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
            rv.headers.add('Accept-Ranges', 'bytes')
            return rv
        except Exception as e:
            logging.error(f"⚠️ [STREAM] Falha no Range: {e}")

    return send_file(path_clean, mimetype=mime, conditional=True)

@nexus_blueprint.route('/api/engine_status')
def api_engine_status():
    status_map = {}
    for name, engine in active_engines.items():
        p = engine["process"]
        if p is None or p.poll() is not None:
            status_map[str(engine["port"])] = "standby"
        else:
            if is_engine_busy(name):
                status_map[str(engine["port"])] = "busy"
            else:
                status_map[str(engine["port"])] = "running"
    return jsonify(status_map)

@nexus_blueprint.route('/')
def serve_hub():
    from nexus.nexus_app import switch_active_engine
    import threading
    threading.Thread(target=switch_active_engine, args=("hub",), daemon=True).start()
    return send_from_directory(CLIENT_DIR, 'nexus_premium.html')

@nexus_blueprint.route('/api/restart_motors')
@nexus_blueprint.route('/api/restart_server', methods=['GET', 'POST'])
def restart_motors():
    print("\n" + "!"*20)
    print("  [CRITICAL] REINICIALIZAÇÃO TOTAL DOS SISTEMAS...")
    print("  Encerrando motores e limpando CPU...")
    print("" + "!"*20 + "\n")

    # 1. Encerramento de processos em active_engines
    for name, engine in active_engines.items():
        p = engine["process"]
        if p is not None and p.poll() is None:
            try:
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(p.pid)], capture_output=True)
            except:
                try: p.terminate()
                except: pass
            engine["process"] = None

    # 2. Encerramento de processos filhos e netos
    for p in running_processes:
        try:
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(p.pid)], capture_output=True)
        except:
            try: p.terminate()
            except: pass
    running_processes.clear()

    time.sleep(1)
    os.execv(sys.executable, ['python'] + sys.argv)
    return jsonify({"success": True, "message": "Reinicialização total disparada!"})

@nexus_blueprint.route('/api/clear_cache', methods=['POST'])
def api_clear_cache():
    try:
        data = request.get_json() or {}
        job_id = data.get('job_id')
        if not job_id:
            return jsonify({"success": False, "message": "Nenhum projeto selecionado."})

        project_dir = UPLOAD_FOLDER / job_id
        if not project_dir.exists():
            return jsonify({"success": False, "message": f"Projeto {job_id} não encontrado."})

        count = 0
        for folder_name in ["_backup_transcricao", "_backup_texto_final", "_dubbed_audio", "_dubbed_segments"]:
            p = project_dir / folder_name
            if p.exists() and p.is_dir():
                import shutil
                shutil.rmtree(p, ignore_errors=True)
                count += 1
        return jsonify({"success": True, "message": f"Limpeza concluída para o projeto {job_id}."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro ao limpar cache: {str(e)}"})

@nexus_blueprint.route('/api/list_project_files')
def list_project_files():
    files = []
    if UPLOAD_FOLDER.exists():
        for f in os.listdir(UPLOAD_FOLDER):
            path = UPLOAD_FOLDER / f
            if os.path.isfile(path):
                files.append({
                    "name": f,
                    "path": str(path.absolute()),
                    "type": "video" if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')) else "audio",
                    "date": datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
            elif os.path.isdir(path) and f.startswith('video_') and (path / "job_status.json").exists():
                files.append({
                    "name": f,
                    "path": str(path.absolute()),
                    "type": "folder",
                    "date": datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
    return jsonify(files)

@nexus_blueprint.route('/<path:filename>')
def serve_pages(filename):
    if not filename.endswith('.html'):
        if os.path.exists(os.path.join(CLIENT_DIR, filename + '.html')):
            filename += '.html'

    page_to_engine = {
        "video_studio.html": "video",
        "games_studio.html": "games",
        "vortex_editor.html": "editor",
        "dj_studio.html": "dj",
        "nexus_premium.html": "hub"
    }

    target_engine = page_to_engine.get(filename)
    if target_engine:
        from nexus.nexus_app import switch_active_engine
        import threading
        threading.Thread(target=switch_active_engine, args=(target_engine,), daemon=True).start()

    return send_from_directory(CLIENT_DIR, filename)

@nexus_blueprint.route('/api/list_vortex_projects')
def list_vortex_projects():
    projects = []
    dj_projects_dir = UPLOAD_FOLDER / "dj_projects"
    if dj_projects_dir.exists():
        for d in dj_projects_dir.iterdir():
            if d.is_dir():
                status_file = d / "job_status.json"
                if status_file.exists():
                    try:
                        with open(status_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            track_count = len(data.get("tracks", {}))
                            mix_count = len(data.get("completed_mixes", []))
                            projects.append({
                                "id": d.name,
                                "type": "vortex_dj",
                                "status": "completed" if mix_count > 0 else "in_progress",
                                "tracks": track_count,
                                "last_mod": time.ctime(status_file.stat().st_mtime)
                            })
                    except: pass
    return jsonify(projects)

@nexus_blueprint.route('/api/security_audit')
def security_audit():
    try:
        pip_path = os.path.join(os.getcwd(), 'env', 'Scripts', 'pip.exe')
        if not os.path.exists(pip_path):
            return jsonify({"status": "error", "message": "Ambiente virtual não detectado."})

        subprocess.run([pip_path, "install", "pip-audit", "--quiet"], check=True)
        audit_path = os.path.join(os.getcwd(), 'env', 'Scripts', 'pip-audit.exe')
        result = subprocess.run([audit_path, "--format", "json"], capture_output=True, text=True)

        if result.returncode == 0:
            return jsonify({
                "status": "safe",
                "message": "Nenhum perigo detectado. Todas as bibliotecas estão seguras!",
                "details": json.loads(result.stdout) if result.stdout else []
            })
        else:
            vulnerabilities = json.loads(result.stdout) if result.stdout else []
            return jsonify({
                "status": "danger",
                "message": f"ALERTA: Detectadas {len(vulnerabilities)} vulnerabilidades!",
                "details": vulnerabilities
            })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao auditar: {str(e)}"})

@nexus_blueprint.route('/api/security_repair', methods=['POST'])
def security_repair():
    try:
        pip_path = os.path.join(os.getcwd(), 'env', 'Scripts', 'pip.exe')
        target_req = "requirements_CPU.txt"
        process = subprocess.run([pip_path, "install", "--force-reinstall", "-r", target_req],
                                capture_output=True, text=True)

        if process.returncode == 0:
            return jsonify({"status": "success", "message": "Reparo concluído!"})
        else:
            return jsonify({"status": "error", "message": "Falha no auto-reparo."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro no motor de reparo: {str(e)}"})

@nexus_blueprint.route('/recent_jobs')
def recent_jobs():
    jobs = []
    upload_path = UPLOAD_FOLDER.resolve()
    if not upload_path.exists():
        return jsonify([])

    try:
        dirs = sorted([d for d in upload_path.iterdir() if d.is_dir()],
                      key=lambda x: x.stat().st_mtime, reverse=True)
        for d in dirs:
            status_file = d / "job_status.json"
            if status_file.exists():
                try:
                    with open(status_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if data:
                        jobs.append({
                            'id': data.get('job_id', d.name),
                            'status': data.get('status', 'unknown'),
                            'progress': data.get('progress', 0),
                            'etapa': data.get('etapa', 'Projeto Detectado'),
                            'file_count': data.get('file_count', 0),
                            'date': datetime.fromtimestamp(d.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        })
                except: pass
            if len(jobs) >= 10: break
    except Exception as e:
        print(f"[ERRO LISTAGEM] {e}")

    return jsonify(jobs)
