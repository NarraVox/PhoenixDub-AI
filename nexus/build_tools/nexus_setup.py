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
        self.installation_failed = False
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
        self.installation_failed = False
        try:
            if getattr(sys, 'frozen', False):
                from nexus.distribution import deploy_runtime
                deploy_runtime(Path.cwd(), overwrite=True)
            self._log(f"Iniciando instalacao no modo {mode.upper()}...", "success")
            if not modules or mode != "modular":
                modules = {"base": True, "voice": True, "llama": True, "video": True}
                
            from nexus.build_tools.setup_support import ensure_environment, ensure_ffmpeg, requirement_plan
            python_exe = ensure_environment(Path.cwd())
            self._update(20, "Preparando dependencias...")
            subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], check=True)
            self._run_pip(python_exe, requirement_plan(Path.cwd(), modules))
            subprocess.run([python_exe, "-m", "pip", "check"], check=True)
            ensure_ffmpeg(Path.cwd(), self._log)
            if modules.get("voice"):
                self._log("Diarizacao: aceite os termos de pyannote/speaker-diarization-3.1 e configure HF_TOKEN.", "warn")

                models_dir_1 = Path(os.getcwd()) / "MODELS"
                models_dir_2 = Path(os.getcwd()) / "models"

                # 1. Qwen-3.5 GGUF
                qwen_9b_filename = "Qwen3.5-9B-UD-IQ3_XXS.gguf"
                qwen_filename = "Qwen3.5-4B-Q4_K_M.gguf"
                gemma_filename = "gemma-4-E4B-it-Q4_K_M.gguf"
                if (models_dir_1 / qwen_9b_filename).exists() or (models_dir_2 / qwen_9b_filename).exists():
                    self._log("✅ Modelo Qwen-3.5 9B (IQ3_XXS) detectado localmente.", "success")
                elif (models_dir_1 / qwen_filename).exists() or (models_dir_2 / qwen_filename).exists():
                    self._log("✅ Modelo Qwen-3.5 4B detectado localmente.", "success")
                elif (models_dir_1 / gemma_filename).exists() or (models_dir_2 / gemma_filename).exists():
                    self._log("✅ Modelo Gemma-4 detectado localmente em MODELS.", "success")
                else:
                    self.download_model_with_retry(python_exe, repo_id='unsloth/Qwen3.5-4B-GGUF', filename=qwen_filename)

                # 2. Qwen3-TTS-Base (1.7B PyTorch)
                qwen_base_dir_1 = models_dir_1 / "qwen3_1.7b_pytorch"
                qwen_base_dir_2 = models_dir_2 / "qwen3_1.7b_pytorch"
                if (qwen_base_dir_1 / "model.safetensors").exists():
                    self._log("✅ Modelo Qwen3-TTS-Base (1.7B PyTorch) detectado em MODELS.", "success")
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
                audit_res = subprocess.run([python_exe, "-m", "pip_audit"], capture_output=True, text=True)
                if audit_res.returncode == 0:
                    self._log("SENTINEL: Nenhuma vulnerabilidade conhecida apontada nesta auditoria.", "success")
                else:
                    self._log("SENTINEL: ALERTA! Vulnerabilidades detectadas. Comunique o dev.", "error")
            except:
                self._log("Aviso: Nao foi possivel completar a auditoria automatica.", "warn")

            # Extrai o executável principal do painel para a pasta local do usuário
            if getattr(sys, 'frozen', False):
                bundle_exe = os.path.join(sys._MEIPASS, "Nexus_AI_Pro.exe")
                dest_exe = os.path.join(os.getcwd(), "Nexus_AI_Pro.exe")
                if os.path.exists(bundle_exe):
                    self._log("Extraindo painel principal (Nexus_AI_Pro.exe) para o diretório...", "info")
                    import shutil
                    shutil.copy2(bundle_exe, dest_exe)
                    self._log("✅ Executável do painel extraído com sucesso!", "success")

            self._update(100, "Instalacao Concluida!")
            self._log("PROCESSO FINALIZADO!", "success")
            
        except Exception as e:
            self.installation_failed = True
            self._log(f"[SETUP_FAILED] Instalacao interrompida: {e}", "error")

    def download_model_with_retry(self, python_exe, repo_id, filename=None, is_snapshot=False, allow_patterns=None):
        global token_submitted_event, current_token
        
        if is_snapshot:
            local_dir_name = "qwen3_1.7b_pytorch" if "1.7B-Base" in repo_id else ("qwen3_0.6b" if "Qwen3-TTS-12Hz-0.6B-Base" in repo_id else repo_id.split('/')[-1])
            if allow_patterns:
                patterns_str = ", ".join([f"'{p}'" for p in allow_patterns])
                code = f"from huggingface_hub import snapshot_download; snapshot_download(repo_id='{repo_id}', local_dir='MODELS/{local_dir_name}', local_dir_use_symlinks=False, allow_patterns=[{patterns_str}])"
            else:
                code = f"from huggingface_hub import snapshot_download; snapshot_download(repo_id='{repo_id}', local_dir='MODELS/{local_dir_name}', local_dir_use_symlinks=False)"
            desc = f"snapshot do repositório '{repo_id}'"
        else:
            code = f"from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='{repo_id}', filename='{filename}', local_dir='MODELS')"
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
            if current_token:
                try:
                    token_str = str(current_token).strip()
                    token_file = Path("token_hf.txt")
                    token_file.write_text(token_str, encoding="utf-8")
                    os.environ["HF_TOKEN"] = token_str
                    os.environ["HUGGING_FACE_HUB_TOKEN"] = token_str
                except Exception as e:
                    print(f"[INSTALADOR] Erro ao gravar token_hf.txt: {e}")
            token_submitted_event.set()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

    def log_message(self, format, *args): return

def main():
    port = 5899
    global api
    api = SetupAPI(NexusServer.ui_logs)
    server = HTTPServer(("127.0.0.1", port), NexusServer)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    
    window = webview.create_window("NarraVox - Nexus AI Setup Pro", f"http://127.0.0.1:{port}", 
                                   width=1280, height=800, background_color='#050505')
    window.events.shown += lambda: window.maximize()
    webview.start()
    if api.installation_failed:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
