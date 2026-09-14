# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Nexus AI Pro - High-Speed Audio Batch Normalization & Preprocessing Module
# Token-efficient modularization (< 500 lines)

import os
import subprocess
import logging
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

SUPPORTED_AUDIO_EXTENSIONS = ('.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aac', '.wma', '.opus')

def _convert_single_audio_ffmpeg(src_path: Path, dst_path: Path, sample_rate: int = 16000) -> bool:
    """
    Converte rapidamente um arquivo de áudio para WAV PCM 16-bit Mono 16kHz via FFmpeg.
    """
    try:
        # -y: sobrescrever, -vn: sem vídeo, -ac 1: mono, -ar 16000: 16kHz, -sample_fmt s16: PCM 16-bit
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-i", str(src_path),
            "-ac", "1",
            "-ar", str(sample_rate),
            "-acodec", "pcm_s16le",
            str(dst_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return res.returncode == 0 and dst_path.exists() and dst_path.stat().st_size > 44
    except Exception as e:
        logging.debug(f"FFmpeg falhou para {src_path.name}: {e}")
        return False

def _convert_single_audio_soundfile(src_path: Path, dst_path: Path, sample_rate: int = 16000) -> bool:
    """
    Fallback usando soundfile / librosa / pydub se FFmpeg não estiver disponível no PATH.
    """
    try:
        import soundfile as sf
        import numpy as np

        # Tenta ler com soundfile
        try:
            data, sr = sf.read(str(src_path))
        except Exception:
            # Fallback para pydub
            from pydub import AudioSegment
            seg = AudioSegment.from_file(str(src_path))
            seg = seg.set_frame_rate(sample_rate).set_channels(1).set_sample_width(2)
            seg.export(str(dst_path), format="wav")
            return dst_path.exists() and dst_path.stat().st_size > 44

        # Converte para mono se for multi-canal
        if data.ndim > 1:
            data = np.mean(data, axis=1)

        # Se a taxa for diferente, faz resample simples
        if sr != sample_rate:
            import scipy.signal
            num_samples = int(len(data) * sample_rate / sr)
            data = scipy.signal.resample(data, num_samples)

        # Normaliza float para int16 se necessário
        if data.dtype != np.int16:
            data = np.clip(data, -1.0, 1.0)
            data = (data * 32767).astype(np.int16)

        sf.write(str(dst_path), data, sample_rate, subtype='PCM_16')
        return dst_path.exists() and dst_path.stat().st_size > 44
    except Exception as e:
        logging.error(f"Falha na conversão de áudio para {src_path.name}: {e}")
        return False

def convert_audio_file(src_path: Path, dst_path: Path, sample_rate: int = 16000) -> bool:
    """
    Converte e padroniza um arquivo para WAV PCM 16-bit Mono na taxa desejada.
    """
    if dst_path.exists() and dst_path.stat().st_size > 44:
        return True

    # 1. Tenta FFmpeg nativo (o mais rápido)
    if _convert_single_audio_ffmpeg(src_path, dst_path, sample_rate):
        return True

    # 2. Fallback via Soundfile / PyDub
    return _convert_single_audio_soundfile(src_path, dst_path, sample_rate)

def batch_preprocess_audio_to_16k_mono(source_dir: Path, dest_dir: Path, cb=None, sample_rate: int = 16000) -> list:
    """
    Pré-converte em paralelo MULTITHREAD todos os áudios do diretório de entrada
    para WAV PCM 16-bit 16.000 Hz Mono.
    Garante aceleração extrema na transcrição com Whisper / Faster-Whisper.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Coleta todos os arquivos suportados
    source_files = [
        f for f in source_dir.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
    ]

    if not source_files:
        logging.warning(f"Nenhum arquivo de áudio encontrado em '{source_dir}'.")
        return []

    total_files = len(source_files)
    logging.info(f"⚡ [AUDIO PREPARER] Iniciando pré-conversão paralela de {total_files} arquivos para WAV {sample_rate}Hz Mono...")

    if cb:
        cb(0, 1, f"⚡ Pré-convertendo {total_files} áudios para WAV {sample_rate}Hz Mono (Turbo CPU)...", current_seg=0, total_seg=total_files)

    num_threads = min(16, (os.cpu_count() or 4) * 2)
    progress_lock = threading.Lock()
    completed_count = 0
    converted_files = []

    def _worker(src: Path):
        nonlocal completed_count
        dst = dest_dir / f"{src.stem}.wav"

        ok = convert_audio_file(src, dst, sample_rate=sample_rate)

        with progress_lock:
            completed_count += 1
            if ok:
                converted_files.append(dst)
            if cb and (completed_count % 25 == 0 or completed_count == total_files):
                pct = (completed_count / total_files) * 100
                cb(pct, 1, f"⚡ Pré-convertendo áudios [{completed_count}/{total_files}]: {src.name}", current_seg=completed_count, total_seg=total_files)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        list(executor.map(_worker, source_files))

    converted_files = sorted(list(dest_dir.glob("*.wav")))
    logging.info(f"✅ [AUDIO PREPARER] Concluída pré-conversão: {len(converted_files)}/{total_files} arquivos prontos para a GPU.")
    return converted_files
