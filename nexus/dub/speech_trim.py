"""Conservative speech-boundary detection for generated dubbing audio."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from pydub import AudioSegment


TRIM_CACHE_VERSION = "silero-v1"
_SAFETY_CHECKED = False


@dataclass(frozen=True)
class SpeechTrimResult:
    audio: AudioSegment
    start_removed_ms: int = 0
    end_removed_ms: int = 0
    detector: str = "preserved"
    reason: str = ""


def _speech_padding_ms(emotion: str) -> tuple[int, int]:
    emotion = (emotion or "NORMAL").upper()
    if emotion in {"TRISTE", "MEDO", "SUSPENSE"}:
        return 260, 200
    if emotion in {"RAIVA", "FELIZ", "DRAMATICO"}:
        return 200, 170
    return 170, 150


def _to_float_16k_mono(audio: AudioSegment) -> np.ndarray:
    prepared = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    samples = np.asarray(prepared.get_array_of_samples(), dtype=np.float32)
    return samples / 32768.0


def _ensure_safe_once() -> None:
    global _SAFETY_CHECKED
    if not _SAFETY_CHECKED:
        from nexus.core.system_guard import check_system_safety

        check_system_safety()
        _SAFETY_CHECKED = True


def _energy_boundary(audio: AudioSegment, threshold_dbfs: float = -42.0) -> tuple[int, int] | None:
    """Fallback only: require sustained energy instead of accepting one click."""
    duration = len(audio)
    active = []
    for pos in range(0, duration, 10):
        active.append(audio[pos : min(duration, pos + 10)].dBFS > threshold_dbfs)

    run = 0
    start = None
    for index, is_active in enumerate(active):
        run = run + 1 if is_active else 0
        if run >= 3:
            start = max(0, (index - run + 1) * 10)
            break

    run = 0
    end = None
    for index in range(len(active) - 1, -1, -1):
        run = run + 1 if active[index] else 0
        if run >= 3:
            end = min(duration, (index + run) * 10)
            break

    if start is None or end is None or end <= start:
        return None
    return start, end


def trim_generated_speech(audio: AudioSegment, emotion: str = "NORMAL") -> SpeechTrimResult:
    """Trim long TTS padding while protecting breaths and word attacks.

    Silero supplies speech boundaries; it is deliberately not used as an exact
    knife. Generous pre/post roll is retained, and uncertain detections preserve
    the original audio.
    """
    duration = len(audio)
    if duration < 120:
        return SpeechTrimResult(audio, reason="audio_too_short")

    start_pad, end_pad = _speech_padding_ms(emotion)
    try:
        _ensure_safe_once()
        from faster_whisper.vad import VadOptions, get_speech_timestamps

        samples = _to_float_16k_mono(audio)
        timestamps = get_speech_timestamps(
            samples,
            VadOptions(
                threshold=0.42,
                min_speech_duration_ms=48,
                min_silence_duration_ms=140,
                speech_pad_ms=0,
            ),
            sampling_rate=16000,
        )
        if not timestamps:
            return SpeechTrimResult(audio, reason="silero_no_confident_speech")

        speech_start = round(timestamps[0]["start"] * 1000 / 16000)
        speech_end = round(timestamps[-1]["end"] * 1000 / 16000)
        trim_start = max(0, speech_start - start_pad)
        trim_end = min(duration, speech_end + end_pad)
        detector = "silero"
    except Exception as exc:
        logging.warning("Silero VAD indisponivel; usando fallback conservador: %s", exc)
        boundary = _energy_boundary(audio)
        if boundary is None:
            return SpeechTrimResult(audio, reason="fallback_no_confident_speech")
        speech_start, speech_end = boundary
        trim_start = max(0, speech_start - max(start_pad, 220))
        trim_end = min(duration, speech_end + max(end_pad, 180))
        detector = "energy_fallback"

    kept_ms = trim_end - trim_start
    if kept_ms < 120 or speech_end <= speech_start:
        return SpeechTrimResult(audio, reason="unsafe_short_result")
    if trim_start > 1500:
        return SpeechTrimResult(audio, reason="unsafe_large_leading_trim")

    # A microscopic fade prevents a boundary click without softening consonants.
    trimmed = audio[trim_start:trim_end]
    fade_ms = min(5, len(trimmed) // 4)
    if fade_ms:
        trimmed = trimmed.fade_in(fade_ms).fade_out(fade_ms)
    return SpeechTrimResult(
        trimmed,
        start_removed_ms=trim_start,
        end_removed_ms=max(0, duration - trim_end),
        detector=detector,
    )
