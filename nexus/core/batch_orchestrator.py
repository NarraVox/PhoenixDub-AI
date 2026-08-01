"""
Batch Stage Orchestrator - NarraVox / PhoenixDub AI
Processa múltiplas pastas/jobs em lote por estágios de IA:
- Estágio 1: Transcrição & Diarização (Whisper ASR)
- Estágio 2: Tradução & Sanitização (Gemma / Qwen3.5 LLM)
- Estágio 3: Geração de Voz (Qwen3-TTS)
- Estágio 4: LQA, Sincronia & Masterização Final

Evita trocas e descarregamentos repetitivos de modelos de IA na VRAM (RTX 3050 6GB target).
"""

import os
import sys
import time
import gc
import logging
import threading
from pathlib import Path

from nexus.core import utils
from nexus.core.utils import safe_json_read, safe_json_write, set_progress
from nexus.core import (
    unload_whisper_model,
    unload_qwen3_model,
    unload_gema_model,
    unload_local_gemma_engine
)

_batch_queue_lock = threading.Lock()
_active_batch_queue = []
_is_batch_running = False

def purge_vram():
    logging.info("🧹 [BATCH VRAM] Realizando limpeza preventiva de VRAM...")
    try:
        unload_whisper_model()
        unload_qwen3_model()
        unload_gema_model()
        unload_local_gemma_engine()
        gc.collect()
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception as e:
        logging.warning(f"[BATCH VRAM] Aviso ao limpar VRAM: {e}")

def enqueue_batch_jobs(job_list):
    """
    job_list: lista de dicts com [{'job_id': ..., 'job_dir': Path, 'start_time': float}]
    """
    global _active_batch_queue, _is_batch_running
    with _batch_queue_lock:
        for job_info in job_list:
            if not any(j['job_id'] == job_info['job_id'] for j in _active_batch_queue):
                _active_batch_queue.append(job_info)
        
        logging.info(f"📋 [BATCH QUEUE] {len(job_list)} novo(s) job(s) adicionados à fila. Total na fila: {len(_active_batch_queue)}")
        
        if not _is_batch_running:
            _is_batch_running = True
            t = threading.Thread(target=_run_batch_pipeline_worker, daemon=True)
            t.start()
            logging.info("🚀 [BATCH QUEUE] Thread do Orquestrador em Lote iniciada.")

def _run_batch_pipeline_worker():
    global _active_batch_queue, _is_batch_running
    try:
        while True:
            with _batch_queue_lock:
                if not _active_batch_queue:
                    _is_batch_running = False
                    logging.info("✅ [BATCH QUEUE] Fila concluída. Nenhum job pendente.")
                    break
                current_batch = list(_active_batch_queue)
                _active_batch_queue.clear()
            
            _execute_stage_batch_pipeline(current_batch)
    except Exception as e:
        logging.critical(f"❌ [BATCH QUEUE] Erro fatal no executor em lote: {e}", exc_info=True)
    finally:
        with _batch_queue_lock:
            _is_batch_running = False

def _execute_stage_batch_pipeline(jobs_list):
    total_jobs = len(jobs_list)
    logging.info(f"🔄 [BATCH PIPELINE] Executando pipeline em lote para {total_jobs} pasta(s)...")

    # =========================================================================
    # ESTÁGIO 1: Transcrição & Diarização (Whisper ASR)
    # =========================================================================
    purge_vram()
    logging.info("🎙️ [BATCH ESTÁGIO 1/4] Transcrição & Diarização Whisper...")
    from nexus.core.diarization import run_auto_diarization_batch

    for idx, job in enumerate(jobs_list, start=1):
        j_id, j_dir, st = job['job_id'], job['job_dir'], job['start_time']
        logging.info(f"➔ [BATCH ESTÁGIO 1] Processando {idx}/{total_jobs}: {j_id}")
        
        def cb(p, etapa, s=None, **kwargs):
            sub_msg = f"[Lote {idx}/{total_jobs}] {s or ''}"
            set_progress(j_id, p, 1, st, utils.ETAPAS_JOGOS, subetapa=sub_msg, **kwargs)

        try:
            run_auto_diarization_batch(j_dir, j_id, cb)
        except Exception as e:
            logging.error(f"❌ [BATCH ESTÁGIO 1] Falha no job {j_id}: {e}")

    # =========================================================================
    # ESTÁGIO 2: Tradução & Sanitização (LLM Gemma / Qwen3.5)
    # =========================================================================
    purge_vram()
    logging.info("🌐 [BATCH ESTÁGIO 2/4] Tradução & Sincronização de Texto (LLM)...")
    from nexus.core.orchestrator_jobs_games import processar_dublagem_jogos

    for idx, job in enumerate(jobs_list, start=1):
        j_id, j_dir, st = job['job_id'], job['job_dir'], job['start_time']
        logging.info(f"➔ [BATCH ESTÁGIO 2] Traduzindo {idx}/{total_jobs}: {j_id}")
        
        def cb(p, etapa, s=None, **kwargs):
            sub_msg = f"[Lote {idx}/{total_jobs}] {s or ''}"
            set_progress(j_id, p, 3, st, utils.ETAPAS_JOGOS, subetapa=sub_msg, **kwargs)

        try:
            # Executa apenas as fases de tradução salvando project_data.json
            processar_dublagem_jogos(j_dir, j_id, st, stop_after_stage=5)
        except Exception as e:
            logging.error(f"❌ [BATCH ESTÁGIO 2] Falha na tradução do job {j_id}: {e}")

    # =========================================================================
    # ESTÁGIO 3: Geração de Voz (Qwen3-TTS)
    # =========================================================================
    purge_vram()
    logging.info("🗣️ [BATCH ESTÁGIO 3/4] Geração de Áudios (Qwen3-TTS)...")

    for idx, job in enumerate(jobs_list, start=1):
        j_id, j_dir, st = job['job_id'], job['job_dir'], job['start_time']
        logging.info(f"➔ [BATCH ESTÁGIO 3] Gerando vozes {idx}/{total_jobs}: {j_id}")

        def cb(p, etapa, s=None, **kwargs):
            sub_msg = f"[Lote {idx}/{total_jobs}] {s or ''}"
            set_progress(j_id, p, 6, st, utils.ETAPAS_JOGOS, subetapa=sub_msg, **kwargs)

        try:
            processar_dublagem_jogos(j_dir, j_id, st, start_from_stage=6, stop_after_stage=7)
        except Exception as e:
            logging.error(f"❌ [BATCH ESTÁGIO 3] Falha na geração TTS do job {j_id}: {e}")

    # =========================================================================
    # ESTÁGIO 4: LQA, Sincronia Profissional & Masterização Final
    # =========================================================================
    purge_vram()
    logging.info("🎛️ [BATCH ESTÁGIO 4/4] Sincronização Final & Masterização LQA...")

    for idx, job in enumerate(jobs_list, start=1):
        j_id, j_dir, st = job['job_id'], job['job_dir'], job['start_time']
        logging.info(f"➔ [BATCH ESTÁGIO 4] Masterizando {idx}/{total_jobs}: {j_id}")

        def cb(p, etapa, s=None, **kwargs):
            sub_msg = f"[Lote {idx}/{total_jobs}] {s or ''}"
            set_progress(j_id, p, 8, st, utils.ETAPAS_JOGOS, subetapa=sub_msg, **kwargs)

        try:
            processar_dublagem_jogos(j_dir, j_id, st, start_from_stage=8)
        except Exception as e:
            logging.error(f"❌ [BATCH ESTÁGIO 4] Falha na masterização do job {j_id}: {e}")

    logging.info(f"🎉 [BATCH PIPELINE] Fila concluída para {total_jobs} pasta(s) com isolamento total!")
