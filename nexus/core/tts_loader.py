# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Extracted for modularization and compliance with token limits.

import os
import time
import logging
import subprocess
import torch
import gc

_QWEN3_INSTANCE = None
_VOICE_PROMPT_CACHE = {}

def get_qwen3_engine():
    global _QWEN3_INSTANCE
    # model_lock is injected dynamically via namespace patch
    with model_lock:
        if _QWEN3_INSTANCE is None:
            try:
                try:
                    torch.set_num_threads(1)
                except:
                    pass
                
                device = "cuda:0" if torch.cuda.is_available() else "cpu"
                
                # Caminho para o modelo PyTorch de 1.7B
                model_dir_17b = "c:/IA_dublagem/_MODELS_/qwen3_1.7b_pytorch"
                model_dir_06b = "c:/IA_dublagem/_MODELS_/qwen3_0.6b"
                
                # Se o CUDA estiver ativo e não estiver forçado o uso do 0.6B, prioriza o de 1.7B
                force_06b = os.path.exists("C:/IA_dublagem/usar_qwen_06b.txt")
                
                # Escolhe qual modelo carregar
                if force_06b:
                    chosen_model_dir = model_dir_06b
                    model_id_hf = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
                    model_label = "0.6B"
                else:
                    chosen_model_dir = model_dir_17b
                    model_id_hf = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
                    model_label = "1.7B"

                if torch.cuda.is_available():
                    if not os.path.exists(os.path.join(chosen_model_dir, "model.safetensors")):
                        logging.info(f"⏳ Modelo Qwen3-{model_label} PyTorch não encontrado. Iniciando download da HuggingFace...")
                        from huggingface_hub import snapshot_download
                        snapshot_download(
                            repo_id=model_id_hf,
                            local_dir=chosen_model_dir,
                            local_dir_use_symlinks=False
                        )
                        logging.info(f"✅ Download do PyTorch de {model_label} concluído!")

                    logging.info(f"🎙️ [NEXUS_VOICE] Despertando Qwen3-TTS {model_label} PyTorch via FasterQwen3TTS (CUDA Graphs) em: {device}")
                    from faster_qwen3_tts import FasterQwen3TTS
                    
                    _QWEN3_INSTANCE = FasterQwen3TTS.from_pretrained(
                        model_name=chosen_model_dir, 
                        device="cuda", 
                        dtype=torch.bfloat16,
                        attn_implementation="sdpa",
                        max_seq_len=2048
                    )
                    logging.info(f"✅ [NEXUS_VOICE] Qwen3-TTS {model_label} PyTorch via FasterQwen3TTS carregado com sucesso.")
                else:
                    # Sem CUDA: Fallback automático para o modelo PyTorch de 0.6B (CPU)
                    raise RuntimeError("GPU CUDA não disponível. Usando fallback de CPU.")
                    
            except Exception as e:
                import traceback
                logging.warning(f"⚠️ [NEXUS_VOICE] Falha ao carregar o motor via FasterQwen3TTS: {e}. Usando Fallback PyTorch 0.6B padrão...")
                try:
                    # Baixa o 0.6B se não existir localmente
                    if not os.path.exists(os.path.join(model_dir_06b, "model.safetensors")):
                        logging.info("⏳ Modelo Qwen3-0.6B não encontrado. Baixando...")
                        from huggingface_hub import snapshot_download
                        snapshot_download(
                            repo_id="Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                            local_dir=model_dir_06b,
                            local_dir_use_symlinks=False
                        )
                    
                    from qwen_tts import Qwen3TTSModel
                    dtype = torch.bfloat16
                    _QWEN3_INSTANCE = Qwen3TTSModel.from_pretrained(
                        model_dir_06b, 
                        device_map="cuda:0" if torch.cuda.is_available() else "cpu",
                        dtype=dtype,
                        attn_implementation="sdpa"
                    )
                    logging.info("✅ [NEXUS_VOICE] Fallback para Qwen3-TTS 0.6B (PyTorch) carregado com sucesso.")
                except Exception as fallback_err:
                    logging.error(f"❌ Falha crítica total no carregamento de TTS: {fallback_err}\n{traceback.format_exc()}")
                    return None
                    
    return _QWEN3_INSTANCE

def unload_qwen3_model():
    """Libera a VRAM ocupada pelo Qwen3 agressivamente."""
    global _QWEN3_INSTANCE
    with model_lock:
        if _QWEN3_INSTANCE is not None:
            logging.info("🧹 [VRAM_PURGE] Removendo Qwen3-TTS da GPU...")
            try:
                del _QWEN3_INSTANCE
                _QWEN3_INSTANCE = None
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                logging.info("✅ [VRAM_PURGE] Qwen3 descarregado.")
            except Exception as e:
                logging.warning(f"⚠️ Falha na limpeza do Qwen3: {e}")

def wait_for_vram_release(threshold_mb=4000, cb=None):
    """[v2026.VRAM_WATCHDOG] Aguarda a VRAM ser liberada (Geralmente após fechar o LM Studio)"""
    try:
        total_result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,nounits,noheader'], 
            capture_output=True, text=True, check=True
        )
        total_vram = int(total_result.stdout.strip().split('\n')[0])
        logging.info(f"💾 [VRAM WATCHDOG] VRAM Total detectada: {total_vram}MB")
        if total_vram <= 4500:
            threshold_mb = min(threshold_mb, 1500)
        elif total_vram <= 6500:
            threshold_mb = min(threshold_mb, 2500)
        elif total_vram <= 8500:
            threshold_mb = min(threshold_mb, 3500)
    except Exception as e:
        logging.warning(f"⚠️ Não foi possível ler a VRAM total via nvidia-smi: {e}")

    logging.info(f"⏳ [VRAM WATCHDOG] Aguardando liberação de memória (Alvo: >{threshold_mb}MB livres)...")
    if cb: cb(99, 1, "⚠️ Tradução concluída! FECHE O LM STUDIO para continuar.")
    
    while True:
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.free', '--format=csv,nounits,noheader'], 
                capture_output=True, text=True, check=True
            )
            free_vram = int(result.stdout.strip().split('\n')[0])
            logging.info(f"📊 [VRAM] Livre agora: {free_vram}MB | Necessário: {threshold_mb}MB")
            if free_vram >= threshold_mb:
                logging.info("✅ [VRAM] Memória liberada! Iniciando dublagem...")
                if cb: cb(100, 1, "VRAM OK! Iniciando Voz...")
                time.sleep(2)
                break
        except Exception as e:
            logging.warning(f"⚠️ Erro ao ler VRAM: {e}")
            break 
            
        time.sleep(10)
    return True
