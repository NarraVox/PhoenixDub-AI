# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Extracted for modularization and compliance with token limits.

import os
import time
import logging
import requests
import torch
import gc
from threading import RLock

gema_instance = None  # Alias de compatibilidade
_LOCAL_LLM_INSTANCE = None  # Alias de compatibilidade
gema_lock = RLock()  # Alias de compatibilidade
ai_global_lock = gema_lock  # Alias de compatibilidade

# Novos nomes limpos direcionados ao Qwen 3.5
qwen_instance = None
_LOCAL_QWEN_INSTANCE = None
qwen_lock = gema_lock

def start_llama_server_standalone(model_path, cb=None):
    """[v2026.LM_STUDIO_EDITION] Detector dedicado para LM Studio / Servidor Local"""
    logging.info("🎮 [NEXUS] Modo Servidor Ativado. Verificando porta 1234...")
    for i in range(1, 4):
        try:
            requests.get("http://127.0.0.1:1234/v1/models", timeout=1)
            logging.info("✅ [Super Motor] ONLINE e pronto para a RTX 3050.")
            if cb: cb(100, 1, "Motor de IA Online!")
            return True
        except:
            msg = f"⏳ [IA] Carregando motor Qwen 3.5... ({i}s/3s)"
            logging.info(msg)
            if cb: cb((i/3)*100, 1, msg)
            time.sleep(1)
            
    if cb: cb(0, 1, "ERRO: O motor de IA Qwen 3.5 demorou demais para ligar.")
    return False

def find_gemma_model_path():
    """[v2026.FLEXIBLE_MODEL_SCAN] Busca o modelo Qwen 3.5 em caminhos conhecidos ou por padrão curinga (wildcard)"""
    from pathlib import Path
    root = Path("C:/IA_dublagem")
    possible_paths = [
        root / "_MODELS_" / "Qwen3.5-4B-Q4_K_M.gguf",
        root / "Qwen3.5-4B-Q4_K_M.gguf",
        root / "_MODELS_" / "gemma-4-E4B-it-qat-UD-Q4_K_XL.gguf",
        root / "gemma-4-E4B-it-qat-UD-Q4_K_XL.gguf",
        root / "_MODELS_" / "gemma-4-E4B-it-Q4_K_M.gguf",
        root / "gemma-4-E4B-it-Q4_K_M.gguf",
        Path("_MODELS_/Qwen3.5-4B-Q4_K_M.gguf"),
        Path("Qwen3.5-4B-Q4_K_M.gguf"),
        Path("_MODELS_/gemma-4-E4B-it-Q4_K_M.gguf"),
        Path("gemma-4-E4B-it-Q4_K_M.gguf"),
        root / "uploads" / "_MODELS_" / "gemma-4-E4B-it-Q4_K_M.gguf",
        Path("uploads/_MODELS_/gemma-4-E4B-it-Q4_K_M.gguf")
    ]
    for p in possible_paths:
        if p.exists():
            return p
            
    search_dirs = [root / "_MODELS_", root, Path("_MODELS_"), Path("uploads/_MODELS_"), Path(".")]
    for d in search_dirs:
        if d.exists() and d.is_dir():
            qwen_files = list(d.glob("*Qwen3.5*.gguf")) + list(d.glob("*qwen*.gguf"))
            qwen_files = [f for f in qwen_files if "tts" not in f.name.lower() and "embed" not in f.name.lower() and "acestep" not in f.name.lower()]
            if qwen_files:
                logging.info(f"🔎 [NEXUS_SCAN] Modelo GGUF de Qwen 3.5 detectado e selecionado: {qwen_files[0].name}")
                return qwen_files[0]
                
            gguf_files = list(d.glob("*gemma-4*.gguf"))
            if gguf_files:
                logging.info(f"🔎 [NEXUS_SCAN] Modelo GGUF de Gemma 4 alternativo detectado e selecionado: {gguf_files[0].name}")
                return gguf_files[0]
                
    return None

find_qwen_model_path = find_gemma_model_path

def get_gemma_model(cb=None):
    """Retorna o motor Qwen 3.5 (Prioriza o Standalone B9093 Turbo)"""
    global gema_instance, _LOCAL_LLM_INSTANCE, gema_lock
    global qwen_instance, _LOCAL_QWEN_INSTANCE
    
    with gema_lock:
        if gema_instance is not None:
            return gema_instance
        if _LOCAL_LLM_INSTANCE is not None:
            gema_instance = _LOCAL_LLM_INSTANCE
            return gema_instance
            
    model_path = find_gemma_model_path()
    if not model_path:
        logging.error("❌ Modelo Qwen 3.5 não encontrado em nenhuma das pastas de sistema.")
        return None

    if start_llama_server_standalone(model_path, cb=cb):
        return "standalone_server"

    with gema_lock:
        try:
            from llama_cpp import Llama
            torch.cuda.empty_cache()
            gc.collect()
            logging.info("🚀 [NATIVO] Usando motor Qwen 3.5 local (Fallback)...")
            gema_instance = Llama(
                model_path=str(model_path),
                n_gpu_layers=-1,
                n_ctx=8192,
                n_threads=2,
                f16_kv=True,
                flash_attn=True,
                offload_kqv=True,
                use_mmap=False,
                main_gpu=0,
                n_batch=512,
                verbose=False
            )
            qwen_instance = gema_instance
            return gema_instance
        except Exception as e:
            logging.error(f"❌ Falha crítica no carregamento do Qwen 3.5: {e}")
            return None

get_qwen_model = get_gemma_model

def unload_gema_model():
    """Libera memória RAM ocupada pelo LLM Qwen 3.5 (v2026.RTX)."""
    global gema_instance, gema_lock, qwen_instance
    try:
        unload_local_gemma_engine()
        with gema_lock:
            if gema_instance is not None:
                logging.info("🧹 [MEMÓRIA] Descarregando Qwen 3.5 Local e limpando VRAM...")
                del gema_instance
                gema_instance = None
                qwen_instance = None
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                logging.info("✅ [MEMÓRIA] Qwen 3.5 removido. Placa de vídeo liberada.")
    except Exception as e:
        logging.warning(f"⚠️ [AVISO] Falha ao descarregar Qwen 3.5: {e}")

unload_qwen_model = unload_gema_model

def check_or_load_gemma_model(progress_callback=None):
    if progress_callback is None:
        progress_callback = lambda x: None

    progress_callback("Carregando motor de IA Qwen 3.5 local...")
    try:
        llm = get_gemma_model()
        if llm:
            logging.info("✅ Motor de IA Local Qwen 3.5 ativo.")
            progress_callback("Motor de IA Local Ativo!")
            return True
    except Exception as e:
        logging.warning(f"⚠️ Falha ao carregar motor local: {e}. Tentando conexões externas...")

    try:
        res = requests.get("http://127.0.0.1:8080/health", timeout=1)
        if res.status_code == 200:
            logging.info("🚀 Super Motor Qwen 3.5 ativo na porta 8080!")
            progress_callback("Motor Externo (8080) Online!")
            return True
    except: pass

    progress_callback("Verificando conexão com LM Studio (Porta 1234)...")
    try:
        res = requests.get("http://127.0.0.1:1234/v1/models", timeout=2)
        if res.status_code == 200:
            logging.info("✅ LM Studio detectado na porta 1234. Usando cérebro Qwen 3.5 externo.")
            progress_callback("LM Studio Conectado!")
            return True
    except: pass

    msg = "ERRO: IA não encontrada. Certifique-se de que o modelo 'Qwen3.5-4B-Q4_K_M.gguf' está baixado na pasta _MODELS_."
    logging.error(msg)
    progress_callback(msg)
    raise RuntimeError(msg)

check_or_load_qwen_model = check_or_load_gemma_model

def wait_for_gema_service(progress_callback=None):
    if progress_callback is None:
        progress_callback = lambda x: None

    max_seconds = 120
    interval = 3
    max_attempts = max_seconds // interval

    logging.info(f"⏳ [WAIT_FOR_ENGINE] Iniciando espera de sincronização com o motor Qwen 3.5 (limite: {max_seconds}s)...")
    progress_callback("Aguardando inicialização do motor de IA Qwen 3.5...")

    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            if check_or_load_gemma_model(progress_callback):
                logging.info(f"✅ [WAIT_FOR_ENGINE] Conexão com o motor Qwen 3.5 estabelecida com sucesso na tentativa {attempt}!")
                progress_callback("Motor de IA Qwen 3.5 conectado!")
                return True
        except Exception as e:
            last_err = e
            msg = f"⏳ Aguardando motor Qwen 3.5... ({attempt * interval}s/{max_seconds}s)"
            logging.warning(f"⚠️ [WAIT_FOR_ENGINE] Tentativa {attempt}/{max_attempts} falhou: {e}. Re-tentando em {interval}s...")
            progress_callback(msg)
            
        time.sleep(interval)

    error_msg = f"❌ [WAIT_FOR_ENGINE] Falha crítica: O motor Qwen 3.5 não ficou pronto após {max_seconds} segundos."
    if last_err:
        error_msg += f" Último erro: {last_err}"
    logging.error(error_msg)
    progress_callback(error_msg)
    if last_err:
        raise last_err
    else:
        raise RuntimeError(error_msg)

wait_for_qwen_service = wait_for_gema_service

def get_local_gemma_engine(model_path=None):
    global _LOCAL_LLM_INSTANCE, gema_instance
    global _LOCAL_QWEN_INSTANCE, qwen_instance
    
    if _LOCAL_LLM_INSTANCE: return _LOCAL_LLM_INSTANCE
    if gema_instance and gema_instance != "standalone_server":
        _LOCAL_LLM_INSTANCE = gema_instance
        _LOCAL_QWEN_INSTANCE = gema_instance
        return _LOCAL_LLM_INSTANCE
        
    try:
        from llama_cpp import Llama
        if not model_path:
            p = find_gemma_model_path()
            if p:
                model_path = str(p)
        
        if not model_path or not os.path.exists(model_path):
            logging.error(f"❌ [ERRO] MODELO NÃO ENCONTRADO!")
            logging.error(f"👉 Por favor, coloque um arquivo do Qwen 3.5 (ex: 'Qwen3.5-4B-Q4_K_M.gguf') em: C:/IA_dublagem/_MODELS_")
            return None
  
        vram_before = 0
        if torch.cuda.is_available():
            vram_before, _ = torch.cuda.mem_get_info()

        logging.info(f"🧠 [NEXUS_LOCAL] Carregando motor Qwen 3.5 interno: {model_path}...")
        
        os.environ["GGML_CUDA_NO_PINNED"] = "0"
        _LOCAL_LLM_INSTANCE = Llama(
            model_path=model_path,
            n_gpu_layers=-1,
            n_ctx=8192,
            n_threads=2,
            f16_kv=True,
            flash_attn=True,
            offload_kqv=True,
            verbose=False,
            use_mmap=False,
            main_gpu=0,
            n_batch=512
        )
        _LOCAL_QWEN_INSTANCE = _LOCAL_LLM_INSTANCE
        
        time.sleep(0.5)
        
        if torch.cuda.is_available():
            vram_after, total_vram = torch.cuda.mem_get_info()
            vram_delta = (vram_before - vram_after) / (1024**2)
            gpu_name = torch.cuda.get_device_name(0)
            
            if vram_delta > 50:
                logging.info(f"🚀 [RTX_TURBO] Hardware: {gpu_name} | VRAM Delta: +{vram_delta:.0f}MB | Status: GPU_ACTIVE")
            else:
                msg = f"❌ [BLOQUEIO_DE_HARDWARE] A RTX 3050 FOI REJEITADA! Delta: {vram_delta:.0f}MB."
                logging.error(msg)
                logging.error("👉 O motor Qwen 3.5 tentou usar o processador, o que é PROIBIDO nesta versão.")
                logging.error("👉 Verifique se há outros programas usando a GPU ou se o driver NVIDIA está atualizado.")
                _LOCAL_LLM_INSTANCE = None
                _LOCAL_QWEN_INSTANCE = None
                raise RuntimeError("RTX_REJECTED_BY_SYSTEM")
        else:
            logging.error("❌ [NEXUS_LOCAL] ERRO CRÍTICO: Driver NVIDIA não encontrado!")
            raise RuntimeError("NVIDIA_DRIVER_NOT_FOUND")
            
        return _LOCAL_LLM_INSTANCE
    except Exception as e:
        logging.error(f"❌ Erro ao inicializar Llama-cpp: {e}")
        if "RTX_REJECTED" in str(e) or "NVIDIA" in str(e):
            raise e
        return None

get_local_qwen_engine = get_local_gemma_engine

def unload_local_gemma_engine():
    global _LOCAL_LLM_INSTANCE, _LOCAL_QWEN_INSTANCE
    if _LOCAL_LLM_INSTANCE:
        logging.info("🧹 [VRAM_PURGE] Expulsando motor Qwen 3.5 da GPU...")
        try:
            if hasattr(_LOCAL_LLM_INSTANCE, '__del__'):
                _LOCAL_LLM_INSTANCE.__del__()
            del _LOCAL_LLM_INSTANCE
            _LOCAL_LLM_INSTANCE = None
            _LOCAL_QWEN_INSTANCE = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
            logging.info("✅ [VRAM_PURGE] VRAM do Qwen 3.5 liberada com sucesso.")
        except Exception as e:
            logging.warning(f"⚠️ Erro parcial ao liberar motor Qwen 3.5: {e}")

unload_local_qwen_engine = unload_local_gemma_engine
