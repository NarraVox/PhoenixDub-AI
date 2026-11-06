"""Run DJ-only HTDemucs in a separate Python process and package directory."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import soundfile as sf

from ..store import TARGETS

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PYTHON = ROOT / "scratchpad/dj_demucs_env/Scripts/python.exe"
MODEL_CACHE = ROOT / "scratchpad/dj_demucs_models"
MODEL = "htdemucs"
SEGMENT_SECONDS = 6


def _gpu_memory_mib():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return int(result.stdout.strip().splitlines()[0])
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def separate(source, output, progress=lambda *args: None, device="gpu"):
    """Produce the four stems with CUDA; never silently switch to CPU."""
    if device == "cpu":
        raise ValueError("HTDemucs do Nexus DJ requer CUDA nesta configuração")
    source, output = Path(source).resolve(), Path(output).resolve()
    python = Path(os.environ.get("NEXUS_DJ_DEMUCS_PYTHON", DEFAULT_PYTHON))
    if not python.is_file():
        raise RuntimeError(f"Ambiente DJ HTDemucs ausente: {python}")
    if not source.is_file():
        raise FileNotFoundError(source)
    output.mkdir(parents=True, exist_ok=True)
    MODEL_CACHE.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TORCH_HOME"] = str(MODEL_CACHE)
    # Demucs 4.0.1 loads its own trusted checkpoint with torch.load. Torch 2.6
    # changed that call's default; scope the compatibility setting to the child.
    env["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
    baseline = _gpu_memory_mib()
    peak = baseline
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="htdemucs_", dir=output.parent) as tmp:
        command = [str(python), "-m", "demucs", "-n", MODEL, "-d", "cuda",
                   "--segment", str(SEGMENT_SECONDS), "--overlap", "0.25",
                   "--shifts", "0", "-j", "1", "-o", tmp, str(source)]
        with (output / "demucs.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       cwd=str(ROOT), env=env,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            while process.poll() is None:
                used = _gpu_memory_mib()
                if used is not None:
                    peak = max(peak or 0, used)
                time.sleep(0.5)
            if process.returncode:
                tail = (output / "demucs.log").read_text(encoding="utf-8", errors="replace")[-3000:]
                raise RuntimeError(f"HTDemucs CUDA falhou (código {process.returncode}): {tail}")
        source_dir = Path(tmp) / MODEL / source.stem
        stems = {name: source_dir / f"{name}.wav" for name in TARGETS}
        if not all(path.is_file() for path in stems.values()):
            raise RuntimeError(f"HTDemucs não produziu os quatro stems em {source_dir}")
        with sf.SoundFile(source) as reference:
            expected_frames = reference.frames
            expected_rate = reference.samplerate
        for name, path in stems.items():
            with sf.SoundFile(path) as audio:
                if audio.frames < expected_frames - expected_rate or audio.samplerate != expected_rate or audio.channels != 2:
                    raise RuntimeError(f"Stem HTDemucs inválido: {name}")
        for name, path in stems.items():
            shutil.move(str(path), str(output / f"{name}.wav"))
    elapsed = time.monotonic() - started
    metadata = {"separator": "htdemucs", "model": MODEL, "device": "cuda",
                "segment_seconds": SEGMENT_SECONDS, "overlap": 0.25, "shifts": 0,
                "jobs": 1, "elapsed_seconds": round(elapsed, 2),
                "gpu_memory_baseline_mib": baseline,
                "gpu_memory_peak_mib": peak,
                "gpu_memory_increase_mib": max(0, peak - baseline) if peak is not None and baseline is not None else None,
                "python": str(python), "model_cache": str(MODEL_CACHE)}
    (output / "demucs_run.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    progress("separation", 1.0)
    return {name: output / f"{name}.wav" for name in TARGETS}
