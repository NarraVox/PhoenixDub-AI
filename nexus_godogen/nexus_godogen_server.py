import os
import sys
import site
import socket
import time
import subprocess
import webbrowser
import threading
import psutil
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pipeline_engine import PipelineEngine

# Garante detecção de pacotes instalados com --user
user_site = site.getusersitepackages()
if user_site not in sys.path:
    sys.path.append(user_site)

app = FastAPI(title="Nexus Godogen Hub (Bare-Metal)")
engine = PipelineEngine()

# Certificar pastas
os.makedirs("static", exist_ok=True)
os.makedirs("projects", exist_ok=True)

# Servir arquivos estáticos se existirem
app.mount("/static", StaticFiles(directory="static"), name="static")

# ==========================================
# MODELOS DE REQUISIÇÃO
# ==========================================
class GenerateRequest(BaseModel):
    name: str
    prompt: str

class AiderRequest(BaseModel):
    cwd: str
    prompt: str

class ForgePlanRequest(BaseModel):
    cwd: str
    goal: str

class ForgeRunRequest(BaseModel):
    cwd: str
    title: str
    description: str
    files: list

class ToggleLockRequest(BaseModel):
    name: str
    file_path: str

# ==========================================
# GESTÃO DO SERVIDOR IA LOCAL (GPU)
# ==========================================
llama_process = None
LLAMA_LOG_FILE = "llama_server.log"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    index_path = "static/index.html"
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Interface Dashboard não encontrada em static/index.html</h1>"

@app.get("/api/project/status")
async def project_status():
    global llama_process
    
    # Checa se o Llama Server está rodando
    server_running = False
    server_pid = None
    if llama_process and llama_process.poll() is None:
        server_running = True
        server_pid = llama_process.pid
    else:
        # Checagem secundária em processos do sistema
        for proc in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any("run_llama_server.py" in arg for arg in cmdline):
                    server_running = True
                    server_pid = proc.info['pid']
                    break
            except:
                continue

    # Cálculo de RAM real
    ram = psutil.virtual_memory()
    total_gb = ram.total / (1024**3)
    used_gb = ram.used / (1024**3)
    ram_usage = f"{used_gb:.1f}GB / {total_gb:.1f}GB"
    
    godot_path = engine.get_godot_path()
    godot_found = os.path.exists(godot_path) or godot_path == "godot"
    aider_exe = r"C:\aider_env\Scripts\aider.exe"
    
    api_key_set = bool(engine.settings.get("gemini_api_key"))
    
    return {
        "status": "Online",
        "ram": ram_usage,
        "godot_path": godot_path,
        "godot_status": "Pronto" if godot_found else "Não encontrado",
        "aider_status": "Pronto" if os.path.exists(aider_exe) else "Não encontrado",
        "api_key_configured": api_key_set,
        "server_running": server_running,
        "server_pid": server_pid
    }

def _start_llama_subprocess():
    global llama_process
    if llama_process and llama_process.poll() is None:
        return llama_process.pid
        
    python_exe = r"C:\IA_dublagem\env\Scripts\python.exe"
    server_script = r"C:\IA_dublagem\nexus\build_tools\run_llama_server.py"
    
    # Resolve o caminho do modelo Qwen 3.5 / Gemma 4 dinamicamente
    def find_model():
        import glob
        default_path = r"C:\IA_dublagem\_MODELS_\Qwen3.5-4B-Q4_K_M.gguf"
        if os.path.exists(default_path):
            return default_path
        
        patterns = [
            r"C:\IA_dublagem\_MODELS_\*Qwen3.5*.gguf",
            r"C:\IA_dublagem\_MODELS_\*qwen*.gguf",
            r"C:\IA_dublagem\_MODELS_\*gemma-4*.gguf",
            r"C:\IA_dublagem\*Qwen3.5*.gguf",
            r".\_MODELS_\*Qwen3.5*.gguf"
        ]
        for pattern in patterns:
            matches = glob.glob(pattern)
            # Filter out speech and embeddings files
            matches = [m for m in matches if "tts" not in os.path.basename(m).lower() and "embed" not in os.path.basename(m).lower() and "acestep" not in os.path.basename(m).lower()]
            if matches:
                return matches[0]
        return default_path

    model_path = find_model()
    
    if not os.path.exists(python_exe):
        raise HTTPException(status_code=404, detail=f"Python env não encontrado em {python_exe}")
    if not os.path.exists(server_script):
        raise HTTPException(status_code=404, detail=f"Script de servidor não encontrado em {server_script}")
    if not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail=f"Nenhum modelo Qwen 3.5 ou Gemma 4 encontrado em _MODELS_ ou C:\\IA_dublagem.")
         
    cmd = [
        python_exe,
        server_script,
        "--model", model_path,
        "--port", "1234",
        "--n_ctx", "16384",  # Limite de 16k tokens de contexto
        "--flash_attn", "True",
        "--n_gpu_layers", "33",
        "--cache", "True",
        "--cache_size", "1073741824",
        "--use_mmap", "False"
    ]
    
    log_file = open(LLAMA_LOG_FILE, "w", encoding="utf-8")
    
    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    llama_process = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags
    )
    return llama_process.pid

@app.post("/api/server/start")
async def start_server():
    try:
        pid = _start_llama_subprocess()
        return {"status": "Iniciando servidor de IA local...", "pid": pid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao iniciar servidor: {e}")

@app.post("/api/server/stop")
async def stop_server():
    global llama_process
    status_messages = []
    
    if llama_process:
        try:
            llama_process.terminate()
            llama_process.wait(timeout=5)
            status_messages.append("Processo principal encerrado via terminate()")
        except subprocess.TimeoutExpired:
            llama_process.kill()
            status_messages.append("Processo principal forçado a encerrar via kill()")
        except Exception as e:
            status_messages.append(f"Erro ao encerrar processo principal: {e}")
        llama_process = None
        
    try:
        cleaned_any = False
        for proc in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any("run_llama_server.py" in arg for arg in cmdline):
                    proc.kill()
                    status_messages.append(f"Processo Llama local {proc.info['pid']} morto via psutil")
                    cleaned_any = True
            except:
                continue
        if not cleaned_any and not status_messages:
            status_messages.append("Nenhum processo órfão detectado")
    except Exception as e:
        status_messages.append(f"Erro ao forçar limpeza via psutil: {e}")
        
    return {"status": "Servidor de IA desligado", "details": status_messages}

@app.get("/api/server/logs")
async def get_server_logs():
    if not os.path.exists(LLAMA_LOG_FILE):
        return {"logs": "Sem logs disponíveis."}
    try:
        with open(LLAMA_LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            return {"logs": "".join(lines[-100:])}
    except Exception as e:
        return {"logs": f"Erro ao ler logs: {e}"}

# ==========================================
# MOTOR DE GERAÇÃO E COMPILAÇÃO DE JOGOS
# ==========================================
@app.post("/api/project/generate")
async def generate_game(req: GenerateRequest):
    game_name = req.name.strip().replace(" ", "_")
    if not game_name:
        raise HTTPException(status_code=400, detail="Nome do jogo inválido")
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt inválido")
        
    try:
        # 1. Planejamento (Gemma) + Geração do código (Qwen) + Polimento (Aider)
        proj_dir, files = engine.generate_game_files(game_name, req.prompt)
        
        # 2. Compilação da Cena via Godot Headless
        build_success = engine.run_scene_builder(proj_dir)
        if not build_success:
            return JSONResponse(status_code=500, content={
                "status": "Erro na compilação", 
                "detail": "O EditorScript falhou ao criar a cena main.tscn. Verifique se o Aider gerou o código correto."
            })
            
        # 3. Execução e captura visual da tela do jogo
        verification_success = engine.verify_game_visually(proj_dir)
        
        return {
            "status": "Sucesso",
            "game_name": game_name,
            "files": files,
            "visual_validation": "Aprovado" if verification_success else "Falhou em tirar screenshot"
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "Erro", "detail": str(e)})

@app.get("/api/projects/list")
async def list_projects():
    projects_dir = "projects"
    if not os.path.exists(projects_dir):
        os.makedirs(projects_dir)
    projects = [d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d)) and d != "Teste_Pipeline_Game"]
    return {"projects": projects}

@app.get("/api/project/lock_status")
async def get_lock_status(name: str):
    proj_path = os.path.join("projects", name)
    if not os.path.exists(proj_path):
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
        
    locked_files = engine.get_locked_files(name)
    
    files_list = []
    for folder in ["builders", "scripts"]:
        folder_path = os.path.join(proj_path, folder)
        if os.path.exists(folder_path):
            for f in os.listdir(folder_path):
                if f.endswith(".gd"):
                    rel_path = f"{folder}/{f}"
                    files_list.append({
                        "path": rel_path,
                        "name": f,
                        "locked": rel_path in locked_files
                    })
    return {"files": files_list}

@app.post("/api/project/toggle_lock")
async def toggle_lock(req: ToggleLockRequest):
    proj_path = os.path.join("projects", req.name)
    if not os.path.exists(proj_path):
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
        
    try:
        is_locked = engine.toggle_file_lock(req.name, req.file_path)
        return {"status": "Sucesso", "file_path": req.file_path, "locked": is_locked}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/project/screenshot/{game_name}")
async def get_screenshot(game_name: str):
    screenshot_path = os.path.join("projects", game_name, "screenshot.png")
    if os.path.exists(screenshot_path):
        return FileResponse(screenshot_path)
    return JSONResponse(status_code=404, content={"error": "Sem imagem disponível"})

def monitor_godot_and_restart(proc, restart_llama):
    proc.wait()
    if restart_llama:
        print("🎮 [Godot] Processo do Godot encerrado. Reiniciando Servidor de IA local...")
        try:
            _start_llama_subprocess()
        except Exception as e:
            print(f"⚠️ Erro ao reiniciar servidor de IA local: {e}")

async def _check_llama_running():
    global llama_process
    if llama_process and llama_process.poll() is None:
        return True
    for proc in psutil.process_iter(['cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and any("run_llama_server.py" in arg for arg in cmdline):
                return True
        except:
            continue
    return False

@app.post("/api/project/open_editor")
async def open_editor(name: str):
    godot_exe = engine.get_godot_path()
    proj_path = os.path.abspath(os.path.join("projects", name))
    if not os.path.exists(proj_path):
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    server_running = await _check_llama_running()
    if server_running:
        print("🛠️ [Godot] Liberando VRAM: Parando servidor de IA local...")
        await stop_server()
        
    print(f"🛠️ [Godot] Abrindo no editor: {name}")
    try:
        godot_proc = subprocess.Popen([godot_exe, "--path", proj_path, "-e"])
        threading.Thread(target=monitor_godot_and_restart, args=(godot_proc, server_running), daemon=True).start()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao abrir Godot: {e}")
        
    return {"status": "Editor lançado (VRAM liberada)"}

@app.post("/api/project/play")
async def play_game(name: str):
    godot_exe = engine.get_godot_path()
    proj_path = os.path.abspath(os.path.join("projects", name))
    if not os.path.exists(proj_path):
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
        
    server_running = await _check_llama_running()
    if server_running:
        print("🎮 [Godot] Liberando VRAM: Parando servidor de IA local...")
        await stop_server()
        
    print(f"🎮 [Godot] Jogando: {name}")
    try:
        godot_proc = subprocess.Popen([godot_exe, "--path", proj_path])
        threading.Thread(target=monitor_godot_and_restart, args=(godot_proc, server_running), daemon=True).start()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao rodar Godot: {e}")
        
    return {"status": "Jogo iniciado (VRAM liberada)"}

# ==========================================
# STREAMING DO AIDER PARA PROGRAMAÇÃO GERAL
# ==========================================
@app.post("/api/aider/run")
async def run_aider(req: AiderRequest):
    folder_path = os.path.abspath(req.cwd)
    aider_exe = r"C:\aider_env\Scripts\aider.exe"
    
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=400, detail="Diretório de trabalho não existe.")
    if not os.path.exists(aider_exe):
        raise HTTPException(status_code=404, detail="Aider não encontrado em C:\\aider_env\\Scripts\\aider.exe")

    def generate_aider_logs():
        cmd = [
            aider_exe,
            "--openai-api-base", "http://localhost:1234/v1",
            "--openai-api-key", "fake-key",
            "--model", "openai/qwen-3.5",
            "--message", req.prompt,
            "--yes"
        ]
        
        # Test command se houver
        test_cmd = r"C:\IA_dublagem\tools\testar_imports.bat"
        if os.path.exists(test_cmd):
            cmd.extend(["--test-cmd", test_cmd])
            
        yield f"data: ▶ [Forge] Iniciando Aider na pasta: {folder_path}\n\n"
        yield f"data: ▶ [Forge] Comando: {req.prompt}\n\n"
        yield f"data: --------------------------------------------------\n\n"
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=folder_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            
            for line in process.stdout:
                yield f"data: {line}\n\n"
                
            process.wait()
            yield f"data: --------------------------------------------------\n\n"
            yield f"data: 🏁 [Forge] Execução concluída! Código de saída: {process.returncode}\n\n"
        except Exception as e:
            yield f"data: ❌ Erro crítico ao rodar o Aider: {e}\n\n"
            
    return StreamingResponse(generate_aider_logs(), media_type="text/event-stream")

# ==========================================
# ENDPOINTS ADICIONAIS DO LOCAL FORGE (ORQUESTRADOR DE METAS)
# ==========================================
@app.post("/api/forge/plan")
async def forge_plan(req: ForgePlanRequest):
    import re
    import json
    
    planner_system = (
        "Você é o Nexus-Forge Planner (Gemma). Sua missão é receber o objetivo do usuário e criar um plano "
        "de desenvolvimento extremamente segmentado e modular em arquivos. Cada tarefa deve ser minúscula, "
        "focando em no máximo 1 ou 2 arquivos por vez, para que cada execução caiba em menos de 4.000 tokens.\n\n"
        "Você DEVE retornar OBRIGATORIAMENTE um objeto JSON contendo a lista de tarefas organizadas sequencialmente.\n"
        "As tarefas devem seguir dependências de baixo para cima (ex: arquivos de configuração e utilitários primeiro, lógica depois).\n\n"
        "Modelo de Retorno JSON:\n"
        "{\n"
        "  \"tasks\": [\n"
        "    {\n"
        "      \"id\": 1,\n"
        "      \"title\": \"Configurar banco de dados\",\n"
        "      \"description\": \"Crie a conexão sqlite e crie as tabelas necessárias no db.py\",\n"
        "      \"files\": [\"db.py\"]\n"
        "    },\n"
        "    {\n"
        "      \"id\": 2,\n"
        "      \"title\": \"Implementar lógica do usuário\",\n"
        "      \"description\": \"Crie funções para adicionar e autenticar usuários baseando-se no db.py\",\n"
        "      \"files\": [\"auth.py\", \"db.py\"]\n"
        "    }\n"
        "  ]\n"
        "}"
    )
    
    try:
        url = engine.settings.get("planner_model_url")
        model_name = engine.settings.get("planner_model_name")
        use_local = engine.settings.get("use_local_models", True)
        
        if use_local:
            planner_resp = engine.call_local_model(
                url,
                model_name,
                planner_system,
                f"Objetivo: {req.goal}",
                json_mode=True
            )
        else:
            planner_resp = engine.call_gemini(planner_system + "\nRetorne no formato JSON indicado.", f"Objetivo: {req.goal}")
            if isinstance(planner_resp, dict):
                return planner_resp
        
        # Extrai o JSON da resposta da IA
        match = re.search(r"```json(.*?)```", planner_resp, re.DOTALL)
        if match:
            content = match.group(1).strip()
        else:
            start = planner_resp.find('{')
            end = planner_resp.rfind('}')
            if start != -1 and end != -1:
                content = planner_resp[start:end+1]
            else:
                content = planner_resp.strip()
                
        plan_data = json.loads(content)
        return plan_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar plano local: {e}")

@app.post("/api/forge/run_task")
async def forge_run_task(req: ForgeRunRequest):
    folder_path = os.path.abspath(req.cwd)
    aider_exe = r"C:\aider_env\Scripts\aider.exe"
    
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=400, detail="Diretório de trabalho não existe.")
    if not os.path.exists(aider_exe):
        raise HTTPException(status_code=404, detail="Aider não encontrado.")

    from pathlib import Path
    Path(folder_path).mkdir(exist_ok=True, parents=True)

    for f in req.files:
        file_path = Path(folder_path) / f
        file_path.parent.mkdir(exist_ok=True, parents=True)
        if not file_path.exists():
            with open(file_path, "w", encoding="utf-8") as empty_f:
                empty_f.write("")

    def generate_aider_forge_logs():
        cmd = [
            aider_exe,
            "--openai-api-base", "http://localhost:1234/v1",
            "--openai-api-key", "fake-key",
            "--model", "openai/qwen-3.5",
            "--yes"
        ]
        
        for f in req.files:
            file_path = Path(folder_path) / f
            cmd.extend(["--file", str(file_path.resolve())])

        test_cmd = Path(folder_path) / "testar_imports.bat"
        if not test_cmd.exists():
            test_cmd = Path(r"C:\IA_dublagem\tools\testar_imports.bat")
        if test_cmd.exists():
            cmd.extend(["--test-cmd", str(test_cmd)])
            
        prompt_msg = (
            f"INSTRUÇÃO DA TAREFA:\n"
            f"Sua missão é realizar estritamente as alterações descritas abaixo.\n"
            f"Foque APENAS nesta tarefa e não tente criar outras funcionalidades.\n\n"
            f"Tarefa: {req.title}\n"
            f"Descrição detalhada: {req.description}\n"
        )
        cmd.extend(["--message", prompt_msg])
        
        yield f"data: ▶ [Forge] Executando Tarefa: {req.title}\n\n"
        yield f"data: ▶ [Forge] Arquivos: {', '.join(req.files)}\n\n"
        yield f"data: --------------------------------------------------\n\n"
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=folder_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            
            for line in process.stdout:
                yield f"data: {line}\n\n"
                
            process.wait()
            yield f"data: --------------------------------------------------\n\n"
            if process.returncode == 0:
                yield f"data: ✅ [Forge] Tarefa concluída com sucesso!\n\n"
            else:
                yield f"data: ❌ [Forge] Falha na execução da tarefa. Código: {process.returncode}\n\n"
        except Exception as e:
            yield f"data: ❌ [Forge] Erro crítico ao rodar o Aider: {e}\n\n"
            
    return StreamingResponse(generate_aider_forge_logs(), media_type="text/event-stream")

# ==========================================
# INICIALIZAÇÃO
# ==========================================
def start():
    def find_free_port(start_port):
        port = start_port
        while port < 3050:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:
                    return port
                port += 1
        return start_port

    port = find_free_port(3000)
    
    print(f"\n🚀 [Nexus Godogen Hub] Servidor Unificado ONLINE!")
    print(f"🌐 Dashboard: http://localhost:{port}")
    
    def open_browser():
        time.sleep(2)
        webbrowser.open(f"http://localhost:{port}")
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")

if __name__ == "__main__":
    start()
