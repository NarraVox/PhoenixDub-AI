# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

# 1. IMPORTAÇÃO DO MÓDULO DE SEGURANÇA E PATCH DO FLASK (SEMPRE EM PRIMEIRO LUGAR)
import nexus.core.security as security

import webview
import threading
import os
import sys
import time
import subprocess
import logging
from pathlib import Path
from flask import Flask

# --- CONFIGURAÇÕES DE DIRETÓRIO DINÂMICAS ---
BASE_DIR = security.BASE_DIR
UPLOAD_FOLDER = security.UPLOAD_FOLDER
TEMP_DIR = UPLOAD_FOLDER / "_NEXUS_TEMP_"

os.environ["NEXUS_TEMP"] = str(TEMP_DIR)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

# Silencia logs do Flask/Werkzeug
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Inicialização do Flask (Herdado via SecuredFlask pelo import do security)
app = Flask(__name__, static_folder='client')

# --- CONFIGURAÇÃO E GERENCIAMENTO DINÂMICO DE MOTORES ---
active_engines = {
    "games": {"module": "nexus.dub.dubbing", "port": 5002, "process": None},
    "editor": {"module": "nexus.editor.narravox_editor", "port": 5003, "process": None},
    "video": {"module": "nexus.dub.dubbing", "port": 5004, "process": None},
    "dj": {"module": "nexus.dj.vortex_dj", "port": 5005, "process": None}
}
running_processes = []
engine_switch_lock = threading.Lock()

# Inicialização e registro das rotas HTTP modularizadas
from nexus.nexus_routes import nexus_blueprint, init_routes
init_routes(active_engines, running_processes, engine_switch_lock)
app.register_blueprint(nexus_blueprint)


def is_port_free(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except socket.error:
            return False

def kill_process_on_port(port):
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.splitlines():
            if f":{port} " in line or f".0.0.1:{port} " in line or f"[::]:{port} " in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        pid_int = int(pid)
                        if pid_int > 0:
                            print(f"[CLEANUP] Matando processo órfão PID {pid_int} na porta {port}...")
                            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid_int)], capture_output=True)
                    except ValueError:
                        pass
    except Exception as e:
        print(f"[CLEANUP] Erro ao limpar porta {port}: {e}")

def start_engine(name):
    engine = active_engines.get(name)
    if not engine: return
    if engine["process"] is not None and engine["process"].poll() is None:
        return

    python_exe = os.path.join(os.getcwd(), 'env', 'Scripts', 'python.exe')
    if not os.path.exists(python_exe):
        python_exe = sys.executable

    port = engine["port"]
    if not is_port_free(port):
        print(f"[SISTEMA] Porta {port} ocupada. Forçando liberação de recursos...")
        kill_process_on_port(port)

    for _ in range(30):
        if is_port_free(port):
            break
        time.sleep(0.1)

    print(f"\n[DINÂMICO] Ativando motor {name} na porta {engine['port']}...")
    try:
        p = subprocess.Popen(
            [python_exe, "-u", "-m", engine["module"], str(engine["port"])],
            bufsize=1,
            universal_newlines=True
        )
        engine["process"] = p
        time.sleep(0.5)
    except Exception as e:
        print(f"[FALHA] Não foi possível iniciar {name}: {e}")

def stop_engine(name):
    engine = active_engines.get(name)
    if not engine: return
    p = engine["process"]
    if p is not None and p.poll() is None:
        print(f"\n[DINÂMICO] Colocando motor {name} (porta {engine['port']}) em STANDBY...")
        try:
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(p.pid)], capture_output=True)
        except Exception:
            try: p.terminate()
            except: pass
        engine["process"] = None

def switch_active_engine(active_name):
    with engine_switch_lock:
        from nexus.nexus_routes import is_engine_busy
        for name, engine in active_engines.items():
            if name != active_name:
                try:
                    if not is_engine_busy(name):
                        stop_engine(name)
                    else:
                        print(f"[DINÂMICO] Motor {name} está OCUPADO com tarefa ativa. Mantendo-o ligado.")
                except Exception as e:
                    print(f"[DINÂMICO] Erro ao verificar busy do motor {name}: {e}")

        if active_name and active_name in active_engines:
            start_engine(active_name)

def start_hub_server():
    """Roda o servidor do Hub na porta 5000."""
    try:
        app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[ERRO HUB] {e}")


# --- API JAVASCRIPT DO PYWEBVIEW ---
class Api:
    def open_file_dialog(self, file_filter="Todos os arquivos (*.*)", allow_multiple=False):
        """Abre o seletor de arquivos do Windows."""
        clean_filter = file_filter.split('|')[0]
        result = window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=allow_multiple, file_types=(clean_filter,))
        if result:
            # Garante que paths seja uma lista de strings, seja result string ou tupla
            if isinstance(result, str):
                paths = [result]
            else:
                paths = list(result)
            for p in paths:
                security.register_allowed_path(p)
            return result if allow_multiple else paths[0]
        return None

    def open_folder_dialog(self):
        """Abre o seletor de pastas do Windows."""
        result = window.create_file_dialog(webview.FOLDER_DIALOG)
        if result:
            folder_path = result if isinstance(result, str) else result[0]
            security.register_allowed_path(folder_path)
            return folder_path
        return None

    def open_folder_explorer(self, folder_path):
        """Abre uma pasta específica no Windows Explorer (Seguro contra RCE)."""
        # Restringe apenas para pastas reais, impedindo execução acidental de arquivos .exe ou .bat
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            os.startfile(folder_path)
            return True
        logging.warning(f"⚠️ [API] Tentativa recusada de explorar caminho inválido ou não-diretório: {folder_path}")
        return False


def main():
    print("\n" + "="*20)
    print("  NARRAVOX STUDIOS - JANELA SENTINELA (PORTÁTIL)")
    print("  Monitorando todos os motores na raiz do projeto...")
    print("="*20 + "\n")

    # 1. Liga o Hub
    threading.Thread(target=start_hub_server, daemon=True).start()

    # 2. Abre a Janela Mestra do Hub
    api = Api()
    window = webview.create_window(
        "NarraVox Studios Premium Suite",
        "http://127.0.0.1:5000",
        maximized=True,
        background_color='#050505',
        js_api=api
    )

    def on_closed():
        print("\n[ENCERRANDO] Finalizando motores e fechando CMD...")
        for name, engine in active_engines.items():
            p = engine["process"]
            if p is not None and p.poll() is None:
                try:
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(p.pid)], capture_output=True)
                except: pass
        for p in running_processes:
            try:
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(p.pid)], capture_output=True)
            except: pass
        os._exit(0)

    window.events.closed += on_closed
    print("\n[OK] Interface lançada. Logs dos motores ativos abaixo:")
    print("-" * 50)
    webview.start()

if __name__ == '__main__':
    main()