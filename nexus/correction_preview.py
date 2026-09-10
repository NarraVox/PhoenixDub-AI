"""Prévia manual: referência individual e aceleração de no máximo 20%."""
import math
import uuid
from nexus.correction_service import CorrectionError, read_audio, write_json
from nexus.correction_timing import original_duration

def preview(self, key, sid, text):
    text = text.strip() if isinstance(text, str) else ""
    if not text or len(text) > 3000:
        raise CorrectionError("Digite a tradução corrigida (até 3.000 caracteres).")
    folder, kind, seg = self.segment(key, sid)
    source = self.audio(folder, kind, seg)
    reference = self.reference(folder, seg)
    before = self.fingerprint(folder, source)
    token = uuid.uuid4().hex
    work = folder / "_correcoes" / "previas" / token
    work.mkdir(parents=True)
    from pydub import AudioSegment
    duration = original_duration(seg, kind)
    if duration is None:
        duration = len(read_audio(reference)) / 1000
    if not math.isfinite(duration) or duration <= 0:
        raise CorrectionError("Duração inválida para esta fala.")
    raw = work / "gerado.wav"
    self.synthesizer(text, reference, raw, duration, seg.get("emotion", "NORMAL"))
    if not raw.is_file():
        raise CorrectionError("O motor não gerou um arquivo de áudio.")
    from pydub.silence import detect_nonsilent
    generated = read_audio(raw)
    ranges = detect_nonsilent(generated, min_silence_len=120, silence_thresh=-45)
    if not ranges:
        raise CorrectionError("O motor gerou silêncio. Tente gerar a prévia novamente.")
    generated = generated[max(0, ranges[0][0] - 40):min(len(generated), ranges[-1][1] + 60)]
    ratio = len(generated) / (duration * 1000)
    speed = min(1.20, max(1.0, ratio))
    trimmed = work / "fala.wav"
    generated.export(trimmed, format="wav").close()
    output = work / ("previa" + source.suffix)
    original = read_audio(source)
    # atempo preserva o tom. apad só completa silêncio se faltar tempo;
    # não há corte nem compressão adicional quando a fala ainda é longa.
    filters = ([f"atempo={speed:.6f}"] if speed > 1 else []) + [f"apad=whole_dur={duration:.6f}"]
    self.run_ffmpeg(["-i", trimmed, "-af", ",".join(filters), "-ar", original.frame_rate, "-ac", original.channels, output])
    actual = len(read_audio(output)) / 1000
    info = {"token": token, "segment_id": str(sid), "text": text, "audio": output.name,
            "fingerprint": before, "duration": actual, "generated_duration": actual,
            "original_duration": duration, "speed": speed,
            "overrun_seconds": max(0, actual - duration), "kind": kind}
    write_json(work / "previa.json", info)
    return info

