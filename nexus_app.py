import webview
import threading
import os
import sys
import time
import subprocess
import logging
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, send_from_directory, jsonify, request, send_file

# --- NARRAVOX PREMIUM HUB MASTER LAUNCHER (v2026.SENTINEL) ---
# Centraliza todos os logs em uma única janela de comando.

# --- CONFIGURAÇÕES DE DIRETÓRIO DINÂMICAS (v2026.PORTABLE_REAL) ---
# O programa agora olha para onde o SCRIPT está e cria as pastas lá.
BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_FOLDER = BASE_DIR / "uploads"
TEMP_DIR = UPLOAD_FOLDER / "_NEXUS_TEMP_"

if not UPLOAD_FOLDER.exists():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
if not TEMP_DIR.exists():
    os.makedirs(TEMP_DIR, exist_ok=True)
os.environ["NEXUS_TEMP"] = str(TEMP_DIR)

# --- PATCH DE SEGURANÇA: WINDOWS SYMLINKS ---
# Impede que a HuggingFace tente criar atalhos (que exigem modo admin no Windows)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

app = Flask(__name__, static_folder='client')

@app.route('/stream_media')
def stream_media():
    path = request.args.get('path')
    if not path: return "Caminho ausente", 400
    
    # [v2026.PATH_CLEAN] Limpeza agressiva para caminhos Windows/Webview
    path = path.replace('file:///', '').replace('file://', '').replace('/', os.sep)
    
    # [v2026.PATH_SMART] Se for apenas um nome de arquivo, tenta achar na pasta de uploads
    if os.sep not in path and ':' not in path:
        potential_path = UPLOAD_FOLDER / path
        if potential_path.exists():
            path = str(potential_path.absolute())
    
    # Remove / inicial se for /C:/... (comum em URIs de navegadores baseados em Chromium)
    if path.startswith(os.sep) and len(path) > 2 and path[2] == ':':
        path = path[1:]
    
    path = path.replace('"', '').replace("'", "").strip()
    
    if not os.path.exists(path):
        # Tenta procurar recursivamente em uploads se ainda não achou
        found = False
        if UPLOAD_FOLDER.exists():
             for root, dirs, files in os.walk(UPLOAD_FOLDER):
                 if path in files:
                     path = os.path.join(root, path)
                     found = True
                     break
        
        if not found:
            # Tenta decodificar espaços
            import urllib.parse
            path = urllib.parse.unquote(path)
            if not os.path.exists(path):
                logging.error(f"❌ [STREAM] Arquivo NÃO encontrado após limpeza e busca: {path}")
                return f"Arquivo inexistente: {path}", 404

    # Detecta Mime Type dinamicamente
    import mimetypes
    mime, _ = mimetypes.guess_type(path)
    if not mime: mime = 'video/mp4' # Fallback

    # [v2026.STREAM_OPTIMIZED] Suporte a Range para Seek suave no Chrome/Edge
    file_size = os.path.getsize(path)
    range_header = request.headers.get('Range', None)
    
    if range_header:
        try:
            byte_range = range_header.replace('bytes=', '').split('-')
            start = int(byte_range[0])
            end = int(byte_range[1]) if byte_range[1] else file_size - 1
            
            # [v2026.SPEED_UP] Garante que chunks iniciais sejam rápidos
            length = end - start + 1
            if length > 1024 * 1024 * 2: # Max 2MB por chunk para não travar a RAM
                length = 1024 * 1024 * 2
                end = start + length - 1

            with open(path, 'rb') as f:
                f.seek(start)
                data = f.read(length)
                
            from flask import Response
            rv = Response(data, 206, mimetype=mime, content_type=mime)
            rv.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
            rv.headers.add('Accept-Ranges', 'bytes')
            rv.headers.add('Access-Control-Allow-Origin', '*')
            return rv
        except Exception as e:
            logging.error(f"⚠️ [STREAM] Falha no Range: {e}")

    response = send_file(path, mimetype=mime, conditional=True)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/')
def serve_hub():
    return send_from_directory('client', 'nexus_premium.html')

@app.route('/api/restart_motors')
@app.route('/api/restart_server', methods=['GET', 'POST'])
def restart_motors():
    print("\n" + "🔥"*20)
    print("  [CRITICAL] REINICIALIZAÇÃO TOTAL DOS SISTEMAS...")
    print("  Encerrando motores e limpando CPU...")
    print("" + "🔥"*20 + "\n")
    
    # 1. Encerramento agressivo de processos filhos e netos (Windows Tree Kill)
    for p in running_processes:
        try:
            # Tenta matar a árvore de processos (filhos do filho)
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(p.pid)], capture_output=True)
        except:
            try: p.terminate()
            except: pass
    running_processes.clear()
    
    # 2. Aguarda um momento para a CPU estabilizar
    time.sleep(1)
    
    # 3. AUTO-RESTART: Reinicia o próprio Hub para carregar mudanças de código
    # Isso substitui o processo atual por um novo, aplicando todas as atualizações.
    os.execv(sys.executable, ['python'] + sys.argv)
    
    return jsonify({"success": True, "message": "Reinicialização total disparada!"})

@app.route('/api/clear_cache', methods=['POST'])
def api_clear_cache():
    """Limpa diretórios de cache e backups temporários de um projeto específico."""
    try:
        data = request.get_json() or {}
        job_id = data.get('job_id')
        
        if not job_id:
            return jsonify({"success": False, "message": "Nenhum projeto selecionado para limpeza."})
            
        project_dir = UPLOAD_FOLDER / job_id
        if not project_dir.exists():
            return jsonify({"success": False, "message": f"Projeto {job_id} não encontrado."})

        count = 0
        # Limpa apenas dentro da pasta do projeto selecionado
        for folder_name in ["_backup_transcricao", "_backup_texto_final", "_dubbed_audio", "_dubbed_segments"]:
            p = project_dir / folder_name
            if p.exists() and p.is_dir():
                import shutil
                shutil.rmtree(p, ignore_errors=True)
                count += 1
        return jsonify({"success": True, "message": f"Limpeza concluída para o projeto {job_id}. ({count} pastas limpas)"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro ao limpar cache: {str(e)}"})

@app.route('/api/list_project_files')
def list_project_files():
    files = []
    if UPLOAD_FOLDER.exists():
        # 1. Lista arquivos individuais (Vídeos e Áudios soltos)
        for f in os.listdir(UPLOAD_FOLDER):
            path = UPLOAD_FOLDER / f
            if os.path.isfile(path):
                files.append({
                    "name": f,
                    "path": str(path.absolute()),
                    "type": "video" if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')) else "audio",
                    "date": datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
            # 2. Lista apenas pastas de projeto de VÍDEO (Dossies de Vídeo/IA)
            elif os.path.isdir(path) and f.startswith('video_') and (path / "job_status.json").exists():
                files.append({
                    "name": f,
                    "path": str(path.absolute()),
                    "type": "folder",
                    "date": datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
    return jsonify(files)


@app.route('/<path:filename>')
def serve_pages(filename):
    """Serve qualquer página HTML dentro da pasta client."""
    if not filename.endswith('.html'):
        # Tenta adicionar .html se o usuário esqueceu
        if os.path.exists(os.path.join('client', filename + '.html')):
            filename += '.html'
    return send_from_directory('client', filename)

@app.route('/api/list_vortex_projects')
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

@app.route('/api/security_audit')
def security_audit():
    """Realiza uma varredura completa de segurana nas bibliotecas instaladas."""
    try:
        pip_path = os.path.join(os.getcwd(), 'env', 'Scripts', 'pip.exe')
        if not os.path.exists(pip_path):
            return jsonify({"status": "error", "message": "Ambiente virtual não detectado."})

        # 1. Garante que o pip-audit esteja presente
        subprocess.run([pip_path, "install", "pip-audit", "--quiet"], check=True)
        
        # 2. Executa a auditoria em formato JSON
        audit_path = os.path.join(os.getcwd(), 'env', 'Scripts', 'pip-audit.exe')
        result = subprocess.run([audit_path, "--format", "json"], capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({
                "status": "safe", 
                "message": "Nenhum perigo detectado. Todas as bibliotecas estão seguras!",
                "details": json.loads(result.stdout) if result.stdout else []
            })
        else:
            # Se retornar erro, significa que encontrou vulnerabilidades
            vulnerabilities = json.loads(result.stdout) if result.stdout else []
            return jsonify({
                "status": "danger", 
                "message": f"ALERTA: Detectadas {len(vulnerabilities)} vulnerabilidades!",
                "details": vulnerabilities
            })
            
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao auditar: {str(e)}"})

@app.route('/api/security_repair', methods=['POST'])
def security_repair():
    """Tenta reparar as bibliotecas voltando para as versões seguras do projeto."""
    try:
        pip_path = os.path.join(os.getcwd(), 'env', 'Scripts', 'pip.exe')
        
        # O reparo aqui não é 'update', é 'reinstall' da nossa versão de confiança
        # Isso garante que não quebremos o programa com versões novas demais.
        target_req = "requirements_CPU.txt" # Padrão, mas pode ser dinâmico
        
        process = subprocess.run([pip_path, "install", "--force-reinstall", "-r", target_req], 
                                capture_output=True, text=True)
        
        if process.returncode == 0:
            return jsonify({"status": "success", "message": "Reparo concluído! O ambiente foi restaurado para o estado seguro."})
        else:
            return jsonify({"status": "error", "message": "Falha no auto-reparo. Recomendado reinstalação manual via Setup."})
            
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro no motor de reparo: {str(e)}"})

@app.route('/recent_jobs')
def recent_jobs():
    jobs = []
    upload_path = UPLOAD_FOLDER.resolve()
    
    if not upload_path.exists():
        return jsonify([])

    try:
        # Lista diretórios ordenados por data de modificação (mais recentes primeiro)
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
                except:
                     pass

            if len(jobs) >= 10: break # Limite de 10 dossiês na home
            
    except Exception as e:
        print(f"[ERRO LISTAGEM] {e}")
        
    return jsonify(jobs)

running_processes = []

def start_hub_server():
    """Roda o servidor do Hub na porta 5000."""
    try:
        app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[ERRO HUB] {e}")

def run_service(script_name, port):
    """Lança um motor que compartilha os logs com esta janela."""
    python_exe = os.path.join(os.getcwd(), 'env', 'Scripts', 'python.exe')
    if not os.path.exists(python_exe):
        python_exe = sys.executable 
    
    print(f"[CONECTANDO] {script_name} na porta {port}...")
    try:
        p = subprocess.Popen(
            [python_exe, script_name], 
            stdout=sys.stdout, 
            stderr=sys.stderr,
            bufsize=1,
            universal_newlines=True
        )
        running_processes.append(p)
    except Exception as e:
        print(f"[FALHA] {script_name}: {e}")

class Api:
    def open_file_dialog(self, file_filter="Todos os arquivos (*.*)", allow_multiple=False):
        """Abre o seletor de arquivos do Windows."""
        clean_filter = file_filter.split('|')[0]
        result = window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=allow_multiple, file_types=(clean_filter,))
        if result:
            return result if allow_multiple else result[0]
        return None

    def open_folder_dialog(self):
        """Abre o seletor de pastas do Windows."""
        result = window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            return result[0]
        return None

    def open_folder_explorer(self, folder_path):
        """Abre uma pasta específica no Windows Explorer."""
        if os.path.exists(folder_path):
            os.startfile(folder_path)
            return True
        return False

if __name__ == '__main__':
    print("\n" + "🔱"*20)
    print("  NARRAVOX STUDIOS - JANELA SENTINELA (PORTÁTIL)")
    print("  Monitorando todos os motores na raiz do projeto...")
    print("🔱"*20 + "\n")
    
    # 1. Liga os Motores na Raiz
    run_service("nexus_dub_games.py", 5002)
    run_service("narravox_editor.py", 5003)
    run_service("nexus_dub_video.py", 5004)
    run_service("vortex_dj.py", 5005)
    run_service("nexus_docs.py", 5006)
    
    # 2. Liga o Hub
    threading.Thread(target=start_hub_server, daemon=True).start()
    
    # 3. Aguarda estabilização dos Motores e da GPU (MODO SENTINELA)
    print("\n" + "⏳"*10)
    print("  [SISTEMA] Aguardando motores despertarem (RTX Ignition)...")
    
    import socket
    def is_port_open(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    engine_ports = [5002, 5003, 5004, 5005, 5006]
    ready = False
    timeout = 30 # Max 30 segundos de espera total
    start_wait = time.time()
    
    while not ready and (time.time() - start_wait) < timeout:
        all_up = True
        for p in engine_ports:
            if not is_port_open(p):
                all_up = False
                break
        if all_up:
            ready = True
        else:
            elapsed = int(time.time() - start_wait)
            print(f"  [WAIT] Motores carregando... ({elapsed}s)    ", end="\r")
            time.sleep(1)

    if ready:
        print("\n  [OK] Todos os sistemas em prontidão total! Lançando interface...")
    else:
        print("\n  [AVISO] Alguns motores demoraram a responder, mas lançando interface assim mesmo...")
    print("⏳"*10 + "\n")
    
    # 4. Abre a Janela Mestra do Hub
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
        for p in running_processes:
            try:
                p.terminate()
            except:
                pass
        os._exit(0)

    def on_files_dropped(files):
        if files:
            print(f"[DROP] Arquivos recebidos: {files}")
            window.evaluate_js(f"if(window.handleNativeDrop) window.handleNativeDrop({files})")

    # Tenta registrar o evento de drop de forma segura (compatibilidade)
    try:
        window.events.files_dropped += on_files_dropped
    except Exception as e:
        print(f"[AVISO] Drag & Drop nativo no suportado nesta verso do PyWebView: {e}")

    window.events.closed += on_closed

    print("\n[OK] Interface lançada. Logs dos motores ativos abaixo:")
    print("-" * 50)
    
    webview.start()
