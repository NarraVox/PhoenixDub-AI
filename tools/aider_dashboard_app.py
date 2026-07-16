# -*- coding: utf-8 -*-
# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

# 1. IMPORTAÇÃO DO MÓDULO DE SEGURANÇA E PATCH DO FLASK (SEMPRE EM PRIMEIRO LUGAR)
import nexus.core.security as security

import os
import sys
import time
import logging
import threading
import webview
from flask import Flask

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AiderDashboard")

# Inicialização do Flask protegida (SecuredFlask herdado via monkeypatch)
app = Flask(__name__)

# Importação e registro dos Blueprints refatorados
from tools.video_services import check_server_online, stop_processes
from tools.dashboard_routes import dashboard_routes
from tools.video_routes import video_routes
from tools.video_actions import video_actions

app.register_blueprint(dashboard_routes)
app.register_blueprint(video_routes)
app.register_blueprint(video_actions)

window = None

# --- API JAVASCRIPT DO PYWEBVIEW ---
class Api:
    def open_file_dialog(self, file_filter="Todos os arquivos (*.*)", allow_multiple=False):
        """Abre o seletor de arquivos do Windows."""
        global window
        if window is None:
            return None
        clean_filter = file_filter.split('|')[0]
        result = window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=allow_multiple, file_types=(clean_filter,))
        if result:
            paths = result if allow_multiple else [result]
            for p in paths:
                security.register_allowed_path(p)
            return result if allow_multiple else result[0]
        return None

    def open_folder_dialog(self):
        """Abre o seletor de pastas do Windows."""
        global window
        if window is None:
            return None
        result = window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            security.register_allowed_path(result[0])
            return result[0]
        return None

    def open_folder_explorer(self, folder_path):
        """Abre uma pasta específica no Windows Explorer (Seguro contra RCE)."""
        # Restringe apenas para pastas reais, impedindo execução acidental de arquivos .exe ou .bat
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            os.startfile(folder_path)
            return True
        logger.warning(f"⚠️ [API] Tentativa de explorar caminho inválido ou arquivo: {folder_path}")
        return False


@app.route("/")
def index():
    """Serves the dashboard HTML."""
    html_path = security.BASE_DIR / "nexus" / "client" / "aider_dashboard.html"
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h3>Error: aider_dashboard.html not found!</h3>", 404


if __name__ == "__main__":
    logger.info("=== Starting Narravox Aider Dashboard Controller (Desktop Window Mode) ===")
    
    # Start Flask server in background thread
    def run_flask():
        app.run(host="127.0.0.1", port=5500, debug=False)
        
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(0.5) # Give Flask a moment to initialize
    
    # Create Webview Window
    window = webview.create_window(
        title="NarraVox - Aider Dashboard Pro",
        url="http://127.0.0.1:5500",
        width=1200,
        height=850,
        background_color='#0b0d19',
        resizable=True,
        js_api=Api()
    )
    
    # Handle Window Close Event
    def on_closed():
        logger.info("Window closed. Stopping all sub-processes and exiting...")
        stop_processes()
        os._exit(0)
        
    window.events.closed += on_closed
    
    # Start GUI Main Loop
    webview.start()
