"""Reuse installed UMXHQ weights, in bounded chunks, without implicit downloads."""
from pathlib import Path
import time

from ..store import TARGETS

WEIGHTS = {"bass": "bass-8d85a5bd.pth", "drums": "drums-9619578f.pth",
           "other": "other-b52fbbf7.pth", "vocals": "vocals-b62c91ce.pth"}


def _resolve_device(device):
    if device == "cpu":
        return "cpu"
    if device == "gpu":
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA foi solicitada para Open-Unmix, mas não está disponível")
        return "cuda"
    raise ValueError("Open-Unmix device deve ser cpu ou gpu")


_DEFAULT_DEVICE = "gpu"


def separate(source, output, progress=lambda *args: None, device=_DEFAULT_DEVICE):
    import numpy as np
    import soundfile as sf
    import torch

    source = Path(source)
    
    device = _resolve_device(device)
    
    cache = Path(torch.hub.get_dir()) / "checkpoints"
    
    # Check weights availability
    missing = [name for name in WEIGHTS.values() if not (cache / name).is_file()]
    if missing:
        raise RuntimeError("Pesos UMXHQ ausentes em %s: %s. Download automatico desativado." % (cache, "', '".join(missing)))

    import openunmix
    models = openunmix.umxhq_spec(targets=list(TARGETS), device="cpu", pretrained=False)
    
    print("DISPOSITIVO: %s" % ("GPU CUDA" if device == "cuda" else "CPU"))

    for target, model in models.items():
        # The official Open-Unmix loader uses strict=False for these UMXHQ
        # checkpoints. They include STFT/window buffers that are regenerated
        # by the installed library and are not parameters of OpenUnmix.
        model.load_state_dict(
            torch.load(cache / WEIGHTS[target], map_location="cpu", weights_only=True),
            strict=False,
        )

    from openunmix.model import Separator
    separator = Separator(models, niter=1, residual=False, sample_rate=44100)
    separator.freeze()
    separator.to(device)

    # Log device confirmation and start separation timing
    start_sep_time = time.time()
    
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    writers = {}

    try:
        with sf.SoundFile(source) as audio:
            if audio.samplerate != 44100 or audio.channels != 2:
                raise ValueError("Open-Unmix requer audio preparado em 44.1 kHz stereo")
            print("ARQUIVO: %s" % source.name)
            
            writers = {t: sf.SoundFile(output / f"{t}.wav", "w", samplerate=44100,
                                      channels=2, subtype="PCM_16") for t in TARGETS}
            step, context = 441000, 44100
            
            # Log separation start
            print("INICIO SEPARACAO Open-Unmix")
            
            frames_total = audio.frames
            chunks_processed = 0
            
            for start in range(0, frames_total, step):
                left, right = max(0, start - context), min(frames_total, start + step + context)
                audio.seek(left)
                samples = audio.read(right - left, dtype="float32", always_2d=True)
                
                with torch.inference_mode():
                    result = predict.separate(torch.from_numpy(samples.T.copy())[None], rate=44100,
                                              separator=separator, device=device)
                count = min(step, frames_total - start)
                chunks_processed += 1
                
                for target in TARGETS:
                    data = result[target][0, :, start-left:start-left+count].cpu().numpy().T
                    if len(data) != count or not np.isfinite(data).all():
                        raise RuntimeError("Saida invalida do separador")
                    writers[target].write(data)
                del result
                
                # Log progress periodically (every 10 chunks or at milestones)
                if chunks_processed % 10 == 0 or chunks_processed == 1:
                    pct = min(1.0, (start + count) / frames_total)
                    print("PROGRESSO: separacao (%d%%)" % int(pct*100) + 
                          (" (%d chunks)" % chunks_processed) if chunks_processed > 1 else "")
                progress("separation", (start + count) / audio.frames)
            
            # Log stems generated
            print("STEMES GERADOS: %s" % ", ".join(TARGETS))
    finally:
        for writer in writers.values():
            writer.close()
        
        end_sep_time = time.time()
        sep_duration = end_sep_time - start_sep_time
        
        import gc
        print("TEMPO SEPARACAO: %.1fs" % sep_duration)
        del separator, models
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
        print("Modelos descartados (%s)" % device)

    return {t: output / f"{t}.wav" for t in TARGETS}


# Ensure predict is imported locally within function scope
from openunmix import predict
