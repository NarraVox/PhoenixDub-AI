"""DJ-only MTG-Jamendo instrument inference with official Essentia ONNX models.

Implements the Essentia TensorflowInputMusiCNN feature recipe without importing
Essentia or TensorFlow: 16 kHz mono, 512-sample Hann magnitude spectrum every
256 samples, 96 Slaney mel bands with unit-triangle normalization, then
log10(1 + 10000 * bands). Discogs EffNet uses 128-frame patches, hop 62.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import librosa
import numpy as np
import onnxruntime as ort
import soundfile as sf


SAMPLE_RATE = 16000
FRAME_SIZE = 512
HOP_SIZE = 256
PATCH_FRAMES = 128
PATCH_HOP = 62
MODEL_EMBED = "discogs-effnet-bsdynamic-1.onnx"
MODEL_HEAD = "mtg_jamendo_instrument-discogs-effnet-1.onnx"
MODEL_HEAD_META = "mtg_jamendo_instrument-discogs-effnet-1.json"
MIN_RMS = 1e-4
ACTIVE_SCORE = 0.20
MIN_ACTIVE_WINDOWS = 2


def mel_patches(audio: np.ndarray) -> tuple[np.ndarray, list[float]]:
    """Return model patches and their start times (seconds)."""
    mel_filter = librosa.filters.mel(
        sr=SAMPLE_RATE, n_fft=FRAME_SIZE, n_mels=96, htk=False, norm="slaney"
    )
    spectrum = np.abs(librosa.stft(
        audio, n_fft=FRAME_SIZE, hop_length=HOP_SIZE,
        window="hann", center=True, pad_mode="constant"
    ))
    bands = mel_filter @ spectrum
    frames = np.log10(1.0 + 10000.0 * bands).T.astype(np.float32)
    starts = list(range(0, max(0, len(frames) - PATCH_FRAMES + 1), PATCH_HOP))
    patches = np.stack([frames[index:index + PATCH_FRAMES] for index in starts]) if starts else np.empty((0, PATCH_FRAMES, 96), np.float32)
    return patches, [index * HOP_SIZE / SAMPLE_RATE for index in starts]


def _regions(scores: np.ndarray, starts: list[float], duration: float) -> list[dict]:
    active = scores >= ACTIVE_SCORE
    regions = []
    beginning = None
    for index in range(len(active) + 1):
        selected = bool(active[index]) if index < len(active) else False
        if selected and beginning is None:
            beginning = index
        if not selected and beginning is not None:
            if index - beginning >= MIN_ACTIVE_WINDOWS:
                segment = scores[beginning:index]
                regions.append({
                    "start_seconds": round(starts[beginning], 3),
                    "end_seconds": round(min(duration, starts[index - 1] + PATCH_FRAMES * HOP_SIZE / SAMPLE_RATE), 3),
                    "confidence": round(float(np.mean(segment)), 4),
                    "max_score": round(float(np.max(segment)), 4),
                    "window_count": index - beginning,
                })
            beginning = None
    return regions


def summarize(predictions: np.ndarray, starts: list[float], duration: float, classes: list[str]) -> dict:
    if predictions.ndim != 2 or predictions.shape != (len(starts), len(classes)):
        raise ValueError("Instrument ONNX output shape does not match model labels")
    detected, candidates = [], []
    for column, label in enumerate(classes):
        scores = predictions[:, column]
        regions = _regions(scores, starts, duration)
        mean_score = round(float(np.mean(scores)), 4) if len(scores) else 0.0
        maximum = round(float(np.max(scores)), 4) if len(scores) else 0.0
        if regions:
            detected.append({
                "instrument": label,
                "confidence": round(float(np.mean([region["confidence"] for region in regions])), 4),
                "mean_score": mean_score,
                "max_score": maximum,
                "regions": regions,
            })
        elif maximum >= 0.15:
            candidates.append({"instrument": label, "mean_score": mean_score, "max_score": maximum})
    detected.sort(key=lambda row: row["confidence"], reverse=True)
    candidates.sort(key=lambda row: row["max_score"], reverse=True)
    return {"detected": detected, "candidates": candidates}


def analyze(source: Path, model_dir: Path) -> dict:
    started = time.monotonic()
    source, model_dir = Path(source), Path(model_dir)
    for filename in (MODEL_EMBED, MODEL_HEAD, MODEL_HEAD_META):
        if not (model_dir / filename).is_file():
            raise FileNotFoundError(model_dir / filename)
    classes = json.loads((model_dir / MODEL_HEAD_META).read_text(encoding="utf-8"))["classes"]
    if len(classes) != 40:
        raise ValueError("Unexpected MTG-Jamendo instrument class count")
    audio, sample_rate = sf.read(source, dtype="float32", always_2d=True)
    if not len(audio) or not np.isfinite(audio).all():
        raise ValueError("Instrument source is empty or invalid")
    duration = len(audio) / sample_rate
    mono = audio.mean(axis=1)
    if sample_rate != SAMPLE_RATE:
        mono = librosa.resample(mono, orig_sr=sample_rate, target_sr=SAMPLE_RATE)
    patches, starts = mel_patches(mono)
    if not len(patches):
        raise ValueError("Instrument source is shorter than the model patch")
    embedding = ort.InferenceSession(str(model_dir / MODEL_EMBED), providers=["CPUExecutionProvider"])
    head = ort.InferenceSession(str(model_dir / MODEL_HEAD), providers=["CPUExecutionProvider"])
    predictions = np.empty((len(patches), len(classes)), dtype=np.float32)
    batch_size = 32
    for first in range(0, len(patches), batch_size):
        last = min(len(patches), first + batch_size)
        vectors = embedding.run(["embeddings"], {"melspectrogram": patches[first:last]})[0]
        predictions[first:last] = head.run(["activations"], {"embeddings": vectors})[0]
    patch_duration = PATCH_FRAMES * HOP_SIZE / SAMPLE_RATE
    for index, offset in enumerate(starts):
        fragment = mono[round(offset * SAMPLE_RATE):round((offset + patch_duration) * SAMPLE_RATE)]
        if not len(fragment) or float(np.sqrt(np.mean(fragment * fragment))) < MIN_RMS:
            predictions[index] = 0.0
    if not np.isfinite(predictions).all() or np.any(predictions < 0) or np.any(predictions > 1):
        raise ValueError("Invalid MTG-Jamendo probabilities")
    summary = summarize(predictions, starts, duration, classes)
    return {
        "status": "detected",
        "source_stem": str(source.resolve()),
        "method": "MTG-Jamendo Instrument / Discogs EffNet, official ONNX models; Essentia-compatible log-mel features",
        "device": "cpu",
        "runtime": f"onnxruntime {ort.__version__}",
        "duration_seconds": round(duration, 3),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "window_seconds": patch_duration,
        "window_hop_seconds": PATCH_HOP * HOP_SIZE / SAMPLE_RATE,
        "thresholds": {"active_score": ACTIVE_SCORE, "minimum_consecutive_windows": MIN_ACTIVE_WINDOWS, "silence_rms": MIN_RMS},
        "confidence_kind": "model_multilabel_score_not_calibrated_probability",
        "models": [MODEL_EMBED, MODEL_HEAD],
        "classes": classes,
        "detected": summary["detected"],
        "candidates": summary["candidates"],
        "windows": [
            {"start_seconds": round(offset, 3),
             "end_seconds": round(min(duration, offset + patch_duration), 3),
             "scores": {label: round(float(value), 4) for label, value in zip(classes, scores)}}
            for offset, scores in zip(starts, predictions)
        ],
        "limitations": [
            "The model is a multi-label whole-music tagger; sliding windows approximate presence, not exact note or instrument boundaries.",
            "Scores are not calibrated probabilities and may include stem leakage or confusion between related timbres.",
            "Only the 40 instrument tags defined by the official MTG-Jamendo head can be reported.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("model_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = analyze(args.source, args.model_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
