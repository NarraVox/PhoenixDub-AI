# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# =====================================================================
# [v2026.INTEL] OPTIMIZATION LAYER (SKYLAKE READY)
# =====================================================================
import os
import sys
import pathlib
import shutil
import logging
import numpy as np

# [v2026.NUMPY_FIX] Conserto global para o bug do Numpy 2.0+ que quebra o Pyannote nativo
if not hasattr(np, 'NAN'):
    np.NAN = np.nan

# [v2026.ENVIRONMENT_PURGE] Remove apenas bibliotecas externas "impostoras"
try:
    from pathlib import Path
    base_env = Path(sys.executable).parent.parent
    local_site = base_env / "Lib" / "site-packages"
    sys.path = [p for p in sys.path if not ("AppData" in p and "site-packages" in p)]
    if str(local_site) not in sys.path:
        sys.path.insert(0, str(local_site))
except Exception as e:
    print(f"⚠️ [FALHA_ISOLAMENTO] Erro ao limpar caminhos: {e}")

# [v2026.DLL_PANIC_FIX] Força bruta para encontrar a RTX 3050 (OPTIMIZED & SILENT)
try:
    import ctypes
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
    os.environ["GGML_CUDA_NO_PINNED"] = "0"
except Exception:
    pass

# --- PATCH DE COMPATIBILIDADE MASTER: WINDOWS SYMLINK BYPASS (v2026.90) ---
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import torch
import gc
from threading import RLock

# Locks globais e infraestrutura básica exportada para os submódulos
model_lock = RLock()

# Funções utilitárias básicas do hardware
def get_optimal_device(required_free_gb=1.5):
    """Escolhe CUDA quando o modelo cabe sob o teto de 90%; caso contrário, CPU."""
    import torch
    if torch.cuda.is_available() and torch.cuda.device_count() > 0:
        device_idx = torch.cuda.current_device()
        if ensure_vram_safety("seleção de dispositivo", required_free_gb=required_free_gb):
            logging.info(f"🚀 [RTX_LOCKED] Hardware Identificado. Usando CUDA:{device_idx}.")
            return f"cuda:{device_idx}"
        logging.warning("⚠️ VRAM sem margem segura; usando CPU para esta etapa.")
    logging.info("💻 [MODO CPU] NVIDIA ausente ou sem margem segura; usando processador nesta etapa.")
    return "cpu"

def get_vram_usage():
    """Retorna o uso atual de VRAM em GB"""
    import torch
    if not torch.cuda.is_available(): return 0.0
    free_m, total_m = torch.cuda.mem_get_info()
    return (total_m - free_m) / (1024**3)

def get_vram_stats():
    """Retorna VRAM livre/total da GPU em GiB, incluindo uso de outros processos."""
    if not torch.cuda.is_available():
        return None, None
    free_m, total_m = torch.cuda.mem_get_info()
    return free_m / (1024**3), total_m / (1024**3)

def ensure_system_memory_safety(label="Processo", min_free_gb=4.0):
    """Preserva 4 GiB de RAM para Windows e bloqueia nova carga acima de 90%."""
    import psutil
    memory = psutil.virtual_memory()
    free_gb = memory.available / (1024**3)
    if memory.percent >= 90 or free_gb < min_free_gb:
        logging.error(
            "❌ [GUARDIÃO RAM] %s bloqueado: %.1f%% em uso, %.2f GiB livres; "
            "requer menos de 90%% e pelo menos %.1f GiB livres.",
            label, memory.percent, free_gb, min_free_gb)
        return False
    return True

def ensure_vram_safety(label="Processo", required_free_gb=0.0):
    """Não inicia uma etapa CUDA se a reserva prevista ultrapassar 90% da VRAM."""
    import time
    required_free_gb = max(0.0, float(required_free_gb))
    for attempt in range(4):
        try:
            free_gb, total_gb = get_vram_stats()
        except Exception as exc:
            logging.error("❌ [GUARDIÃO VRAM] Não foi possível ler a VRAM para %s: %s", label, exc)
            return False
        if total_gb is None:
            logging.warning("⚠️ [GUARDIÃO VRAM] CUDA indisponível durante %s.", label)
            return required_free_gb == 0
        used_gb = total_gb - free_gb
        max_safe_gb = total_gb * 0.95
        if free_gb >= required_free_gb and (used_gb + required_free_gb) <= max_safe_gb:
            return True
        logging.warning(
            "⚠️ [GUARDIÃO VRAM] %s aguardando margem: %.2f/%.2f GiB usados; "
            "reserva %.2f GiB; teto 95%% (%.2f GiB).",
            label, used_gb, total_gb, required_free_gb, max_safe_gb)
        if attempt == 0:
            unload_whisper_model()
        gc.collect()
        torch.cuda.empty_cache()
        time.sleep(1)

    logging.error("❌ [GUARDIÃO VRAM] VRAM insuficiente para %s; etapa bloqueada para evitar OOM.", label)
    return False

# Importações seletivas dos submódulos para manter 100% de retrocompatibilidade
from nexus.core.whisper_loader import whisper_model, get_whisper_model, unload_whisper_model
from nexus.core.qwen_loader import gema_instance, _LOCAL_LLM_INSTANCE, gema_lock, ai_global_lock, get_gemma_model, unload_gema_model, check_or_load_gemma_model, wait_for_gema_service, get_local_gemma_engine, unload_local_gemma_engine, start_llama_server_standalone, find_gemma_model_path
from nexus.core.tts_loader import _QWEN3_INSTANCE, _VOICE_PROMPT_CACHE, get_qwen3_engine, unload_qwen3_model, wait_for_vram_release

# Alias para compatibilidade total
get_llama_instance = get_gemma_model
get_qwen3_model = get_qwen3_engine

def prewarm_audio_engines():
    try:
        import sys
        import types
        import logging
        
        logging.info("[INFO] Iniciando Pre-warm e Protecao de Memoria...")
        
        import speechbrain
        try:
            import speechbrain.utils.quirks
            import speechbrain.utils.importutils
        except: pass

        stubs = ['speechbrain.integrations.numba', 'speechbrain.integrations.numba.transducer_loss']
        for stub in stubs:
            if stub not in sys.modules:
                sys.modules[stub] = types.ModuleType(stub)
        
        os.environ["SB_DISABLE_QUIRKS"] = "1"
        import speechbrain.inference
        logging.info("[OK] Motores blindados e prontos.")
    except Exception as e:
        logging.warning(f"[AVISO] Aviso no Pre-warm: {e}")

def cleanup_on_exit():
    """Limpa processos residuais para liberar a VRAM"""
    try:
        import subprocess
        subprocess.run(['taskkill', '/F', '/IM', 'llama-server.exe', '/T'], capture_output=True)
    except:
        pass
