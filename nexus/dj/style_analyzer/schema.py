"""Small versioned public Style contract; observations live in analysis.json."""
import math


def validate_style(style):
    if style.get("style_version") != "0.2" or not isinstance(style.get("name"), str):
        raise ValueError("Style inválido ou versão não suportada")
    patterns = style.get("drums", {}).get("patterns")
    sections = style.get("sections")
    if not isinstance(patterns, list) or not isinstance(sections, list):
        raise ValueError("Catálogo e timeline obrigatórios")
    ids = [p["id"] for p in patterns]
    if len(set(ids)) != len(ids):
        raise ValueError("IDs de padrão duplicados")
    previous = 0.0
    for section in sections:
        start, end = section["start_seconds"], section["end_seconds"]
        confidence = section["confidence"]
        if not all(math.isfinite(v) for v in (start, end, confidence)):
            raise ValueError("Valores não finitos")
        if start < previous - 1e-6 or end <= start or not 0 <= confidence <= 1:
            raise ValueError("Timeline inválida")
        if section.get("pattern_id") and section["pattern_id"] not in ids:
            raise ValueError("Padrão desconhecido")
        previous = end
    return style


from . import VERSION

def make_style(name, analysis):

    return validate_style({
        "style_version": "0.2", "algorithm_version": VERSION, "name": name,
        "source_analysis": {k: analysis.get(k) for k in ("bpm", "meter", "duration", "grid_confidence",
                                                           "tempo_estimate", "tempo_ambiguous", "tempo_hypotheses")},
        "rhythm_consensus": analysis.get("rhythm_consensus"),
        "sections": analysis["sections"], "drums": {"patterns": analysis["patterns"]},
        "harmony": analysis.get("harmony"),
        "style_pack": analysis.get("style_pack"),
        "fills": analysis.get("fills", []),
        "instruments": {
            "status": (analysis.get("instrument_detection") or {}).get("status", "not_run"),
            "source": "other.wav",
            "raw_predictions": {
                key: (analysis.get("instrument_detection") or {}).get("raw_predictions", {}).get(key)
                for key in ("detected", "candidates", "confidence_kind")},
            "confirmed_instruments": (analysis.get("instrument_detection") or {}).get("confirmed_instruments", []),
            "ambiguous_instruments": (analysis.get("instrument_detection") or {}).get("ambiguous_instruments", []),
            "stem_authority": (analysis.get("instrument_detection") or {}).get("stem_authority", {}),
            "validation_status": (analysis.get("instrument_detection") or {}).get("validation_status", "not_run"),
        },
        "capabilities": {"rhythm": True,
                         "key_estimation": bool((analysis.get("harmony") or {}).get("key", {}).get("root")),
                         "chord_transcription": bool((analysis.get("harmony") or {}).get("chord_progression")),
                         "melody_transcription": bool((analysis.get("harmony") or {}).get("melody_profiles")),
                         "harmonic_transposition": False, "instrument_notes": False,
                         "instrument_detection": (analysis.get("instrument_detection") or {}).get("status") == "detected"},
        "confidence_kind": "heuristic_not_calibrated", "limitations": analysis["limitations"],
        "evidence_file": "analysis.json",
    })
