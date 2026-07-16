# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import os
import sys
import io
import pathlib
import shutil
import logging
import warnings
import platform
import ctypes
import threading
import types
import psutil
import gc
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Força o terminal a aceitar UTF-8 no Windows para evitar quedas por emojis
if sys.platform == "win32" and not getattr(sys.stdout, '_utf8_wrapped', False):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        sys.stdout._utf8_wrapped = True
    except Exception:
        pass

# [v2026.ENVIRONMENT_PURGE] Remove apenas bibliotecas externas "impostoras"
try:
    base_env = Path(sys.executable).parent.parent
    local_site = base_env / "Lib" / "site-packages"
    sys.path = [p for p in sys.path if not ("AppData" in p and "site-packages" in p)]
    if str(local_site) not in sys.path:
        sys.path.insert(0, str(local_site))
except Exception as e:
    print(f"⚠️ [FALHA_ISOLAMENTO] Erro ao limpar caminhos: {e}")

# [v2026.DLL_PANIC_FIX] Força bruta para encontrar a RTX 3050 (OPTIMIZED & SILENT)
try:
    base_env = Path(sys.executable).parent.parent
    site_packages = base_env / "Lib" / "site-packages"
    dll_paths = [
        site_packages / "llama_cpp" / "lib",
        site_packages / "nvidia" / "cublas" / "bin",
        site_packages / "nvidia" / "cuda_runtime" / "bin",
        site_packages / "nvidia" / "cuda_nvrtc" / "bin"
    ]
    for p in dll_paths:
        if p.exists():
            os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                try: os.add_dll_directory(str(p))
                except: pass
            try: ctypes.windll.kernel32.SetDllDirectoryW(str(p))
            except: pass
    os.environ["LLAMA_CUDA"] = "1"
    os.environ["GGML_CUDA_NO_PINNED"] = "1"
except Exception:
    pass

# --- PATCH DE COMPATIBILIDADE MASTER: WINDOWS SYMLINK BYPASS (v2026.90) ---
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

def _patched_symlink_to(self, target, target_is_directory=False):
    try:
        _original_symlink_to(self, target, target_is_directory)
    except OSError as e:
        if getattr(e, 'winerror', 0) == 1314:
            target_path = pathlib.Path(target)
            if not target_path.is_absolute():
                abs_target = (self.parent / target_path).resolve()
            else:
                abs_target = target_path.resolve()
            
            if abs_target.exists():
                if abs_target.is_dir():
                    shutil.copytree(abs_target, self, dirs_exist_ok=True)
                else:
                    shutil.copy2(abs_target, self)
        else:
            raise

_original_symlink_to = pathlib.Path.symlink_to
pathlib.Path.symlink_to = _patched_symlink_to

# --- PATCH DE COMPATIBILIDADE API: HUGGINGFACE HUB (v2026.RTX) ---
try:
    import huggingface_hub
    _original_hf_hub_download = huggingface_hub.hf_hub_download
    def _patched_hf_hub_download(*args, **kwargs):
        if 'use_auth_token' in kwargs:
            kwargs['token'] = kwargs.pop('use_auth_token')
        try:
            return _original_hf_hub_download(*args, **kwargs)
        except Exception as e:
            arg_str = str(args) + str(kwargs)
            if "custom.py" in arg_str:
                logging.warning(f"⚠️ [HF_PATCH] Ignorando falha em arquivo opcional custom.py: {e}")
                raise FileNotFoundError("Arquivo opcional não encontrado no servidor.")
            raise e
    huggingface_hub.hf_hub_download = _patched_hf_hub_download
except:
    pass

# Performance tuning
os.environ["KMP_AFFINITY"] = "granularity=fine,compact,1,0"
os.environ["OMP_NUM_THREADS"] = str(os.cpu_count() or 4)
os.environ["MKL_NUM_THREADS"] = str(os.cpu_count() or 4)
os.environ["KMP_BLOCKTIME"] = "1"
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"
os.environ["SPEECHBRAIN_FETCH_STRATEGY"] = "COPY"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["COQUI_TOS_AGREED"] = "1"

warnings.filterwarnings("ignore", category=UserWarning, module="speechbrain")
warnings.filterwarnings("ignore", message="Module 'speechbrain.*' was deprecated")

# SpeechBrain Stub logic
class MockModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        return MockModule(name)
    def __call__(self, *args, **kwargs):
        return MockModule("dummy")

stubs = [
    'speechbrain.integrations.numba', 
    'speechbrain.integrations.numba.transducer_loss',
    'speechbrain.integrations.k2_fsa',
    'speechbrain.integrations.nlp',
    'speechbrain.integrations.huggingface',
    'speechbrain.integrations.huggingface.wordemb',
    'speechbrain.integrations.huggingface.g2p',
    'speechbrain.integrations.huggingface.whisper'
]
for stub in stubs:
    sys.modules[stub] = MockModule(stub)

# --- LOGGING SETUP ---
script_name = "nexus_generic"
try:
    import __main__
    if hasattr(__main__, "__file__") and __main__.__file__:
        script_name = Path(__main__.__file__).stem
except Exception:
    pass

if not script_name or script_name in ["-m", "nexus_generic"]:
    try:
        script_name = Path(sys.argv[0]).stem
        if script_name == "-m" and len(sys.argv) > 1:
            script_name = sys.argv[1].split('.')[-1]
    except Exception:
        pass

if not script_name or script_name.strip() in ["-m", ""]:
    script_name = "nexus_generic"

log_path = Path("c:/IA_dublagem/logs")
log_path.mkdir(exist_ok=True)
current_log_file = log_path / f"{script_name}.log"

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        stream_handler,
        RotatingFileHandler(str(current_log_file), encoding='utf-8', maxBytes=2*1024*1024, backupCount=1)
    ]
)

logging.getLogger("chatterbox").setLevel(logging.ERROR)
logging.getLogger("werkzeug").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", message=".*Reference mel length is not equal.*")
warnings.filterwarnings("ignore", message=".*is_causal.*")

def log_uncaught(exctype, value, tb):
    logging.critical("ERRO NÃO TRATADO (CRASH):", exc_info=(exctype, value, tb))

sys.excepthook = log_uncaught

logging.getLogger('numba').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('torchaudio').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

def set_low_process_priority():
    try:
        p = psutil.Process(os.getpid())
        p.nice(psutil.NORMAL_PRIORITY_CLASS if sys.platform == "win32" else 0)
        logging.info("Prioridade do processo definida como 'normal' para garantir estabilidade.")
    except Exception:
        pass

def check_ffmpeg():
    import subprocess
    local_full_bin = os.path.join(os.getcwd(), 'env', 'Library', 'bin', 'ffmpeg.exe')
    if os.path.exists(local_full_bin):
        logging.info(f"FFmpeg FULL detectado na pasta local: {local_full_bin}")
        os.environ["PATH"] = os.path.dirname(local_full_bin) + os.pathsep + os.environ["PATH"]
        return True
    try:
        output = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, shell=True)
        if 'libmp3lame' in output.stdout:
            logging.info("FFmpeg (Full c/ MP3) encontrado no PATH.")
            return True
        else:
            logging.warning("⚠️ FFmpeg do PATH não tem suporte a MP3 (libmp3lame).")
    except:
        pass
    logging.error("❌ ERRO CRÍTICO: FFmpeg FULL não encontrado!")
    return False

def check_lm_studio():
    model_path = Path("uploads/_MODELS_/gemma-4-E4B-it-Q4_K_M.gguf")
    if model_path.exists():
        logging.info(f"Cérebro IA (Gemma 4) detectado localmente: {model_path}")
        return True
    else:
        logging.warning(f"⚠️ AVISO: Modelo GGUF não encontrado em {model_path}")
        return False
