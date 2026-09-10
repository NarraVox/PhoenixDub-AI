# [v2026.VIDEO_SLICER] Fatiador de Vídeo — sem re-encoding (stream copy)
# Divide qualquer vídeo em pedaços de duração fixa usando FFmpeg.

import os
import subprocess
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify

video_slicer_blueprint = Blueprint('video_slicer', __name__)

logger = logging.getLogger(__name__)


def _find_ffmpeg() -> str:
    """Retorna o caminho do ffmpeg (bundled ou do PATH)."""
    base_dir = Path(__file__).resolve().parents[2]
    candidates = [
        str(base_dir / "env" / "Library" / "bin" / "ffmpeg.exe"),
        str(base_dir / "ffmpeg" / "bin" / "ffmpeg.exe"),
        str(base_dir / "ffmpeg.exe"),
        "ffmpeg",  # PATH do sistema
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "ffmpeg"


@video_slicer_blueprint.route('/api/fatiar_video', methods=['POST'])
def fatiar_video():
    """
    Fatia um vídeo em pedaços de duração igual.
    Body JSON: { "video_path": "...", "segment_seconds": 300 }
    Retorna: { "ok": true, "fatias": [...], "pasta": "..." }
    """
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or not isinstance(data.get("video_path", ""), str):
        return jsonify({"ok": False, "erro": "Informe um caminho de vídeo válido."}), 400
    video_path = data.get("video_path", "").strip()
    try:
        segment_sec = int(data.get("segment_seconds", 300))
    except (TypeError, ValueError, OverflowError):
        return jsonify({"ok": False, "erro": "Duração inválida."}), 400

    # --- Validações ---
    if not video_path:
        return jsonify({"ok": False, "erro": "video_path não informado."}), 400
    if not os.path.isfile(video_path):
        return jsonify({"ok": False, "erro": f"Arquivo não encontrado: {video_path}"}), 404
    if segment_sec < 5:
        return jsonify({"ok": False, "erro": "Duração mínima: 5 segundos."}), 400
    if segment_sec > 7200:
        return jsonify({"ok": False, "erro": "Duração máxima: 2 horas."}), 400

    src = Path(video_path)
    pasta_fatias = src.parent / f"{src.stem}_fatias"
    try:
        pasta_fatias.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return jsonify({"ok": False, "erro": f"Não foi possível criar a pasta de fatias: {exc}"}), 500

    padrao_saida = str(pasta_fatias / f"{src.stem}_parte_%03d{src.suffix}")
    ffmpeg = _find_ffmpeg()

    cmd = [
        ffmpeg, "-y",
        "-i", str(src),
        "-c", "copy",                   # Sem re-encoding → ultra rápido
        "-f", "segment",
        "-segment_time", str(segment_sec),
        "-reset_timestamps", "1",
        "-avoid_negative_ts", "make_zero",
        padrao_saida
    ]

    logger.info(f"[SLICER] Fatiando: {src.name} em blocos de {segment_sec}s → {pasta_fatias}")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=600          # Máx 10 min de processamento
        )
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "erro": "Timeout: o vídeo é muito longo ou o FFmpeg travou."}), 500
    except FileNotFoundError:
        return jsonify({"ok": False, "erro": "FFmpeg não encontrado. Verifique a instalação."}), 500
    except OSError as exc:
        return jsonify({"ok": False, "erro": f"Não foi possível executar o FFmpeg: {exc}"}), 500

    if proc.returncode != 0:
        logger.error(f"[SLICER] FFmpeg erro:\n{proc.stderr}")
        return jsonify({"ok": False, "erro": "FFmpeg falhou.", "detalhe": proc.stderr[-400:]}), 500

    # Lista fatias geradas
    fatias = sorted([
        str(f) for f in pasta_fatias.iterdir()
        if f.suffix.lower() in {".mp4", ".mkv", ".avi", ".mov", ".webm"}
    ])

    logger.info(f"[SLICER] Geradas {len(fatias)} fatia(s) em: {pasta_fatias}")
    return jsonify({
        "ok": True,
        "fatias": fatias,
        "total": len(fatias),
        "pasta": str(pasta_fatias)
    })
