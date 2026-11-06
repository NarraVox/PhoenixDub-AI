"""Launch DJ Instrument Discovery in a separate CPU process."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MODEL_DIR = ROOT / "scratchpad/dj_instrument_models"


def discover(other_stem: str | Path, *, model_dir: str | Path = MODEL_DIR) -> dict:
    """Classify instruments in an existing other.wav without touching any stems."""
    source = Path(other_stem).resolve()
    models = Path(model_dir).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    python = Path(os.environ.get("NEXUS_DJ_INSTRUMENT_PYTHON", sys.executable))
    if not python.is_file():
        raise FileNotFoundError(python)
    with tempfile.TemporaryDirectory(prefix="nexus_instruments_") as temporary:
        output = Path(temporary) / "result.json"
        command = [str(python), "-m", "nexus.dj.style_analyzer.adapters.instrument_worker",
                   str(source), str(models), str(output)]
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                              timeout=900, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if proc.returncode != 0:
            raise RuntimeError(f"DJ Instrument Discovery failed: {(proc.stderr or proc.stdout)[-2000:]}")
        if not output.is_file():
            raise RuntimeError("DJ Instrument Discovery returned no JSON")
        result = json.loads(output.read_text(encoding="utf-8"))
    if result.get("status") != "detected":
        raise RuntimeError("DJ Instrument Discovery returned an invalid status")
    return result
