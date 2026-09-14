"""Transport for ACE-Step synthesis; reference files stay open during upload."""

import json
import mimetypes
import math
from contextlib import ExitStack


def choose_reference_start(total_seconds, uniform=None):
    """Choose 30 seconds inside the track, excluding at least 5s at each end."""
    import random
    total_seconds = float(total_seconds)
    if not math.isfinite(total_seconds) or total_seconds < 40:
        raise ValueError('Extended precisa de uma referência de pelo menos 40 segundos para evitar o começo e o final.')
    margin = min(15.0, max(5.0, total_seconds * 0.1))
    return (uniform or random.uniform)(margin, total_seconds - margin - 30.0)


def prepare_extension_reference(source, destination, total_seconds, uniform=None):
    import subprocess
    start = choose_reference_start(total_seconds, uniform)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(start), '-i', str(source),
                    '-t', '30', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le', str(destination)],
                   capture_output=True, check=True)
    import soundfile as sf
    if abs(sf.info(destination).duration - 30.0) > 0.05:
        raise ValueError('Não foi possível extrair os 30 segundos de referência.')
    return start


def configure_extension(parameters, source_duration, extra_seconds):
    """Use measured audio seconds, never the formatting of semantic tokens."""
    source_duration, extra_seconds = float(source_duration), float(extra_seconds)
    if not all(math.isfinite(v) and v > 0 for v in (source_duration, extra_seconds)):
        raise ValueError("A música base e a extensão precisam ter duração positiva.")
    parameters.update(
        task_type="repaint",
        repainting_start=max(0.0, source_duration - 1.5),
        repainting_end=source_duration + extra_seconds,
        duration=source_duration + extra_seconds,
    )


def extract_continuation(source, destination, original_seconds, extra_seconds):
    """Export only time after the original ends, excluding the repaint overlap."""
    import soundfile as sf
    original_seconds, extra_seconds = float(original_seconds), float(extra_seconds)
    if not all(math.isfinite(v) and v > 0 for v in (original_seconds, extra_seconds)):
        raise ValueError('Duração inválida para recortar a continuação.')
    with sf.SoundFile(source) as audio:
        start = round(original_seconds * audio.samplerate)
        count = round(extra_seconds * audio.samplerate)
        available = len(audio) - start
        # Allow only encoder/frame rounding, never export the original as success.
        if available <= 0 or available < count - round(0.15 * audio.samplerate):
            raise ValueError('O motor não gerou a continuação completa solicitada.')
        audio.seek(start)
        samples = audio.read(min(count, available), dtype='float32', always_2d=True)
        sf.write(destination, samples, audio.samplerate, subtype='PCM_24')


def submit_synthesis(client, parameters, source_path=None):
    url = "http://127.0.0.1:8085/synth"
    if source_path is None:
        return client.post(url, json=parameters, timeout=300)
    mime = mimetypes.guess_type(str(source_path))[0] or "application/octet-stream"
    with ExitStack() as stack:
        audio = stack.enter_context(open(source_path, "rb"))
        files = {"audio": (source_path.name, audio, mime)}
        if parameters.get("task_type") == "cover-nofsq":
            reference = stack.enter_context(open(source_path, "rb"))
            files["ref_audio"] = (source_path.name, reference, mime)
        return client.post(
            url,
            files=files,
            data={"request": json.dumps(parameters)},
            timeout=300,
        )
