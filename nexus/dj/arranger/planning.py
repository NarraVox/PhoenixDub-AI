"""Create an original, symbolic arrangement plan from a Nexus style.json.

This MVP deliberately emits harmonic degrees and performance roles rather than
reference note events. Audio rendering is left to a future YuE2 handoff.
"""
import hashlib
import json
import math
import re


NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
NOTE_TO_PC = {name: pitch for pitch, name in enumerate(NOTE_NAMES)}
NOTE_TO_PC.update({"Db": 1, "Eb": 3, "Gb": 6, "Ab": 8, "Bb": 10})

_MAJOR_QUALITIES = {1: "", 2: "m", 3: "m", 4: "", 5: "", 6: "m", 7: "dim"}
_MINOR_QUALITIES = {1: "m", 2: "dim", 3: "", 4: "m", 5: "", 6: "", 7: ""}
_MAJOR_INTERVALS = (0, 2, 4, 5, 7, 9, 11)
_MINOR_INTERVALS = (0, 2, 3, 5, 7, 8, 10)


def _key_parts(key):
    if isinstance(key, dict):
        symbol = key.get("symbol")
        root = key.get("root")
        mode = key.get("mode")
    else:
        symbol, root, mode = key, None, None
    match = re.match(r"^([A-G](?:#|b)?)(.*)$", str(symbol or ""))
    if match:
        root = root or match.group(1)
        if mode not in {"major", "minor"}:
            mode = "minor" if match.group(2).lower().startswith("m") else "major"
    if root not in NOTE_TO_PC:
        return None, mode if mode in {"major", "minor"} else None, symbol
    return NOTE_TO_PC[root], mode if mode in {"major", "minor"} else "major", symbol


def _seed_for(style, seed):
    if seed is not None:
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 0xFFFFFFFF:
            raise ValueError("seed deve ser um inteiro entre 0 e 4294967295")
        return seed
    canonical = json.dumps(style, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return int(hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:8], 16)


def _tempo_and_meter(style):
    source = style.get("source_analysis") if isinstance(style.get("source_analysis"), dict) else {}
    consensus = style.get("rhythm_consensus") if isinstance(style.get("rhythm_consensus"), dict) else {}
    bpm = consensus.get("bpm") or source.get("bpm") or source.get("tempo_estimate")
    try:
        bpm = float(bpm)
    except (TypeError, ValueError):
        bpm = 120.0
        bpm_source = "arranger_default"
    else:
        bpm_source = "rhythm_consensus" if consensus.get("bpm") else "style_source_analysis"
        if not math.isfinite(bpm) or not 40 <= bpm <= 240:
            raise ValueError("BPM do style.json deve estar entre 40 e 240")
    meter = consensus.get("meter") or source.get("meter") or "4/4"
    match = re.fullmatch(r"([2-7])/4", str(meter))
    if not match:
        meter = "4/4"
        meter_source = "arranger_default_unsupported_meter"
    else:
        meter_source = "rhythm_consensus" if consensus.get("meter") else "style_source_analysis"
    return round(bpm, 3), meter, int(meter.split("/")[0]), bpm_source, meter_source


def _new_key(style, seed):
    harmony = style.get("harmony") if isinstance(style.get("harmony"), dict) else {}
    source_pc, mode, source_symbol = _key_parts(harmony.get("key"))
    source_pcs = set()
    if source_pc is not None:
        source_pcs.add(source_pc)
    for change in harmony.get("key_changes", []):
        pc, _, _ = _key_parts(change.get("key")) if isinstance(change, dict) else (None, None, None)
        if pc is not None:
            source_pcs.add(pc)
    if mode is None:
        mode = "major"
    if source_pc is None:
        source_pc = seed % 12
        source_symbol = None
        source_pcs.add(source_pc)
    candidates = [pc for pc in range(12) if pc not in source_pcs]
    if not candidates:
        candidates = [(source_pc + offset) % 12 for offset in range(1, 12)]
    new_pc = candidates[seed % len(candidates)]
    return {"root": NOTE_NAMES[new_pc], "mode": mode,
            "symbol": NOTE_NAMES[new_pc] + ("m" if mode == "minor" else ""),
            "source_key_reference": source_symbol,
            "transposition_semitones": (new_pc - source_pc) % 12}


def _chord_for_degree(key_pc, mode, degree, seventh=False):
    if mode == "minor":
        intervals, qualities = _MINOR_INTERVALS, _MINOR_QUALITIES
    else:
        intervals, qualities = _MAJOR_INTERVALS, _MAJOR_QUALITIES
    root = NOTE_NAMES[(key_pc + intervals[degree - 1]) % 12]
    quality = qualities[degree]
    suffix = "7" if seventh and quality == "" else quality
    return root + suffix


def _phrase_lengths(style):
    patterns = (style.get("drums") or {}).get("patterns", [])
    lengths = {}
    for pattern in patterns:
        if not isinstance(pattern, dict):
            continue
        label = str(pattern.get("label", "")).upper()
        try:
            length = int(pattern.get("length_bars", 0))
        except (TypeError, ValueError):
            continue
        if label in {"MAIN A", "MAIN B"} and 4 <= length <= 16:
            lengths[label] = length
    return lengths.get("MAIN A", 8), lengths.get("MAIN B", lengths.get("MAIN A", 8))


def _harmony_bars(key_pc, mode, degrees, bars, section_type):
    chords = []
    for index in range(bars):
        degree = degrees[(index * len(degrees)) // bars] if bars >= len(degrees) else degrees[index % len(degrees)]
        is_fill = section_type.startswith("FILL")
        chords.append({"bar_offset": index + 1, "scale_degree": degree,
                       "chord": _chord_for_degree(key_pc, mode, degree, seventh=is_fill),
                       "source": "new_diatonic_template"})
    return chords


def _song_sections(style, song_plan, main_a_bars, main_b_bars):
    requested = song_plan.get("sections") if isinstance(song_plan, dict) else None
    if requested:
        if not isinstance(requested, list):
            raise ValueError("song.sections precisa ser uma lista")
        result = []
        for item in requested:
            if not isinstance(item, dict):
                raise ValueError("Cada seção da nova música precisa ser um objeto")
            kind = str(item.get("type", "")).strip().upper()
            bars = item.get("bars")
            if kind not in {"INTRO", "MAIN A", "MAIN B", "FILL A", "FILL B", "BREAK", "ENDING", "VARIATION"}:
                raise ValueError(f"Tipo de seção não suportado: {kind}")
            if isinstance(bars, bool) or not isinstance(bars, int) or bars < 1 or bars > 64:
                raise ValueError("Cada seção deve ter de 1 a 64 compassos")
            result.append({"type": kind, "bars": bars,
                           "energy": float(item.get("energy", 0.7)),
                           "chords": item.get("chords")})
        if not result:
            raise ValueError("Informe ao menos uma seção para a nova música")
        return result

    pack = style.get("style_pack") or {}
    form = pack.get("form") or []
    accepted = [item for item in form if item.get("status") == "detected"
                and item.get("type") in {"INTRO", "MAIN A", "MAIN B", "FILL A", "FILL B", "BREAK", "ENDING", "VARIATION"}
                and isinstance(item.get("bars"), int) and item["bars"] > 0]
    if accepted:
        return [{"type": item["type"], "bars": item["bars"],
                 "energy": 0.7, "chords": None, "source_pattern_id": item.get("pattern_id"),
                 "source_confidence": item.get("confidence")} for item in accepted]
    raise ValueError("O Style não contém seções detectadas; informe song.sections para definir a forma sem inventar seções")


def _style_template(style, section_type):
    pack = style.get("style_pack") or {}
    def has_events(item):
        return any(profile.get("attack_probability") or profile.get("attack_steps")
                   for profile in (item.get("roles") or {}).values())
    matches = [item for item in pack.get("patterns", [])
               if item.get("label") == section_type and has_events(item)]
    matches += [item for item in pack.get("form", [])
                if item.get("type") == section_type and item.get("roles") and has_events(item)]
    return matches[0] if matches else None


def _audited_entry_template(style):
    for pattern in (style.get("style_pack") or {}).get("patterns", []):
        review = ((pattern.get("roles") or {}).get("drums") or {}).get("audited_continuous_loops") or {}
        if pattern.get("label") == "MAIN A" and review.get("initial_turn_excerpt"):
            return pattern
    return None


def _section_chords(item, key_pc, mode, defaults):
    bars = item["bars"]
    supplied = item.get("chords")
    if supplied is None:
        return _harmony_bars(key_pc, mode, defaults[item["type"]], bars, item["type"])
    if not isinstance(supplied, list) or not supplied:
        raise ValueError(f"{item['type']}: chords deve ser uma lista não vazia")
    if len(supplied) not in {1, bars}:
        raise ValueError(f"{item['type']}: forneça um acorde ou exatamente um acorde por compasso")
    expanded = supplied * bars if len(supplied) == 1 else supplied
    result = []
    for offset, chord in enumerate(expanded, start=1):
        if isinstance(chord, dict):
            chord = chord.get("chord")
        if not isinstance(chord, str) or not re.fullmatch(r"[A-G](?:#|b)?(?:m|dim|aug|sus2|sus4)?\d{0,2}", chord):
            raise ValueError(f"Acorde inválido no compasso {offset}: {chord!r}")
        result.append({"bar_offset": offset, "chord": chord, "source": "new_song_request"})
    return result


def _chord_pitches(chord):
    match = re.match(r"^([A-G](?:#|b)?)(.*)$", chord)
    root = NOTE_TO_PC.get(match.group(1), 0) if match else 0
    quality = match.group(2).lower() if match else ""
    third = 3 if quality.startswith("m") or "dim" in quality else 4
    return root, third


def _template_events(profile, template_bar):
    if not profile:
        return []
    length = int(profile.get("length_bars", 1) or 1)
    bar = ((template_bar - 1) % length) + 1
    if profile.get("stem") == "drums":
        return [dict(event) for event in profile.get("attack_steps", []) if event.get("bar_offset") == bar]
    probability = profile.get("attack_probability", [])
    strength = profile.get("attack_strength", [])
    substeps = profile.get("attack_substep", [])
    first = (bar - 1) * 16
    return [{"step": step, "probability": probability[first + step],
             "strength": strength[first + step] if first + step < len(strength) else 0.0,
             "substep": substeps[first + step] if first + step < len(substeps) else 0}
            for step in range(16) if first + step < len(probability) and probability[first + step] >= .5]


def _adapt_performance(pattern, section_type, harmony_bars, bar_count):
    roles = (pattern or {}).get("roles", {})
    output = []
    for bar_offset in range(1, bar_count + 1):
        chord = harmony_bars[bar_offset - 1]["chord"]
        root, third = _chord_pitches(chord)
        drums = _template_events(roles.get("drums"), bar_offset)
        bass_template = _template_events(roles.get("bass"), bar_offset)
        accompaniment_template = _template_events(roles.get("accompaniment"), bar_offset)
        bass = []
        bass_profile = roles.get("bass") or {}
        relative_pattern = bass_profile.get("relative_pattern") or {}
        relative_events = relative_pattern.get("events") or []
        if section_type == "MAIN A" and relative_pattern.get("status") == "confirmed" and relative_events:
            for event in relative_events:
                degree = int(event.get("degree", 1))
                chord_match = re.match(r"^([A-G](?:#|b)?)(.*)$", str(chord))
                quality = chord_match.group(2).lower() if chord_match else ""
                minor = quality.startswith("m") or "dim" in quality
                semitone = {1: 0, 3: (3 if minor else 4), 5: 7}.get(degree)
                if semitone is None:
                    continue
                octave = int(event.get("octave_offset", 0))
                bass.append({**event, "pitch_midi": 36 + root + semitone + octave * 12,
                             "degree": degree, "source": "learned_relative_chord_degree"})
        else:
            # MAIN B (and other sections) must not inherit an unconfirmed MAIN A motif silently.
            for event in bass_template:
                bass.append({**event, "pitch_midi": 36 + root,
                             "degree": 1, "source": "root_only_unconfirmed_fallback"})
        accompaniment = []
        for event in accompaniment_template:
            accompaniment.append({**event,
                                  "pitches_midi": [60 + root, 60 + root + third, 60 + root + 7],
                                  "chord": chord, "source": "new_chord_voicing"})
        output.append({"bar_offset": bar_offset, "chord": chord,
                       "drums": drums, "bass": bass, "accompaniment": accompaniment,
                       "template_id": (pattern or {}).get("id"),
                       "template_type": section_type if pattern else None})
    return output


def _reviewed_drum_loop_plan(pattern, section_type, bar_count):
    if section_type not in {"MAIN A", "INTRO"} or not pattern:
        return None
    review = ((pattern.get("roles") or {}).get("drums") or {}).get("audited_continuous_loops") or {}
    if section_type == "INTRO":
        entry = review.get("initial_turn_excerpt")
        if not entry:
            return None
        if bar_count != int(entry["bars"]):
            raise ValueError("A entrada auditada precisa usar sua duração original")
        return {"status": "single_entry_transition_excerpt", "loop_bars": bar_count,
                "sequence": [{"id": entry["id"], "target_start_bar": 1,
                              "target_end_bar": bar_count,
                              "source_bars": [entry["start_bar"], entry["end_bar"]],
                              "source_start_seconds": entry["source_start_seconds"],
                              "source_end_seconds": entry["source_end_seconds"]}],
                "full_candidate_region_classified_as_fill": False}
    stable = review.get("stable_main_a") or []
    loop_bars = int(review.get("loop_bars", 0))
    if not stable or loop_bars < 1:
        return None
    sequence = []
    for index in range(math.ceil(bar_count / loop_bars)):
        item = stable[index % len(stable)]
        first = index * loop_bars + 1
        sequence.append({"id": item["id"], "target_start_bar": first,
                         "target_end_bar": min(bar_count, first + loop_bars - 1),
                         "source_bars": [item["start_bar"], item["end_bar"]],
                         "source_start_seconds": item["source_start_seconds"],
                         "source_end_seconds": item["source_end_seconds"]})
    return {"status": "stable_main_a_only", "loop_bars": loop_bars,
            "sequence": sequence, "transition_candidates_used": False}


def _new_melody(sections, beats_per_bar):
    """Compose a fresh deterministic chord-tone motif, never sourcing ref notes."""
    result = []
    for section in sections:
        for harmony in section["harmony_by_bar"]:
            chord = harmony["chord"]
            match = re.match(r"^([A-G](?:#|b)?)(.*)$", chord)
            root = NOTE_TO_PC.get(match.group(1), 0) if match else 0
            quality = match.group(2).lower() if match else ""
            third = 3 if quality.startswith("m") or "dim" in quality else 4
            root_midi = 60 + root
            pitches = [root_midi, root_midi + third, root_midi + 7, root_midi + third]
            total_eighths = beats_per_bar * 2
            durations = [2] * (total_eighths // 2)
            if total_eighths % 2:
                durations.append(1)
            result.append([{"pitch": pitches[index % len(pitches)], "duration_eighths": length}
                           for index, length in enumerate(durations)])
    return result


def validate_arrangement(arrangement):
    if arrangement.get("arrangement_version") != "0.1":
        raise ValueError("Versão de arrangement não suportada")
    if arrangement.get("reference_melody_copied") is not False:
        raise ValueError("O arrangement não pode copiar a melodia da referência")
    sections = arrangement.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("O arrangement precisa conter seções")
    next_bar = 1
    for section in sections:
        start, end, bars = section.get("start_bar"), section.get("end_bar"), section.get("bars")
        if start != next_bar or not isinstance(bars, int) or bars < 1 or end != start + bars - 1:
            raise ValueError("As seções devem cobrir compassos consecutivos")
        if len(section.get("harmony_by_bar", [])) != bars:
            raise ValueError("Cada compasso precisa ter um plano harmônico")
        next_bar = end + 1
    melody = arrangement.get("melody_by_bar")
    if melody is not None:
        if not isinstance(melody, list) or len(melody) != sum(item["bars"] for item in sections):
            raise ValueError("melody_by_bar precisa conter um item por compasso")
    return arrangement


def build_arrangement(style, seed=None, song_plan=None):
    """Adapt a new song plan to the reusable performance patterns in style.json."""
    if not isinstance(style, dict) or style.get("style_version") != "0.2":
        raise ValueError("style.json inválido ou versão não suportada (esperado 0.2)")
    seed_value = _seed_for(style, seed)
    bpm, meter, beats_per_bar, bpm_source, meter_source = _tempo_and_meter(style)
    song_plan = song_plan or {}
    if not isinstance(song_plan, dict):
        raise ValueError("song precisa ser um objeto JSON")
    requested_key = song_plan.get("key")
    key_pc, mode, _ = _key_parts(requested_key) if requested_key else (None, None, None)
    new_key = _new_key(style, seed_value) if key_pc is None else {
        "root": NOTE_NAMES[key_pc], "mode": mode or "major",
        "symbol": NOTE_NAMES[key_pc] + ("m" if mode == "minor" else ""),
        "source_key_reference": (style.get("harmony") or {}).get("key", {}).get("symbol")
        if isinstance((style.get("harmony") or {}).get("key"), dict) else (style.get("harmony") or {}).get("key"),
        "transposition_semitones": None,
    }
    key_pc = NOTE_TO_PC[new_key["root"]]
    mode = new_key["mode"]
    main_a_bars, main_b_bars = _phrase_lengths(style)

    # This harmonic fallback is deterministic. Caller-supplied chords take
    # precedence and are never copied from the reference.
    templates = {
        "INTRO": [1, 6] if mode == "minor" else [1, 4],
        "MAIN A": [1, 6, 3, 7] if mode == "minor" else [1, 5, 6, 4],
        "MAIN B": [4, 1, 5, 5] if mode == "minor" else [6, 4, 1, 5],
        "FILL A": [5], "FILL B": [5],
        "BREAK": [6, 7] if mode == "minor" else [6, 4],
        "ENDING": [4, 5, 1, 1] if mode == "minor" else [4, 5, 1, 1],
    }
    plan = _song_sections(style, song_plan, main_a_bars, main_b_bars)
    if song_plan.get("melody_by_bar") is not None:
        melody = song_plan["melody_by_bar"]
        if not isinstance(melody, list) or len(melody) != sum(item["bars"] for item in plan):
            raise ValueError("song.melody_by_bar precisa conter um item por compasso da forma")
    sections = []
    bar_cursor = 1
    for index, item in enumerate(plan, start=1):
        section_type, bars, energy = item["type"], item["bars"], item.get("energy", .7)
        harmony_bars = _section_chords(item, key_pc, mode, templates)
        pattern = _style_template(style, section_type)
        audited_entry = False
        if section_type == "INTRO" and pattern is None:
            pattern = _audited_entry_template(style)
            audited_entry = pattern is not None
        bass_template_type = "MAIN A" if audited_entry else section_type
        performance = pattern.get("roles", {}) if pattern else {}
        relative_pattern = (performance.get("bass") or {}).get("relative_pattern") or {}
        sections.append({
            "id": f"S{index:02d}", "type": section_type,
            "start_bar": bar_cursor, "end_bar": bar_cursor + bars - 1, "bars": bars,
            "energy": float(energy), "harmony_by_bar": harmony_bars,
            "style_pattern_id": pattern.get("id") if pattern else None,
            "style_pattern_label": section_type,
            "pattern_origin": ("audited_entry_excerpt" if audited_entry else
                               "learned_style_pack" if pattern else "not_observed_in_source"),
            "performance_profiles": performance,
            "performance_by_bar": _adapt_performance(pattern, bass_template_type, harmony_bars, bars),
            "drum_loop_plan": _reviewed_drum_loop_plan(pattern, section_type, bars),
            "source_pattern_confidence": pattern.get("confidence", item.get("source_confidence")) if pattern else None,
            "bass_behavior": ("learned chord-relative root-third-fifth motif; minor chords use b3" if bass_template_type == "MAIN A" and relative_pattern.get("status") == "confirmed" else "bass degree pattern unconfirmed; root-only fallback"),
            "accompaniment_behavior": "preserve learned groove/entry density; reharmonize to the new chord",
        })
        bar_cursor += bars

    total_bars = bar_cursor - 1
    seconds_per_bar = beats_per_bar * 60.0 / bpm
    duration = total_bars * seconds_per_bar
    source_analysis = style.get("source_analysis") if isinstance(style.get("source_analysis"), dict) else {}
    source_duration = source_analysis.get("duration")
    try:
        source_duration = float(source_duration)
        if not math.isfinite(source_duration) or source_duration <= 0:
            source_duration = None
    except (TypeError, ValueError):
        source_duration = None
    style_digest = hashlib.sha256(json.dumps(
        style, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()

    generated_melody = song_plan.get("melody_by_bar")
    if generated_melody is None:
        generated_melody = _new_melody(sections, beats_per_bar)

    arrangement = {
        "arrangement_version": "0.1", "planner": "nexus_arranger_mvp",
        "name": song_plan.get("title") or f"Nova música no estilo {style.get('name') or 'Style'}",
        "lyrics": str(song_plan.get("lyrics") or "").strip(),
        "seed": seed_value,
        "source_style": {"name": style.get("name"), "style_version": style.get("style_version"),
                         "algorithm_version": style.get("algorithm_version"), "sha256": style_digest},
        "tempo_bpm": bpm, "meter": meter,
        "duration_estimate_seconds": round(duration, 2),
        "duration_reference_seconds": round(source_duration, 2) if source_duration is not None else None,
        "total_bars": total_bars,
        "harmony": {"key": new_key["symbol"], "root": new_key["root"], "mode": mode,
                    "source_key_reference": new_key["source_key_reference"],
                    "transposition_semitones": new_key["transposition_semitones"],
                    "progression_method": "caller-supplied new-song chords" if any(item.get("chords") is not None for item in plan) else "new deterministic diatonic templates; source chord symbols are not reused",
                    "progressions_by_section": [
                        {"section_id": section["id"], "type": section["type"],
                         "chords_by_bar": section["harmony_by_bar"]} for section in sections]},
        "sections": sections,
        "style_pack": style.get("style_pack") or {"version": "unavailable", "patterns": [], "form": []},
        "drums": {"grid_steps_per_bar": 16, "patterns": [
                      item for item in (style.get("style_pack") or {}).get("patterns", [])
                      if item.get("roles", {}).get("drums")],
                  "adaptation": "replay learned step-energy profile; preserve relative groove while fitting new harmony/melody"},
        "bass": {"role": "bass accompaniment", "adaptation": "MAIN A uses the confirmed relative root-third-fifth motif; minor chords lower the third. Unconfirmed section motifs are not invented.",
                 "learned_patterns": [item for item in (style.get("style_pack") or {}).get("patterns", [])
                                      if item.get("roles", {}).get("bass")]},
        "keyboard_accompaniment": {"role": "keyboard-led harmonic backing",
                                    "adaptation": "preserve learned accompaniment timing/density; voice new chords",
                                    "learned_patterns": [item for item in (style.get("style_pack") or {}).get("patterns", [])
                                                         if item.get("roles", {}).get("accompaniment")]},
        "instrumentation": (style.get("instrumentation") or []),
        "dynamics": {"scale": "0.0-1.0 relative section energy", "by_section": [
            {"section_id": section["id"], "type": section["type"], "energy": section["energy"]}
            for section in sections]},
        "generation_handoff": {
            "status": "plan_only_audio_not_rendered",
            "qwen_role": "optional new-song text/score preparation; does not receive reference note events",
            "yue2_role": "ABC-conditioned renderer; audio is not rendered while planning",
            "prompt": (f"Keep the learned style-pack performance patterns at {bpm:g} BPM in {meter}; "
                       f"adapt harmony and accompaniment to new key {new_key['symbol']}, chords, melody and lyrics. "
                       "Do not copy any melody or exact notes from the reference."),
            "section_map": [{"type": section["type"], "bars": section["bars"]} for section in sections],
            "reference_melody_included": False,
            "ready_for_audio_generation": bool(song_plan.get("lyrics") or song_plan.get("melody_by_bar") or song_plan.get("instrumental", False)),
        },
        "provenance": {"tempo_source": bpm_source, "meter_source": meter_source,
                       "phrase_source": "style_pack.form and learned MAIN pattern lengths; legacy form prior only when no detected style form exists",
                       "source_chord_progression_used": False,
                       "source_melody_or_note_events_used": False,
                       "source_key_used_only_for_mode_and_to_choose_a_different_tonic": True,
                       "heuristics": ["new diatonic chord templates only when the song request omits chords",
                                      "new lead melody is procedural if no melody_by_bar is supplied"],
                       "limitations": ["MVP is symbolic planning, not MIDI or audio generation.",
                                       "Instrument suggestions are priors, not confirmed instrument recognition.",
                                       "Style Analyzer confidence is not calibrated; review BPM/meter and harmony before rendering."]},
        "reference_melody_copied": False,
        "melody_by_bar": generated_melody,
        "melody_source": "new_song_request" if song_plan.get("melody_by_bar") else "new_deterministic_chord_tone_motif",
    }
    return validate_arrangement(arrangement)
