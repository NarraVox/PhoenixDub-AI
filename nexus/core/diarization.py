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

import os
import sys
import random
import re
import time
import subprocess
import shutil
import logging
import datetime
import traceback
import atexit
from pathlib import Path
from datetime import timedelta

import numpy as np
import torch
import soundfile as sf
import torchaudio
import librosa
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering
from scipy.spatial.distance import cosine
from pydub import AudioSegment

# Note: Runtime global dependency injection is managed by nexus.core.__init__.py
# Functions like robust_audio_load, get_audio_duration, safe_json_read, safe_json_write,
# get_whisper_model, unload_whisper_model, run_batch_cleaning, run_openunmix_batch
# are dynamically injected into this module's globals at startup.

def preprocess_audio_for_diarization(input_path, output_path):
    """
    Aplica tratamento de áudio.
    1. Tenta DeepFilterNet (OBRIGATÓRIO para redução de ruído).
    2. Se não tiver, APENAS normaliza (dynaudnorm) sem filtros destrutivos.
    """
    try:
        import librosa
        
        y_check, sr_check = librosa.load(str(input_path), sr=16000, duration=5.0)
        rms = librosa.feature.rms(y=y_check)[0]
        mean_rms = np.mean(rms)
        
        if mean_rms > 0.025:
             logging.info(f"RMS: {mean_rms:.3f}. Ruído pesado detectado. Aplicando DeepFilterNet.")
             from df.enhance import enhance, init_df, load_audio, save_audio
             model, df_state, _ = init_df()
             audio, _ = load_audio(input_path, sr=df_state.sr())
             enhanced = enhance(model, df_state, audio)
             save_audio(output_path, enhanced, df_state.sr())
             return True
        else:
             logging.info(f"RMS: {mean_rms:.3f}. Som limpo/intencional (Rádio/Eco). Bypass DeepFilterNet.")
             raise ImportError("Bypass condicional DeepFilterNet via librosa")
              
    except ImportError as e:
        if "Bypass condicional" not in str(e):
             logging.warning("="*60)
             logging.warning("[AVISO] DeepFilterNet não encontrado!")
             logging.warning("Instale com: pip install deepfilternet")
             logging.warning("="*60)
        logging.warning("O áudio será apenas normalizado, SEM redução de ruído.")
        
        try:
            threads = str(max(1, (os.cpu_count() or 4) // 2))
            af_filter = "dynaudnorm=f=150:g=15" 
            
            cmd = [
                'ffmpeg', '-threads', threads, '-y', 
                '-i', str(input_path),
                '-af', af_filter,
                '-ar', '16000', 
                '-ac', '1',     
                str(output_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except:
             pass

    except Exception as e:
        logging.error(f"Erro no pré-processamento (DeepFilterNet): {e}")

    try:
        shutil.copy(str(input_path), str(output_path))
    except: pass
    return False


class PyannoteDiarizer:
    def __init__(self, device=None):
        from pyannote.audio import Pipeline
        import torch
        
        token = os.environ.get("HF_TOKEN", True) 
        
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        elif device == "cuda" and not torch.cuda.is_available():
            device = "cpu"
        
        try:
            try:
                self.pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    token=token
                )
            except TypeError as te:
                if "unexpected keyword argument" in str(te) or "use_auth_token" in str(te):
                    self.pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        use_auth_token=token
                    )
                else:
                    raise
            
            self.pipeline.instantiate({
                "clustering": {
                    "method": "centroid",
                    "min_cluster_size": 12,
                    "threshold": 0.78
                }
            })
            if device == "cuda" and torch.cuda.is_available():
                self.pipeline.to(torch.device("cuda"))
            self.device = device
            logging.info(f"✅ Diarizador Pyannote 3.1 (Elite) carregado no dispositivo: {device}")
        except Exception as e:
            logging.error(f"❌ Erro ao carregar Pyannote: {e}")
            self.pipeline = None
            raise e

    def diarize(self, audio_path, progress_cb=None):
        if not self.pipeline: return None
        return self.pipeline(str(audio_path))

    def get_file_embedding_from_signal(self, signal_tensor):
        """
        [v2026.ELITE_FIX] Extrai o embedding (DNA) diretamente de um tensor de áudio.
        Usa o modelo de embedding autônomo do Pyannote para evitar bugs no pipeline nativo.
        Se falhar (ex: falta de token HF para pyannote/embedding), usa SpeechBrain como fallback.
        """
        import torch
        
        try:
            if not getattr(self, "_use_speechbrain_fallback", False):
                if not hasattr(self, "_embedding_inference"):
                    from pyannote.audio import Model, Inference
                    import os
                    token = os.environ.get("HF_TOKEN", True)
                    
                    try:
                        emb_model = Model.from_pretrained("pyannote/embedding", token=token)
                    except TypeError as te:
                        if "unexpected keyword argument" in str(te) or "use_auth_token" in str(te):
                            emb_model = Model.from_pretrained("pyannote/embedding", use_auth_token=token)
                        else:
                            raise
                    
                    if emb_model is None:
                        raise RuntimeError("Pyannote embedding model returned None")
                    
                    emb_model.to(self.device)
                    self._embedding_inference = Inference(emb_model, window="whole", device=torch.device(self.device))
                
                with torch.no_grad():
                    if len(signal_tensor.shape) == 1:
                        signal_tensor = signal_tensor.unsqueeze(0)
                    elif len(signal_tensor.shape) > 2:
                        signal_tensor = signal_tensor.squeeze()
                        if len(signal_tensor.shape) == 1: signal_tensor = signal_tensor.unsqueeze(0)
                    
                    signal_tensor = signal_tensor.to(self.device)
                    emb = self._embedding_inference({"waveform": signal_tensor, "sample_rate": 16000})
                    if emb is not None:
                        return emb.reshape(-1)
                    return None
        except Exception as e:
            logging.warning(f"⚠️ Falha ao carregar/extrair com Pyannote ({e}). Ativando fallback SpeechBrain (Livre de Tokens)...")
            self._use_speechbrain_fallback = True

        try:
            if not hasattr(self, "_speechbrain_classifier") or self._speechbrain_classifier is None:
                from speechbrain.inference.speaker import EncoderClassifier
                logging.info("Carregando SpeechBrain EncoderClassifier como fallback...")
                self._speechbrain_classifier = EncoderClassifier.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb", 
                    run_opts={"device": self.device}
                )
            
            with torch.no_grad():
                if len(signal_tensor.shape) == 1:
                    signal_tensor = signal_tensor.unsqueeze(0)
                elif len(signal_tensor.shape) > 2:
                    signal_tensor = signal_tensor.squeeze()
                    if len(signal_tensor.shape) == 1: signal_tensor = signal_tensor.unsqueeze(0)
                
                signal_tensor = signal_tensor.to(self.device)
                emb = self._speechbrain_classifier.encode_batch(signal_tensor)
                return emb.squeeze().cpu().numpy()
        except Exception as ex_sb:
            logging.error(f"❌ Falha crítica no extrator SpeechBrain: {ex_sb}")
            return None

    def get_file_embedding(self, audio_path):
        """Gera um embedding único para o arquivo inteiro usando Pyannote 3.1."""
        try:
            signal, fs = robust_audio_load(str(audio_path))
            if signal.shape[0] > 1:
                signal = signal.mean(dim=0, keepdim=True)
            if fs != 16000:
                import torchaudio.transforms as T
                resampler = T.Resample(fs, 16000)
                signal = resampler(signal)
            return self.get_file_embedding_from_signal(signal)
        except Exception as e:
            logging.error(f"Erro ao gerar embedding Pyannote para {audio_path}: {e}")
            return None

    def cluster_batch_embeddings(self, embeddings_map, n_clusters=None, distance_threshold=0.72):
        """
        Agrupa uma coleção de arquivos por similaridade de voz (Agglomerative Clustering).
        """
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering
        
        if not embeddings_map: return {}
        
        fnames = list(embeddings_map.keys())
        embs = np.array([embeddings_map[fn] for fn in fnames])
        
        if len(fnames) < 2:
            return {fnames[0]: "voz1"}

        if n_clusters is None or n_clusters <= 1:
            logging.info(f"Clustering: Agrupando {len(fnames)} arquivos (Modo Dinâmico - Threshold {distance_threshold})...")
            model = AgglomerativeClustering(
                n_clusters=None, 
                distance_threshold=distance_threshold, 
                metric='cosine', 
                linkage='average'
            )
        else:
            logging.info(f"Clustering: Agrupando {len(fnames)} arquivos em {n_clusters} vozes (Modo Fixo)...")
            model = AgglomerativeClustering(n_clusters=n_clusters, metric='cosine', linkage='average')
            
        labels = model.fit_predict(embs)
        num_unique_voices = len(set(labels))
        logging.info(f"✅ Clustering Concluído: {len(fnames)} arquivos agrupados in {num_unique_voices} vozes distintas.")
        
        results = {}
        for i, label in enumerate(labels):
            results[fnames[i]] = f"voz{label+1}"
        return results

    def detect_splits_surgical(self, audio_path):
        """
        [v10.60 SURGICAL VAD SPLIT]
        Detecta silêncios primeiro (Pydub) e analisa se houve troca de voz entre os blocos de fala.
        Garante que nunca corte no meio de uma palavra.
        """
        import torchaudio
        from scipy.spatial.distance import cosine
        from pydub import AudioSegment
        from pydub.silence import detect_nonsilent
        
        sound = AudioSegment.from_wav(str(audio_path))
        nonsilent_ranges = detect_nonsilent(sound, min_silence_len=300, silence_thresh=-40)
        
        if len(nonsilent_ranges) < 2: return []
        
        signal, fs = robust_audio_load(str(audio_path))
        if signal.shape[0] > 1: signal = signal.mean(dim=0, keepdim=True)
        if fs != 16000:
             import torchaudio.transforms as T
             resampler = T.Resample(fs, 16000)
             signal = resampler(signal)
             fs = 16000
        
        embeddings = []
        valid_ranges = []
        
        for start_ms, end_ms in nonsilent_ranges:
            s_start = int((start_ms / 1000.0) * fs)
            s_end = int((end_ms / 1000.0) * fs)
            
            if (end_ms - start_ms) < 500: continue
            
            try:
                chunk = signal[:, s_start:s_end]
                emb = self.get_file_embedding_from_signal(chunk)
                if emb is not None:
                    embeddings.append(emb)
                    valid_ranges.append((start_ms, end_ms))
            except: continue
            
        if len(embeddings) < 2: return []
        
        splits_ms = []
        for i in range(len(embeddings) - 1):
            dist = cosine(embeddings[i], embeddings[i+1])
            if dist > 0.5:
                silence_start = valid_ranges[i][1]
                silence_end = valid_ranges[i+1][0]
                split_point = (silence_start + silence_end) / 2
                splits_ms.append(split_point / 1000.0)
        
        return splits_ms

    def process(self, audio_path, segments, similarity_threshold=0.65):
        """
        [v2026.MASTER] Processa segmentos do Whisper e atribui oradores.
        """
        import torchaudio
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity
        
        logging.info(f"Diarização: Analisando {len(segments)} segmentos...")
        
        try:
            signal, fs = robust_audio_load(str(audio_path))
            if signal.shape[0] > 1: signal = signal.mean(dim=0, keepdim=True)
            if fs != 16000:
                resampler = torchaudio.transforms.Resample(fs, 16000)
                signal = resampler(signal)
                fs = 16000
        except Exception as e:
            logging.error(f"Erro ao carregar áudio para diarização: {e}")
            return segments

        speaker_prototypes = {}
        next_id = 1
        processed = []
        
        for seg in segments:
            start_s = getattr(seg, 'start', seg.get('start', 0))
            end_s = getattr(seg, 'end', seg.get('end', 0))
            text = getattr(seg, 'text', seg.get('text', ""))
            
            s_start = int(start_s * fs)
            s_end = int(end_s * fs)
            
            if (s_end - s_start) < (0.3 * fs):
                seg_data = {"start": start_s, "end": end_s, "text": text, "speaker": processed[-1]['speaker'] if processed else "SPEAKER_01"}
                processed.append(seg_data)
                continue

            try:
                chunk = signal[:, s_start:s_end]
                emb = self.get_file_embedding_from_signal(chunk)
                if emb is None:
                    processed.append({"start": start_s, "end": end_s, "text": text, "speaker": "SPEAKER_01"})
                    continue
                
                best_speaker = None
                max_sim = -1.0
                
                for spk_id, proto in speaker_prototypes.items():
                    sim = cosine_similarity(emb.reshape(1, -1), proto.reshape(1, -1))[0][0]
                    if sim > max_sim:
                        max_sim = sim
                        best_speaker = spk_id
                
                if best_speaker and max_sim > similarity_threshold:
                    speaker_prototypes[best_speaker] = (speaker_prototypes[best_speaker] * 0.8) + (emb * 0.2)
                else:
                    best_speaker = f"SPEAKER_{next_id:02d}"
                    speaker_prototypes[best_speaker] = emb
                    next_id += 1
                
                processed.append({"start": start_s, "end": end_s, "text": text, "speaker": best_speaker})
            except:
                processed.append({"start": start_s, "end": end_s, "text": text, "speaker": "SPEAKER_01"})

        return processed


def run_blind_diarization_pass(job_dir, vocals_path, cb=None, etapa_idx=1):
    """
    Passo 1 (Diarização Dupla): Faz varredura cega no áudio ANTES do Whisper.
    Usa VAD PyDub para fatiar apenas onde há som, Pyannote para embutir.
    """
    job_dir = Path(job_dir)
    if cb: cb(10, etapa_idx, "Diarização Ultra-Sensível: Mapeando vozes (Modo Deep Scan)...")
    from pydub import AudioSegment
    
    cache_path = job_dir / "diarization_cache.json"

    try:
        audio = AudioSegment.from_wav(str(vocals_path))
        duration_ms = len(audio)
        
        slice_len = 3000
        segments_to_process = []
        for start_ms in range(0, duration_ms, slice_len):
            end_ms = min(start_ms + slice_len, duration_ms)
            if end_ms - start_ms < 500: continue
            segments_to_process.append((start_ms, end_ms))
        
        if not segments_to_process: return []
             
        if cb: cb(30, etapa_idx, f"Diarização (Pyannote 3.1): Analisando {len(segments_to_process)} amostras de voz...")
        
        import torch
        diarizer = PyannoteDiarizer(device='cuda' if torch.cuda.is_available() else 'cpu')
        
        signal, fs = robust_audio_load(str(vocals_path))
        if signal.shape[0] > 1: signal = signal.mean(dim=0, keepdim=True)
        if fs != 16000:
            import torchaudio.transforms as T
            resampler = T.Resample(fs, 16000)
            signal = resampler(signal)
        
        results = []
        for i, (sts, ets) in enumerate(segments_to_process):
             start_sec = sts / 1000.0
             end_sec = ets / 1000.0
              
             s_sample = int(start_sec * 16000)
             e_sample = int(end_sec * 16000)
             seg_signal = signal[:, s_sample:e_sample]
              
             if seg_signal.shape[1] < 1600: continue
              
             emb = diarizer.get_file_embedding_from_signal(seg_signal)
             if emb is not None:
                 results.append({"start": start_sec, "end": end_sec, "emb": emb})
               
        if not results: return []

        from sklearn.cluster import AgglomerativeClustering
        embeddings = np.array([r['emb'] for r in results])
        clusterer = AgglomerativeClustering(n_clusters=None, distance_threshold=0.45, metric='cosine', linkage='average')
        labels = clusterer.fit_predict(embeddings)
        
        final_cache = []
        diarization_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
        diarization_dir.mkdir(parents=True, exist_ok=True)
        
        logging.info(f"📁 Organizando amostras de voz em {diarization_dir}...")
        
        for i, lbl in enumerate(labels):
            speaker_id = f"voz{lbl+1}"
            speaker_path = diarization_dir / speaker_id
            speaker_path.mkdir(exist_ok=True)
            
            start_sec = results[i]["start"]
            end_sec = results[i]["end"]
            
            final_cache.append({
                "start": start_sec,
                "end": end_sec,
                "speaker": speaker_id
            })
            
            existing_samples = list(speaker_path.glob("*.wav"))
            if len(existing_samples) < 5:
                try:
                    import soundfile as sf
                    s_sample = int(start_sec * 16000)
                    e_sample = int(end_sec * 16000)
                    seg_data = signal[:, s_sample:e_sample].cpu().numpy().T
                    
                    sample_file = speaker_path / f"amostra_{i}.wav"
                    sf.write(str(sample_file), seg_data, 16000)
                except Exception as e:
                    logging.warning(f"Falha ao exportar amostra de voz {i}: {e}")
            
        safe_json_write(final_cache, cache_path)
        
        logging.info("🧹 [VRAM_PURGE] Expulsando Pyannote da GPU (Cego)...")
        del diarizer
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            torch.cuda.synchronize()
        logging.info("✅ [VRAM_PURGE] Pyannote descarregado com sucesso (Cego).")
        
        if cb: cb(50, etapa_idx, "Diarização Cega: Concluída.")
        return final_cache
        
    except Exception as e:
        logging.error(f"Erro na Diarização Cega: {e}")
        return []


def split_audio_by_speaker(audio_path, job_dir):
    """
    Analisa se houve troca de voz e divide o arquivo usando VAD Cirúrgico.
    """
    try:
        from pydub import AudioSegment
        duration = get_audio_duration(audio_path)
        if duration < 6.0:
            return False
            
        diarizer = PyannoteDiarizer(device="cpu")
        splits = diarizer.detect_splits_surgical(audio_path)
        
        if not splits: return False
        
        logging.info(f"Diarização Cirúrgica v10.60: detectadas {len(splits)} trocas de voz em '{audio_path.name}'.")
        sound = AudioSegment.from_wav(str(audio_path))
        
        points = [0] + [int(s * 1000) for s in splits] + [len(sound)]
        for i in range(len(points) - 1):
            start, end = points[i], points[i+1]
            if end - start < 300: continue
            chunk = sound[start:end]
            chunk.export(audio_path.parent / f"{audio_path.stem}_p{i+1:02d}.wav", format="wav")
            
        backup_dir = job_dir / "_0_ORIGINAIS_BACKUP"
        backup_dir.mkdir(exist_ok=True)
        shutil.move(str(audio_path), str(backup_dir / audio_path.name))
        return True
    except Exception as e:
        logging.error(f"Falha na Diarização Cirúrgica v10.60: {e}")
        return False


def consolidate_speaker_segments(job_dir, project_data, cb, etapa_idx):
    """
    Consolidação de Oradores.
    """
    return project_data


def wait_for_diarization_manual(job_id, cb):
    source_dir = Path(app.config['UPLOAD_FOLDER']) / job_id / "_1_MOVER_OS_FICHEIROS_DAQUI"
    if not any(source_dir.iterdir()):
        logging.info("Nenhum arquivo para diarização manual.")
        return
        
    total_files_in_subdirs = len(list(source_dir.rglob("*.wav")))
    if total_files_in_subdirs == 0:
        logging.info("Nenhum arquivo para diarização manual.")
        return

    while True:
        num_files_remaining = len(list(source_dir.rglob("*.wav")))
        if num_files_remaining == 0:
            logging.info(f">>> Diarização manual para o job '{job_id}' concluída. Retomando pipeline. <<<")
            cb(100, 1, "Diarização manual concluída.")
            break
        else:
            msg = f"Arquivos longos foram separados. Organize todos os {num_files_remaining} segmentos/arquivos."
            sys.stdout.write(f"\r{''.ljust(150)}\r") 
            logging.warning(f">>> PAUSA: {msg} <<<")
            progress = ((total_files_in_subdirs - num_files_remaining) / total_files_in_subdirs) * 100 if total_files_in_subdirs > 0 else 0
            cb(progress, 1, msg)
            time.sleep(5)


def run_auto_diarization_batch(job_dir, job_id, cb):
    """
    Diarização Automática para Lotes de Arquivos (Jogos).
    """
    source_dir = job_dir / "_1_MOVER_OS_FICHEIROS_DAQUI"
    clean_audio_dir = job_dir / "_1b_AUDIO_LIMPO"
    segmented_dir = job_dir / "_1c_AUDIO_SEGMENTADO"
    backup_dir = job_dir / "_backup_transcricao"
    target_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
    
    marker_path = target_dir / "unification_done.marker"
    project_data_path = job_dir / "project_data.json"
    if marker_path.exists() and project_data_path.exists():
        logging.info("Diarização e unificação já concluídas neste projeto. Pulando Fase 1 inteira para acelerar o reinício.")
        cb(100, 1, "Diarização restaurada do cache.")
        return

    clean_audio_dir.mkdir(parents=True, exist_ok=True)
    segmented_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    status_path = job_dir / "job_status.json"
    status_data = safe_json_read(status_path) or {}
    use_openunmix = str(status_data.get('preserve_background', 'false')).lower() == 'true'

    if use_openunmix:
        logging.info("[OPENUNMIX] Separação de Fundo ATIVADA. Iniciando...")
        run_openunmix_batch(source_dir, job_dir, cb)
        source_dir = job_dir / "_0a_SEPARACAO_VOCAL"
        logging.info(f"[OPENUNMIX] Fonte de áudio alterada para: {source_dir}")

    source_files = list(source_dir.rglob("*.wav"))
    if not source_files:
        logging.info("Nenhum arquivo para processar.")
        return

    run_batch_cleaning(source_dir, clean_audio_dir, cb)
    
    clean_files = sorted(list(clean_audio_dir.rglob("*.wav")))
    if not clean_files:
         clean_files = source_files

    status_path = job_dir / "job_status.json"
    status_data = safe_json_read(status_path) or {}
    try:
        num_speakers = int(status_data.get('num_speakers', '0'))
    except: num_speakers = 0
    source_lang = status_data.get('source_language', 'auto')

    cb(0, 1, "Fase 1: Transcrição e Segmentação...")
    
    import threading
    from concurrent.futures import ThreadPoolExecutor
    
    progress_lock = threading.Lock()
    completed_count = 0
    total_files = len(clean_files)
    
    whisper_model = get_whisper_model()
    whisper_lang = source_lang if source_lang != 'auto' else None
    
    def worker_transcribe(audio_file):
        nonlocal completed_count
        try:
            duration = get_audio_duration(audio_file)
            should_split = duration > 25.0 and num_speakers != 1
            
            if not should_split:
                dest_wav = segmented_dir / audio_file.name
                dest_json = backup_dir / f"{audio_file.stem}.json"
                
                if not (dest_wav.exists() and dest_json.exists()):
                    shutil.copy(str(audio_file), str(dest_wav))
                    segments, info = whisper_model.transcribe(str(dest_wav), beam_size=1, word_timestamps=False, language=whisper_lang, vad_filter=True)
                    text = "".join([s.text for s in list(segments)]).strip()
                    
                    safe_json_write({
                        "id": audio_file.stem,
                        "original_text": text,
                        "duration": duration,
                        "source_file": str(dest_wav),
                        "detected_language": getattr(info, 'language', None)
                    }, dest_json)
            else:
                related_jsons = list(backup_dir.glob(f"{audio_file.stem}_seg*.json"))
                if not related_jsons:
                    segments, info = whisper_model.transcribe(str(audio_file), beam_size=1, word_timestamps=False, language=whisper_lang, vad_filter=True)
                    segments = list(segments)
                    detected_lang = getattr(info, 'language', None)
                    
                    if segments:
                        from pydub import AudioSegment
                        audio_seg = AudioSegment.from_wav(str(audio_file))
                        grouped_chunks = []
                        current_group_start = -1
                        current_group_end = -1
                        
                        for seg in segments:
                            start_ms = max(0, int(seg.start * 1000) - 50)
                            end_ms = min(len(audio_seg), int(seg.end * 1000) + 50)
                            
                            if (end_ms - start_ms) < 200: continue
                            
                            if current_group_start == -1:
                                current_group_start = start_ms
                                current_group_end = end_ms
                            else:
                                proposed_duration = (end_ms - current_group_start) / 1000.0
                                if proposed_duration <= 25.0:
                                    current_group_end = end_ms
                                else:
                                    grouped_chunks.append((current_group_start, current_group_end))
                                    current_group_start = start_ms
                                    current_group_end = end_ms
                                    
                        if current_group_start != -1:
                            grouped_chunks.append((current_group_start, current_group_end))
                            
                        for idx, (g_start, g_end) in enumerate(grouped_chunks):
                            chunk = audio_seg[g_start:g_end]
                            chunk_name = f"{audio_file.stem}_seg{idx:03d}_{int(g_start/1000)}s.wav"
                            chunk_path = segmented_dir / chunk_name
                            chunk.export(chunk_path, format="wav")
                            
                            json_path = backup_dir / f"{chunk_path.stem}.json"
                            try:
                                c_segments, _ = whisper_model.transcribe(str(chunk_path), beam_size=1, word_timestamps=False, language=whisper_lang, vad_filter=True)
                                chunk_text = "".join([s.text for s in list(c_segments)]).strip()
                            except:
                                chunk_text = ""
                                
                            safe_json_write({
                                "id": chunk_path.stem,
                                "original_text": chunk_text,
                                "duration": len(chunk) / 1000.0,
                                "source_file": str(chunk_path),
                                "detected_language": detected_lang
                            }, json_path)
            
            with progress_lock:
                completed_count += 1
                cb((completed_count / total_files) * 40, 1, f"Transcrevendo [{completed_count}/{total_files}]: {audio_file.name}", current_seg=completed_count, total_seg=total_files)
        except Exception as e:
            logging.error(f"Erro ao processar {audio_file.name}: {e}")
            with progress_lock:
                completed_count += 1
                cb((completed_count / total_files) * 40, 1, f"Falha [{completed_count}/{total_files}]: {audio_file.name}", current_seg=completed_count, total_seg=total_files)
                
    import torch
    device_hw = "cuda" if torch.cuda.is_available() else "cpu"
    max_w = 2 if device_hw == "cuda" else 1
    logging.info(f"🚀 [TRANSCRICAO] Iniciando transcrição de áudio com {max_w} workers (Safe Mode).")
    
    with ThreadPoolExecutor(max_workers=max_w) as executor:
        executor.map(worker_transcribe, clean_files)
        
    unload_whisper_model()

    cb(40, 1, "Fase 2: Diarização Global...")
    
    diarizer = PyannoteDiarizer()
    all_segments = sorted(list(segmented_dir.glob("*.wav")))
    
    if not all_segments:
        logging.warning("Fase 2 abortada: Nenhum segmento para diarizar.")
        return

    embeddings_map = {}
    
    for i, seg_path in enumerate(all_segments):
        cb(40 + (i / len(all_segments)) * 30, 1, f"Analisando voz: {seg_path.name}", current_seg=i+1, total_seg=len(all_segments))
        emb = diarizer.get_file_embedding(str(seg_path))
        if emb is not None:
             embeddings_map[seg_path.name] = emb
             
    cb(70, 1, "Agrupando Falantes...")
    if num_speakers == 1:
        file_to_voice = {f.name: 'voz1' for f in all_segments}
    else:
        n_clusters = num_speakers if num_speakers > 1 else None
        file_to_voice = diarizer.cluster_batch_embeddings(embeddings_map, n_clusters)
        
    logging.info("🧹 [VRAM_PURGE] Expulsando Pyannote da GPU (Diarização Batch)...")
    del diarizer
    import gc
    import torch
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
        torch.cuda.synchronize()
    logging.info("✅ [VRAM_PURGE] Pyannote descarregado com sucesso.")

    cb(80, 1, "Organizando pastas...")
    
    for seg_path in all_segments:
        fname = seg_path.name
        voice_id = file_to_voice.get(fname, "voz_desconhecida")
        voice_folder = target_dir / voice_id
        voice_folder.mkdir(parents=True, exist_ok=True)
        final_path = voice_folder / fname
        if not final_path.exists():
            shutil.copy(str(seg_path), str(final_path))
            
    cb(90, 1, "Finalizando: Gerando metadados do projeto...")
    
    final_project_data = []
    if target_dir.exists():
        for voice_folder in target_dir.iterdir():
            if not voice_folder.is_dir(): continue
            speaker_id = voice_folder.name
            
            for wav_path in voice_folder.glob("*.wav"):
                if wav_path.name.startswith("_REF_"): continue
                json_backup_path = backup_dir / f"{wav_path.stem}.json"
                
                original_text = ""
                duration = 0.0
                
                if json_backup_path.exists():
                    try:
                        meta = safe_json_read(json_backup_path)
                        original_text = meta.get('original_text', '')
                        duration = meta.get('duration', 0.0)
                    except: pass
                else:
                    try: duration = get_audio_duration(wav_path)
                    except: pass
                
                final_project_data.append({
                    "id": wav_path.stem,
                    "file_name": wav_path.name,
                    "original_text": original_text,
                    "translated_text": "",
                    "speaker": speaker_id,
                    "start_time": 0,
                    "end_time": duration,
                    "duration": duration,
                    "file_path": str(wav_path),
                    "status": "pending_translation" 
                })
    
    safe_json_write(final_project_data, job_dir / "project_data.json")
    
    total_seconds = sum(item.get('duration', 0) for item in final_project_data)
    duracao_total_formatada = str(timedelta(seconds=int(total_seconds)))
    
    status_path = job_dir / "job_status.json"
    status_data = safe_json_read(status_path) or {}
    status_data['duracao_total_formatada'] = duracao_total_formatada
    status_data['total_wav_seconds'] = total_seconds
    safe_json_write(status_data, status_path)

    logging.info(f"Project Data gerado com {len(final_project_data)} segmentos. Duração Total de Áudio: {duracao_total_formatada}")
    cb(100, 1, "Diarização Concluída.")


def unify_speaker_files(job_dir, cb):
    diarization_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
    marker_path = diarization_dir / "unification_done.marker"
    if marker_path.exists():
        logging.info("Unificação de vozes já concluída anteriormente. Pulando.")
        return

    voice_folders = [d for d in diarization_dir.iterdir() if d.is_dir() and d.name.startswith('voz')]
    if not voice_folders: return

    cb(0, 1, "Iniciando unificação inteligente de vozes...")
    diarizer = PyannoteDiarizer()
    
    folder_centroids = []
    for i, folder in enumerate(voice_folders):
        cb((i / len(voice_folders)) * 100, 1, f"Unificando Orador: {folder.name}", current_seg=i+1, total_seg=len(voice_folders))
        wavs = list(folder.glob("*.wav"))
        if not wavs: continue
        
        samples = random.sample(wavs, min(len(wavs), 5)) 
        embeddings = []
        for wav in samples:
            try:
                emb = diarizer.get_file_embedding(str(wav))
                if emb is not None: embeddings.append(emb)
            except: pass
            
        if embeddings:
            centroid = np.mean(embeddings, axis=0)
            folder_centroids.append({'folder': folder, 'centroid': centroid, 'count': len(wavs)})
    
    MERGE_THRESHOLD = 0.65
    folder_centroids.sort(key=lambda x: x['count'], reverse=True)
    final_folders = []
    
    cb(90, 1, "Realizando Consolidação Inteligente de vozes...")
    for i, item in enumerate(folder_centroids):
        current_folder = item['folder']
        current_emb = item['centroid']
        
        cb(90 + (i / len(folder_centroids)) * 10, 1, f"Analisando afinidade: {current_folder.name}", current_seg=i+1, total_seg=len(folder_centroids))
        merged = False
        for target in final_folders:
            dist = cosine_similarity([current_emb], [target['centroid']])[0][0]
            if dist > MERGE_THRESHOLD:
                log_msg = f"Mesclando {current_folder.name} -> {target['folder'].name} (Sim: {round(dist, 2)})"
                logging.info(log_msg)
                cb(90 + (i / len(folder_centroids)) * 10, 1, log_msg, current_seg=i+1, total_seg=len(folder_centroids))
                
                for f in current_folder.glob("*.wav"):
                    try:
                        shutil.move(str(f), str(target['folder'] / f.name))
                    except: pass
                
                try: current_folder.rmdir() 
                except: pass
                merged = True
                break
        
        if not merged:
            final_folders.append(item)

    project_data_path = job_dir / "project_data.json"
    project_text_map = {}
    try:
        if project_data_path.exists():
            pdata = safe_json_read(project_data_path) or []
            for item in pdata:
                txt = item.get('original_text', '').lower().strip()
                txt = re.sub(r'[^\w\s]', '', txt)
                project_text_map[item['id']] = txt
    except: pass

    cb(90, 1, "Realizando Consolidação Inteligente de vozes...")
    voice_folders = [d for d in diarization_dir.iterdir() if d.is_dir() and d.name.startswith('voz')]
    
    valid_voices = []
    questionable_voices = []
    
    def get_folder_stats(folder):
        wavs = list(folder.glob("*.wav"))
        wavs = [w for w in wavs if "_REF_" not in w.name]
        if not wavs: return None
        
        if len(wavs) > 15:
             total_duration = 999.0
        else:
             total_duration = 0.0
             for w in wavs:
                 try: total_duration += get_audio_duration(w)
                 except: pass
                 if total_duration >= 10.0: break

        embeddings = []
        samples = random.sample(wavs, min(len(wavs), 5))
        for w in samples:
             try:
                 emb = diarizer.get_file_embedding(str(w))
                 if emb is not None: embeddings.append(emb)
             except: pass
        
        if not embeddings: return None
        centroid = np.mean(embeddings, axis=0)
        
        return {
            'folder': folder,
            'centroid': centroid,
            'duration': total_duration,
            'file_count': len(wavs)
        }

    stats_list = []
    for vf in voice_folders:
        s = get_folder_stats(vf)
        if s: stats_list.append(s)
        
    for s in stats_list:
        if s['duration'] >= 10.0:
            valid_voices.append(s)
        else:
            questionable_voices.append(s)
            
    count_merged = 0
    count_kept = 0
    
    for q in questionable_voices:
        best_match = None
        best_score = -1.0
        
        for v in valid_voices:
            dist = cosine_similarity([q['centroid']], [v['centroid']])[0][0]
            if dist > best_score:
                best_score = dist
                best_match = v
                
        if best_match and best_score > 0.60:
            logging.info(f"[SMART MERGE] Fundindo {q['folder'].name} -> {best_match['folder'].name} (Sim: {round(best_score, 2)})")
            for f in q['folder'].glob("*.wav"):
                try: shutil.move(str(f), str(best_match['folder'] / f.name))
                except: pass
            try: q['folder'].rmdir()
            except: pass
            count_merged += 1
        else:
            logging.info(f"[SMART KEEP] Mantendo {q['folder'].name} (Sim Máx: {round(best_score, 2)} < 0.60)")
            count_kept += 1
            
    cb(100, 1, f"Consolidação: {count_merged} fundidos, {count_kept} mantidos.")

    if not valid_voices and questionable_voices:
         logging.info("Aviso: Todas as vozes detectadas são curtas (<10s). Mantendo originais.")

    cb(95, 1, "Gerando áudios de referência unificados para as vozes...")
    final_voice_folders = [d for d in diarization_dir.iterdir() if d.is_dir() and d.name.startswith('voz')]
    
    BAD_REF_WORDS = [
        'argh', 'ah', 'oh', 'uh', 'hmm', 'wow', 'tsk', 'ugh', 'screams', 'gasps', 'moans', 'chokes', 'grita', 'geme', 
        'laughs', 'chuckles', 'sobs', 'cries', 'sighs', 'eh', 'heh', 'hum', 'ha', 'haha', 'hah', 'whoa', 'ooh', 'aw', 
        'ouch', 'ow', 'psst', 'shh', 'yikes', 'yay', 'ew', 'ick', 'boo', 'hiss', 'growl', 'snarl', 'roar', 'bark', 
        'meow', 'purr', 'chirp', 'squeak', 'whimper', 'pant', 'gasp', 'cough', 'sneeze', 'burp', 'hiccup', 'yawn',
        'sniff', 'spit', 'swallow', 'gulp', 'choke', 'rasp', 'groan', 'grunt', 'mumble', 'mutter', 'shout', 'yell',
        'scream', 'shriek', 'wail', 'cry', 'sob', 'laugh', 'giggle', 'chuckle', 'snicker', 'snort', 'wheeze', 'breath',
        'breathing', 'inhale', 'exhale', 'noise', 'sound', 'static', 'interference', 'radio', 'beep', 'boop', 'click',
        'clack', 'bang', 'boom', 'crash', 'thud', 'thump', 'smash', 'crack', 'snap', 'pop', 'fizz', 'buzz', 'whir', 
        'clank', 'clatter', 'rattle', 'rustle', 'scratch', 'scrape', 'scuff'
    ]

    for i, voice_folder in enumerate(final_voice_folders):
        output_ref_path = voice_folder / "_REF_VOZ_UNIFICADA.wav"
        
        wav_files = sorted(list(voice_folder.glob("*.wav")))
        actual_wavs = [w for w in wav_files if not w.name.startswith("_REF_")]
        
        if output_ref_path.exists():
            folder_mtime = voice_folder.stat().st_mtime
            ref_mtime = output_ref_path.stat().st_mtime
            if ref_mtime < folder_mtime:
                logging.info(f"[REF UPDATE] Pasta '{voice_folder.name}' atualizada. Regenerando referência...")
                try: output_ref_path.unlink()
                except: pass
            else:
                continue
        if not wav_files: continue
        
        valid_wavs = []
        for w in wav_files:
            if w.name.startswith("_REF_"): continue
            if w.stat().st_size < 8000: continue 

            fid = w.stem
            if fid in project_text_map:
                text = project_text_map[fid]
                if len(text) < 15 and any(bad in text.lower() for bad in BAD_REF_WORDS): continue
                if len(text) < 2: continue
            valid_wavs.append(w)

        if not valid_wavs: 
            valid_wavs = [w for w in wav_files if not w.name.startswith("_REF_") and w.stat().st_size > 8000]

        valid_wavs.sort(key=lambda x: x.stat().st_size, reverse=True)
        top_files = valid_wavs[:50]
        
        combined_audio = AudioSegment.empty()
        total_dur = 0
        
        for wav_file in top_files:
            try: 
                seg = AudioSegment.from_wav(wav_file)
                if len(seg) < 800: continue
                from pydub.silence import detect_nonsilent
                nonsilent = detect_nonsilent(seg, min_silence_len=100, silence_thresh=-40)
                if nonsilent:
                    seg = seg[nonsilent[0][0]:nonsilent[-1][1]]
                
                if len(combined_audio) > 0:
                    combined_audio = combined_audio.append(seg, crossfade=50)
                else:
                    combined_audio = seg

                total_dur += len(seg)
                if total_dur > 15000: break
            except Exception as e: logging.error(f"Erro ref unificada {wav_file}: {e}")
        
        if len(combined_audio) > 0:
            temp_combined_path = voice_folder / "_temp_combined.wav"
            combined_audio.export(temp_combined_path, format="wav")
            try:
                threads = str(max(1, (os.cpu_count() or 4) // 2))
                samples_health = np.array(combined_audio.get_array_of_samples())
                ref_rms = np.sqrt(np.mean(samples_health.astype(np.float32)**2)) / 32768.0
                is_noisy = ref_rms > 0.008
                
                if is_noisy:
                    logging.info(f"Voz {voice_folder.name}: Ruído detectado (RMS {ref_rms:.4f}). Removendo apenas graves inúteis (rumble).")
                    af_filters = "highpass=f=80,aresample=22050"
                else:
                    logging.info(f"Voz {voice_folder.name}: Qualidade de Estúdio detectada (RMS {ref_rms:.4f}). Bypass Cleaner ativado.")
                    af_filters = "aresample=22050"

                speaker_profile = voice_folder / "acoustic_profile.json"
                safe_json_write({"is_noisy": bool(is_noisy), "rms": float(ref_rms)}, speaker_profile)

                cmd = ['ffmpeg', '-threads', threads, '-y', '-i', str(temp_combined_path), 
                       '-af', af_filters, '-ac', '1', '-ar', '22050', str(output_ref_path)]
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e: combined_audio.export(output_ref_path, format="wav")
            finally:
                if temp_combined_path.exists(): os.remove(temp_combined_path)

    if 'diarizer' in locals():
        logging.info("🧹 [VRAM_PURGE] Expulsando Pyannote da GPU (Unificação)...")
        del diarizer
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            torch.cuda.synchronize()
        logging.info("✅ [VRAM_PURGE] Pyannote descarregado com sucesso (Unificação).")

    with open(marker_path, 'w') as f:
        f.write("done")
    cb(100, 1, "Vozes unificadas e limpas.")


def get_speaker_at_time(t, diarization_data):
    if not diarization_data: return "unknown"
    for d in diarization_data:
        if (d['start'] - 0.1) <= t <= (d['end'] + 0.1):
            return d.get('speaker', 'unknown')
    return "unknown"


def recriar_pastas_de_voz(job_dir, audio_path, segments):
    try:
        from pydub import AudioSegment
        job_dir = Path(job_dir)
        voice_folders_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
        voice_folders_dir.mkdir(exist_ok=True, parents=True)
        
        logging.info(f"🔨 [RECONSTRUÇÃO] Recriando referências de áudio para {len(segments)} segmentos...")
        full_audio = AudioSegment.from_wav(str(audio_path))
        
        for i, seg in enumerate(segments):
            spk = seg.get('speaker', 'voz_unknown')
            spk_dir = voice_folders_dir / spk
            spk_dir.mkdir(exist_ok=True, parents=True)
            
            chunk = full_audio[int(max(0, seg['start'])*1000):int(seg['end']*1000)]
            chunk.export(str(spk_dir / f"seg_{i}.wav"), format="wav")
            
        logging.info("✅ [RECONSTRUÇÃO] Pastas de voz restauradas com sucesso!")
        prepare_video_speaker_references(job_dir)
        return True
    except Exception as e:
        logging.error(f"Erro ao recriar pastas de voz: {e}")
        return False


def prepare_video_speaker_references(job_dir):
    try:
        from pydub import AudioSegment
        job_dir = Path(job_dir)
        voice_folders_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
        
        if not voice_folders_dir.exists(): return
        
        for voice_folder in voice_folders_dir.iterdir():
            if not voice_folder.is_dir(): continue
            output_ref_path = voice_folder / "_REF_VOZ_UNIFICADA.wav"
            if output_ref_path.exists(): continue
            
            wav_files = sorted(list(voice_folder.glob("seg_*.wav")), key=lambda x: x.stat().st_size, reverse=True)
            if not wav_files: continue
            
            logging.info(f"🎤 [REF_GEN] Criando áudio mestre para: {voice_folder.name}")
            combined_audio = AudioSegment.empty()
            total_dur_ms = 0
            
            for wav_file in wav_files[:12]:
                try:
                    seg = AudioSegment.from_wav(str(wav_file))
                    if len(seg) < 300: continue
                    if len(combined_audio) > 0: combined_audio = combined_audio.append(seg, crossfade=100)
                    else: combined_audio = seg
                    total_dur_ms += len(seg)
                    if total_dur_ms > 12000: break
                except: continue
            
            if len(combined_audio) > 0:
                combined_audio = combined_audio.set_frame_rate(24000).set_channels(1)
                combined_audio.export(str(output_ref_path), format="wav")
                logging.info(f"✅ [REF_READY] Arquivo mestre criado em {voice_folder.name}")
    except Exception as e:
        logging.error(f"Erro ao preparar referências de vídeo: {e}")


import atexit
def _run_cleanup():
    try:
        from nexus.core.model_loader import cleanup_on_exit
        cleanup_on_exit()
    except Exception:
        pass
atexit.register(_run_cleanup)
