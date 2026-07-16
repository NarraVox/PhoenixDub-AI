# -*- coding: utf-8 -*-
# Vortex Workers Module - [v2026.RTX_ULTRA]
# Background worker tasks for Whisper transcription and Librosa analysis.

import os
import sys
import json
import logging
import time
from datetime import datetime
from pathlib import Path

def run_transcription(files_json_path, project_status_path):
    """Worker de Transcrição Whisper integrado."""
    from faster_whisper import WhisperModel
    
    logging.basicConfig(level=logging.INFO)
    with open(files_json_path, 'r') as f:
        files = json.load(f)
    
    if not files:
        logging.info("ℹ️ [WORKER] Lista vazia. Nada para transcrever.")
        return
    
    if not Path(project_status_path).exists():
        logging.warning(f"⚠️ [WORKER] Arquivo {project_status_path} não encontrado. Criando novo...")
        status = {"tracks": {}, "completed_mixes": []}
    else:
        with open(project_status_path, 'r') as f:
            status = json.load(f)

    logging.info(f"⚡ [FASTER-WHISPER] Ignorando CPU e ativando núcleos CUDA (RTX 3050)...")
    num_threads = os.cpu_count() or 4
    model = WhisperModel("base", device="cuda", compute_type="float16", cpu_threads=num_threads, num_workers=2)
    
    total_files = len(files)
    logging.info(f"🚀 [WHISPER] Iniciando processamento ultra-rápido de {total_files} segmentos...")

    for i, f_path in enumerate(files, 1):
        path = Path(f_path)
        name = path.name
        
        lyrics = ""
        try:
            segments, info = model.transcribe(str(path), beam_size=1, vad_filter=True)
            lyrics = " ".join([s.text for s in segments])
        except Exception as e:
            logging.error(f"Erro no Whisper para {name}: {e}")

        if name not in status["tracks"]: status["tracks"][name] = {}
        status["tracks"][name]["lyrics"] = lyrics
        status["tracks"][name]["whisper_done"] = True
        
        if i % 10 == 0 or i == total_files:
            time_str = datetime.now().strftime("%H:%M:%S")
            msg = f"[{time_str}] 🎙️ [{i}/{total_files}] Dublando... (Último: {name})"
            status["current_task"] = msg
            status.setdefault("logs", []).append(msg)
            
            if Path(project_status_path).exists():
                try:
                    with open(project_status_path, 'r') as f_check:
                        live_status = json.load(f_check)
                        status["completed_mixes"] = live_status.get("completed_mixes", [])
                except: pass

            with open(project_status_path, 'w') as f:
                json.dump(status, f, indent=4)
            logging.info(msg)

    if Path(project_status_path).exists():
        with open(project_status_path, 'r') as f: status = json.load(f)
        status["current_task"] = None
        status.setdefault("logs", []).append("✅ [WHISPER] Transcrição concluída.")
        with open(project_status_path, 'w') as f: json.dump(status, f, indent=4)

    logging.info("✅ [FASTER-WHISPER] Transcrição concluída. Liberando VRAM.")
    try:
        import torch
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except: pass


def run_analysis(files_json_path, project_status_path):
    """Worker de Análise Librosa integrado."""
    import librosa
    import numpy as np
    
    logging.basicConfig(level=logging.INFO)
    with open(files_json_path, 'r') as f:
        files = json.load(f)
        
    if not files:
        logging.info("ℹ️ [WORKER] Lista vazia. Nada para analisar.")
        return
    
    if not Path(project_status_path).exists():
        logging.warning(f"⚠️ [WORKER] Arquivo {project_status_path} não encontrado. Criando novo...")
        status = {"tracks": {}, "completed_mixes": [], "logs": []}
    else:
        with open(project_status_path, 'r') as f:
            status = json.load(f)
        if "logs" not in status: status["logs"] = []

    total_files = len(files)
    for i, f_path in enumerate(files, 1):
        name = Path(f_path).name
        start_t = time.time()
        time_str = datetime.now().strftime("%H:%M:%S")
        
        existing = status.get("tracks", {}).get(name, {})
        if all(k in existing for k in ["bpm", "key", "energy", "energy_map", "beats"]):
            logging.info(f"⏩ [SKIP] {name} já analisado.")
            continue

        msg_start = f"[{time_str}] 🔬 [{i}/{total_files}] Analisando técnica: {name} (Librosa)"
        status["current_task"] = msg_start
        status.setdefault("logs", []).append(f"> {msg_start}")
        with open(project_status_path, 'w') as f:
            json.dump(status, f, indent=4)
        
        try:
            logging.info(f"🔬 [ANALYSIS] Escaneando: {name}")
            y, sr = librosa.load(f_path, sr=44100)
            
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            bpm = float(tempo[0]) if isinstance(tempo, np.ndarray) else float(tempo)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
            
            rms = librosa.feature.rms(y=y)[0]
            chunks = np.array_split(rms, 10)
            energy_map = [round(float(np.mean(c)), 4) for c in chunks]
            
            S = np.abs(librosa.stft(y))
            vocal_presence = [round(float(np.mean(librosa.feature.spectral_centroid(S=S[:, j:j+100], sr=sr))), 2) for j in range(0, S.shape[1], 100)]
            
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            key_idx = np.argmax(np.mean(chroma, axis=1))
            keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            key_name = keys[key_idx]
            
            spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
            brightness = np.mean(spec_centroid)

            if name not in status["tracks"]: status["tracks"][name] = {}
            status["tracks"][name].update({
                "bpm": round(bpm, 2),
                "key": key_name,
                "energy": round(float(np.mean(rms)), 4),
                "energy_map": energy_map,
                "vocal_map": vocal_presence[:10],
                "brightness": round(float(brightness), 2),
                "duration": float(librosa.get_duration(y=y, sr=sr)),
                "beats": beat_times[:40],
                "first_beat": beat_times[0] if beat_times else 0
            })
            
            elapsed = round(time.time() - start_t, 1)
            msg_end = f"✅ [{i}/{total_files}] {name} analisado em {elapsed}s."
            status.setdefault("logs", []).append(msg_end)
            logging.info(msg_end)
            
        except Exception as e:
            logging.error(f"❌ Erro ao analisar {name}: {e}")
            status.setdefault("logs", []).append(f"ERRO: {name} ({str(e)})")
        
        with open(project_status_path, 'w') as f:
            json.dump(status, f, indent=4)

    if Path(project_status_path).exists():
        with open(project_status_path, 'r') as f: status = json.load(f)
        status["current_task"] = None
        status.setdefault("logs", []).append("🏁 [ANALYSIS] Scan técnico concluído.")
        with open(project_status_path, 'w') as f: json.dump(status, f, indent=4)

    logging.info("✅ [ANALYSIS WORKER] Tarefa concluída. Encerrando processo.")
