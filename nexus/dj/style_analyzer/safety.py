"""Lightweight resource checks for the isolated Style Analyzer worker."""
import shutil
import subprocess
from pathlib import Path

MAX_UPLOAD_BYTES = 128 * 1024 * 1024
MAX_DURATION_SECONDS = 300
MAX_SYSTEM_USAGE_PERCENT = 90
MAX_VRAM_USAGE_PERCENT = 90
SYSTEM_RESERVE_BYTES = 1024**3
MAX_WORKER_RSS_BYTES = int(3.5 * 1024**3)
GPU_WORKER_RESERVE_BYTES = int(3.5 * 1024**3)


def vram_stats():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--id=0", "--query-gpu=memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("Não foi possível monitorar a VRAM via nvidia-smi; análise bloqueada por segurança.") from exc
    rows = []
    for line in result.stdout.splitlines():
        used, total = (int(value.strip()) for value in line.split(",", 1))
        if total > 0:
            rows.append((used, total))
    if not rows:
        raise RuntimeError("Não foi possível ler o uso de VRAM pelo nvidia-smi")
    # nvidia-smi's nounits memory values are MiB; convert to bytes for reserves.
    used_mib, total_mib = rows[0]
    return used_mib * 1024**2, total_mib * 1024**2


def vram_usage_percent():
    used, total = vram_stats()
    return used * 100 / total


def probe_duration(source):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(source)],
            capture_output=True, text=True, timeout=15, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("Não foi possível verificar a duração do áudio com ffprobe") from exc
    try:
        duration = float(result.stdout.strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("Não foi possível verificar a duração do áudio") from exc
    if not 0 < duration <= MAX_DURATION_SECONDS:
        raise ValueError("O Style Analyzer aceita áudio de até 5 minutos")
    return duration


def preflight(source, project, sheetsage=False, require_gpu=True):
    import psutil
    source, project = Path(source), Path(project)
    if source.stat().st_size > MAX_UPLOAD_BYTES:
        raise ValueError("Limite de arquivo: 128 MB")
    duration = probe_duration(source)
    memory = psutil.virtual_memory()
    projected_usage = memory.total - memory.available + MAX_WORKER_RSS_BYTES + SYSTEM_RESERVE_BYTES
    if projected_usage >= memory.total * MAX_SYSTEM_USAGE_PERCENT / 100:
        raise RuntimeError(
            "Memória insuficiente para iniciar dentro do teto de 90%: "
            f"uso atual {memory.percent:.1f}%, com reserva projetada "
            f"{projected_usage / memory.total * 100:.1f}%")
    used_vram, total_vram = vram_stats()
    vram_percent = used_vram * 100 / total_vram
    if vram_percent >= MAX_VRAM_USAGE_PERCENT:
        raise RuntimeError(f"VRAM já está em {vram_percent:.1f}%; limite de segurança: 90%")
    if require_gpu and used_vram + GPU_WORKER_RESERVE_BYTES >= total_vram * MAX_VRAM_USAGE_PERCENT / 100:
        raise RuntimeError("VRAM livre insuficiente para reservar até 3,5 GiB ao worker dentro do teto de 90%")
    free_disk = shutil.disk_usage(project).free
    required_disk = max(2 * 1024**3, source.stat().st_size * 4)
    if free_disk < required_disk:
        raise RuntimeError("Espaço livre insuficiente para áudio e stems (mínimo 2 GB ou 4x o arquivo)")
    return duration
