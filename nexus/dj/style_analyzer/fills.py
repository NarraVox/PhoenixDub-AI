"""Detect and group drum fills from 16-step, three-band stem signatures."""
from __future__ import annotations

import math
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


BANDS = {"low": (35, 160), "mid": (160, 2500), "high": (2500, 10000)}
STEPS = 16


def _cosine(a, b):
    a, b = np.asarray(a).ravel(), np.asarray(b).ravel()
    return float(a @ b / max(float(np.linalg.norm(a) * np.linalg.norm(b)), 1e-9))


def _section_type(bar, sections):
    midpoint = (bar["start_seconds"] + bar["end_seconds"]) / 2
    for section in sections:
        if (section.get("status") == "detected" and
                section.get("start_seconds", math.inf) <= midpoint < section.get("end_seconds", -math.inf)):
            return section.get("label")
    return None


def _signatures(path, bars):
    audio, sr = sf.read(str(path), dtype="float32", always_2d=True)
    mono = audio.mean(axis=1)
    if not len(mono) or not np.isfinite(mono).all():
        raise ValueError("Stem drums inválido para detectar fills")
    # Keep the analysis window near 50 ms at both production and test rates;
    # a fixed 2048-point window at 8 kHz smears attacks into prior grid steps.
    n_fft = 2 ** round(math.log2(sr * .05))
    hop = min(256, n_fft // 4)
    spectrum = np.abs(librosa.stft(mono, n_fft=n_fft, hop_length=hop))
    hz = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    flux = []
    for low, high in BANDS.values():
        band = spectrum[(hz >= low) & (hz < min(high, sr / 2))]
        flux.append(np.maximum(np.diff(band, axis=1, prepend=band[:, :1]), 0).mean(axis=0))
    flux = np.stack(flux, axis=-1)
    times = librosa.frames_to_time(np.arange(len(flux)), sr=sr, hop_length=hop)
    values, peaks, rms = [], [], []
    for bar in bars:
        start, end = float(bar["start_seconds"]), float(bar["end_seconds"])
        edges = np.linspace(start, end, STEPS + 1)
        row, row_peaks = [], []
        for left, right in zip(edges[:-1], edges[1:]):
            lo, hi = np.searchsorted(times, [left, right])
            window = flux[lo:hi]
            if len(window):
                row.append(window.max(axis=0))
                row_peaks.append(float(times[lo + np.argmax(window.sum(axis=1))]))
            else:
                row.append(np.zeros(len(BANDS)))
                row_peaks.append(float(left))
        values.append(row)
        peaks.append(row_peaks)
        chunk = mono[max(0, round(start * sr)):min(len(mono), round(end * sr))]
        rms.append(float(np.sqrt(np.mean(chunk * chunk))) if len(chunk) else 0.0)
    return np.asarray(values, dtype=np.float32), np.asarray(peaks), np.asarray(rms)


def detect_fills(stem_path, bars, sections, review=None):
    """Return explainable fills; confidence is a heuristic, not calibrated probability.

    A fill must add attacks/spectral activity, depart from a robust recurrent
    MAIN template, and return to MAIN within two bars. Low-energy BREAKs and
    unreturned endings are kept as rejected candidates, not named fills.
    """
    if review is not None and (not isinstance(review, dict) or review.get("version") != 1):
        raise ValueError("Revisão auditiva de fills inválida")
    confirmed_regions = {
        (int(item["start_bar"]), int(item["end_bar"]))
        for item in (review or {}).get("confirmed_regions", [])
    }
    if len(bars) < 4:
        return {"status": "insufficient_bars", "fills": [], "clusters": [], "bar_signatures": []}
    raw, peak_times, rms = _signatures(Path(stem_path), bars)
    scale = np.maximum(np.percentile(raw.reshape(-1, len(BANDS)), 75, axis=0), 1e-8)
    normalized = np.log1p(raw / scale)
    section_types = [_section_type(bar, sections) for bar in bars]
    reference_indices = [i for i, label in enumerate(section_types) if label == "MAIN A"]
    if len(reference_indices) < 8:
        reference_indices = [i for i, label in enumerate(section_types)
                             if label not in {"INTRO", "ENDING", "BREAK"}]
    if len(reference_indices) < 8:
        return {"status": "insufficient_main_reference", "fills": [], "clusters": [],
                "bar_signatures": []}
    reference_energy = float(np.median(rms[reference_indices]))
    prototypes = []
    for phase in range(4):
        candidates = [i for i in reference_indices if (int(bars[i]["bar"]) - 1) % 4 == phase]
        if len(candidates) < 2:
            candidates = reference_indices
        prototypes.append(np.median(normalized[candidates], axis=0))
    prototypes = np.asarray(prototypes)

    measurements = []
    for i, (bar, row) in enumerate(zip(bars, normalized)):
        main = prototypes[(int(bar["bar"]) - 1) % 4]
        similarity = _cosine(row, main)
        strength = np.linalg.norm(row, axis=1)
        main_strength = np.linalg.norm(main, axis=1)
        extra = np.maximum(strength - main_strength * 1.4, 0)
        extra_ratio = float(extra.sum() / max(float(strength.sum()), 1e-9))
        unusual_steps = np.flatnonzero(extra > 0.35).tolist()
        attack_floor = max(0.65, float(np.max(strength)) * 0.3)
        attack_steps = np.flatnonzero(strength >= attack_floor).tolist()
        density = len(attack_steps)
        main_density = int(np.sum(main_strength >= max(0.65, float(np.max(main_strength)) * 0.3)))
        balance = row.sum(axis=0) / max(float(row.sum()), 1e-9)
        main_balance = main.sum(axis=0) / max(float(main.sum()), 1e-9)
        spectral_shift = float(np.abs(balance - main_balance).sum() / 2)
        density_shift = min(1.0, max(0.0, (density - main_density) / max(main_density, 1)))
        deviation = float(np.clip(.45 * (1 - similarity) / .4 + .30 * extra_ratio / .5
                                  + .15 * density_shift + .10 * spectral_shift, 0, 1))
        active = rms[i] >= reference_energy * .35
        eligible = (active and section_types[i] not in {"INTRO", "ENDING", "BREAK"}
                    and similarity < .88 and extra_ratio > .23 and len(unusual_steps) >= 3)
        measurements.append({"bar": int(bar["bar"]), "section_label": section_types[i],
                             "start_seconds": round(float(bar["start_seconds"]), 4),
                             "end_seconds": round(float(bar["end_seconds"]), 4),
                             "attack_steps": attack_steps, "attack_strength": np.round(strength, 3).tolist(),
                             "band_onsets": {name: np.round(raw[i, :, band], 4).tolist()
                                             for band, name in enumerate(BANDS)},
                             "spectral_balance": {name: round(float(balance[band]), 4)
                                                  for band, name in enumerate(BANDS)},
                             "density": density, "main_density": main_density,
                             "main_similarity": round(similarity, 4),
                             "extra_attack_ratio": round(extra_ratio, 4),
                             "unusual_steps": unusual_steps,
                             "spectral_shift": round(spectral_shift, 4),
                             "relative_rms": round(float(rms[i] / max(reference_energy, 1e-9)), 4),
                             "deviation": round(deviation, 4), "candidate_bar": eligible})

    candidates, rejected = [], []
    matched_reviews = set()
    i = 0
    while i < len(bars):
        if not measurements[i]["candidate_bar"]:
            i += 1
            continue
        first = i
        while i < len(bars) and measurements[i]["candidate_bar"]:
            i += 1
        last = i - 1
        return_indices = [j for j in range(i, min(len(bars), i + 2))
                          if measurements[j]["main_similarity"] >= .92
                          and measurements[j]["extra_attack_ratio"] <= .18
                          and measurements[j]["relative_rms"] >= .35]
        region = (int(bars[first]["bar"]), int(bars[last]["bar"]))
        human_confirmed = region in confirmed_regions
        if not return_indices and not human_confirmed or last - first + 1 > 4:
            rejected.append({"bars": [int(bars[first]["bar"]), int(bars[last]["bar"])],
                             "reason": "no_prompt_main_return" if not return_indices else "too_long_for_fill"})
            continue
        if human_confirmed:
            matched_reviews.add(region)
        first_bin = measurements[first]["unusual_steps"][0]
        end_step = measurements[last]["unusual_steps"][-1] + 1
        start_time = float(peak_times[first, first_bin])
        first_bar = bars[first]
        start_step = int(np.clip(round((start_time - first_bar["start_seconds"]) /
                                       (first_bar["end_seconds"] - first_bar["start_seconds"]) * STEPS),
                                 0, STEPS - 1))
        end_bar = bars[last]
        end_time = float(end_bar["start_seconds"] +
                         (end_bar["end_seconds"] - end_bar["start_seconds"]) * end_step / STEPS)
        if end_time <= start_time:
            continue
        phrase_end = int(bars[last]["bar"]) % 4 == 0
        mean_deviation = float(np.mean([measurements[j]["deviation"] for j in range(first, last + 1)]))
        confidence = float(np.clip(.40 + .32 * mean_deviation + .08 * phrase_end
                                   + .10 * bool(return_indices) + .05 * human_confirmed, 0, .90))
        candidates.append({"start_bar": int(bars[first]["bar"]),
                           "end_bar": int(bars[last]["bar"]),
                           "start_step": start_step, "end_step_exclusive": end_step,
                           "start_seconds": round(start_time, 4),
                           "end_seconds": round(end_time, 4),
                           "duration_seconds": round(end_time - start_time, 4),
                           "confidence": round(confidence, 3),
                           "confidence_kind": "heuristic_not_calibrated",
                           "human_confirmed": human_confirmed,
                           "mean_main_similarity": round(float(np.mean([
                               measurements[j]["main_similarity"] for j in range(first, last + 1)])), 4),
                           "mean_extra_attack_ratio": round(float(np.mean([
                               measurements[j]["extra_attack_ratio"] for j in range(first, last + 1)])), 4),
                           "phrase_end_bonus": phrase_end,
                           "main_returns_at_bar": int(bars[return_indices[0]]["bar"]) if return_indices else None,
                           "signature": normalized[first:last + 1]})

    clusters = []
    for candidate in candidates:
        fingerprint = candidate.pop("signature")
        matched = None
        for cluster in clusters:
            if (cluster["length_bars"] == len(fingerprint)
                    and _cosine(fingerprint, cluster["fingerprint"]) >= .94):
                matched = cluster
                break
        if matched is None:
            matched = {"length_bars": len(fingerprint), "fingerprint": fingerprint,
                       "occurrences": []}
            clusters.append(matched)
        candidate["cluster_similarity"] = round(_cosine(fingerprint, matched["fingerprint"]), 4)
        matched["occurrences"].append(candidate)
        matched["fingerprint"] = np.mean([
            normalized[row["start_bar"] - 1:row["end_bar"]]
            for row in matched["occurrences"]], axis=0)

    # A one-bar turnaround may repeat only the tail of a longer fill. Keep
    # its exact duration/timestamps, but avoid inventing a separate fill type
    # when the same three-band attack motif is exceptionally close.
    for shorter in list(clusters):
        if not any(cluster is shorter for cluster in clusters):
            continue
        best = None
        for longer in clusters:
            if longer is shorter or longer["length_bars"] <= shorter["length_bars"]:
                continue
            for offset in range(longer["length_bars"] - shorter["length_bars"] + 1):
                window = longer["fingerprint"][offset:offset + shorter["length_bars"]]
                similarity = _cosine(shorter["fingerprint"], window)
                if similarity >= .96 and (best is None or similarity > best[0]):
                    best = similarity, longer, offset
        if best is None:
            continue
        similarity, longer, offset = best
        for item in shorter["occurrences"]:
            item["cluster_similarity"] = round(_cosine(
                normalized[item["start_bar"] - 1:item["end_bar"]],
                longer["fingerprint"][offset:offset + shorter["length_bars"]]), 4)
            item["variant"] = ("tail_only" if offset + shorter["length_bars"] == longer["length_bars"]
                               else "head_only" if offset == 0 else "partial")
            longer["occurrences"].append(item)
        clusters = [cluster for cluster in clusters if cluster is not shorter]
    clusters.sort(key=lambda cluster: min(item["start_seconds"] for item in cluster["occurrences"]))

    named = []
    for index, cluster in enumerate(clusters):
        number = index + 1
        suffix = ""
        while number:
            number, digit = divmod(number - 1, 26)
            suffix = chr(65 + digit) + suffix
        label = f"FILL_{suffix}"
        for item in cluster["occurrences"]:
            item["label"] = label
            if len(cluster["occurrences"]) > 1:
                item["confidence"] = round(min(.95, item["confidence"] + .06), 3)
        named.append({"id": label, "length_bars": cluster["length_bars"],
                      "occurrence_count": len(cluster["occurrences"]),
                      "occurrences": sorted(cluster["occurrences"], key=lambda item: item["start_seconds"]),
                      "prototype_band_onsets": np.round(cluster["fingerprint"], 3).tolist(),
                      "clustering_threshold": .94, "partial_motif_threshold": .96})
    return {"status": "detected", "method": "16-step spectral-onset deviation from recurrent MAIN",
            "source_stem": str(Path(stem_path).resolve()),
            "thresholds": {"main_similarity_max": .88, "extra_attack_ratio_min": .23,
                           "unusual_step_excess_min": .35, "unusual_step_count_min": 3,
                           "main_return_similarity_min": .92, "cluster_similarity_min": .94,
                           "partial_motif_similarity_min": .96},
            "bar_signatures": measurements, "fills": [item for cluster in named
                                                        for item in cluster["occurrences"]],
            "clusters": named, "rejected_candidates": rejected,
            "review_source": (review or {}).get("source"),
            "unmatched_review_regions": [list(region) for region in sorted(confirmed_regions - matched_reviews)],
            "limitations": ["Confidence is heuristic, not calibrated.",
                            "Boundaries are localized to the 16-step grid and onset frames; sustain tails may extend beyond them.",
                            "A fill without a prompt return to MAIN requires an explicit human listening review."]}
