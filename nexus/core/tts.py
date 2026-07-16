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
    import sys
    from pathlib import Path
    
    # Define o caminho do nosso ambiente de elite
    base_env = Path(sys.executable).parent.parent
    local_site = base_env / "Lib" / "site-packages"
    
    # Limpeza Seletiva: Remove APENAS o site-packages do AppData (onde moram os impostores)
    # Mas mantém a pasta 'Lib' (onde moram o glob, asyncio, etc)
    sys.path = [p for p in sys.path if not ("AppData" in p and "site-packages" in p)]
    
    # Insere o nosso site-packages como a PRIORIDADE ZERO
    if str(local_site) not in sys.path:
        sys.path.insert(0, str(local_site))
        
    # print(f"🛡️ [NEXUS_ISOLATION] Ambiente blindado e seletivo. Local: {local_site.name}")

except Exception as e:
    print(f"⚠️ [FALHA_ISOLAMENTO] Erro ao limpar caminhos: {e}")

# [v2026.DLL_PANIC_FIX] Força bruta para encontrar a RTX 3050 (OPTIMIZED & SILENT)
try:
    import sys
    import ctypes
    from pathlib import Path
    
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
# Resolve o WinError 1314 interceptando o Path.symlink_to globalmente.
# Se falhar ao criar link, ele faz uma cópia física.
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import torch
import gc


# Cache global para DNA Vocal (Speaker Embeddings)
_VOICE_PROMPT_CACHE = {}

# [v2026.SMART_NUMBER_EXPAND] Função de expansão inteligente de números para TTS
def _expandir_numeros_para_tts(text):
    """
    Expande símbolos numéricos de forma inteligente antes do TTS:
    - Vírgulas decimais (5,3 → '5 vírgula 3') são preservadas como fala
    - Porcentagens (33% → '33 por cento') são expandidas
    - Múltiplicadores (2,75x → '2 vírgula 75 vezes') são expandidos
    - Dólares ($5,3 bilhões → '5 vírgula 3 bilhões de dólares') são tratados
    - Vírgulas de pausa simples são convertidas em espaços
    """
    import re
    # 1. Expande separadores decimais ANTES de qualquer remoção de vírgulas
    # Padrão: dígitos,dígitos (1-3 casas decimais) = decimal em português
    # Ex: 5,3 → '5 vírgula 3' | 2,75 → '2 vírgula 75'
    text = re.sub(r'(\d+),(\d{1,3})(?!\d)', r'\1 vírgula \2', text)
    
    # 2. Expande multiplicadores: 2,75x → '2 vírgula 75 vezes' (já feito acima, trata o 'x')
    text = re.sub(r'(\d+)\s*[xX]\b(?!\w)', r'\1 vezes', text)
    
    # 3. Expande porcentagens: 33% → '33 por cento'
    text = re.sub(r'(\d+(?:\s+vírgula\s+\d+)?)\s*%', r'\1 por cento', text)
    
    # 4. Expande dólares: $5,3 bilhões → '5 vírgula 3 bilhões de dólares'
    # (o $ vem antes do número; já tratamos a vírgula acima)
    text = re.sub(r'\$\s*(\d)', r'\1 dólares de ', text)
    
    # 5. Expande bilhões/milhões abreviados com letra: 5B → '5 bilhões', 3M → '3 milhões'
    text = re.sub(r'(\d+(?:\s+vírgula\s+\d+)?)\s*B\b', r'\1 bilhões', text)
    text = re.sub(r'(\d+(?:\s+vírgula\s+\d+)?)\s*M\b(?!Hz|P)', r'\1 milhões', text)
    
    # 6. Remove vírgulas de pausa restantes (agora todas as vírgulas decimais já foram tratadas)
    text = text.replace(",", " ")
    
    return text
def _chunk_text_for_tts(text, max_len=120):
    import re
    # Divide por pontuações fortes (. ! ?) seguidas de espaço ou fim da string
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    final_chunks = []
    for sentence in sentences:
        if len(sentence) <= max_len:
            final_chunks.append(sentence)
        else:
            # Tenta quebrar por vírgulas ou ponto-e-vírgulas
            parts = re.split(r'(?<=[,;])\s+', sentence)
            current_chunk = ""
            for part in parts:
                if len(current_chunk) + len(part) + 1 <= max_len:
                    current_chunk = f"{current_chunk} {part}".strip()
                else:
                    if current_chunk:
                        final_chunks.append(current_chunk)
                    current_chunk = part.strip()
            if current_chunk:
                final_chunks.append(current_chunk)
                
    # Sanitiza e garante respiração final
    sanitized_chunks = []
    for chunk in final_chunks:
        c = chunk.strip()
        if not c.endswith(('.', '!', '?')):
            c += "."
        sanitized_chunks.append(c + " ")
    return sanitized_chunks


def gerar_audio_qwen3(text, ref_audio_path, output_path, language="Portuguese", emotion="NORMAL", max_duration=None):
    """Gera áudio usando clonagem de voz via FasterQwen3TTS + Emoções (Instruct) com blindagem ativa de duração."""
    engine = get_qwen3_engine()
    if not engine:
        logging.error("❌ Motor Qwen3 não disponível para geração.")
        return False
    
    global _VOICE_PROMPT_CACHE
    
    # [v2026.ACTING_MAP] Mapeia as emoções do Gemma para instruções do Qwen3
    # O Qwen3 entende melhor instruções em inglês
    EMOTION_MAP = {
        "RAIVA": "Expressive, serious and firm tone",
        "TRISTE": "Sad, crying tone and low volume",
        "FELIZ": "Happy, energetic and smiling voice",
        "URGENTE": "Fast, anxious and breathless",
        "SUSPENSE": "Soft and low voice, slow tempo",
        "DRAMATICO": "Dramatic, emotional and intense",
        "NORMAL": ""
    }
    instruction = EMOTION_MAP.get(emotion.upper(), "")
    
    # [v2026.CODE_SWITCH_ENGINE] Se o texto contém aspas (injetadas pelo Gemma), 
    # força o motor a usar a fonética nativa americana nessas palavras.
    if "'" in text or '"' in text:
        accent_instr = "pronounce words inside quotes with a native American accent"
        instruction = f"{instruction}, and {accent_instr}" if instruction else accent_instr
    
    try:
        voice_key = hashlib.md5(ref_audio_path.encode()).hexdigest()
        
        if voice_key not in _VOICE_PROMPT_CACHE:
            logging.info(f"🧬 [DNA_VOCAL] Mapeando voz para FasterQwen: {os.path.basename(ref_audio_path)}...")
            logging.info("🔬 [X_VECTOR] O modo ICL requer biblioteca 'k2' (incompatível com Windows). Forçando X-Vector Seguro.")
            
            prompt_func = getattr(engine, 'create_voice_clone_prompt', None) or getattr(engine.model, 'create_voice_clone_prompt')
            _VOICE_PROMPT_CACHE[voice_key] = prompt_func(
                ref_audio=ref_audio_path,
                ref_text="",
                x_vector_only_mode=True
            )
        
        # [v2026.SMART_COMMA] Expande números decimais/porcentagens, depois remove vírgulas de pausa
        clean_text = text.replace("...", " ").replace("..", " ")
        clean_text = _expandir_numeros_para_tts(clean_text)
        clean_text = " ".join(clean_text.split()).strip()
        
        # [v2026.TIGHT_TIME_PUNCTUATION] Remove pontuações internas se o tempo for apertado para evitar pausas e truncamentos
        if max_duration:
            import re
            char_rate = len(clean_text) / max_duration
            if char_rate > 10.0:
                logging.info(f"⏱️ [PUNCTUATION_SHIELD] Tempo apertado detectado ({char_rate:.1f} char/s). Removendo pontuação interna para acelerar a fala.")
                clean_text = clean_text.replace(",", " ").replace(";", " ")
                clean_text = re.sub(r'\.(?!\s*$)', ' ', clean_text)
                clean_text = " ".join(clean_text.split()).strip()
        
        # [v2026.ACTING_PUNCTUATION] Mantém a pontuação final e adiciona respiro
        if not clean_text.endswith(('.', '!', '?')):
            clean_text += "."
        clean_text += " " 
        
        # [v2026.QWEN_TEMP_SHIELD] Temperatura dinâmica combinada (Duração + Emoção):
        # 1. Base de temperatura conforme a intenção dramática
        emo_upper = emotion.upper()
        if emo_upper in ["TRISTE", "SUSPENSE", "NORMAL"]:
            base_temp = 0.30
        elif emo_upper in ["RAIVA", "FELIZ", "URGENTE", "DRAMATICO"]:
            base_temp = 0.55
        else:
            base_temp = 0.50

        # 2. Se a frase for muito curta, prioriza a estabilidade (temp baixa) contra alucinações
        if max_duration and max_duration < 4.0:
            temp_to_use = 0.30
            top_p_to_use = 0.70
            top_k_to_use = 20
        else:
            temp_to_use = base_temp
            top_p_to_use = 0.80
            top_k_to_use = 40
        
        # [v2026.QWEN_TOKEN_GUARD] Limitador físico de tokens por tempo de cena.
        # O Qwen3-TTS opera nativamente a 12Hz (12 tokens = 1 segundo de áudio).
        # Definimos uma margem segura de 18 tokens por segundo.
        # [v2026.VRAM_SEGMENT_CEILING] Limitamos strictamente safe_sec a 18.0 segundos para evitar OOM na RTX 3050.
        if max_duration:
            safe_sec = min(18.0, max(4.0, max_duration * 2.2))
        else:
            safe_sec = min(18.0, max(4.0, len(clean_text) / 8.0))
        max_tokens_to_gen = int(safe_sec * 18)
        
        # Blindagem de duração estrita
        limit_duration = max(6.0, max_duration * 2.5) if max_duration else None
        
        import time
        start_time_gen = time.time()
        pure_inf_time = 0.0
        
        # [v2026.AUTO_CHUNK_GATE] Divide automaticamente textos longos para evitar OOM e truncamento de fala
        if len(clean_text) > 120:
            chunks = _chunk_text_for_tts(clean_text, max_len=120)
            logging.info(f"🧱 [AUTO_CHUNK] Texto longo detectado ({len(clean_text)} caracteres). Dividido em {len(chunks)} trechos para evitar truncamento e OOM.")
            
            chunk_audios = []
            sr_to_use = 24000
            for idx, chunk in enumerate(chunks):
                safe_sec_chunk = max(4.0, len(chunk) / 8.0)
                max_tokens_chunk = int(safe_sec_chunk * 18)
                
                logging.info(f"🎤 [AUTO_CHUNK] Gerando trecho {idx + 1}/{len(chunks)}: '{chunk.strip()}'")
                t0 = time.time()
                wavs_chk, sr_chk = engine.generate_voice_clone(
                    text=chunk,
                    language=language,
                    voice_clone_prompt=_VOICE_PROMPT_CACHE[voice_key],
                    xvec_only=True,
                    temperature=temp_to_use,
                    top_k=top_k_to_use,
                    top_p=top_p_to_use,
                    repetition_penalty=1.20,
                    max_new_tokens=max_tokens_chunk,
                    append_silence=False,
                    non_streaming_mode=True,
                    instruct=instruction
                )
                pure_inf_time += time.time() - t0
                if wavs_chk is not None and len(wavs_chk) > 0:
                    chunk_audios.append(wavs_chk[0])
                    sr_to_use = sr_chk
                else:
                    logging.warning(f"⚠️ [AUTO_CHUNK] Falha na geração do trecho {idx + 1}/{len(chunks)}")
            
            if chunk_audios:
                import numpy as np
                # Adiciona pequeno silêncio (0.12 segundos) entre sentenças para fluência natural
                silence_samples = int(sr_to_use * 0.12)
                silence = np.zeros(silence_samples, dtype=np.float32)
                
                full_audio_data = []
                for i, wav_c in enumerate(chunk_audios):
                    if i > 0:
                         full_audio_data.append(silence)
                    full_audio_data.append(wav_c)
                audio_data = np.concatenate(full_audio_data)
                wavs = [audio_data]
                sr = sr_to_use
        else:
            # Tentativa 1: Geração Padrão Estabilizada com Parâmetros Avançados (Zero-Slicing, Full Prefill)
            t0 = time.time()
            wavs, sr = engine.generate_voice_clone(
                text=clean_text,
                language=language,
                voice_clone_prompt=_VOICE_PROMPT_CACHE[voice_key],
                xvec_only=True,
                temperature=temp_to_use,
                top_k=top_k_to_use, # Foca o vocabulário, bloqueando silêncios/estalos de preenchimento
                top_p=top_p_to_use,
                repetition_penalty=1.20, # Penalidade ideal contra repetições sem robotizar
                max_new_tokens=max_tokens_to_gen, # Limita fisicamente a alucinação
                append_silence=False, # Impede o Qwen3 de adicionar silêncio artificial no fim
                non_streaming_mode=True, # Prefill do texto completo para evitar pausas/gargalos entre palavras
                instruct=instruction
            )
            pure_inf_time += time.time() - t0
            
            # [v2026.HALLUCINATION_GATE] Detecta loops infinitos ou áudios gigantes
            if wavs is not None and len(wavs) > 0:
                audio_data = wavs[0]
                gen_dur = len(audio_data) / sr
                
                if limit_duration and gen_dur > limit_duration:
                    logging.warning(f"⚠️ [QWEN3_GUARD] Áudio gigante detectado ({gen_dur:.1f}s vs limite {limit_duration:.1f}s). Regenerando em modo ultra-estável...")
                    
                    # Tentativa 2: Regeneração ultra-determinística para forçar encerramento limpo
                    t0 = time.time()
                    wavs, sr = engine.generate_voice_clone(
                        text=clean_text,
                        language=language,
                        voice_clone_prompt=_VOICE_PROMPT_CACHE[voice_key],
                        xvec_only=True,
                        temperature=0.05,
                        top_k=5,
                        top_p=0.3,
                        repetition_penalty=1.35,
                        max_new_tokens=max_tokens_to_gen,
                        append_silence=False,
                        non_streaming_mode=True,
                        instruct=instruction
                    )
                    pure_inf_time += time.time() - t0
                    
                    if wavs is not None and len(wavs) > 0:
                        audio_data = wavs[0]
                        gen_dur = len(audio_data) / sr
                        logging.info(f"✅ [QWEN3_GUARD] Regeneração estável concluída ({gen_dur:.1f}s).")
        
        if wavs is not None and len(wavs) > 0:
            import time
            gen_time_taken = time.time() - start_time_gen
            audio_len_sec = len(audio_data) / sr
            rtf_metric = pure_inf_time / audio_len_sec if audio_len_sec > 0 else 0
            speed_mult = 1.0 / rtf_metric if rtf_metric > 0 else 0
            msg_log = f"⚡ [NEXUS_VOICE] Áudio gerado: {audio_len_sec:.2f}s em {gen_time_taken:.2f}s (Inference: {pure_inf_time:.2f}s) | Velocidade: {speed_mult:.2f}x mais rápido (RTF: {rtf_metric:.3f})"
            logging.info(msg_log)
            print(f"\n{msg_log}", flush=True)
            
            import numpy as np
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                # [v2026.AUDIO_NORM] Normaliza matematicamente a amplitude do sinal, preservando 100% da dinâmica da voz
                audio_data = (audio_data / max_val) * 0.95
                
            sf.write(output_path, audio_data, sr)
            return True
        return False
    except Exception as e:
        import traceback
        logging.error(f"❌ Erro na geração Qwen3: {e}\n{traceback.format_exc()}")
        return False

def gerar_audio_batch_qwen3(batch_items, ref_audio_path, language="Portuguese"):
    """
    Gera um lote (batch) de áudios de uma vez para máxima performance.
    batch_items: Lista de dicionários {'text': str, 'output_path': str}
    """
    engine = get_qwen3_engine()
    if not engine or not batch_items:
        return False
    
    global _VOICE_PROMPT_CACHE
    
    try:
        # [v2026.DNA_CACHE] Reutiliza o DNA da voz para o lote todo
        voice_key = hashlib.md5(ref_audio_path.encode()).hexdigest()
        if voice_key not in _VOICE_PROMPT_CACHE:
            prompt_func = getattr(engine, 'create_voice_clone_prompt', None) or getattr(engine.model, 'create_voice_clone_prompt')
            _VOICE_PROMPT_CACHE[voice_key] = prompt_func(
                ref_audio=ref_audio_path, ref_text="", x_vector_only_mode=True
            )
        
        # Prepara a lista de textos com o "respiro" final
        texts = []
        for item in batch_items:
            t = item['text'].strip()
            if not t.endswith(('.', '!', '?', ',')): t += "."
            texts.append(t + " ")
            
        # [v2026.MEGA_SQUEEZE] Chamada em Lote (Batch)
        # A placa de vídeo processa todos os textos em paralelo!
        wav_list, sr = engine.generate_voice_clone(
            text=texts,
            language=language,
            voice_clone_prompt=_VOICE_PROMPT_CACHE[voice_key],
            xvec_only=True
        )
        
        # Salva os arquivos resultantes
        success_count = 0
        for i, wav in enumerate(wav_list):
            if wav is not None and len(wav) > 0:
                sf.write(batch_items[i]['output_path'], wav, sr)
                success_count += 1
        
        return success_count == len(batch_items)
        
    except Exception as e:
        logging.error(f"❌ Erro no Batch Qwen3: {e}")
        return False

