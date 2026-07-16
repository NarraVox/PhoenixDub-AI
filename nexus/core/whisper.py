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


# --- CÓDIGO EXTRAÍDO ---

def transcribe_audio(model, audio_path, source_lang='auto'):
    # [CPU OPTIMIZATION] beam_size=1 (Greedy Search) é 3x mais rápido que o padrão (5).
    # condition_on_previous_text=False previne alucinações e loops.
    # [v2026.i5_TURBO] beam_size=1 é 3x-5x mais rápido no i5-6400
    whisper_lang = source_lang if source_lang != 'auto' else None

    # [v2026.CLIP_TIMESTAMPS] Mesma técnica do pipeline de vídeo (transcrever_e_diarizar):
    # Em vez do Silero VAD (que rejeita áudio de rádio, sussurro e efeitos de banda),
    # passamos clip_timestamps=[0.0, duration] dizendo ao Whisper que o arquivo INTEIRO
    # pode conter fala. Os arquivos individuais já foram isolados pela diarização —
    # não precisamos de um segundo filtro de voz que vai errar em áudios processados.
    import librosa
    try:
        duration = librosa.get_duration(path=audio_path)
    except Exception:
        duration = 10.0  # fallback seguro se librosa falhar
    
    segments_generator, info = model.transcribe(
        audio_path, 
        beam_size=1, 
        condition_on_previous_text=False, 
        language=whisper_lang,
        vad_filter=False,
        clip_timestamps=[0.0, duration],
        no_speech_threshold=0.6
    )
    return {
        "text": "".join(s.text for s in segments_generator).strip(),
        "detected_language": getattr(info, 'language', None)
    }


def smart_whisper_trim(audio_path, expected_text):
    """
    [v2026.20] Usa Whisper (word_timestamps) para achar o milissegundo exato da primeira 
    e última palavra. Corta o áudio precisamente ali, mantendo uma margem de segurança.
    Retorna True se cortou, False se não precisou ou falhou.
    """
    try:
        from pydub import AudioSegment
        import librosa
        whisper_model = get_whisper_model()
        
        # A Mágica: Pedimos os timestamps por palavra!
        segments, _ = whisper_model.transcribe(str(audio_path), language="pt", word_timestamps=True)
        
        words = []
        for segment in segments:
            if hasattr(segment, 'words') and segment.words:
                words.extend(segment.words)
                
        if not words:
            logging.info(f"🛡️ Smart Trim: Nenhuma palavra clara detectada no Whisper para {Path(audio_path).name}")
            return False
            
        # --- [v2026.25] PODA DE ALUCINAÇÕES (HALLUCINATION PRUNING) ---
        if expected_text:
            import re
            import difflib
            clean_expected = re.sub(r'[^a-záéíóúâêîôûãõç\s]', '', expected_text.lower()).split()
            valid_words = []
            
            for w in words:
                clean_w = re.sub(r'[^a-záéíóúâêîôûãõç]', '', w.word.lower())
                if not clean_w: continue
                
                # Verifica se a palavra falada existe no roteiro (com 60% de tolerância para sotaque/erro de ASR)
                matches = difflib.get_close_matches(clean_w, clean_expected, n=1, cutoff=0.6)
                if matches or clean_w in clean_expected:
                    valid_words.append(w)
            
            if valid_words:
                # Se achou palavras válidas, usamos APENAS elas. O resto (eeeee, aaaaa) será cortado!
                words = valid_words
                logging.info(f"🛡️ Smart Trim: Poda de Alucinação ativada. Restaram {len(words)} palavras válidas.")

        first_word_start = words[0].start
        last_word_end = words[-1].end
        
        y, sr = librosa.load(str(audio_path), sr=None)
        total_duration = librosa.get_duration(y=y, sr=sr)
        
        # Margem de segurança de 50ms para não cortar o respiro da voz
        margin = 0.05
        crop_start = max(0, first_word_start - margin)
        crop_end = min(total_duration, last_word_end + margin)
        
        # Só cortamos se houver pelo menos 100ms de silêncio para limpar (evita cortes inúteis)
        if (crop_end - crop_start) >= (total_duration - 0.1):
            return False
            
        audio = AudioSegment.from_file(str(audio_path))
        trimmed_audio = audio[int(crop_start * 1000) : int(crop_end * 1000)]
        trimmed_audio.export(str(audio_path), format=Path(audio_path).suffix.replace('.', ''))
        
        logging.info(f"✂️ Smart Trim: {Path(audio_path).name} lapidado! De {total_duration:.2f}s para {(crop_end-crop_start):.2f}s")
        return True
    except Exception as e:
        logging.warning(f"Aviso no Smart Trim para {Path(audio_path).name}: {e}")
        return False

# --- MÓDULO NEXUS: CONTROLE DE QUALIDADE AUTOMÁTICO (LQA) ---
def transcrever_arquivo():
    start_time = time.time()
    if 'transcricao_file' not in request.files:
        return jsonify({'error': 'Nenhum ficheiro enviado.'}), 400
    
    file = request.files['transcricao_file']
    if file.filename == '':
        return jsonify({'error': 'Nenhum ficheiro selecionado.'}), 400

    timestamp = int(time.time())
    datestamp = datetime.now().strftime('%d.%m.%Y')
    job_id = f"job_transcricao_{datestamp}_{timestamp}"
    job_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    filename = secure_filename(file.filename)
    extension = Path(filename).suffix
    input_path = job_dir / f"input{extension}"
    file.save(input_path)

    status_data = {'job_id': job_id, 'status': 'iniciando', 'original_filename': filename}
    safe_json_write(status_data, job_dir / "job_status.json")

    threading.Thread(target=processar_transcricao, args=(job_dir, job_id, start_time)).start()
    return jsonify({'status': 'processing', 'job_id': job_id})

def transcrever_e_diarizar(audio_path, job_dir=None, cb=None, source_lang="auto"):
    """[v2026.WHISPERX_MIGRATION] Transcrição com Alinhamento de Fonemas e Diarização Sequencial de Baixo VRAM."""
    from pathlib import Path
    cleanup_on_exit() 
    if not Path(audio_path).exists(): return []
    
    # [v2026.SMART_RESUME] Tenta carregar do cache para evitar re-processamento pesado
    if job_dir:
        cache_path = Path(job_dir) / "transcription_cache.json"
        if cache_path.exists() and cache_path.stat().st_size > 100:
            logging.info("♻️ [CACHE_HIT] Transcrição e Diarização encontradas no cache. Pulando WhisperX.")
            if cb: cb(100, 1, "[Cache] Retomando transcrição salva...")
            return safe_json_read(cache_path)
    
    import torch
    import gc
    import whisperx
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logging.info(f"🎙️ [WhisperX] Inicializando pipeline no dispositivo: {device}")
    
    # 1. TRANSCRIÇÃO (WhisperX)
    if cb: cb(10, 1, "[WhisperX] Carregando modelo Whisper medium...")
    compute_type = "float16" if device == "cuda" else "int8"
    # [v2026.SILERO_VAD] Usa Silero VAD em vez de Pyannote VAD para evitar agrupamentos gigantes de silêncio e falas omitidas
    model = whisperx.load_model("medium", device=device, compute_type=compute_type, vad_method="silero")
    
    if cb: cb(20, 1, "[WhisperX] Transcrevendo áudio do vídeo...")
    audio = whisperx.load_audio(str(audio_path))
    whisper_lang = source_lang if source_lang != "auto" else None
    result = model.transcribe(audio, batch_size=16, language=whisper_lang)
    
    detected_lang = result.get("language")
    logging.info(f"✅ [WhisperX] Transcrição concluída. Idioma: {detected_lang}")
    
    # Descarrega o modelo de transcrição da GPU imediatamente
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
        
    if not result.get("segments"):
        error_msg = "❌ ERRO FATAL: Nenhuma fala detectada no áudio!"
        logging.error(error_msg)
        if cb: cb(100, 1, error_msg, status="erro")
        raise ValueError(error_msg)
        
    # 2. ALINHAMENTO DE FONEMAS FORÇADO
    if cb: cb(40, 1, "[WhisperX] Carregando modelo de alinhamento fonético...")
    align_lang = detected_lang or source_lang
    if align_lang == "auto" or not align_lang:
        align_lang = "pt"
        
    aligned_result = None
    try:
        model_a, metadata = whisperx.load_align_model(language_code=align_lang, device=device)
        if cb: cb(50, 1, "[WhisperX] Sincronizando fonemas e lábios (Alinhamento)...")
        aligned_result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
        
        # Descarrega o modelo de alinhamento da GPU imediatamente
        del model_a
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception as align_err:
        logging.warning(f"⚠️ [WhisperX] Alinhamento fonético falhou para '{align_lang}': {align_err}. Usando tempos originais.")
        aligned_result = result
        
    # 3. DIARIZAÇÃO (Pyannote 3.1 via WhisperX)
    if cb: cb(65, 1, "[WhisperX] Carregando modelo de diarização (Pyannote)...")
    
    # [v2026.HF_TOKEN_AUTOLOAD] Tenta ler o token de arquivos de configuração locais para facilitar a vida do usuário
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        for p in [Path("C:/IA_dublagem/.env"), Path("C:/IA_dublagem/token_hf.txt")]:
            if p.exists():
                try:
                    content = p.read_text(encoding="utf-8").strip()
                    for line in content.splitlines():
                        if "=" in line and "HF_TOKEN" in line:
                            hf_token = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
                        elif not "=" in line and len(line) > 10:
                            hf_token = line.strip()
                            break
                    if hf_token:
                        os.environ["HF_TOKEN"] = hf_token
                        logging.info(f"🔑 [HF_TOKEN] Token carregado com sucesso do arquivo: {p.name}")
                        break
                except Exception as token_err:
                    logging.warning(f"⚠️ Erro ao ler token de {p.name}: {token_err}")
                    
    if not hf_token:
        hf_token = True
        
    diarize_segments = None
    try:
        from whisperx.diarize import DiarizationPipeline
        diarize_model = DiarizationPipeline(model_name="pyannote/speaker-diarization-3.1", token=hf_token, device=device)
        
        # [v2026.DIARIZATION_TUNING] Ajusta o limiar de agrupamento para 0.50 para separar melhor vozes de oradores diferentes
        try:
            diarize_model.model.instantiate({
                "clustering": {
                    "threshold": 0.50,
                }
            })
            logging.info("🎯 [DIARIZAÇÃO] Parâmetros do Pyannote instanciados com clustering.threshold = 0.50")
        except Exception as inst_err:
            logging.warning(f"⚠️ Não foi possível instanciar parâmetros customizados do Pyannote: {inst_err}")

        if cb: cb(75, 1, "[WhisperX] Identificando vozes diferentes no áudio...")
        diarize_segments = diarize_model(audio)
        
        # Descarrega o modelo de diarização da GPU imediatamente
        del diarize_model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception as diarize_err:
        error_msg = f"❌ ERRO CRÍTICO NA DIARIZAÇÃO (Pyannote): {diarize_err}. Certifique-se de que o token do Hugging Face (HF_TOKEN) está configurado e que você aceitou os termos de uso do modelo pyannote/speaker-diarization-3.1."
        logging.error(error_msg)
        if cb: cb(100, 1, error_msg, status="error")
        raise ValueError(error_msg)
        
    # 4. ASSOCIAÇÃO DE ORADORES
    if diarize_segments is not None and aligned_result is not None:
        try:
            aligned_result = whisperx.assign_word_speakers(diarize_segments, aligned_result)
        except Exception as assign_err:
            logging.warning(f"⚠️ [WhisperX] Erro ao associar oradores: {assign_err}")
            
    # 5. MAPEAMENTO E EXTRAÇÃO DE ÁUDIO
    from pydub import AudioSegment
    full_audio = None
    try:
        full_audio = AudioSegment.from_wav(str(audio_path))
    except Exception as e:
        logging.warning(f"⚠️ Não foi possível carregar o áudio original com pydub: {e}")
        
    final_results = []
    voice_base_dir = Path(job_dir) / "_2_PARA_AS_PASTAS_DE_VOZ" if job_dir else None
    recent_texts = []
    
    def clean_speaker(spk):
        if not spk:
            return None
        spk_str = str(spk).strip()
        if spk_str.startswith("SPEAKER_"):
            try:
                num = int(spk_str.split("_")[-1])
                return f"voz_{num}"
            except:
                return f"voz_{spk_str}"
        if spk_str.startswith("voz_"):
            return spk_str
        return f"voz_{spk_str}"
    # 4.5. RESEGMENTAÇÃO BASEADA EM PAUSAS DE 0.5s E SPEAKER
    segments_to_process = []
    if aligned_result:
        all_words = []
        for s in aligned_result.get("segments", []):
            for w in s.get("words", []):
                if 'start' in w and 'end' in w:
                    all_words.append(w)
        
        if all_words:
            all_words.sort(key=lambda x: x['start'])
            segments_to_process = resegment_based_on_pauses({"words": all_words}, silence_threshold=0.5)
            
        if not segments_to_process:
            segments_to_process = aligned_result.get("segments", [])
    
    for i, w_seg in enumerate(segments_to_process):
        text = w_seg.get("text", "").strip()
        if not text or len(text) < 2: continue
        
        # [v2026.ASR_NOISE_SHIELD] Detecta alucinações de ruído do Whisper (caracteres georgianos ou repetições de letras sem sentido)
        import re
        is_noise_hallucination = False
        if any('\u10a0' <= c <= '\u10ff' for c in text):
            is_noise_hallucination = True
        elif re.search(r'([^\s.,!?_#*\-~])\1{3,}', text):
            is_noise_hallucination = True
            
        if is_noise_hallucination:
            logging.info(f"🛡️ [ASR-SHIELD] WhisperX alucinou ruído/sussurro: '{text}'. Convertendo para '[gemido]'.")
            text = "[gemido]"
            
        # Filtro de Alucinação Inteligente (Baseado em Repetições)
        texto_limpo = text.lower().strip()
        if len(recent_texts) >= 2 and texto_limpo == recent_texts[-1] == recent_texts[-2]:
            continue
            
        words = texto_limpo.replace(',', '').replace('.', '').replace('!', '').replace('?', '').split()
        is_hallucination = False
        consec_count = 1
        for w_idx in range(1, len(words)):
            if words[w_idx] == words[w_idx-1]:
                consec_count += 1
                if consec_count > 3:
                    is_hallucination = True
                    break
            else:
                consec_count = 1
                
        if is_hallucination:
            continue
            
        recent_texts.append(texto_limpo)
        if len(recent_texts) > 3: recent_texts.pop(0)
        
        # Identificação de Orador e Cross-Validation
        raw_speaker = w_seg.get("speaker")
        
        # [v2026.CROSS_VALIDATION_SHIELD]
        # Se a diarização foi executada com sucesso, mas o segmento não recebeu nenhum orador,
        # em vez de ignorar e deletar a fala (o que causava silenciamento de diálogos reais),
        # nós atribuímos um orador de fallback ('voz_0') para preservar a integridade da dublagem.
        if not raw_speaker and diarize_segments is not None:
            logging.info(f"⚠️ [CROSS-VALIDATION] Segmento sem orador entre {w_seg.get('start', 0.0):.1f}s e {w_seg.get('end', 0.0):.1f}s: '{text}'. Usando fallback 'voz_0'.")
            raw_speaker = "voz_0"
            
        best_speaker = clean_speaker(raw_speaker) or "voz_0"
        adjusted_start = w_seg.get("start", 0.0)
        adjusted_end = w_seg.get("end", 0.0)
        
        seg_id = f"seg_{len(final_results)}"
        final_results.append({
            "id": seg_id,
            "start": adjusted_start,
            "end": adjusted_end,
            "text": text,
            "speaker": best_speaker
        })
        
        # Extração física
        if full_audio and voice_base_dir:
            try:
                spk_dir = voice_base_dir / best_speaker
                spk_dir.mkdir(parents=True, exist_ok=True)
                chunk = full_audio[int(max(0, adjusted_start-0.05)*1000):int(min(len(full_audio), adjusted_end+0.1)*1000)]
                chunk.export(str(spk_dir / f"{seg_id}.wav"), format="wav")
            except Exception as e:
                logging.warning(f"Falha ao extrair chunk {seg_id}: {e}")
                
        if cb and len(segments_to_process) > 0:
            cb(80 + (i / len(segments_to_process) * 19), 1, f"[Mapeamento] Processando frase {i+1}...")
            
    if job_dir:
        cache_path = Path(job_dir) / "transcription_cache.json"
        safe_json_write(final_results, cache_path)
        logging.info(f"💾 [CACHE_SAVE] Transcrição e Diarização blindadas em: {cache_path.name}")
        prepare_video_speaker_references(job_dir)
        
    return final_results


def resegment_based_on_pauses(whisper_result, max_chars=200, max_duration=10.0, silence_threshold=0.5, diarization_data=None):
    """Resegmenta as palavras do Whisper baseando-se em pausas de silêncio (0.5s por padrão) e orador."""
    words = whisper_result.get('words', [])
    if not words: return []
    segments = []
    current_segment = {'words': [], 'start': 0, 'end': 0}
    
    for i, word in enumerate(words):
        if not current_segment['words']:
            current_segment['start'] = word['start']
            current_segment['words'].append(word)
            current_segment['end'] = word['end']
            continue
        last_word = current_segment['words'][-1]
        gap = word['start'] - last_word['end']
        should_break = gap > silence_threshold or (word['end'] - current_segment['start']) > max_duration
        
        if not should_break:
            spk_current = word.get('speaker')
            spk_last = last_word.get('speaker')
            if spk_current and spk_last and spk_current != spk_last:
                should_break = True
                
        if should_break:
            txt = " ".join([w['word'].strip() for w in current_segment['words']]).strip()
            if txt:
                spk = current_segment['words'][0].get('speaker')
                segments.append({
                    'start': current_segment['start'],
                    'end': current_segment['end'],
                    'text': txt,
                    'speaker': spk,
                    'words': current_segment['words']
                })
            current_segment = {'words': [word], 'start': word['start'], 'end': word['end']}
        else:
            current_segment['words'].append(word)
            current_segment['end'] = word['end']
            
    txt = " ".join([w['word'].strip() for w in current_segment['words']]).strip()
    if txt:
        spk = current_segment['words'][0].get('speaker')
        segments.append({
            'start': current_segment['start'],
            'end': current_segment['end'],
            'text': txt,
            'speaker': spk,
            'words': current_segment['words']
        })
    return segments

