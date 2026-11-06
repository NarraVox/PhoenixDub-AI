"""Phrase-level groove grouping and context-aware section candidates."""
import numpy as np


def _unit(vector):
    vector = np.asarray(vector, dtype=np.float32)
    return vector / max(float(np.linalg.norm(vector)), 1e-9)


def _bar_signatures(features):
    rms = np.log1p(np.asarray([max(0.0, bar.get("rms", 0.0)) for bar in features]))
    density = np.asarray([max(0.0, bar.get("density", 0)) for bar in features], dtype=float)
    rms_scale = float(np.percentile(rms, 85)) if len(rms) else 1.0
    den_scale = float(np.percentile(density, 85)) if len(density) else 1.0
    signatures = []
    for i, bar in enumerate(features):
        spectral = _unit(bar.get("vector", []))
        # Preserve the established spectral flux shape and add modest energy/attack evidence.
        auxiliary = np.asarray([min(1.0, rms[i] / max(rms_scale, 1e-9)),
                                min(1.0, density[i] / max(den_scale, 1.0))], dtype=np.float32)
        signatures.append(_unit(np.r_[spectral * 0.92, auxiliary * 0.28]))
    return np.asarray(signatures), rms, density


def _phrase_groups(signatures):
    """Find recurring non-overlapping 2/4/8-bar phrases by whole-sequence similarity."""
    count = len(signatures)
    groups = []
    for length in (8, 4, 2):
        if count < length * 2:
            continue
        sequences = np.asarray([_unit(signatures[i:i + length].reshape(-1))
                                for i in range(count - length + 1)])
        threshold = {2: 0.94, 4: 0.92, 8: 0.90}[length]
        representatives = []
        for start, vector in enumerate(sequences):
            if any(float(vector @ rep["vector"]) >= threshold for rep in representatives):
                continue
            similarities = sequences @ vector
            occurrences = []
            for candidate, similarity in enumerate(similarities):
                if similarity < threshold:
                    continue
                if occurrences and candidate < occurrences[-1] + length:
                    continue
                occurrences.append(candidate)
            if len(occurrences) >= 2:
                representatives.append({"length_bars": length, "source_index": start,
                                        "vector": vector, "occurrences": occurrences,
                                        "similarities": [float(similarities[i]) for i in occurrences],
                                        "threshold": threshold})
        for group in representatives:
            groups.append(group)

    # Reduce a longer window to its repeated subphrase when both halves carry the same motif.
    for group in groups:
        for shorter, threshold in ((4, 0.92), (2, 0.94)):
            if group["length_bars"] != shorter * 2:
                continue
            repeated_halves = all(
                float(_unit(signatures[start:start + shorter].reshape(-1)) @
                      _unit(signatures[start + shorter:start + shorter * 2].reshape(-1))) >= threshold
                for start in group["occurrences"])
            if repeated_halves:
                group["length_bars"] = shorter
                group["threshold"] = threshold
                group["vector"] = _unit(signatures[group["source_index"]:
                                                     group["source_index"] + shorter].reshape(-1))
                group["similarities"] = [float(group["vector"] @
                                                _unit(signatures[start:start + shorter].reshape(-1)))
                                          for start in group["occurrences"]]
    unique_groups = {}
    for group in groups:
        key = (group["length_bars"], tuple(group["occurrences"]))
        unique_groups.setdefault(key, group)
    groups = list(unique_groups.values())

    # Favor longer musical phrases, with recurrence and similarity as tie-breakers.
    groups.sort(key=lambda g: (g["length_bars"], len(g["occurrences"]),
                               float(np.mean(g["similarities"]))), reverse=True)
    selected = []
    occupied = set()
    for group in groups:
        available = [start for start in group["occurrences"]
                     if not any(i in occupied for i in range(start, start + group["length_bars"]))]
        if len(available) < 2:
            continue
        similarity_by_start = dict(zip(group["occurrences"], group["similarities"]))
        group = {**group, "occurrences": available,
                 "similarities": [similarity_by_start[start] for start in available]}
        selected.append(group)
        for start in available:
            occupied.update(range(start, start + group["length_bars"]))
        if len(selected) == 2:
            break
    return selected


def _trend(values):
    if len(values) < 2 or max(values, default=0) <= 1e-9:
        return 0.0
    x = np.arange(len(values), dtype=float)
    return float(np.polyfit(x, np.asarray(values, dtype=float), 1)[0] /
                 (np.mean(values) + 1e-9))


def classify(features, grid_confidence, duration):
    if not features:
        return [], [], {"phrase_groups": [], "thresholds": {}}
    signatures, energy, density = _bar_signatures(features)
    n = len(features)
    energy_floor = float(np.percentile(energy[energy > 1e-8], 60)) if np.any(energy > 1e-8) else 0.0
    active = energy > max(1e-7, energy_floor * 0.18)
    groups = _phrase_groups(signatures)
    groups.sort(key=lambda group: min(group["occurrences"]))

    labels = [None] * n
    catalog = []
    phrase_debug = []
    for rank, group in enumerate(groups):
        label = "MAIN A" if rank == 0 else "MAIN B"
        pid = f"P{rank + 1}"
        confidence_by_occurrence = []
        for start, similarity in zip(group["occurrences"], group["similarities"]):
            repeat_evidence = min(1.0, len(group["occurrences"]) / 3.0)
            confidence = float(np.clip(0.20 * grid_confidence + 0.55 * similarity +
                                       0.25 * repeat_evidence, 0, 1))
            confidence_by_occurrence.append(round(confidence, 3))
            for index in range(start, start + group["length_bars"]):
                labels[index] = {"type": "MAIN", "label": label, "pattern_id": pid,
                                 "confidence": confidence,
                                 "reason": "Frase recorrente comparada como sequência completa de compassos",
                                 "evidence": {"phrase_length_bars": group["length_bars"],
                                              "phrase_similarity": round(similarity, 4),
                                              "repetitions": len(group["occurrences"]),
                                              "grid_confidence": round(float(grid_confidence), 3)}}
        source = group["source_index"]
        catalog.append({"id": pid, "label": label, "length_bars": group["length_bars"],
                        "occurrences": len(group["occurrences"]),
                        "occurrence_bars": [i + 1 for i in group["occurrences"]],
                        "source_bar": source + 1,
                        "start_seconds": features[source]["start_seconds"],
                        "end_seconds": features[source + group["length_bars"] - 1]["end_seconds"],
                        "confidence": round(float(np.mean(confidence_by_occurrence)), 3)})
        phrase_debug.append({"label": label, "length_bars": group["length_bars"],
                             "occurrence_bars": [i + 1 for i in group["occurrences"]],
                             "similarities": [round(x, 4) for x in group["similarities"]],
                             "threshold": group["threshold"]})

    main_indices = [i for i, label in enumerate(labels) if label and label["type"] == "MAIN"]
    main_set = set(main_indices)
    active_values = energy[active]
    reference_energy = float(np.median(active_values)) if len(active_values) else 0.0
    reference_density = float(np.median(density[active])) if np.any(active) else 0.0
    nearest_main = np.zeros(n, dtype=float)
    for i in range(n):
        if main_indices:
            nearest_main[i] = max(float(signatures[i] @ signatures[j]) for j in main_indices)

    # Breaks require a short low-drum run, active context on both sides, and a return.
    i = 0
    while i < n:
        if i in main_set or energy[i] > max(reference_energy * 0.20, 1e-7) or density[i] > max(reference_density * 0.25, 1):
            i += 1
            continue
        start = i
        while i < n and i not in main_set and energy[i] <= max(reference_energy * 0.20, 1e-7) and density[i] <= max(reference_density * 0.25, 1):
            i += 1
        end = i
        before = start > 0 and any(active[max(0, start - 4):start])
        after = end < n and any(active[end:min(n, end + 4)])
        returned_main = end < n and any(j in main_set for j in range(end, min(n, end + 5)))
        length = end - start
        if before and after and returned_main and 1 <= length <= 4:
            for j in range(start, end):
                silence = float(np.clip(1 - energy[j] / max(reference_energy * 0.20, 1e-7), 0, 1))
                confidence = float(np.clip(0.15 * grid_confidence + 0.38 * silence +
                                           0.22 * (1.0 if before and after else 0.0) +
                                           0.25 * (1.0 if returned_main else 0.0), 0, 1))
                labels[j] = {"type": "BREAK", "label": "BREAK", "pattern_id": None,
                             "confidence": confidence,
                             "reason": "Queda de bateria curta, com atividade antes e retorno ao groove",
                             "evidence": {"relative_energy": round(float(energy[j] / max(reference_energy, 1e-9)), 4),
                                          "before_active": True, "after_active": True,
                                          "return_to_main": True, "duration_bars": length}}

    # Fill: a brief deviation near a phrase end with denser/different attacks and a Main return.
    for i in range(1, n - 1):
        if labels[i] is not None or not active[i]:
            continue
        prev_main = labels[i - 1] if labels[i - 1] and labels[i - 1]["type"] == "MAIN" else None
        next_indices = [j for j in range(i + 1, min(n, i + 3))
                        if labels[j] and labels[j]["type"] == "MAIN"]
        if not prev_main or not next_indices:
            continue
        novelty = float(np.clip(1 - max(float(signatures[i] @ signatures[i - 1]),
                                        float(signatures[i] @ signatures[next_indices[0]])), 0, 1))
        density_ratio = float((density[i] + 1) / (reference_density + 1))
        phrase_position = (i + 1) % 4 in (0, 3) or (i + 1) % 8 in (0, 7)
        density_change = density_ratio >= 1.30
        if novelty < 0.20 or not (density_change or novelty >= 0.35) or not phrase_position:
            continue
        return_label = labels[next_indices[0]]["label"]
        novelty_evidence = float(np.clip(novelty / 0.45, 0, 1))
        density_evidence = float(np.clip(abs(np.log(max(density_ratio, 1e-6))) / 0.8, 0, 1))
        confidence_parts = {"grid": 0.12 * float(grid_confidence),
                            "pattern_change": 0.32 * novelty_evidence,
                            "attack_change": 0.18 * density_evidence,
                            "phrase_position": 0.18,
                            "return_to_main": 0.20}
        confidence = float(np.clip(sum(confidence_parts.values()), 0, 1))
        labels[i] = {"type": "FILL", "label": f"FILL {return_label[-1]}", "pattern_id": None,
                     "confidence": confidence,
                     "reason": "Desvio curto no fim de frase, com mudança de ataques e retorno a seção recorrente",
                     "evidence": {"change_strength": round(novelty, 4),
                                  "attack_density_ratio": round(density_ratio, 4),
                                  "phrase_end": True, "duration_bars": 1,
                                  "return_to_main": return_label,
                                  "confidence_components": {k: round(v, 4) for k, v in confidence_parts.items()}}}

    # Intro/ending require a low or developing drum stem relative to the first/last Main.
    if main_indices:
        first_main, last_main = min(main_indices), max(main_indices)
        if 0 < first_main <= 8:
            intro_energy = energy[:first_main]
            ratio = float(np.median(intro_energy) / max(reference_energy, 1e-9))
            rising = _trend(intro_energy) >= 0.12
            inactive = float(np.mean(~active[:first_main])) >= 0.5
            if (ratio <= 0.58 and (rising or inactive)):
                conf = float(np.clip(0.20 * grid_confidence + 0.35 * (1 - ratio) +
                                     0.25 * float(rising) + 0.20 * float(inactive), 0, 1))
                for j in range(first_main):
                    if labels[j] is None:
                        labels[j] = {"type": "INTRO", "label": "INTRO", "pattern_id": None,
                                     "confidence": conf, "reason": "Entrada anterior ao primeiro Main com bateria reduzida/progressiva",
                                     "evidence": {"relative_energy": round(ratio, 4), "energy_rising": rising,
                                                  "drum_absence_fraction": round(float(np.mean(~active[:first_main])), 3),
                                                  "before_first_main": True}}
        trailing = n - 1 - last_main
        if 0 < trailing <= 8:
            outro_energy = energy[last_main + 1:]
            ratio = float(np.median(outro_energy) / max(reference_energy, 1e-9))
            falling = _trend(outro_energy) <= -0.12
            inactive = float(np.mean(~active[last_main + 1:])) >= 0.5
            if ratio <= 0.58 and (falling or inactive):
                conf = float(np.clip(0.20 * grid_confidence + 0.35 * (1 - ratio) +
                                     0.25 * float(falling) + 0.20 * float(inactive), 0, 1))
                for j in range(last_main + 1, n):
                    if labels[j] is None:
                        labels[j] = {"type": "ENDING", "label": "ENDING", "pattern_id": None,
                                     "confidence": conf, "reason": "Saída após o último Main com bateria reduzida/progressiva",
                                     "evidence": {"relative_energy": round(ratio, 4), "energy_falling": falling,
                                                  "drum_absence_fraction": round(float(np.mean(~active[last_main + 1:])), 3),
                                                  "after_last_main": True}}

    # Preserve partial measures around the detected grid as UNKNOWN evidence.
    raw_sections = []
    for i, feature in enumerate(features):
        item = labels[i] or {"type": "UNKNOWN", "label": "UNKNOWN", "pattern_id": None,
                             "confidence": float(grid_confidence),
                             "reason": "Sem repetição ou contexto suficientes para classificar",
                             "evidence": {"nearest_main_similarity": round(float(nearest_main[i]), 4),
                                          "relative_energy": round(float(energy[i] / max(reference_energy, 1e-9)), 4),
                                          "active_drum": bool(active[i])}}
        accepted = item["type"] == "UNKNOWN" or item["confidence"] >= 0.65
        final_type = item["type"] if accepted else "UNKNOWN"
        raw_sections.append({"type": final_type,
                             "candidate_type": item["label"],
                             "label": (item["label"] if final_type != "UNKNOWN" else
                                       (item["label"] + " ?" if item["type"] != "UNKNOWN" else "Não classificado")),
                             "status": "detected" if final_type != "UNKNOWN" else ("candidate" if item["type"] != "UNKNOWN" else "unknown"),
                             "start_bar": i + 1, "duration_bars": 1,
                             "pattern_id": item["pattern_id"],
                             "start_seconds": feature["start_seconds"],
                             "end_seconds": feature["end_seconds"],
                             "confidence": round(float(item["confidence"]), 3),
                             "reason": item["reason"], "evidence": item["evidence"]})

    sections = []
    for section in raw_sections:
        key = (section["type"], section["candidate_type"], section["pattern_id"])
        if sections and key == (sections[-1]["type"], sections[-1]["candidate_type"], sections[-1]["pattern_id"]):
            prev = sections[-1]
            prev["end_seconds"] = section["end_seconds"]
            prev["duration_bars"] += 1
            prev["confidence"] = round(min(prev["confidence"], section["confidence"]), 3)
            prev["evidence"].setdefault("merged_bar_evidence", []).append(section["evidence"])
        else:
            sections.append(dict(section))

    partials = [(0.0, features[0]["start_seconds"], "partial_before_grid"),
                (features[-1]["end_seconds"], duration, "partial_after_grid")]
    for start, end, why in partials:
        if end - start > 0.03:
            sections.append({"type": "UNKNOWN", "candidate_type": "UNKNOWN", "label": "Trecho parcial",
                             "status": "unknown", "start_bar": None, "duration_bars": None,
                             "pattern_id": None, "start_seconds": start, "end_seconds": end,
                             "confidence": 0.0, "reason": "Trecho fora dos compassos completos da grade",
                             "evidence": {"kind": why}})
    sections.sort(key=lambda section: section["start_seconds"])
    debug = {"phrase_groups": phrase_debug,
             "bar_evidence": [{"bar": i + 1, "relative_energy": round(float(energy[i] / max(reference_energy, 1e-9)), 4),
                               "attack_density": float(density[i]), "active_drum": bool(active[i]),
                               "nearest_main_similarity": round(float(nearest_main[i]), 4)} for i in range(n)],
             "energy_baseline": reference_energy,
             "thresholds": {"phrase_similarity": {"2_bars": 0.94, "4_bars": 0.92, "8_bars": 0.90},
                            "fill_min_change": 0.20, "fill_density_ratio": 1.30,
                            "break_relative_energy": 0.20, "edge_relative_energy": 0.58}}
    return catalog, sections, debug
