import logging
import os
import random
import subprocess
import sys
import threading
import time
import atexit
from pathlib import Path

# Configurações globais do YuE2Backend - CLI CUDA direto
AUDIO_CPP_CLI = r"C:\IA_dublagem\env\tools_yue2\audio-v0.8.0-bin-windows-x64-cuda12.4\audiocpp_cli.exe"
CUDA_DLL_DIR = r"C:\IA_dublagem\env\tools_yue2\audio-v0.8.0-cudart-windows-x64-cuda12.4"

# Lista global para rastrear processos iniciados pelo Nexus DJ (para limpeza em atexit)
_audio_cpp_processes = []

def cleanup_audio_processes():
    """Limpa todos os processos de audiocpp_cli.exe registrados durante shutdown."""
    for pid in list(_audio_cpp_processes):
        try:
            # taskkill por PID em Windows
            subprocess.run(['taskkill', '/PID', str(pid), '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Remove PID da lista após tentar matar (evita duplicação)
            _audio_cpp_processes.remove(pid)
        except Exception:
            pass

# Registra cleanup automático ao encerrar o Python (fechamento da janela, SystemExit, etc.)
atexit.register(cleanup_audio_processes)


class YuE2Backend:
    """YuE2 Backend para Nexus DJ - usa audio.cpp CLI CUDA v0.8.0 diretamente sem servidor HTTP."""

    def __init__(self):
        self.logger = logging.getLogger("YuE2Backend")
        # Registra PIDs dos subprocessos criados durante a vida deste backend
        self._registered_pids = []

    def prepare_command(self, lyrics_list, style_str=None, target_tokens=None, seed=None, abc_file=None, cot="off"):
        """Build the exact CLI invocation without starting model inference."""
        model_gguf_path = "yue2-3b-q4_k_m.gguf"
        vae_gguf_path = "yue2-vae-f16.gguf"
        lyrics_str = "".join(lyrics_list) if isinstance(lyrics_list, list) else str(lyrics_list)
        command = [
            AUDIO_CPP_CLI, "--backend", "cuda", "--task", "gen", "--threads", "8",
            "--family", "yue2", "--model", "C:\\IA_dublagem\\MODELS",
            "--session-option", f"yue2.model_gguf={model_gguf_path}",
            "--session-option", f"yue2.vae_gguf={vae_gguf_path}",
            "--lyrics", lyrics_str, "--request-option", f"style={style_str or ''}",
            "--request-option", f"cot={cot}", "--seed", str(seed if seed is not None else random.randint(1, 1000000)),
            "--out", "yue2_output.wav", "--log",
        ]
        if target_tokens is not None:
            semantic_max = max(round(int(target_tokens) * 6), int(target_tokens) + 512)
            command.extend(["--request-option", f"semantic_min_tokens={int(target_tokens * 0.9)}",
                            "--request-option", f"semantic_max_tokens={semantic_max}"])
        if abc_file:
            command.extend(["--request-option", f"abc_file={os.fspath(abc_file)}"])
        return command

    def generate_music(self, lyrics_list, style_str=None, target_tokens=None, abc_file=None, cot="off"):
        """Generate music via audiocpp_cli.exe com YuE2 Q4_K_M + VAE F16.
        
        Args:
            lyrics_list: str ou list[str] de letras
            style_str: estilo (string)
            target_tokens: duração convertida para tokens (estimativa 25 tokens/segundo). 
                        Se fornecido, ajusta min/max tokens com ±10%.
        
        Retorna dicionário consistente compatível com vortex_music.py:
        {"success": bool, "id": str | None, "audio_data": bytes | None, "message": str}
        Nunca retorna None para evitar AttributeError em vortex_music.py
        """

        # Paths dos modelos - caminhos relativos ao model_root (documentação oficial confirma)
        model_gguf_path = "yue2-3b-q4_k_m.gguf"
        vae_gguf_path = "yue2-vae-f16.gguf"
        
        # Se lyrics_list for list, junta; se str, usa como está
        if isinstance(lyrics_list, list):
            lyrics_str = "".join(lyrics_list)
        else:
            lyrics_str = str(lyrics_list)

        self.logger.info(f"🎵 [Geração] Lyrics ({len(lyrics_str)} chars), Style: {style_str[:50]}...")

        command = self.prepare_command(lyrics_str, style_str, target_tokens, abc_file=abc_file, cot=cot)
        
        self.logger.info(f"🚀 [COMANDO] {' '.join(command)}")

        try:
            # Configurações de subprocesso para Windows (CREATE_NO_WINDOW) e PATH CUDA
            creation_flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            
            env = os.environ.copy()
            env['PATH'] = f"{CUDA_DLL_DIR};{env['PATH']}"
            process_id = None

            # Executa o CLI diretamente - logs em tempo real via threading
            self.logger.info(f"⚙️  [EXEC] Iniciando subprocesso do CLI (PID não aplicável para wait)")
            
            # Lista compartilhada para thread de logging escrever em tempo real
            log_lines = []

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,  # Python 3.7+: retorna strings UTF-8
                creationflags=creation_flags,
                env=env,
                start_new_session=True,  # Cria novo session group para facilitar limpeza em Windows
                cwd=None
            )
            process_id = process.pid

            # Registra PID para cleanup global (atexit)
            _audio_cpp_processes.append(process_id)

            # Threads separadas para stdout e stderr em tempo real
            log_stdout_thread = threading.Thread(target=log_stdout_thread_func, args=(process,), daemon=True)
            log_stderr_thread = threading.Thread(target=log_stderr_thread_func, args=(process,), daemon=True)
            log_stdout_thread.start()
            log_stderr_thread.start()

            try:
                # Espera processo terminar (thread já está lendo logs em background)
                process.wait()
                # Remove PID da lista após processo terminar normalmente
                try:
                    _audio_cpp_processes.remove(process_id)
                except ValueError:
                    pass  # Já removido ou não estava na lista
                exit_code = process.returncode

                # Aguarda thread de logging finalizar
                log_stdout_thread.join(timeout=1.0)  # Espera até 1s após processo terminar
                log_stderr_thread.join(timeout=1.0)
            except KeyboardInterrupt:
                # Tratamento de cancelamento: encerra o subprocesso imediatamente
                self.logger.warning("⚠️  [INTERRUPÇÃO] Usuário cancelou a geração - encerrando audiocpp_cli...")
                process.kill()
                exit_code = 1
                raise

            # Validação do resultado
            success = (exit_code == 0) and (Path("yue2_output.wav").exists())

            result = {}

            if success:
                # Lê o arquivo WAV gerado
                try:
                    audio_data = Path("yue2_output.wav").read_bytes()
                    self.logger.info(f"✅ [SUCESSO] WAV gerado ({len(audio_data)} bytes)")

                    result = {
                        "success": True,
                        "id": f"{int(time.time())}_{random.randint(1000, 9999)}",  # Compatibilidade com vortex
                        "audio_data": audio_data,
                        "message": f"Gerado com sucesso (exit_code={exit_code})",
                        "model_used": f"{model_gguf_path} ({'Q4_K_M' if 'q4_k_m' in model_gguf_path.lower() else 'quantização desconhecida'})",
                        "vae_used": vae_gguf_path,
                        "seed": random.randint(1, 1000000)
                    }
                except Exception as e:
                    self.logger.error(f"❌ [ERRO] Falha ao ler arquivo WAV gerado: {e}")
                    result = {
                        "success": False,
                        "id": None,
                        "audio_data": None,
                        "message": f"Arquivo WAV gerado mas falhou ao ser lido: {str(e)}",
                        "error_detail": str(e)
                    }

            else:
                # Constrói mensagem de erro detalhada
                output_summary = ""
                
                result = {
                    "success": False,
                    "id": None,
                    "audio_data": None,
                    "message": f"Geração falhou (exit_code={exit_code})",
                    "error_detail": "Logs disponíveis no console em tempo real.",
                    "command_used": command
                }

            return result

        except FileNotFoundError as e:
            self.logger.error(f"❌ [CRITICAL] Executável não encontrado:")
            self.logger.error(f"  Comando: {' '.join(command)}")
            self.logger.error(f"  CUDA_DLL_DIR: {CUDA_DLL_DIR}")
            import traceback
            self.logger.error(traceback.format_exc())

            return {
                "success": False,
                "id": None,
                "audio_data": None,
                "message": f"Executável não encontrado: {str(e)}",
                "error_detail": str(e)
            }

        except Exception as e:
            self.logger.error(f"❌ [CRITICAL] Exceção durante geração: {type(e).__name__}: {repr(e)}")
            import traceback
            self.logger.error(traceback.format_exc())

            return {
                "success": False,
                "id": None,
                "audio_data": None,
                "message": f"Exceção durante geração: {str(e)}",
                "error_detail": str(e)
            }


# Funções de thread para logging em tempo real
def log_stdout_thread_func(process):
    """Thread que lê stdout em tempo real e imprime no console."""
    with process.stdout as stdout:
        for line in stdout:
            if line:
                print(line, end='', flush=True)


def log_stderr_thread_func(process):
    """Thread que lê stderr em tempo real e imprime no console."""
    with process.stderr as stderr:
        for line in stderr:
            if line:
                print(line, end='', flush=True)


# Mantém referências para documentação e debugging
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    backend = YuE2Backend()
    print("YuE2Backend carregado. Usar backend.generate_music(lyrics_list, style_str)")
