# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Extracted for modularization and compliance with token limits.

import os
import logging
import torch
import gc
from faster_whisper import WhisperModel

whisper_model = None

def get_whisper_model():
    global whisper_model
    # model_lock and get_optimal_device are injected dynamically via nexus.core namespace patch
    with model_lock:
        if whisper_model is None:
            device = get_optimal_device()
            total_threads = os.cpu_count() or 4
            
            if device.startswith("cuda"):
                w_threads = min(4, total_threads)
                logging.info(f"🚀 [HARDWARE] Whisper em CUDA (int8_float16) - MODO ULTRA: {w_threads} threads CPU de suporte.")
                whisper_model = WhisperModel("small", device="cuda", compute_type="int8_float16", cpu_threads=w_threads)
            else:
                w_threads = max(1, total_threads // 2)
                logging.info(f"💻 [HARDWARE] Whisper em CPU (int8) - MODO SEGURO: {w_threads} threads CPU.")
                whisper_model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=w_threads)
                
            logging.info("Modelo faster-whisper carregado.")
    return whisper_model

def unload_whisper_model():
    global whisper_model
    with model_lock:
        if whisper_model is not None:
            logging.info("🧹 [VRAM_PURGE] Expulsando Whisper da GPU...")
            try:
                del whisper_model
                whisper_model = None
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
                    torch.cuda.synchronize()
                logging.info("✅ [VRAM_PURGE] Whisper descarregado com sucesso.")
            except Exception as e:
                logging.warning(f"⚠️ Falha na limpeza do Whisper: {e}")
