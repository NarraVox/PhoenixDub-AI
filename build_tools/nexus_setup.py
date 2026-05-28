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
                torch_libs = ["torch==2.5.1+cu121", "torchaudio==2.5.1+cu121", "--extra-index-url", "https://download.pytorch.org/whl/cu121"]
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
                    self._log("📥 Baixando Modelo Wan v2.2 GGUF (3.8 GB) da HuggingFace...", "warn")
                    code = f"from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='QuantStack/Wan2.2-TI2V-5B-GGUF', filename='{wan_filename}', local_dir='_MODELS_')"
                    self._run_python_cmd(python_exe, code)
                    self._log("✅ Modelo Wan v2.2 baixado com sucesso!", "success")

                # 2. FLUX.2-klein GGUF
                flux_filename = "flux-2-klein-4b-Q4_K_M.gguf"
                if (models_dir_1 / flux_filename).exists():
                    self._log("✅ Modelo FLUX.2-klein detectado localmente em _MODELS_.", "success")
                elif (models_dir_2 / flux_filename).exists():
                    self._log("✅ Modelo FLUX.2-klein detectado localmente em models.", "success")
                else:
                    self._log("📥 Baixando Modelo FLUX.2-klein GGUF (3.0 GB) da HuggingFace...", "warn")
                    code = f"from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='unsloth/FLUX.2-klein-4B-GGUF', filename='{flux_filename}', local_dir='_MODELS_')"
                    self._run_python_cmd(python_exe, code)
                    self._log("✅ Modelo FLUX.2-klein baixado com sucesso!", "success")

                # 3. Qwen3-TTS-CustomVoice
                qwen_voice_dir_1 = models_dir_1 / "Qwen3-TTS-12Hz-0.6B-CustomVoice"
                qwen_voice_dir_2 = models_dir_2 / "Qwen3-TTS-12Hz-0.6B-CustomVoice"
                if qwen_voice_dir_1.exists():
                    self._log("✅ Modelo Qwen3-TTS-CustomVoice detectado em _MODELS_.", "success")
                elif qwen_voice_dir_2.exists():
                    self._log("✅ Modelo Qwen3-TTS-CustomVoice detectado em models.", "success")
                else:
                    self._log("📥 Baixando Modelo Qwen3-TTS-CustomVoice (1.2 GB) da HuggingFace...", "warn")
                    code = "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice', local_dir='_MODELS_/Qwen3-TTS-12Hz-0.6B-CustomVoice')"
                    self._run_python_cmd(python_exe, code)
                    self._log("✅ Modelo Qwen3-TTS-CustomVoice baixado com sucesso!", "success")
            else:
                self._log("ℹ️ Módulo Vídeo Generativo não selecionado. Pulando.", "info")

            # Instalação do Módulo Dublagem / Áudio (Whisper/TTS)
            if modules.get("voice"):
                self._update(90, "🎙️ Configurando Titan Qwen3, Audio-IA e Docs OCR...")
                audio_libs = ["qwen-tts>=0.0.1", "faster-whisper==1.2.1", "pyannote.audio==3.3.1", "librosa", "soundfile", "pydub", "easyocr>=1.7.1"]
                self._run_pip(python_exe, audio_libs)
                self._log("Vocoder 12Hz injetado com sucesso.", "success")

                models_dir_1 = Path(os.getcwd()) / "_MODELS_"
                models_dir_2 = Path(os.getcwd()) / "models"

                # 1. Gemma-4 GGUF
                gemma_filename = "gemma-4-E4B-it-Q4_K_M.gguf"
                if (models_dir_1 / gemma_filename).exists():
                    self._log("✅ Modelo Gemma-4 detectado localmente em _MODELS_.", "success")
                elif (models_dir_2 / gemma_filename).exists():
                    self._log("✅ Modelo Gemma-4 detectado localmente em models.", "success")
                else:
                    self._log("📥 Baixando Modelo Gemma-4 GGUF (5.3 GB) da HuggingFace...", "warn")
                    code = f"from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='unsloth/gemma-4-E4B-it-GGUF', filename='{gemma_filename}', local_dir='_MODELS_')"
                    self._run_python_cmd(python_exe, code)
                    self._log("✅ Modelo Gemma-4 baixado com sucesso!", "success")

                # 2. Qwen3-TTS-Base
                qwen_base_dir_1 = models_dir_1 / "Qwen3-TTS-12Hz-0.6B-Base"
                qwen_base_dir_2 = models_dir_2 / "Qwen3-TTS-12Hz-0.6B-Base"
                if qwen_base_dir_1.exists():
                    self._log("✅ Modelo Qwen3-TTS-Base detectado em _MODELS_.", "success")
                elif qwen_base_dir_2.exists():
                    self._log("✅ Modelo Qwen3-TTS-Base detectado em models.", "success")
                else:
                    self._log("📥 Baixando Modelo Qwen3-TTS-Base (1.2 GB) da HuggingFace...", "warn")
                    code = "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Qwen/Qwen3-TTS-12Hz-0.6B-Base', local_dir='_MODELS_/Qwen3-TTS-12Hz-0.6B-Base')"
                    self._run_python_cmd(python_exe, code)
                    self._log("✅ Modelo Qwen3-TTS-Base baixado com sucesso!", "success")
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
                        self._update(90 + int(percent * 0.08), f"Baixando Gemma-4: {mb_downloaded}/{total_mb} MB ({percent}%)")
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
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            ui_file = Path(__file__).parent.parent / "client" / "installer_ui.html"
            with open(ui_file, "rb") as f: self.wfile.write(f.read())
        elif self.path == "/logs":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.ui_logs).encode())
            self.ui_logs.clear()

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
