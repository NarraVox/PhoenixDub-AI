"""Keep instrument model observations separate from human-confirmed instrumentation."""
from __future__ import annotations


DEDICATED_STEMS = {"bass": "bass.wav", "drums": "drums.wav"}


def prepare_instrument_validation(result: dict) -> dict:
    """Wrap a model result without changing any original scores or regions."""
    if "raw_predictions" in result:
        return result
    raw = {key: value for key, value in result.items()
           if key not in {"raw_predictions", "confirmed_instruments", "ambiguous_instruments"}}
    ambiguous = []
    for item in raw.get("detected", []):
        label = item["instrument"]
        entry = {"model_label": label, "model_score": item["confidence"],
                 "status": "awaiting_auditory_validation",
                 "possible_confusion": [], "source_stem": "other.wav"}
        if label in DEDICATED_STEMS:
            entry["status"] = "possible_stem_leakage"
            entry["dedicated_stem_authority"] = DEDICATED_STEMS[label]
        if label == "synthesizer" and "accordion" in raw.get("classes", []):
            entry["possible_confusion"] = ["accordion", "keyboard", "organ"]
            entry["note"] = "Timbre hypothesis only; no accordion confirmation from model A."
        ambiguous.append(entry)
    return {"status": raw.get("status", "unknown"),
            "source_stem": raw.get("source_stem"),
            "raw_predictions": raw,
            "confirmed_instruments": [],
            "ambiguous_instruments": ambiguous,
            "stem_authority": {"bass": "bass.wav", "drums": "drums.wav",
                               "other": "other.wav", "vocals": "vocals.wav"},
            "validation_status": "pending_human_review"}
