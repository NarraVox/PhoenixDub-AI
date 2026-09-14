"""Mixagem manual que preserva falas completas, inclusive acima da janela."""
import math
from pathlib import Path
from nexus.correction_service import CorrectionError, read_audio, read_json, local_file, safe_name

def export_video(self, folder, segments, manifest, output):
    # Remonta as vozes nos tempos do roteiro, preservando o fundo separado.
    from pydub import AudioSegment, effects
    status = read_json(folder / "job_status.json", {})
    name = Path(status.get("video_path") or "").name
    source = folder / name if name else None
    if not source or not source.is_file():
        candidates = list(folder.glob("* dublado.mp4"))
        source = candidates[0] if len(candidates) == 1 else None
    vocals = folder / "vocals.wav"
    instrumental = folder / "instrumental.wav"
    if not source or not vocals.is_file() or not instrumental.is_file():
        raise CorrectionError("Para exportar, preserve o vídeo, vocals.wav e instrumental.wav na pasta do projeto.")
    source = local_file(folder, source)
    original = read_audio(vocals)
    voices = AudioSegment.silent(duration=len(original), frame_rate=44100).set_channels(2)
    windows = []
    for seg in segments:
        sid = safe_name(seg["id"])
        start, end = float(seg["start"]), float(seg["end"])
        if not all(math.isfinite(v) for v in (start, end)) or start < 0 or end <= start or end * 1000 > len(original) + 100:
            raise CorrectionError(f"Tempos inválidos na fala {sid}.")
        start_ms, end_ms = round(start * 1000), round(end * 1000)
        duration = end - start
        if sid in manifest:
            path = local_file(folder, folder / manifest[sid]["path"])
            audio = read_audio(path)
        else:
            path = local_file(folder, folder / "_dubbed_segments" / f"{sid}.wav")
            if path.is_file():
                audio = read_audio(path)
            else:
                audio = original[start_ms:end_ms]
        occupied_end = max(end_ms, start_ms + len(audio))
        if occupied_end > len(voices):
            voices += AudioSegment.silent(duration=occupied_end - len(voices), frame_rate=44100).set_channels(2)
        voices = voices.overlay(audio, position=start_ms)
        windows.append((start_ms, occupied_end))
    # Mantém sons vocais fora dos trechos do roteiro, como no mixer principal.
    last = 0
    for start, end in sorted(windows):
        if start > last:
            voices = voices.overlay(original[last:start], position=last)
        last = max(last, end)
    if last < len(original):
        voices = voices.overlay(original[last:], position=last)
    master = output / "vozes_corrigidas.wav"
    effects.normalize(voices).export(master, format="wav").close()
    filters = ("[1:a]aresample=44100,highpass=f=80,volume=1.4,asplit=2[v1][v2];"
               "[2:a]aresample=44100[bg];[bg][v1]sidechaincompress=threshold=0.02:ratio=5:attack=15:release=500[duck];"
               "[v2][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[mix]")
    self.run_ffmpeg(["-i", source, "-i", master, "-i", instrumental, "-filter_complex", filters,
                     "-map", "0:v:0", "-map", "[mix]", "-c:v", "copy", "-c:a", "aac",
                     "-b:a", "192k", "-movflags", "+faststart", output / "video_corrigido.mp4"])
