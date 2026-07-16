import sys
import os
import threading
import time
import subprocess
import json
import urllib.request
import zipfile
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import webview

token_submitted_event = threading.Event()
current_token = None

# --- MODO DE DIAGNÓSTICO (LOGS NO CMD REATIVADOS) ---

class SetupAPI:
    def __init__(self, logs_container):
        self.logs = logs_container
        self.env_path = Path(os.getcwd()) / "env"

    def run_setup(self, mode="cpu", modules=None):
        # Executa direto na thread para evitar recursão
        if mode == "test":
            self._execute_test()
        else:
            self._execute_installation(mode, modules)

    def _execute_test(self):
        """[v2026.90] Executa diagnóstico completo do ambiente."""
        try:
            self._update(10, "Iniciando Diagnóstico...")
            self._log("🔍 VARREDURA DE SISTEMA INICIADA...", "cmd")
            
            # 1. Verifica Python
            self._log(f"Motor Python: {sys.version.split()[0]}", "info")
            
            # 2. Verifica Torch (Core)
            self._update(30, "Verificando Motores de Áudio...")
            try:
                import torch
                self._log(f"✅ PyTorch: {torch.__version__}", "success")
                if torch.cuda.is_available():
                    self._log(f"🚀 GPU Detectada: {torch.cuda.get_device_name(0)}", "success")
                else:
                    self._log("💻 Modo CPU Ativo (Nenhuma GPU CUDA encontrada)", "info")
            except:
                self._log("❌ PyTorch: Não instalado ou corrompido.", "error")

            # 3. Verifica Qwen3-TTS (Motor de Voz de Alta Fidelidade)
            self._update(60, "Verificando Motor de Voz...")
            try:
                import qwen_tts
                self._log("✅ Qwen3-TTS: Pronto para dublagem.", "success")
            except ImportError:
                self._log("❌ Qwen3-TTS: NÃO ENCONTRADO!", "error")
                self._log("DICA: Use o botão 'REPARAR' para instalar o motor de voz.", "warn")

            # 4. Verifica Faster-Whisper
            try:
                from faster_whisper import WhisperModel
                self._log("✅ Faster-Whisper: Pronto para transcrição.", "success")
            except:
                self._log("❌ Faster-Whisper: Falha crítica.", "error")

            self._update(100, "Diagnóstico Concluído!")
            self._log("🏁 TESTE FINALIZADO. Verifique os alertas acima.", "success")

        except Exception as e:
            self._log(f"FALHA NO DIAGNÓSTICO: {e}", "error")

    def _execute_installation(self, mode, modules):
        try:
            self._log(f"Iniciando instalacao no modo {mode.upper()}...", "success")
            if not modules or mode != "modular":
                modules = {"base": True, "voice": True, "llama": True, "video": True}
                
            # [SURVIVAL] Criação do ENV ou Download de Python Portátil
            if not self.env_path.exists():
                self._update(10, "Preparando Ambiente...")
                try:
                    self._log("Tentando criar ambiente virtual...")
                    subprocess.run(["python", "-m", "venv", "env"], check=True)
                except:
                    self._log("Baixando motor portatil...", "warn")
                    self._update(15, "Baixando Python (25MB)...")
                    py_url = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip"
                    zip_path = os.path.join(os.getcwd(), "python_base.zip")
                    urllib.request.urlretrieve(py_url, zip_path)
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall("env")
                    os.remove(zip_path)
                    with open(os.path.join("env", "python310._pth"), "w") as f:
                        f.write(".\npython310.zip\nimport site\n")
                    pip_script = os.path.join("env", "get-pip.py")
                    urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", pip_script)
                    subprocess.run([os.path.join("env", "python.exe"), pip_script, "--quiet"], check=True)
                    os.remove(pip_script)

            # [v2026.PYTHON_PATH] Localiza o executável do Python no ambiente
            python_options = [os.path.join("env", "Scripts", "python.exe"), os.path.join("env", "python.exe")]
            python_exe = next((p for p in python_options if os.path.exists(p)), "python")

            # [v2026.BUILD_TOOLS] Garante que as ferramentas de construção estejam atualizadas
            self._update(20, "🛠️ Atualizando ferramentas de build (Pip/Wheel/Setuptools)...")
            subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel", "--quiet"], check=True)

            # Instalação do Módulo Base / Core (Sempre instalado)
            self._update(30, "🚀 Instalando Módulo Base / Core...")
            base_libs = ["Flask", "Flask-Cors", "requests", "psutil", "python-dotenv", "tqdm", "Jinja2", "Pillow", "PyYAML", "pdfplumber>=0.11.0"]
            self._run_pip(python_exe, base_libs)

            # Se áudio ou vídeo forem selecionados, precisamos de PyTorch
            precisa_pytorch = modules.get("video") or modules.get("voice")
            if precisa_pytorch:
                self._update(50, "🧠 Sincronizando PyTorch e CUDA...")
                torch_libs = ["torch==2.6.0+cu124", "torchvision==0.21.0+cu124", "torchaudio==2.6.0+cu124", "--extra-index-url", "https://download.pytorch.org/whl/cu124"]
                self._run_pip(python_exe, torch_libs)
            else:
                self._log("ℹ️ Módulos de Áudio e Vídeo não selecionados. Pulando PyTorch.", "info")

            # Instalação do Llama-CPP (Opcional)
            if modules.get("llama"):
                self._update(70, "🏎️ Compilando Aceleração RTX (Llama-CPP)...")
                self._log("⚠️ Esta etapa é pesada e pode parecer lenta, mas a GPU está trabalhando!", "warn")
                llama_libs = ["llama-cpp-python==0.3.23", "--extra-index-url", "https://abetlen.github.io/llama-cpp-python/whl/cu124"]
                self._run_pip(python_exe, llama_libs)
            else:
                self._log("ℹ️ Módulo Aceleração Llama-CPP não selecionado. Pulando.", "info")

            # Instalação do Módulo Vídeo Generativo (Diffusers + transformers)
            if modules.get("video"):
                self._update(80, "🎬 Configurando dependências de Vídeo (Diffusers/Transformers)...")
                video_libs = ["diffusers", "transformers", "accelerate", "sentencepiece"]
                self._run_pip(python_exe, video_libs)
                try:
                    self._log("Tentando injetar Flash-Attention 2 (Turbo Mode)...", "info")
                    self._run_pip(python_exe, ["flash-attn>=2.5.0", "--no-build-isolation"])
                    self._log("✅ Flash-Attention 2 ATIVO!", "success")
                except:
                    self._log("⚠️ Flash-Attention 2 falhou na compilação. Usando modo estável padrão.", "warn")

                # Verificação e download dos modelos de vídeo
                models_dir_1 = Path(os.getcwd()) / "_MODELS_"
                models_dir_2 = Path(os.getcwd()) / "models"
                
                # 1. Wan v2.2 GGUF
                wan_filename = "Wan2.2-TI2V-5B-Q4_K_M.gguf"
                if (models_dir_1 / wan_filename).exists():
                    self._log("✅ Modelo Wan v2.2 detectado localmente em _MODELS_.", "success")
                elif (models_dir_2 / wan_filename).exists():
                    self._log("✅ Modelo Wan v2.2 detectado localmente em models.", "success")
                else:
                    self.download_model_with_retry(python_exe, repo_id='QuantStack/Wan2.2-TI2V-5B-GGUF', filename=wan_filename)

                # 2. FLUX.2-klein GGUF
                flux_filename = "flux-2-klein-4b-Q4_K_M.gguf"
                if (models_dir_1 / flux_filename).exists():
                    self._log("✅ Modelo FLUX.2-klein detectado localmente em _MODELS_.", "success")
                elif (models_dir_2 / flux_filename).exists():
                    self._log("✅ Modelo FLUX.2-klein detectado localmente em models.", "success")
                else:
                    self.download_model_with_retry(python_exe, repo_id='unsloth/FLUX.2-klein-4B-GGUF', filename=flux_filename)

                # 3. Qwen3-TTS-CustomVoice
                qwen_voice_dir_1 = models_dir_1 / "Qwen3-TTS-12Hz-0.6B-CustomVoice"
                qwen_voice_dir_2 = models_dir_2 / "Qwen3-TTS-12Hz-0.6B-CustomVoice"
                if qwen_voice_dir_1.exists():
                    self._log("✅ Modelo Qwen3-TTS-CustomVoice detectado em _MODELS_.", "success")
                elif qwen_voice_dir_2.exists():
                    self._log("✅ Modelo Qwen3-TTS-CustomVoice detectado em models.", "success")
                else:
                    self.download_model_with_retry(python_exe, repo_id='Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice', is_snapshot=True)
            else:
                self._log("ℹ️ Módulo Vídeo Generativo não selecionado. Pulando.", "info")

            # Instalação do Módulo Dublagem / Áudio (Whisper/TTS)
            if modules.get("voice"):
                self._update(90, "🎙️ Configurando Titan Qwen3, Audio-IA e Docs OCR...")
                audio_libs = ["faster-qwen3-tts[ggml]", "qwen-tts>=0.0.1", "faster-whisper==1.2.1", "pyannote.audio==3.3.1", "whisperx", "librosa", "soundfile", "pydub", "easyocr>=1.7.1", "--extra-index-url", "https://download.pytorch.org/whl/cu124"]
                self._run_pip(python_exe, audio_libs)
                self._log("Vocoder 12Hz injetado com sucesso.", "success")
                self._log("💡 LEMBRETE: Acesse hf.co/pyannote/speaker-diarization-community-1 para aceitar os termos de uso e configure a variável HF_TOKEN para habilitar a diarização.", "warn")

                models_dir_1 = Path(os.getcwd()) / "_MODELS_"
                models_dir_2 = Path(os.getcwd()) / "models"

                # 1. Qwen-3.5 GGUF
                qwen_filename = "Qwen3.5-4B-Q4_K_M.gguf"
                gemma_filename = "gemma-4-E4B-it-Q4_K_M.gguf"
                if (models_dir_1 / qwen_filename).exists():
                    self._log("✅ Modelo Qwen-3.5 detectado localmente em _MODELS_.", "success")
                elif (models_dir_2 / qwen_filename).exists():
                    self._log("✅ Modelo Qwen-3.5 detectado localmente em models.", "success")
                elif (models_dir_1 / gemma_filename).exists():
                    self._log("✅ Modelo Gemma-4 detectado localmente em _MODELS_.", "success")
                elif (models_dir_2 / gemma_filename).exists():
                    self._log("✅ Modelo Gemma-4 detectado localmente em models.", "success")
                else:
                    self.download_model_with_retry(python_exe, repo_id='unsloth/Qwen3.5-4B-GGUF', filename=qwen_filename)

                # 2. Qwen3-TTS-Base (1.7B PyTorch)
                qwen_base_dir_1 = models_dir_1 / "qwen3_1.7b_pytorch"
                qwen_base_dir_2 = models_dir_2 / "qwen3_1.7b_pytorch"
                if (qwen_base_dir_1 / "model.safetensors").exists():
                    self._log("✅ Modelo Qwen3-TTS-Base (1.7B PyTorch) detectado em _MODELS_.", "success")
                elif (qwen_base_dir_2 / "model.safetensors").exists():
                    self._log("✅ Modelo Qwen3-TTS-Base (1.7B PyTorch) detectado em models.", "success")
                else:
                    self.download_model_with_retry(
                        python_exe, 
                        repo_id='Qwen/Qwen3-TTS-12Hz-1.7B-Base', 
                        is_snapshot=True
                    )
            else:
                self._log("ℹ️ Módulo Dublagem/Áudio não selecionado. Pulando.", "info")

            # [SECURITY] Auditoria Final de Integridade
            self._update(95, "Auditando seguranca...")
            self._log("Executando varredura Sentinel de integridade...")
            try:
                audit_path = os.path.join(os.getcwd(), "env", "Scripts", "pip-audit.exe")
                if not os.path.exists(audit_path):
                    subprocess.run([python_exe, "-m", "pip", "install", "pip-audit", "--quiet"], check=True)
                audit_res = subprocess.run([audit_path], capture_output=True, text=True)
                if audit_res.returncode == 0:
                    self._log("SENTINEL: Ambiente verificado e 100% SEGURO.", "success")
                else:
                    self._log("SENTINEL: ALERTA! Vulnerabilidades detectadas. Comunique o dev.", "error")
            except:
                self._log("Aviso: Nao foi possivel completar a auditoria automatica.", "warn")

            self._update(100, "Instalacao Concluida!")
            self._log("PROCESSO FINALIZADO!", "success")
            
        except Exception as e:
            print(f"ERRO NO BACKEND: {e}")
            self._log(f"ERRO: {str(e)}", "error")

    def download_model_with_retry(self, python_exe, repo_id, filename=None, is_snapshot=False, allow_patterns=None):
        global token_submitted_event, current_token
        
        if is_snapshot:
            local_dir_name = "qwen3_1.7b_pytorch" if "1.7B-Base" in repo_id else ("qwen3_0.6b" if "Qwen3-TTS-12Hz-0.6B-Base" in repo_id else repo_id.split('/')[-1])
            if allow_patterns:
                patterns_str = ", ".join([f"'{p}'" for p in allow_patterns])
                code = f"from huggingface_hub import snapshot_download; snapshot_download(repo_id='{repo_id}', local_dir='_MODELS_/{local_dir_name}', local_dir_use_symlinks=False, allow_patterns=[{patterns_str}])"
            else:
                code = f"from huggingface_hub import snapshot_download; snapshot_download(repo_id='{repo_id}', local_dir='_MODELS_/{local_dir_name}', local_dir_use_symlinks=False)"
            desc = f"snapshot do repositório '{repo_id}'"
        else:
            code = f"from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='{repo_id}', filename='{filename}', local_dir='_MODELS_')"
            desc = f"arquivo '{filename}' do repositório '{repo_id}'"
            
        while True:
            try:
                self._log(f"📥 Baixando {desc} da HuggingFace...", "warn")
                # Executa o comando e captura a saída
                output_lines = []
                cmd = [python_exe, "-c", code]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
                for line in process.stdout:
                     if line.strip():
                         self._log(line.strip())
                         output_lines.append(line.strip())
                process.wait()
                
                if process.returncode == 0:
                     self._log(f"✅ Download de {desc} concluído com sucesso!", "success")
                     return
                
                # Se falhou, vamos analisar a saída
                error_output = "\n".join(output_lines)
                is_gated = any(kw in error_output.lower() for kw in ["gated", "accept the terms", "terms", "gatedrepo", "authorization", "license"])
                is_auth = any(kw in error_output.lower() for kw in ["unauthorized", "401", "403", "token", "credentials", "login", "invalid token"])
                
                if is_gated or is_auth:
                     self._log("⚠️ DETECTADO ERRO DE AUTORIZAÇÃO / TERMOS NO HUGGING FACE!", "warn")
                     if is_gated:
                         self._log("Este modelo requer que você aceite os termos no site do Hugging Face.", "warn")
                     else:
                         self._log("Este modelo requer um token de acesso válido do Hugging Face.", "warn")
                     
                     # Notifica a interface web
                     # Vamos usar o prefixo [NEED_TOKEN] para a UI interceptar
                     terms_url = f"https://huggingface.co/{repo_id}"
                     self._update(90, f"[NEED_TOKEN]{repo_id}|{terms_url}")
                     
                     # Limpa e aguarda o evento do token
                     token_submitted_event.clear()
                     self._log("Aguardando fornecimento do token e confirmação dos termos na interface...", "info")
                     token_submitted_event.wait()
                     
                     if current_token:
                         self._log("Token recebido! Aplicando credenciais e tentando novamente...", "success")
                         os.environ["HF_TOKEN"] = current_token
                         # Persiste o token de forma definitiva no sistema Windows do usuário
                         try:
                             import subprocess
                             subprocess.run(["setx", "HF_TOKEN", current_token], capture_output=True)
                             self._log("✅ Token do Hugging Face salvo permanentemente no Windows!", "success")
                         except Exception as token_err:
                             self._log(f"Aviso: Não foi possível persistir o token via setx ({token_err})", "warn")
                     continue
                else:
                     raise Exception(f"Erro no download do modelo. Código de retorno: {process.returncode}")
                     
            except Exception as e:
                self._log(f"Falha ao baixar modelo: {e}", "error")
                raise e

    def _download_large_file(self, url, dest_path):
        """Baixa arquivos grandes com reporte de progresso periódico."""
        import urllib.request
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            total_size = int(response.info().get('Content-Length', 0))
            bytes_so_far = 0
            chunk_size = 1024 * 1024 # 1 MB
            
            with open(dest_path, 'wb') as f:
                last_update_time = time.time()
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_so_far += len(chunk)
                    
                    current_time = time.time()
                    if current_time - last_update_time > 3.0:
                        percent = int((bytes_so_far / total_size) * 100) if total_size else 0
                        mb_downloaded = round(bytes_so_far / (1024 * 1024), 1)
                        total_mb = round(total_size / (1024 * 1024), 1) if total_size else "Desconhecido"
                        self._update(90 + int(percent * 0.08), f"Baixando Qwen-3.5: {mb_downloaded}/{total_mb} MB ({percent}%)")
                        self._log(f"Progresso do download do modelo: {mb_downloaded}/{total_mb} MB ({percent}%)")
                        last_update_time = current_time

    def _run_python_cmd(self, python_exe, code_str):
        """Executa um comando inline Python dentro do env virtual e streama os logs."""
        cmd = [python_exe, "-c", code_str]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        for line in process.stdout:
            if line.strip():
                self._log(line.strip())
        process.wait()
        if process.returncode != 0:
            raise Exception(f"Erro ao executar script interno do Python: {code_str}")

    def _run_pip(self, python_exe, args):
        """Executa comandos pip com streaming de logs em tempo real."""
        cmd = [python_exe, "-m", "pip", "install"] + args
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        for line in process.stdout:
            if line.strip():
                self._log(line.strip())
        process.wait()
        if process.returncode != 0:
            raise Exception(f"Erro no comando pip: {args}")

    def _log(self, msg, type="info"):
        self.logs.append({"msg": msg, "type": type})

    def _update(self, percent, label):
        self.logs.append({"msg": f"[PROGRESS]{percent}|{label}", "type": "system"})

class NexusServer(BaseHTTPRequestHandler):
    ui_logs = []
    def do_GET(self):
        if self.path == "/logs":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.ui_logs).encode())
            self.ui_logs.clear()
            return

        client_dir = Path(__file__).parent.parent / "client"
        if self.path == "/":
            file_path = client_dir / "installer_ui.html"
        else:
            file_path = (client_dir / self.path.lstrip("/")).resolve()

        if not str(file_path).startswith(str(client_dir)):
            self.send_error(403, "Acesso proibido")
            return

        if file_path.exists() and file_path.is_file():
            self.send_response(200)
            if file_path.suffix == ".html":
                self.send_header("Content-type", "text/html; charset=utf-8")
            elif file_path.suffix == ".css":
                self.send_header("Content-type", "text/css; charset=utf-8")
            elif file_path.suffix == ".js":
                self.send_header("Content-type", "application/javascript; charset=utf-8")
            elif file_path.suffix == ".png":
                self.send_header("Content-type", "image/png")
            else:
                self.send_header("Content-type", "application/octet-stream")
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "Arquivo não encontrado")

    def do_POST(self):
        if self.path == "/start":
            content_length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(content_length))
            mode = data.get("mode", "cpu")
            modules = data.get("modules", None)
            # Inicia o setup em uma thread separada para não travar o servidor
            threading.Thread(target=api.run_setup, args=(mode, modules), daemon=True).start()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        elif self.path == "/submit_token":
            global current_token
            content_length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(content_length))
            current_token = data.get("token")
            token_submitted_event.set()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

    def log_message(self, format, *args): return

if __name__ == '__main__':
    port = 5899
    api = SetupAPI(NexusServer.ui_logs)
    server = HTTPServer(("127.0.0.1", port), NexusServer)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    
    window = webview.create_window("NarraVox - Nexus AI Setup Pro", f"http://127.0.0.1:{port}", 
                                   width=1280, height=800, background_color='#050505')
    window.events.shown += lambda: window.maximize()
    webview.start()
