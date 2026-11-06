"""Extract reusable grid attacks and role rhythms from separated stems."""
import copy
from pathlib import Path

import numpy as np
import soundfile as sf


ROLES = {"drums": "drums", "bass": "bass", "other": "accompaniment"}
SECTION_TYPES = {"MAIN A", "MAIN B", "FILL A", "FILL B", "BREAK", "INTRO", "ENDING", "VARIATION"}
STEPS_PER_BAR = 16
SUBSTEPS_PER_STEP = 4
BANDS = {"low": (35, 160), "mid": (160, 2500), "high": (2500, 10000)}


def _features_for_bar(audio, sr, start, end):
    """Return 16th-grid energy/onsets; band evidence is coarse, not hit naming."""
    features = {"energy": [], "onset": [], "substep": []}
    for band in BANDS:
        features[f"{band}_onset"] = []
    for step in range(STEPS_PER_BAR):
        edge0 = start + (end - start) * step / STEPS_PER_BAR
        edge1 = start + (end - start) * (step + 1) / STEPS_PER_BAR
        rms_parts, band_parts = [], {band: [] for band in BANDS}
        previous_left = max(0, int((edge0 - (edge1 - edge0) / SUBSTEPS_PER_STEP) * sr))
        previous_right = max(previous_left, min(len(audio), int(edge0 * sr)))
        previous = audio[previous_left:previous_right]
        previous_rms = float(np.sqrt(np.mean(previous * previous))) if len(previous) else 0.0
        previous_spectrum = np.abs(np.fft.rfft(previous * np.hanning(len(previous)))) if len(previous) else np.asarray([])
        previous_hz = np.fft.rfftfreq(len(previous), 1.0 / sr) if len(previous) else np.asarray([])
        previous_bands = {}
        for band, (low, high) in BANDS.items():
            selection = previous_spectrum[(previous_hz >= low) & (previous_hz < min(high, sr / 2))] if len(previous_hz) else []
            previous_bands[band] = float(np.sqrt(np.mean(selection * selection))) if len(selection) else 0.0
        for substep in range(SUBSTEPS_PER_STEP):
            left = max(0, min(len(audio), int((edge0 + (edge1 - edge0) * substep / SUBSTEPS_PER_STEP) * sr)))
            right = max(left, min(len(audio), int((edge0 + (edge1 - edge0) * (substep + 1) / SUBSTEPS_PER_STEP) * sr)))
            chunk = audio[left:right]
            if not len(chunk):
                rms_parts.append(0.0)
                for band in BANDS:
                    band_parts[band].append(0.0)
                continue
            rms_parts.append(float(np.sqrt(np.mean(chunk * chunk))))
            spectrum = np.abs(np.fft.rfft(chunk * np.hanning(len(chunk))))
            hz = np.fft.rfftfreq(len(chunk), 1.0 / sr)
            for band, (low, high) in BANDS.items():
                selected = spectrum[(hz >= low) & (hz < min(high, sr / 2))]
                band_parts[band].append(float(np.sqrt(np.mean(selected * selected))) if len(selected) else 0.0)
        rms = np.asarray(rms_parts, dtype=np.float32)
        flux = np.maximum(np.diff(rms, prepend=previous_rms), 0)
        features["energy"].append(float(np.sqrt(np.mean(rms * rms))))
        features["onset"].append(float(flux.max(initial=0)))
        features["substep"].append(int(np.argmax(flux)))
        for band, values in band_parts.items():
            band_flux = np.maximum(np.diff(np.asarray(values, dtype=np.float32), prepend=previous_bands[band]), 0)
            features[f"{band}_onset"].append(float(band_flux.max(initial=0)))
    return features


def _occurrence(audio, sr, by_number, first_bar, length):
    result = {key: [] for key in ("energy", "onset", "substep", *(f"{band}_onset" for band in BANDS))}
    for offset in range(length):
        bar = by_number.get(int(first_bar) + offset)
        if bar is None:
            return None
        features = _features_for_bar(audio, sr, bar["start_seconds"], bar["end_seconds"])
        for key in result:
            result[key].extend(features[key])
    return result


def _merge_occurrences(audio, sr, bars, starts, length, role):
    by_number = {int(item["bar"]): item for item in bars if isinstance(item.get("bar"), (int, float))}
    observations = [item for start in starts if (item := _occurrence(audio, sr, by_number, start, length)) is not None]
    if not observations:
        return None
    energy = np.mean([item["energy"] for item in observations], axis=0)
    scale = float(np.percentile(energy[energy > 0], 95)) if np.any(energy > 0) else 0.0
    if scale > 1e-9:
        energy = np.clip(energy / scale, 0.0, 1.0)

    onset = np.asarray([item["onset"] for item in observations], dtype=np.float32)
    thresholds = [max(float(np.quantile(row[row > 0], .85)), float(row.max(initial=0)) * .25, 1e-9)
                  if np.any(row > 0) else float("inf") for row in onset]
    detected = np.asarray([row >= threshold for row, threshold in zip(onset, thresholds)], dtype=np.float32)
    probability = detected.mean(axis=0)
    onset_mean = onset.mean(axis=0)
    onset_scale = float(np.percentile(onset_mean[onset_mean > 0], 95)) if np.any(onset_mean > 0) else 0.0
    if onset_scale > 1e-9:
        onset_mean = np.clip(onset_mean / onset_scale, 0.0, 1.0)
    substeps = np.asarray([item["substep"] for item in observations], dtype=np.float32)
    substep_mean = np.rint(np.sum(substeps * detected, axis=0) / np.maximum(detected.sum(axis=0), 1)).astype(int)

    profile = {"stem": role, "steps_per_bar": STEPS_PER_BAR, "length_bars": length,
               "step_energy": [round(float(v), 4) for v in energy],
               "attack_probability": [round(float(v), 4) for v in probability],
               "attack_strength": [round(float(v), 4) for v in onset_mean],
               "attack_substep": substep_mean.tolist(), "observations": len(observations),
               "normalization": "energy and attack strength scaled to template 95th percentile",
               "event_source": "stem waveform grid attacks; no pitch or vocal-melody events"}
    if role == "drums":
        band_probs = {}
        for band in BANDS:
            values = np.asarray([item[f"{band}_onset"] for item in observations], dtype=np.float32)
            binary = []
            for row in values:
                threshold = (max(float(np.quantile(row[row > 0], .85)),
                                 float(row.max(initial=0)) * .25, 1e-9)
                             if np.any(row > 0) else float("inf"))
                binary.append(row >= threshold)
            band_probs[band] = np.asarray(binary, dtype=np.float32).mean(axis=0)
        probability = np.maximum.reduce([probability, *band_probs.values()])
        profile["attack_probability"] = [round(float(v), 4) for v in probability]
        profile["frequency_band_attack_probability"] = {
            band: [round(float(v), 4) for v in values] for band, values in band_probs.items()}
        profile["frequency_bands_hz"] = {band: [low, high] for band, (low, high) in BANDS.items()}
        profile["attack_steps"] = [
            {"bar_offset": index // STEPS_PER_BAR + 1, "step": index % STEPS_PER_BAR,
             "probability": round(float(probability[index]), 4),
             "substep": int(substep_mean[index]),
             "bands": [band for band, values in band_probs.items() if values[index] >= .5]}
            for index in range(len(probability)) if probability[index] >= .5]
    return profile


def _template(pattern, bars, audio_by_role):
    length = int(pattern.get("length_bars", 0) or 0)
    starts = pattern.get("occurrence_bars") or [pattern.get("source_bar")]
    starts = [int(start) for start in starts if isinstance(start, (int, float)) and int(start) > 0]
    if length < 1 or not starts:
        return None
    roles = {}
    for role, (audio, sr) in audio_by_role.items():
        profile = _merge_occurrences(audio, sr, bars, starts, length, role)
        if profile:
            if role == "bass":
                profile["relative_pattern"] = {
                    "status": "unconfirmed", "events": [],
                    "reason": "A relative degree motif requires pitch-event and chord-alignment evidence; onset energy alone cannot establish notes.",
                }
            roles[role] = profile
    return {"id": pattern.get("id"), "label": pattern.get("label"),
            "length_bars": length, "occurrence_bars": starts,
            "confidence": pattern.get("confidence"), "roles": roles}


def build_style_pack(patterns, sections, bars, stem_paths):
    """Build repeatable role events only for patterns/sections with source evidence."""
    audio_by_role = {}
    for stem, role in ROLES.items():
        path = Path(stem_paths[stem])
        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
        mono = data.mean(axis=1)
        if len(mono) and np.isfinite(mono).all():
            audio_by_role[role] = (mono, int(sr))

    templates = []
    for pattern in patterns:
        if not isinstance(pattern, dict):
            continue
        item = _template(pattern, bars, audio_by_role)
        if item:
            templates.append(item)

    form = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        start_bar, length = section.get("start_bar"), section.get("duration_bars")
        if not isinstance(start_bar, int) or not isinstance(length, int) or length < 1:
            continue
        label = str(section.get("candidate_type") or section.get("label") or section.get("type") or "UNKNOWN").upper()
        status = section.get("status", "unknown")
        item = {"type": label, "start_bar": start_bar, "bars": length,
                "pattern_id": section.get("pattern_id"), "confidence": section.get("confidence"),
                "status": status}
        if status == "detected" and label in SECTION_TYPES:
            roles = {}
            for role, (audio, sr) in audio_by_role.items():
                profile = _merge_occurrences(audio, sr, bars, [start_bar], length, role)
                if profile:
                    if role == "bass":
                        profile["relative_pattern"] = {
                            "status": "unconfirmed", "events": [],
                            "reason": "A relative degree motif requires pitch-event and chord-alignment evidence; onset energy alone cannot establish notes.",
                        }
                    roles[role] = profile
            if roles:
                item["roles"] = roles
        form.append(item)

    return {
        "version": "2.1", "source": "separated_stem_grid_attacks",
        "grid_steps_per_bar": STEPS_PER_BAR, "substeps_per_step": SUBSTEPS_PER_STEP,
        "patterns": templates, "form": form,
        "limitations": [
            "Drum events are waveform attacks with coarse low/mid/high frequency evidence; they are not guaranteed kick/snare/hat labels.",
            "Bass/accompaniment events preserve onset timing and energy only; their source pitches and reference vocal melody are not stored.",
            "The accompaniment stem may contain residual vocal bleed; no pitch contour or vocal note event is extracted.",
            "Only recurring catalog patterns and sections classified as detected receive reusable events; absent section types are not synthesized.",
        ],
    }


def apply_manual_drum_review(style_pack, review, bars):
    """Attach an explicit listening review without relabeling Nexus sections.

    A region that contains a turn remains a candidate region until its exact
    fill boundaries have been established. Only stable loops are renderable as
    a repeating MAIN A groove.
    """
    if not review:
        return style_pack
    if not isinstance(review, dict) or review.get("version") != 1:
        raise ValueError("Versão inválida da revisão auditiva do Style Pack")
    pattern = next((item for item in style_pack.get("patterns", [])
                    if item.get("id") == review.get("pattern_id")), None)
    if pattern is None or pattern.get("label") != "MAIN A":
        raise ValueError("Revisão auditiva aponta para um padrão MAIN A ausente")
    by_number = {int(item["bar"]): item for item in bars}
    starts = pattern.get("occurrence_bars", [])
    pattern_length = int(pattern.get("length_bars", 0))
    stable = review.get("stable_loops") or []
    candidates = review.get("transition_candidates") or []
    if not stable or not isinstance(stable, list) or not isinstance(candidates, list):
        raise ValueError("A revisão precisa identificar loops estáveis")
    loop_bars = int(review.get("loop_bars", 0))
    if loop_bars < 1:
        raise ValueError("loop_bars inválido na revisão auditiva")
    occupied, identifiers = set(), set()

    def resolve(item, stable_loop):
        if not isinstance(item, dict) or not isinstance(item.get("start_bar"), int):
            raise ValueError("Trecho inválido na revisão auditiva")
        identifier = str(item.get("id") or "").strip()
        first = item["start_bar"]
        length = int(item.get("bars", 0))
        last = first + length - 1
        if not identifier or identifier in identifiers or length < 1:
            raise ValueError("Identificador ou duração inválida na revisão auditiva")
        if stable_loop and length != loop_bars:
            raise ValueError("Loops estáveis devem ter a duração indicada por loop_bars")
        if not any(start <= first and last < start + pattern_length for start in starts):
            raise ValueError("Trecho auditivo fora das ocorrências do padrão")
        covered = set(range(first, last + 1))
        if covered & occupied or any(number not in by_number for number in covered):
            raise ValueError("Trechos auditivos ausentes ou sobrepostos")
        occupied.update(covered)
        identifiers.add(identifier)
        result = {"id": identifier, "start_bar": first, "end_bar": last, "bars": length,
                  "source_start_seconds": float(by_number[first]["start_seconds"]),
                  "source_end_seconds": float(by_number[last]["end_seconds"]),
                  "review_source": review.get("source", "manual_listening")}
        if not stable_loop:
            result["status"] = "contains_turn_location_unresolved"
            result["possible_role"] = "FILL"
        else:
            result["status"] = "stable_main_a"
        return result

    stable_rows = [resolve(item, True) for item in stable]
    candidate_rows = [resolve(item, False) for item in candidates]
    entry_excerpt = review.get("initial_turn_excerpt")
    entry_row = None
    if entry_excerpt is not None:
        if not isinstance(entry_excerpt, dict) or not isinstance(entry_excerpt.get("start_bar"), int):
            raise ValueError("Trecho inicial inválido na revisão auditiva")
        first = entry_excerpt["start_bar"]
        length = int(entry_excerpt.get("bars", 0))
        last = first + length - 1
        if length < 1 or not any(row["start_bar"] <= first and last <= row["end_bar"]
                                     for row in candidate_rows):
            raise ValueError("A entrada deve estar dentro de uma região candidata")
        entry_row = {"id": str(entry_excerpt.get("id") or "entry_turn"),
                     "start_bar": first, "end_bar": last, "bars": length,
                     "source_start_seconds": float(by_number[first]["start_seconds"]),
                     "source_end_seconds": float(by_number[last]["end_seconds"]),
                     "status": "single_entry_excerpt_not_localized_fill",
                     "review_source": review.get("source", "manual_listening")}
    drums = (pattern.get("roles") or {}).get("drums")
    if not drums:
        raise ValueError("Padrão MAIN A sem stem drums")
    drums["audited_continuous_loops"] = {
        "status": "manual_listening_review", "loop_bars": loop_bars,
        "stable_main_a": stable_rows,
        "transition_candidates": candidate_rows,
        "initial_turn_excerpt": entry_row,
        "note": "Candidate regions are not full FILL sections until the turn is localized.",
    }
    relative_bass = review.get("bass_relative_pattern")
    if relative_bass is not None:
        bass = (pattern.get("roles") or {}).get("bass")
        if (not bass or not isinstance(relative_bass, dict)
                or relative_bass.get("status") != "confirmed"
                or [event.get("degree") for event in relative_bass.get("events", [])] != [1, 3, 5]):
            raise ValueError("Padrão de baixo confirmado inválido na revisão auditiva")
        bass["relative_pattern"] = copy.deepcopy(relative_bass)
    style_pack["version"] = "2.2"
    return style_pack
