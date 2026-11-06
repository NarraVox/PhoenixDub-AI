"""Explainable combination of rhythm, score and separated-stem evidence."""
import math
import re

import numpy as np


def _relative_error(left, right):
    return abs(float(left) - float(right)) / max(abs(float(right)), 1e-9)


def consolidate_rhythm(grid, sheetsage, bpm_hint=None, meter_hint=None):
    """Select an equivalent pulse/meter interpretation without hiding raw ambiguity."""
    hypotheses = grid.get("tempo_hypotheses") or []
    raw_bars = grid.get("bars") or []
    if len(raw_bars) > 1:
        bar_period = float(np.median([b["end_seconds"] - b["start_seconds"] for b in raw_bars]))
    else:
        bar_period = None
    score = sheetsage or {}
    score_tempo = score.get("model_tempo_bpm")
    score_meter = score.get("meter")
    score_meter_value = int(score_meter.split("/")[0]) if isinstance(score_meter, str) and "/" in score_meter else None
    candidates = []
    for hypothesis in hypotheses:
        bpm = float(hypothesis.get("measured_bpm") or hypothesis.get("bpm") or 0)
        if bpm <= 0:
            continue
        meter_hypotheses = hypothesis.get("meter_hypotheses") or []
        for meter_result in meter_hypotheses:
            meter = int(meter_result["meter"])
            if meter_hint is not None and meter != int(meter_hint):
                continue
            phase = int(meter_result["phase"])
            candidate_bar_period = 60.0 * meter / bpm
            if bar_period and _relative_error(candidate_bar_period, bar_period) > 0.08:
                continue
            rhythm_score = float(np.clip(hypothesis.get("score", 0), 0, 1))
            accent = float(meter_result.get("accent_score", 0))
            meter_score = float(np.clip(0.5 + 2.0 * accent, 0, 1))
            if score_tempo:
                equivalent_tempos = (bpm / 2.0, bpm, bpm * 2.0)
                tempo_error = min(_relative_error(value, score_tempo) for value in equivalent_tempos)
                score_tempo_match = math.exp(-tempo_error / 0.06)
            else:
                tempo_error = None
                score_tempo_match = None
            score_meter_match = (1.0 if meter == score_meter_value else 0.0) if score_meter_value else None
            user_tempo_match = (math.exp(-_relative_error(bpm, bpm_hint) / 0.04)
                                if bpm_hint is not None else None)
            user_meter_match = (1.0 if meter == int(meter_hint) else 0.0) if meter_hint is not None else None
            bar_match = (math.exp(-abs(math.log(candidate_bar_period / bar_period)) / 0.04)
                         if bar_period else 0.5)
            components = {"rhythm_score": round(rhythm_score, 4),
                          "stem_meter_accent": round(meter_score, 4),
                          "observed_bar_duration_match": round(bar_match, 4)}
            if score_tempo_match is not None:
                components["sheetsage_tempo_match_half_base_double"] = round(score_tempo_match, 4)
            if score_meter_match is not None:
                components["sheetsage_meter_match"] = score_meter_match
            if user_tempo_match is not None:
                components["user_bpm_hint_match"] = round(user_tempo_match, 4)
            if user_meter_match is not None:
                components["user_meter_hint_match"] = user_meter_match
            weights = {"rhythm_score": 0.35, "stem_meter_accent": 0.15,
                       "observed_bar_duration_match": 0.15,
                       "sheetsage_tempo_match_half_base_double": 0.20,
                       "sheetsage_meter_match": 0.15,
                       "user_bpm_hint_match": 0.50,
                       "user_meter_hint_match": 0.50}
            active_weights = {key: value for key, value in weights.items() if key in components}
            total_weight = sum(active_weights.values())
            combined = sum(components[key] * weight for key, weight in active_weights.items()) / total_weight
            candidates.append({"bpm": round(bpm, 3), "meter": f"{meter}/4", "phase": phase,
                               "bar_duration_seconds": round(candidate_bar_period, 6),
                               "rhythm_hypothesis_bpm": hypothesis.get("bpm"),
                               "rhythm_hypothesis_score": hypothesis.get("score"),
                               "meter_accent_score": round(accent, 4),
                               "sheetsage_tempo_relative_error": round(tempo_error, 4) if tempo_error is not None else None,
                               "evidence": components, "combined_score": round(combined, 4),
                               "beat_times": hypothesis.get("beat_times", [])})
    candidates.sort(key=lambda item: item["combined_score"], reverse=True)
    if not candidates:
        return {"status": "unresolved", "bpm": grid.get("bpm"), "meter": grid.get("meter"),
                "grid_confidence": grid.get("grid_confidence"), "candidates": [],
                "reason": "Sem par BPM/métrica com duração de compasso compatível com a grade observada."}
    best = candidates[0]
    second_score = candidates[1]["combined_score"] if len(candidates) > 1 else 0.0
    margin = round(best["combined_score"] - second_score, 4) if len(candidates) > 1 else None
    margin_for_status = margin or 0.0
    # Preserve tempo ambiguity when independent evidence does not separate candidates.
    raw_ambiguous = bool(grid.get("tempo_ambiguous"))
    resolved_by_score = (score_tempo is not None and score_meter_value is not None and
                         (best.get("sheetsage_tempo_relative_error") or 0.0) <= 0.08 and
                         best.get("evidence", {}).get("sheetsage_meter_match") == 1.0)
    user_constrained = bpm_hint is not None or meter_hint is not None
    status = "user_constrained_interpretation" if user_constrained else (
        "corroborated_interpretation" if resolved_by_score and margin_for_status >= 0.015 else
        ("provisional_interpretation" if margin_for_status >= 0.04 else "ambiguous"))
    return {"status": status, "bpm": best["bpm"], "meter": best["meter"],
            "bar_duration_seconds": best["bar_duration_seconds"], "phase": best["phase"],
            "combined_score": best["combined_score"], "candidate_margin": margin,
            "raw_tempo_ambiguous": raw_ambiguous,
            "raw_bpm": grid.get("bpm"), "raw_meter": grid.get("meter"),
            "grid_confidence": grid.get("grid_confidence"),
            "evidence": best["evidence"], "candidates": [
                {key: value for key, value in item.items() if key != "beat_times"}
                for item in candidates[:8]],
            "reason": ("BPM/métrica escolhidos entre hipóteses que preservam a duração observada dos compassos; "
                       "SheetSage2 corrobora uma interpretação half/double dentro da tolerância e os acentos da bateria pontuam a métrica."
                       if score_tempo is not None and score_meter_value is not None else
                       "BPM/métrica provisórios escolhidos pelas hipóteses de pulso, duração dos compassos e acentos da bateria; a ambiguidade não foi resolvida por SheetSage2."),
            "_selected_beat_times": best["beat_times"]}


def apply_rhythm_consensus(grid, consensus):
    """Apply only the selected beat interpretation; retain bar phase and duration evidence."""
    if consensus.get("status") == "unresolved":
        return grid
    # The selected BPM/meter pair was constrained to the observed bar period.
    # Anchor its beat phase to Rhythm's first drum-derived downbeat so a weak
    # half-time tracker phase cannot shift every bar by one pulse.
    updated = dict(grid)
    candidate_beat_times = np.asarray(consensus.get("_selected_beat_times") or [], dtype=float)
    meter = int(consensus["meter"].split("/")[0])
    phase = int(consensus.get("phase", 0))
    raw_downbeats = np.asarray(grid.get("downbeats") or [], dtype=float)
    target_start = float(raw_downbeats[0]) if len(raw_downbeats) else float(grid.get("bars", [{}])[0].get("start_seconds", 0))
    raw_beats = np.asarray(grid.get("beats") or [], dtype=float)
    raw_tempo = float(grid.get("tempo_tracker_hypothesis") or 0)
    relation = raw_tempo / max(float(consensus["bpm"]), 1e-9)
    phase_offset = 0.0
    beat_source = "selected Rhythm hypothesis"
    if len(raw_beats) and 1.8 <= relation <= 2.2 and len(raw_downbeats):
        # A half-time interpretation uses every second raw beat. Choose its
        # phase from Rhythm's first downbeat, preserving the measured bar grid.
        raw_anchor = int(np.argmin(np.abs(raw_beats - target_start)))
        stride = 2
        start_index = raw_anchor % stride
        beat_times = raw_beats[start_index::stride]
        phase = (raw_anchor - start_index) // stride % meter
        beat_source = "every second Nexus Rhythm beat, phased to its drum downbeat"
    else:
        beat_times = candidate_beat_times
    candidate_downbeats = beat_times[phase::meter]
    phase_offset = target_start - float(candidate_downbeats[0]) if len(candidate_downbeats) else 0.0
    beat_times = beat_times + phase_offset
    beat_times = beat_times[(beat_times >= 0) & (beat_times <= float(grid.get("duration", 0)))]
    downbeats = beat_times[phase::meter]
    bars = [{"start_seconds": float(start), "end_seconds": float(end), "bar": index + 1}
            for index, (start, end) in enumerate(zip(downbeats[:-1], downbeats[1:]))]
    updated.update({"bpm": consensus["bpm"], "meter": consensus["meter"],
                    "beats": beat_times.tolist(), "downbeats": downbeats.tolist(), "bars": bars,
                    "tempo_estimate": consensus["bpm"],
                    "tempo_tracker_hypothesis": next((item.get("rhythm_hypothesis_bpm")
                                                       for item in consensus.get("candidates", [])
                                                       if item.get("bpm") == consensus["bpm"]),
                                                      grid.get("tempo_tracker_hypothesis")),
                    "tempo_ambiguous": consensus.get("status") == "ambiguous",
                    "meter_is_hypothesis": True,
                    "grid_method": str(grid.get("grid_method", "")) + "_multimodal_consensus"})
    consensus.pop("_selected_beat_times", None)
    consensus["phase_offset_seconds"] = round(float(phase_offset), 4)
    consensus["applied_phase"] = int(phase)
    consensus["applied_bar_count"] = len(bars)
    consensus["beat_source"] = beat_source
    consensus["bar_phase_source"] = "Beat phase anchored to the first Nexus Rhythm drum-derived downbeat"
    return updated


_ROOTS = {"C": 0, "B#": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
          "E": 4, "Fb": 4, "E#": 5, "F": 5, "F#": 6, "Gb": 6, "G": 7,
          "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11, "Cb": 11}


def _chord_classes(symbol):
    match = re.match(r"^([A-G](?:#|b)?)(.*)$", str(symbol).strip())
    if not match or match.group(1) not in _ROOTS:
        return None
    root, quality = _ROOTS[match.group(1)], match.group(2).lower()
    if "dim" in quality or "°" in quality:
        intervals = (0, 3, 6)
    elif "aug" in quality or "+" in quality:
        intervals = (0, 4, 8)
    elif quality.startswith("m") and not quality.startswith(("maj", "m7b5")):
        intervals = (0, 3, 7)
    elif "sus2" in quality:
        intervals = (0, 2, 7)
    elif "sus" in quality:
        intervals = (0, 5, 7)
    else:
        intervals = (0, 4, 7)
    return {(root + interval) % 12 for interval in intervals}


def _stem_chroma(stem_paths, bars, target_sr=22050):
    """Average pitch-class energy per actual bar from bass and accompaniment stems."""
    import librosa
    import soundfile as sf

    chroma_by_stem = []
    frame_times = None
    for name in ("bass", "other"):
        path = stem_paths.get(name)
        if not path or not path.is_file():
            continue
        with sf.SoundFile(path) as stream:
            signal = stream.read(dtype="float32", always_2d=True).mean(axis=1)
            sr = stream.samplerate
        if sr != target_sr:
            signal = librosa.resample(signal, orig_sr=sr, target_sr=target_sr)
        chroma = librosa.feature.chroma_stft(y=signal, sr=target_sr, n_fft=4096,
                                              hop_length=1024, tuning=None, norm=2)
        if frame_times is None:
            frame_times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=target_sr,
                                                  hop_length=1024)
        chroma_by_stem.append(chroma)
    if not chroma_by_stem or frame_times is None:
        return [], []
    total = np.sum(chroma_by_stem, axis=0)
    profiles, energies = [], []
    for bar in bars:
        mask = (frame_times >= bar["start_seconds"]) & (frame_times < bar["end_seconds"])
        profile = total[:, mask].mean(axis=1) if np.any(mask) else np.zeros(12)
        profiles.append(profile.astype(float))
        energies.append(float(profile.sum()))
    return profiles, energies


def align_harmony_to_sections(sheetsage, bars, sections, stem_paths):
    """Map score-bar chords onto the Nexus grid using bass/other chroma evidence."""
    if not sheetsage or not bars:
        return {"status": "unavailable", "aligned_chords": [], "by_section": [],
                "reason": "SheetSage2 score or Nexus bars are unavailable."}
    profiles, bar_energy = _stem_chroma(stem_paths, bars)
    if not profiles:
        return {"status": "unavailable", "aligned_chords": [], "by_section": [],
                "reason": "Bass/other stem chroma could not be computed."}
    profiles = np.asarray(profiles, dtype=float)
    model_bpm = float(sheetsage.get("model_tempo_bpm") or 0)
    model_meter = sheetsage.get("meter") or "4/4"
    model_beats = int(model_meter.split("/")[0])
    model_period = 60 * model_beats / model_bpm if model_bpm else float(np.median(
        [b["end_seconds"] - b["start_seconds"] for b in bars]))
    grid_period = float(np.median([b["end_seconds"] - b["start_seconds"] for b in bars]))
    nominal_scale = model_period / max(grid_period, 1e-9)
    chord_rows = [row for row in sheetsage.get("chords_by_bar", []) if row.get("chords")]
    templates = [(int(row.get("bar", 1)) - 1,
                  set().union(*[pc for pc in (_chord_classes(chord) for chord in row["chords"]) if pc]))
                 for row in chord_rows]
    templates = [(idx, pcs) for idx, pcs in templates if pcs]
    if not templates:
        return {"status": "unavailable", "aligned_chords": [], "by_section": [],
                "reason": "No score chord labels could be interpreted."}
    templates = templates[:]
    scale_values = np.arange(max(0.85, nominal_scale - 0.10), min(1.15, nominal_scale + 0.1001), 0.005)
    offset_values = range(-4, min(5, len(bars) // 8 + 1))
    scored = []
    for scale in scale_values:
        for offset in offset_values:
            values = []
            mapping = []
            for score_index, pcs in templates:
                grid_index = int(round(offset + score_index * scale))
                if not 0 <= grid_index < len(profiles):
                    continue
                profile = profiles[grid_index]
                total = float(profile.sum()) + 1e-9
                support = float(profile[list(pcs)].sum() / total)
                outside = float(profile[[i for i in range(12) if i not in pcs]].mean() / total)
                values.append(support - 0.30 * outside)
                mapping.append((score_index, grid_index))
            if len(values) < max(12, int(len(templates) * 0.60)):
                continue
            coverage = len(values) / len(templates)
            objective = float(np.mean(values)) * coverage
            scored.append({"scale": float(scale), "offset_bars": int(offset),
                           "score": objective, "mean_chord_support": float(np.mean(values)),
                           "coverage": coverage, "mapping": mapping})
    if not scored:
        return {"status": "unresolved", "aligned_chords": [], "by_section": [],
                "reason": "Score bars could not be mapped onto the detected grid."}
    scored.sort(key=lambda item: item["score"], reverse=True)
    best = scored[0]
    # Exclude near-identical neighboring stretch/offset variants from the comparison margin.
    runner_up = next((item for item in scored[1:]
                      if abs(item["scale"] - best["scale"]) > 0.015 or
                      abs(item["offset_bars"] - best["offset_bars"]) > 1), None)
    margin = best["score"] - (runner_up["score"] if runner_up else 0.0)
    mapping = {score_index: grid_index for score_index, grid_index in best["mapping"]}
    for score_index in range(int(sheetsage.get("measure_count") or 0)):
        grid_index = int(round(best["offset_bars"] + score_index * best["scale"]))
        if 0 <= grid_index < len(bars):
            mapping.setdefault(score_index, grid_index)
    section_ids = []
    for section_index, section in enumerate(sections):
        section_ids.append((section_index, section))
    aligned = []
    for row in chord_rows:
        score_bar = int(row.get("bar", 1))
        grid_index = mapping.get(score_bar - 1)
        if grid_index is None:
            continue
        grid_bar = bars[grid_index]
        midpoint = (grid_bar["start_seconds"] + grid_bar["end_seconds"]) / 2
        section_choice = max(section_ids,
                             key=lambda pair: max(0.0, min(pair[1]["end_seconds"], grid_bar["end_seconds"]) -
                                                max(pair[1]["start_seconds"], grid_bar["start_seconds"])),
                             default=(None, None))
        section_index, section = section_choice
        pc = set().union(*[value for value in (_chord_classes(chord) for chord in row["chords"]) if value])
        profile = profiles[grid_index]
        score_value = float(profile[list(pc)].sum() / (profile.sum() + 1e-9)) if pc else None
        aligned.append({"score_bar": score_bar, "grid_bar": grid_index + 1,
                        "start_seconds": round(float(grid_bar["start_seconds"]), 3),
                        "end_seconds": round(float(grid_bar["end_seconds"]), 3),
                        "chords": row["chords"], "stem_chord_support": round(score_value, 4) if score_value is not None else None,
                        "nexus_section_index": section_index,
                        "nexus_section": section.get("candidate_type", section.get("type")) if section else "UNKNOWN",
                        "nexus_section_type": section.get("type", "UNKNOWN") if section else "UNKNOWN"})
    groups = {}
    for section_index, section in enumerate(sections):
        groups[(section_index, section.get("candidate_type", section.get("type")), section.get("type"))] = {
            "nexus_section_index": section_index,
            "section": section.get("candidate_type", section.get("type")),
            "section_type": section.get("type"),
            "start_seconds": round(float(section["start_seconds"]), 3),
            "end_seconds": round(float(section["end_seconds"]), 3),
            "start_grid_bar": section.get("start_bar"),
            "end_grid_bar": (section.get("start_bar") + section.get("duration_bars", 0) - 1
                             if section.get("start_bar") is not None and section.get("duration_bars") is not None else None),
            "chords": [], "chord_observations": 0}
    for item in aligned:
        key = (item["nexus_section_index"], item["nexus_section"], item["nexus_section_type"])
        group = groups.setdefault(key, {"nexus_section_index": key[0], "section": key[1],
                                        "section_type": key[2], "start_seconds": item["start_seconds"],
                                        "end_seconds": item["end_seconds"], "start_grid_bar": item["grid_bar"],
                                        "end_grid_bar": item["grid_bar"], "chords": [], "chord_observations": 0})
        group["end_seconds"] = item["end_seconds"]
        group["end_grid_bar"] = item["grid_bar"]
        group["chords"].extend(chord for chord in item["chords"] if not group["chords"] or group["chords"][-1] != chord)
        group["chord_observations"] += len(item["chords"])
    by_section = list(groups.values())
    return {"status": "stem_aligned" if margin >= 0.02 and best["mean_chord_support"] >= 0.40 else "weak_alignment",
            "alignment_method": "grid-bar chord-template support from bass + other stem chroma; local score tempo stretch and bar offset search",
            "score_bar_count": sheetsage.get("measure_count"), "grid_bar_count": len(bars),
            "model_bar_duration_seconds": round(model_period, 6), "grid_bar_duration_seconds": round(grid_period, 6),
            "score_to_grid_scale": round(best["scale"], 4), "score_bar_offset": best["offset_bars"],
            "mean_chord_support": round(best["mean_chord_support"], 4),
            "alignment_score": round(best["score"], 4), "alignment_margin": round(float(margin), 4),
            "coverage": round(best["coverage"], 4), "confidence_kind": "heuristic_not_calibrated",
            "sections_mapped": len({item["nexus_section_index"] for item in aligned}),
            "key_changes_aligned": _align_key_changes(sheetsage.get("key_changes", []), mapping, bars, sections),
            "aligned_chords": aligned, "by_section": by_section,
            "reason": "Each SheetSage2 chord bar was mapped to the Nexus bar maximizing chord-tone support in bass and accompaniment stems. This is an alignment score, not a calibrated chord probability."}


def _align_key_changes(changes, mapping, bars, sections):
    aligned = []
    for change in changes:
        score_bar = max(1, int(change.get("after_bar", 0)) + 1)
        grid_index = mapping.get(score_bar - 1)
        if grid_index is None or grid_index >= len(bars):
            continue
        bar = bars[grid_index]
        midpoint = (bar["start_seconds"] + bar["end_seconds"]) / 2
        section = next((item for item in sections if item["start_seconds"] <= midpoint < item["end_seconds"]), None)
        aligned.append({"score_bar": score_bar, "grid_bar": grid_index + 1, "key": change.get("key"),
                        "start_seconds": round(float(bar["start_seconds"]), 3),
                        "nexus_section": section.get("candidate_type", section.get("type")) if section else "UNKNOWN"})
    return aligned
