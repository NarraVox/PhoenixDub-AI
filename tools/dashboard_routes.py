# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from flask import Blueprint, jsonify, request

import tools.video_services as services

logger = logging.getLogger("AiderDashboard.MainRoutes")
dashboard_routes = Blueprint('dashboard_routes', __name__)

@dashboard_routes.route("/api/status", methods=["GET"])
def api_status():
    config = services.load_config()
    server_alive = services.server_process is not None and services.server_process.poll() is None
    aider_alive = services.aider_process is not None and services.aider_process.poll() is None
    port_responsive = services.check_server_online(config.get("host", "127.0.0.1"), config.get("port", 1234))
    
    loaded_model_name = "Nenhum"
    if port_responsive:
        try:
            import requests
            res = requests.get(f"http://{config.get('host')}:{config.get('port')}/v1/models", timeout=1)
            data = res.json()
            if data and "data" in data and len(data["data"]) > 0:
                loaded_model_name = Path(data["data"][0]["id"]).name
        except:
            if config.get("model_path"):
                loaded_model_name = Path(config["model_path"]).name
    
    return jsonify({
        "server_running": server_alive,
        "aider_running": aider_alive,
        "port_responsive": port_responsive,
        "loaded_model": loaded_model_name,
        "config": config,
        "stats": services.get_system_stats()
    })

@dashboard_routes.route("/api/models", methods=["GET"])
def api_models():
    return jsonify({"models": services.get_models_list()})

@dashboard_routes.route("/api/save_config", methods=["POST"])
def api_save_config():
    config_data = request.json
    if not config_data:
        return jsonify({"success": False, "error": "No data received"}), 400
    success = services.save_config(config_data)
    return jsonify({"success": success})

@dashboard_routes.route("/api/start", methods=["POST"])
def api_start():
    config = services.load_config()
    host = config.get("host", "127.0.0.1")
    port = config.get("port", 1234)
    model_path = config.get("model_path")
    
    if not model_path or not os.path.exists(model_path):
        return jsonify({"success": False, "error": "Arquivo do modelo selecionado não existe!"}), 400
    
    server_already_online = services.check_server_online(host, port)
    
    if services.aider_process is not None:
        try:
            logger.info("Terminating existing Aider process...")
            services.aider_process.terminate()
            services.aider_process.wait(timeout=2)
        except: pass
        services.aider_process = None
        
    if server_already_online:
        logger.info("Server is already online. Skipping server start.")
        online = True
    else:
        if services.server_process is not None and services.server_process.poll() is None:
            logger.info("Server process exists but port not responsive. Restarting...")
            services.stop_processes()
            time.sleep(1)
            
        logger.info(f"Starting local server with model: {model_path}")
        python_bin = sys.executable
        server_script = str(services.ROOT_DIR / "tools" / "run_local_server.py")
        server_log_file = open(services.SERVER_LOG, "w", encoding="utf-8")
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        
        services.server_process = subprocess.Popen(
            [python_bin, server_script],
            stdout=server_log_file,
            stderr=subprocess.STDOUT,
            creationflags=creationflags
        )
        
        logger.info("Waiting for llama-server to initialize...")
        online = False
        for _ in range(45):
            if services.server_process.poll() is not None:
                server_log_file.close()
                log_content = services.SERVER_LOG.read_text(encoding="utf-8")
                return jsonify({
                    "success": False, 
                    "error": "O servidor de IA falhou ao iniciar.",
                    "log": log_content[-1000:]
                }), 500
                
            if services.check_server_online(host, port):
                online = True
                break
            time.sleep(1)
            
        if not online:
            return jsonify({"success": False, "error": "Servidor de IA demorou muito para responder."}), 504

    # Inicia o Aider
    logger.info("Launching Aider Chat...")
    aider_bin = os.path.join(os.path.dirname(sys.executable), "aider")
    if os.name == 'nt' and not aider_bin.endswith(".exe"):
        aider_bin += ".exe"
    if not os.path.exists(aider_bin):
        aider_bin = "aider"
        
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = "lm-studio"
    env["OPENAI_API_BASE"] = f"http://{host}:{port}/v1"
    aider_log_file = open(services.AIDER_LOG, "w", encoding="utf-8")
    
    aider_args = [
        aider_bin,
        "--openai-api-base", f"http://{host}:{port}/v1",
        "--openai-api-key", "lm-studio",
        "--model", "openai/gemma-4",
        "--config", ".aider.local.conf.yml"
    ]
    
    config_file = services.ROOT_DIR / "scratch" / "video_editor_config.json"
    transcribe_path = None
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                transcribe_path = cfg.get("transcribe_output_path")
        except: pass
            
    if not transcribe_path:
        transcribe_path = str(services.ROOT_DIR / "scratch" / "transcricao_video.txt")
        
    v_edit_file = services.ROOT_DIR / "scratch" / "editar_video_profissional.py"
    if v_edit_file.exists():
        aider_args.extend(["--file", str(v_edit_file.resolve())])
    if os.path.exists(transcribe_path):
        aider_args.extend(["--read", str(transcribe_path)])
        
    aider_args.append("--browser")
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    services.aider_process = subprocess.Popen(
        aider_args,
        env=env,
        stdout=aider_log_file,
        stderr=subprocess.STDOUT,
        creationflags=creationflags
    )
    
    return jsonify({
        "success": True, 
        "msg": "Servidor local e Aider iniciados!",
        "model_loaded": Path(model_path).name if not server_already_online else "Já carregado"
    })

@dashboard_routes.route("/api/stop", methods=["POST"])
def api_stop():
    services.stop_processes()
    return jsonify({"success": True, "msg": "Processos encerrados e VRAM liberada."})

@dashboard_routes.route("/api/logs", methods=["GET"])
def api_logs():
    server_lines = []
    aider_lines = []
    
    if services.SERVER_LOG.exists():
        try:
            with open(services.SERVER_LOG, "r", encoding="utf-8", errors="replace") as f:
                server_lines = f.readlines()[-150:]
        except Exception as e:
            server_lines = [f"Error reading server logs: {e}"]
            
    if services.AIDER_LOG.exists():
        try:
            with open(services.AIDER_LOG, "r", encoding="utf-8", errors="replace") as f:
                aider_lines = f.readlines()[-100:]
        except Exception as e:
            aider_lines = [f"Error reading Aider logs: {e}"]
            
    return jsonify({
        "server_log": "".join(server_lines),
        "aider_log": "".join(aider_lines)
    })

@dashboard_routes.route("/api/system_stats", methods=["GET"])
def api_system_stats():
    return jsonify(services.get_system_stats())
