"""Small deterministic software renderer for learned Nexus Style Pack grooves.

This MVP synthesizes simple drum, bass and chord sounds directly from the
performance events in arrangement.json. It intentionally does not call YuE2 or
copy any reference audio.
"""
from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np
import soundfile as sf

from .planning import validate_arrangement


def _midi_hz(note: int) -> float:
    return 440.0 * (2.0 ** ((int(note) - 69) / 12.0))


class _RhythmTimeline:
    """One sample grid shared by drum excerpts and all symbolic note attacks."""

    def __init__(self, bpm: float, numerator: int, denominator: int, sample_rate: int):
        self.sample_rate = sample_rate
        self.bar_seconds = numerator * 4 / denominator * 60 / bpm
        self.step_seconds = self.bar_seconds / 16

    def step_sample(self, bar_index: int, step: float, substep: float = 0) -> int:
        return round(((bar_index * 16) + step + substep / 4) *
                     self.step_seconds * self.sample_rate)

    def bar_sample(self, bar_index: int) -> int:
        return self.step_sample(bar_index, 0)


def _put(mix: np.ndarray, signal: np.ndarray, start: int, gain: float) -> None:
    if start >= len(mix) or len(signal) == 0:
        return
    end = min(len(mix), start + len(signal))
    mix[start:end] += signal[:end - start] * gain


def _reference_drum_hit(
    audio: np.ndarray,
    source_rate: int,
    output_rate: int,
    center_seconds: float,
    length_seconds: float,
) -> np.ndarray | None:
    """Take a short one-shot from the corresponding learned drum-stem step."""
    length = max(1, round(length_seconds * output_rate))
    center = round(center_seconds * source_rate)
    # A small search tolerates the analyzer's quantization error while keeping
    # the sample tied to this learned step instead of finding arbitrary hits.
    radius = round(0.045 * source_rate)
    probe = max(1, round(0.012 * source_rate))
    low = max(0, center - radius)
    high = min(len(audio) - probe, center + radius)
    if high < low:
        return None
    candidates = np.arange(low, high + 1, max(1, source_rate // 1000), dtype=np.int64)
    rms = np.asarray([np.mean(audio[i:i + probe] ** 2) for i in candidates])
    start = int(candidates[int(np.argmax(rms))]) - round(0.006 * source_rate)
    start = max(0, start)
    segment = audio[start:min(len(audio), start + round(length_seconds * source_rate))]
    if len(segment) < max(8, round(0.025 * source_rate)):
        return None
    # Linear resampling keeps this optional path dependency-light. A short
    # fade prevents clicks at the sample boundary.
    if source_rate != output_rate:
        target_positions = np.arange(length, dtype=np.float64) * source_rate / output_rate
        segment = np.interp(target_positions, np.arange(len(segment)), segment).astype(np.float32)
    else:
        segment = segment[:length].astype(np.float32, copy=True)
    segment -= float(np.mean(segment))
    fade = min(round(0.004 * output_rate), len(segment) // 2)
    if fade:
        segment[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)
        segment[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    peak = float(np.max(np.abs(segment)))
    if peak < 1e-5:
        return None
    return segment / peak


def _best_reference_drum_hit(
    audio: np.ndarray,
    source_rate: int,
    output_rate: int,
    occurrences: list[int],
    source_bar_offset: int,
    step_seconds: float,
    event_step: float,
    grid_start_seconds: float,
) -> np.ndarray | None:
    """Choose the strongest usable matching hit and keep that timbre stable."""
    best = None
    best_peak = -1.0
    for occurrence in occurrences:
        source_bar = int(occurrence) + source_bar_offset - 1
        center = (grid_start_seconds + (source_bar - 1) * step_seconds * 16
                  + event_step * step_seconds)
        sample_center = round(center * source_rate)
        lo, hi = max(0, sample_center - round(0.045 * source_rate)), min(
            len(audio), sample_center + round(0.045 * source_rate) + 1)
        strength = float(np.max(np.abs(audio[lo:hi]))) if hi > lo else 0.0
        hit = _reference_drum_hit(audio, source_rate, output_rate, center, 0.18)
        if hit is None or strength <= best_peak:
            continue
        best, best_peak = hit, strength
    return best


def _kick(length: int, sr: int) -> np.ndarray:
    t = np.arange(length, dtype=np.float32) / sr
    phase = 2 * np.pi * (48 * t + 42 * (1 - np.exp(-t * 24)) / 24)
    return (np.sin(phase) * np.exp(-t * 13)).astype(np.float32)


def _mid_hit(length: int, sr: int) -> np.ndarray:
    """A dry, repeatable mid-band tap; the source band is not a snare label."""
    t = np.arange(length, dtype=np.float32) / sr
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 24)
    click = np.sin(2 * np.pi * 560 * t) * np.exp(-t * 55)
    return ((0.78 * body + 0.22 * click) * np.minimum(1.0, t / 0.001)).astype(np.float32)


def _high_metal(length: int, sr: int) -> np.ndarray:
    t = np.arange(length, dtype=np.float32) / sr
    tone = (np.sin(2 * np.pi * 4100 * t) + 0.6 * np.sin(2 * np.pi * 6370 * t)
            + 0.35 * np.sin(2 * np.pi * 8900 * t)) / 1.95
    return (tone * np.exp(-t * 35)).astype(np.float32)


def _bass_note(note: int, length: int, sr: int) -> np.ndarray:
    t = np.arange(length, dtype=np.float32) / sr
    f = _midi_hz(note)
    attack = np.minimum(1.0, t / 0.008)
    decay = np.exp(-t * 2.4)
    tone = np.sin(2 * np.pi * f * t) + 0.24 * np.sin(4 * np.pi * f * t)
    return (tone * attack * decay / 1.24).astype(np.float32)


def _chord_stab(notes: list[int], length: int, sr: int) -> np.ndarray:
    t = np.arange(length, dtype=np.float32) / sr
    attack = np.minimum(1.0, t / 0.006)
    decay = np.exp(-t * 9.0)
    signal = np.zeros(length, dtype=np.float32)
    for note in notes:
        f = _midi_hz(note)
        signal += (np.sin(2 * np.pi * f * t)
                   + 0.28 * np.sin(4 * np.pi * f * t)
                   + 0.12 * np.sin(6 * np.pi * f * t)) / 1.4
    signal /= max(1, len(notes))
    return (signal * attack * decay).astype(np.float32)


def _repeat_continuous_drum_loop(
    path: str | Path, sample_rate: int, loop_samples: int, total_samples: int,
) -> tuple[np.ndarray, int]:
    """Repeat an intact stem loop on the arrangement grid, smoothing only its joins."""
    source, _ = sf.read(str(path), dtype="float32", always_2d=True)
    if len(source) < 2 or loop_samples < 2:
        raise ValueError("Loop de bateria vazio ou curto demais")
    ratio = total_samples / loop_samples
    nearest = round(ratio)
    if nearest >= 1 and abs(ratio - nearest) < 0.001:
        # A few rounded samples must not count as an extra loop repetition.
        loop_samples = round(total_samples / nearest)
        repetitions = nearest
    else:
        repetitions = math.ceil(ratio)
    positions = np.arange(loop_samples, dtype=np.float64) * (len(source) - 1) / (loop_samples - 1)
    source_positions = np.arange(len(source))
    cycle = np.column_stack([
        np.interp(positions, source_positions, source[:, channel])
        for channel in range(source.shape[1])
    ]).astype(np.float32)
    repeated = np.tile(cycle, (repetitions, 1))
    if len(repeated) < total_samples:
        repeated = np.pad(repeated, ((0, total_samples - len(repeated)), (0, 0)), mode="edge")
    repeated = repeated[:total_samples]
    # A raw cut through a waveform can click at every repeat. Apply a brief
    # fade at each join without slicing the individual drum hits.
    fade = min(round(0.012 * sample_rate), loop_samples // 8)
    if fade:
        ramp = np.linspace(1.0, 0.0, fade, endpoint=True, dtype=np.float32)
        for boundary in range(loop_samples, total_samples, loop_samples):
            left = min(fade, boundary)
            right = min(fade, total_samples - boundary)
            repeated[boundary - left:boundary] *= ramp[-left:, None]
            repeated[boundary:boundary + right] *= ramp[-right:, None][::-1]
    return repeated, repetitions


def _render_reviewed_drum_schedule(
    arrangement: dict, source_path: str | Path, selected_sections: list[tuple[dict, int]],
    timeline: _RhythmTimeline, total_samples: int,
) -> tuple[np.ndarray, list[dict]]:
    """Place one entry excerpt and approved MAIN A loops on the common grid."""
    patterns = {item.get("id"): item for item in arrangement.get("style_pack", {}).get("patterns", [])}
    source, source_rate = sf.read(str(source_path), dtype="float32", always_2d=True)
    if len(source) < 2:
        raise ValueError("Stem drums vazio")
    output = np.zeros((total_samples, source.shape[1]), dtype=np.float32)
    sequence = []
    global_bar = 0
    entry_used = False
    for section, rendered_bars in selected_sections:
        plan = section.get("drum_loop_plan") or {}
        pattern = patterns.get(section.get("style_pattern_id")) or {}
        review = ((pattern.get("roles") or {}).get("drums") or {}).get("audited_continuous_loops") or {}
        stable = {item["id"]: item for item in review.get("stable_main_a", [])}
        entry = review.get("initial_turn_excerpt") or {}
        next_local_bar = 1
        for planned in plan.get("sequence") or []:
            first_local = int(planned["target_start_bar"])
            last_local = min(rendered_bars, int(planned["target_end_bar"]))
            if first_local > rendered_bars:
                break
            if first_local != next_local_bar or last_local < first_local:
                raise ValueError("Plano de bateria não cobre a grade compartilhada")
            if section.get("type") == "INTRO":
                if entry_used or plan.get("status") != "single_entry_transition_excerpt" or planned["id"] != entry.get("id"):
                    raise ValueError("A virada inicial só pode tocar uma vez")
                item = entry
                entry_used = True
            elif section.get("type") == "MAIN A":
                if plan.get("status") != "stable_main_a_only":
                    raise ValueError("MAIN A exige loops estáveis auditados")
                item = stable.get(planned["id"])
                if not item or item.get("status") != "stable_main_a":
                    raise ValueError("Plano MAIN A referencia trecho não aprovado")
            else:
                raise ValueError("Trecho de bateria sem revisão auditiva")
            source_first = round(float(item["source_start_seconds"]) * source_rate)
            source_last = round(float(item["source_end_seconds"]) * source_rate)
            excerpt = source[source_first:source_last]
            if len(excerpt) < 2:
                raise ValueError("Trecho auditado ausente no stem drums")
            target_first = timeline.bar_sample(global_bar + first_local - 1)
            target_last = timeline.bar_sample(global_bar + last_local)
            positions = np.linspace(0, len(excerpt) - 1, target_last - target_first)
            source_positions = np.arange(len(excerpt))
            output[target_first:target_last] = np.column_stack([
                np.interp(positions, source_positions, excerpt[:, channel])
                for channel in range(excerpt.shape[1])
            ])
            sequence.append({"id": item["id"], "source_bars": [item["start_bar"], item["end_bar"]],
                             "target_bars": [global_bar + first_local, global_bar + last_local]})
            next_local_bar = last_local + 1
        if next_local_bar != rendered_bars + 1:
            raise ValueError("Plano de bateria incompleto")
        global_bar += rendered_bars
    fade = round(0.012 * timeline.sample_rate)
    if fade:
        ramp = np.linspace(1.0, 0.0, fade, endpoint=True, dtype=np.float32)
        for row in sequence[:-1]:
            boundary = timeline.bar_sample(row["target_bars"][1])
            if fade <= boundary and boundary + fade <= total_samples:
                output[boundary - fade:boundary] *= ramp[:, None]
                output[boundary:boundary + fade] *= ramp[::-1, None]
    return output, sequence


def render_arrangement(
    arrangement: dict,
    output_path: str | Path,
    *,
    section_types: tuple[str, ...] = ("MAIN A", "MAIN B"),
    max_bars_per_section: int = 4,
    sample_rate: int = 44100,
    tail_seconds: float = 0.25,
    minimum_drum_probability: float = 0.6667,
    reference_drum_stem: str | Path | None = None,
    reference_grid_start_seconds: float = 0.0,
    include_drums: bool = True,
    include_bass: bool = True,
    include_accompaniment: bool = True,
    reference_drum_loop: str | Path | None = None,
    drum_loop_bars: int = 4,
    reference_drum_loop_stem: str | Path | None = None,
) -> dict:
    """Render a short PCM WAV from learned per-bar performance events.

    Only sections present in the arrangement are rendered. Events keep their
    16-step positions and stored substeps; bass notes and chord voicings come
    from the arrangement's new harmony.
    """
    validate_arrangement(arrangement)
    if sample_rate < 8000 or max_bars_per_section < 1:
        raise ValueError("sample_rate ou max_bars_per_section inválido")
    if not math.isfinite(minimum_drum_probability) or not 0 <= minimum_drum_probability <= 1:
        raise ValueError("minimum_drum_probability precisa estar entre 0 e 1")
    if sum(item is not None for item in (reference_drum_loop, reference_drum_stem,
                                         reference_drum_loop_stem)) > 1:
        raise ValueError("Use somente uma fonte de bateria: loop contínuo ou stem por ataques")
    if reference_drum_loop is not None and (not isinstance(drum_loop_bars, int) or drum_loop_bars < 1):
        raise ValueError("drum_loop_bars precisa ser positivo")
    bpm = float(arrangement.get("tempo_bpm", 0))
    if not math.isfinite(bpm) or bpm <= 0:
        raise ValueError("tempo_bpm precisa ser positivo")
    try:
        numerator, denominator = map(int, str(arrangement.get("meter", "4/4")).split("/"))
    except (TypeError, ValueError):
        raise ValueError("Métrica inválida") from None
    if numerator < 1 or denominator < 1:
        raise ValueError("Métrica inválida")
    timeline = _RhythmTimeline(bpm, numerator, denominator, sample_rate)
    bar_seconds = timeline.bar_seconds
    step_seconds = timeline.step_seconds
    drum_audio = None
    drum_rate = None
    if reference_drum_stem is not None:
        drum_audio, drum_rate = sf.read(str(reference_drum_stem), dtype="float32", always_2d=True)
        drum_audio = np.mean(drum_audio, axis=1, dtype=np.float32)
        if not math.isfinite(reference_grid_start_seconds) or reference_grid_start_seconds < 0:
            raise ValueError("reference_grid_start_seconds precisa ser finito e não negativo")
    patterns_by_id = {p.get("id"): p for p in arrangement.get("style_pack", {}).get("patterns", [])}
    selected = []
    selected_sections = []
    for section in arrangement["sections"]:
        if section.get("type") not in section_types:
            continue
        if section.get("pattern_origin") not in {"learned_style_pack", "audited_entry_excerpt"}:
            continue
        bars = section.get("performance_by_bar") or []
        rendered_bars = bars[:max_bars_per_section]
        if rendered_bars:
            selected_sections.append((section, len(rendered_bars)))
        for bar in rendered_bars:
            selected.append((section["type"], bar, section))
    if not selected:
        raise ValueError("Não há compassos MAIN A/B aprendidos ou entrada auditada disponíveis para renderizar")

    total_samples = timeline.bar_sample(len(selected)) + round(max(0.0, tail_seconds) * sample_rate)
    mix = np.zeros(total_samples, dtype=np.float32)
    stats = {"bars": len(selected), "drum_attacks": 0, "drum_events_requested": 0,
             "reference_samples_used": 0, "reference_sample_misses": 0,
             "synthetic_drum_attacks": 0, "bass_notes": 0,
             "accompaniment_stabs": 0, "sections": [], "event_bands": {},
             "bar_event_counts": [], "bass_attack_grid": []}
    section_bar_counts: dict[str, int] = {}
    for bar_index, (section_type, bar, section) in enumerate(selected):
        if not stats["sections"] or stats["sections"][-1] != section_type:
            stats["sections"].append(section_type)
        section_bar_index = section_bar_counts.get(section_type, 0)
        section_bar_counts[section_type] = section_bar_index + 1
        pattern = patterns_by_id.get(section.get("style_pattern_id"), {})
        occurrences = pattern.get("occurrence_bars", [])
        accepted_drums = [event for event in bar.get("drums", [])
                          if float(event.get("probability", 1.0)) >= minimum_drum_probability]
        stats["bar_event_counts"].append({"section": section_type,
                                          "source_bar_offset": bar.get("bar_offset"),
                                          "drums": len(accepted_drums) if include_drums and reference_drum_loop is None and reference_drum_loop_stem is None else 0,
                                          "bass": len(bar.get("bass", [])) if include_bass else 0,
                                          "accompaniment": len(bar.get("accompaniment", [])) if include_accompaniment else 0})
        for event in accepted_drums if include_drums and reference_drum_loop is None and reference_drum_loop_stem is None else []:
            step = float(event.get("step", 0)) + float(event.get("substep", 0)) / 4
            start = timeline.step_sample(bar_index, float(event.get("step", 0)),
                                         float(event.get("substep", 0)))
            probability = float(event.get("probability", 1.0))
            bands = set(event.get("bands") or [])
            hit_gain = 0.28 + 0.25 * min(1.0, max(0.0, probability))
            sample = None
            stats["drum_events_requested"] += 1
            if drum_audio is not None:
                if occurrences:
                    sample = _best_reference_drum_hit(
                        drum_audio, drum_rate, sample_rate, occurrences,
                        int(bar.get("bar_offset", 1)), step_seconds, step,
                        reference_grid_start_seconds,
                    )
                if sample is not None:
                    _put(mix, sample, start, hit_gain * 0.72)
                    stats["reference_samples_used"] += 1
                else:
                    # A sampled render must never switch to synthetic timbre:
                    # a missing source hit is silence, not a generic drum.
                    stats["reference_sample_misses"] += 1
            else:
                audible_bands = bands or {"mid"}  # keep unclassified attacks audible
                if "low" in audible_bands:
                    _put(mix, _kick(round(0.20 * sample_rate), sample_rate), start, hit_gain)
                if "mid" in audible_bands:
                    _put(mix, _mid_hit(round(0.13 * sample_rate), sample_rate), start, hit_gain * 0.52)
                if "high" in audible_bands:
                    _put(mix, _high_metal(round(0.085 * sample_rate), sample_rate), start, hit_gain * 0.27)
                stats["synthetic_drum_attacks"] += 1
            if sample is not None or drum_audio is None:
                stats["drum_attacks"] += 1
            for band in bands:
                stats["event_bands"][band] = stats["event_bands"].get(band, 0) + 1

        bass_events = sorted(bar.get("bass", []), key=lambda e: (e.get("step", 0), e.get("substep", 0))) if include_bass else []
        for index, event in enumerate(bass_events):
            step = float(event.get("step", 0)) + float(event.get("substep", 0)) / 4
            start = timeline.step_sample(bar_index, float(event.get("step", 0)),
                                         float(event.get("substep", 0)))
            next_step = (float(bass_events[index + 1].get("step", 16))
                         + float(bass_events[index + 1].get("substep", 0)) / 4) if index + 1 < len(bass_events) else 16
            if event.get("duration_grid_steps") is not None:
                note_seconds = float(event["duration_grid_steps"]) * step_seconds
            else:
                note_seconds = float(event.get("duration_seconds") or max(0.08, min(0.48, (next_step - step) * step_seconds * 0.9)))
            note_seconds = max(0.04, min(bar_seconds, note_seconds))
            strength = event.get("intensity")
            gain = 0.47 if strength is None else 0.47 * max(0.0, min(1.0, float(strength)))
            _put(mix, _bass_note(event["pitch_midi"], round(note_seconds * sample_rate), sample_rate),
                 start, gain)
            stats["bass_notes"] += 1
            stats["bass_attack_grid"].append({"bar": bar_index + 1, "step": step,
                                               "sample": start})

        for event in bar.get("accompaniment", []) if include_accompaniment else []:
            start = timeline.step_sample(bar_index, float(event.get("step", 0)),
                                         float(event.get("substep", 0)))
            pitches = event.get("pitches_midi") or []
            if pitches:
                _put(mix, _chord_stab(pitches, round(0.19 * sample_rate), sample_rate),
                     start, 0.54)
                stats["accompaniment_stabs"] += 1

    loop_repetitions = 0
    reviewed_sequence = []
    if reference_drum_loop is not None and include_drums:
        drum_loop, loop_repetitions = _repeat_continuous_drum_loop(
            reference_drum_loop, sample_rate,
            timeline.bar_sample(drum_loop_bars),
            len(mix),
        )
        mix = np.repeat(mix[:, None], drum_loop.shape[1], axis=1) + drum_loop
    if reference_drum_loop_stem is not None and include_drums:
        if any(kind not in {"INTRO", "MAIN A"} for kind, _, _ in selected):
            raise ValueError("Trechos auditados disponíveis apenas para entrada e MAIN A")
        reviewed_audio, reviewed_sequence = _render_reviewed_drum_schedule(
            arrangement, reference_drum_loop_stem, selected_sections, timeline, len(mix))
        mix = np.repeat(mix[:, None], reviewed_audio.shape[1], axis=1) + reviewed_audio
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    if peak > 0.94:
        mix *= 0.94 / peak
    pcm = np.round(np.clip(mix, -1.0, 1.0) * 32767).astype("<i2")
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1 if mix.ndim == 1 else mix.shape[1])
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    stats.update({"output_path": str(path.resolve()), "sample_rate": sample_rate,
                  "duration_seconds": len(pcm) / sample_rate, "peak_before_limiter": peak,
                  "bpm": bpm, "meter": arrangement.get("meter"),
                  "minimum_drum_probability": minimum_drum_probability,
                  "drum_source": ("audited entry and stable MAIN A loops from reference stem" if reference_drum_loop_stem is not None
                                  else "continuous reference stem loop" if reference_drum_loop is not None
                                  else "reference stem one-shots at corresponding learned grid positions"
                                  if drum_audio is not None else "procedural synthesis"),
                  "reference_drum_stem": str(Path(reference_drum_stem).resolve()) if reference_drum_stem else None,
                  "included_parts": {"drums": include_drums, "bass": include_bass,
                                     "accompaniment": include_accompaniment},
                  "continuous_drum_loop": str(Path(reference_drum_loop).resolve()) if reference_drum_loop else None,
                  "reviewed_drum_stem": str(Path(reference_drum_loop_stem).resolve()) if reference_drum_loop_stem else None,
                  "reviewed_drum_sequence": reviewed_sequence,
                  "drum_loop_repetitions": loop_repetitions,
                  "shared_timeline": {"steps_per_bar": 16,
                                      "bar_edges_samples": [timeline.bar_sample(index)
                                                            for index in range(len(selected) + 1)]},
                  "note": "Deterministic preview; source drum excerpts and bass events share one 16-step timeline and identical bar edges. Source drum microtiming remains intact."})
    return stats
