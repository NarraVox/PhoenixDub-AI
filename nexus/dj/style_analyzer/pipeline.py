"""Audio analysis pipeline for the experimental Nexus Style Analyzer."""
import logging
from pathlib import Path

from nexus.json_io import safe_json_read
from . import VERSION
from .consolidation import (align_harmony_to_sections, apply_rhythm_consensus,
                            consolidate_rhythm)
from .fills import detect_fills
from .patterns import classify
from .rhythm import bar_features, build_grid
from .schema import make_style
from .style_pack import apply_manual_drum_review, build_style_pack
from .store import TARGETS, digest, write_json
from .safety import preflight


def run(root, project, progress=lambda *args: None):
    root, project = Path(root), Path(project)
    source_info = safe_json_read(project / "source.json") or {}
    source = Path(source_info.get("path", ""))
    if not source.is_file() or digest(source) != source_info.get("sha256"):
        raise ValueError("Arquivo de referência ausente ou alterado")
    options = source_info.get("options", {})
    if options.get("device") not in {"cpu", "gpu"} or options.get("separator") != "openunmix":
        raise ValueError("Configuração inválida: Analyzer exige Open-Unmix e device cpu/gpu")
    preflight(source, project, sheetsage=options.get("sheetsage", False),
              require_gpu=options.get("device") == "gpu" or options.get("sheetsage_backend") == "cuda")

    logger = logging.getLogger("style_analyzer")

    def stage(name, fraction):
        logger.info("ETAPA: %s (%d%%)", name, int(fraction * 100))
        progress(name, fraction)

    import numpy as np
    import soundfile as sf
    import librosa

    stage("preparing", 0.05)
    audio, sr = librosa.load(source, sr=44100, mono=True, dtype=np.float32)
    if not len(audio) or not np.isfinite(audio).all():
        raise ValueError("Áudio vazio ou inválido")
    reference = project / "reference.wav"
    sf.write(reference, np.column_stack((audio, audio)), sr, subtype="PCM_16")

    stage("separation", 0.1)
    stem_dir = project / "stems"
    stem_paths = {name: stem_dir / f"{name}.wav" for name in TARGETS}
    previous_manifest = safe_json_read(project / "stem_manifest.json") or {}
    separated_now = False
    compute_device = "reused_existing_stems"
    separator_requested = options.get("separator", "openunmix")
    separator_used = None
    separation_fallback_error = None
    if not all(p.is_file() for p in stem_paths.values()):
        if separator_requested in {"demucs", "auto"}:
            try:
                from .adapters.demucs import separate as demucs_separate
                separated = demucs_separate(str(reference), str(stem_dir),
                                            device=options.get("device", "auto"),
                                            progress=lambda _stage, value: progress("separation", 0.1 + value * 0.35))
                separator_used = "htdemucs"
                compute_device = "cuda"
            except Exception as exc:
                if separator_requested != "auto":
                    raise
                separation_fallback_error = str(exc)
                logger.warning("HTDemucs falhou; tentando Open-Unmix: %s", exc)
        if separator_used is None:
            from .adapters.openunmix import separate as openunmix_separate
            separated = openunmix_separate(str(reference), str(stem_dir),
                                           device=options.get("device", "gpu"),
                                           progress=lambda _stage, value: progress("separation", 0.1 + value * 0.35))
            separator_used = "openunmix"
            compute_device = "cuda" if options.get("device", "gpu") == "gpu" else "cpu"
        stem_paths = {name: Path(path) for name, path in separated.items()}
        separated_now = True
    else:
        separator_used = previous_manifest.get("separator") or (
            "htdemucs" if (stem_dir / "demucs_run.json").is_file() else "openunmix")
        compute_device = previous_manifest.get("device") or (
            "cuda" if separator_used == "htdemucs" else "reused_existing_stems")
    stem_records = {f"{name}.wav": {"sha256": digest(path), "size": path.stat().st_size}
                    for name, path in stem_paths.items()}
    write_json(project / "stem_manifest.json", {"files": stem_records,
                                                "separator": separator_used,
                                                "device": compute_device})

    instrument_detection = None
    if separator_used == "htdemucs" and options.get("instrument_discovery", True):
        stage("instrument_discovery", 0.47)
        try:
            from .adapters.instruments import discover
            from .instrument_validation import prepare_instrument_validation
            instrument_detection = prepare_instrument_validation(discover(stem_paths["other"]))
            write_json(project / "instrument_detection.json", instrument_detection)
        except Exception as exc:
            logger.warning("DJ Instrument Discovery falhou: %s", exc)
            instrument_detection = {"status": "error", "source_stem": str(stem_paths["other"]),
                                    "error": str(exc), "detected": [], "candidates": []}

    score = None
    sheetsage = None
    if options.get("sheetsage"):
        stage("score", 0.48)
        from .adapters.sheetsage import transcribe
        sheetsage = transcribe(root, reference, project / "score",
                               backend=options.get("sheetsage_backend", "auto"))
        score = {key: value for key, value in sheetsage.items() if key != "structured"}

    sheetsage_harmony = sheetsage.get("structured") if sheetsage else None
    # Rhythm and drum descriptors use the separated drum stem, not the full mix.
    with sf.SoundFile(stem_paths["drums"]) as stream:
        drums = stream.read(dtype="float32", always_2d=True).mean(axis=1)
        drum_sr = stream.samplerate
    mix_for_grid = audio if sr == drum_sr else librosa.resample(audio, orig_sr=sr, target_sr=drum_sr)
    stage("beats", 0.52)
    hints = {argument: options[option] for option, argument in
             (("bpm", "bpm_hint"), ("meter", "meter_hint"), ("offset", "offset"))
             if options.get(option) is not None}
    grid = build_grid(drums, drum_sr, secondary_audio=mix_for_grid, **hints)
    raw_rhythm = {key: value for key, value in grid.items() if key not in ("beats", "downbeats", "bars")}
    raw_rhythm["tempo_hypotheses"] = [
        {key: value for key, value in hypothesis.items() if key != "beat_times"}
        for hypothesis in grid.get("tempo_hypotheses", [])]
    rhythm_consensus = consolidate_rhythm(grid, sheetsage_harmony,
                                         bpm_hint=options.get("bpm"),
                                         meter_hint=options.get("meter"))
    grid = apply_rhythm_consensus(grid, rhythm_consensus)
    grid["tempo_hypotheses"] = raw_rhythm.get("tempo_hypotheses", [])
    bars = grid.get("bars", [])
    features = bar_features(drums, drum_sr, bars, int(grid["meter"].split("/")[0])) if bars and grid.get("meter") else []
    stage("patterns", 0.72)
    catalog, sections, debug = classify(features, grid.get("grid_confidence", 0.0), grid.get("duration", len(drums) / drum_sr))
    style_pack = build_style_pack(catalog, sections, bars, stem_paths)
    style_pack = apply_manual_drum_review(
        style_pack, safe_json_read(project / "style_pack_review.json"), bars)
    stage("fills", 0.88)
    fill_detection = (detect_fills(stem_paths["drums"], bars, sections,
                                   review=safe_json_read(project / "fill_review.json"))
                      if separator_used == "htdemucs" else None)
    if fill_detection and fill_detection.get("status") == "detected":
        style_pack["fill_patterns"] = fill_detection["clusters"]
    limitations = [
        "Confianças heurísticas, não probabilidades calibradas.",
        "A métrica automática considera 3/4 e 4/4; use indicação manual em outros casos.",
        "BREAK descreve redução de atividade no stem de bateria, não silêncio da banda.",
        "A grade, a segmentação e os padrões precisam de validação auditiva.",
        "A consolidação BPM/métrica combina Rhythm e SheetSage2, mas continua heurística e requer validação auditiva.",
        "A harmonia alinhada usa suporte de notas nos stems bass/other, não uma probabilidade calibrada de acorde.",
    ]
    stage("harmony", 0.92)
    harmony_alignment = align_harmony_to_sections(sheetsage_harmony, bars, sections, stem_paths)
    analysis = {**grid, "bars": bars, "features": features, "patterns": catalog,
                "sections": sections, "debug": debug,
                "stem_origin": (f"{separator_used}_generated" if separated_now
                                else f"{separator_used}_reused_existing_stems"),
                "separation_executed": separated_now,
                "separation_device": compute_device,
                "separator_requested": separator_requested,
                "separator_used": separator_used,
                "separation_fallback_error": separation_fallback_error,
                "score": score, "sheetsage2": sheetsage_harmony,
                "rhythm_raw": raw_rhythm, "rhythm_consensus": rhythm_consensus,
                "harmony_alignment": harmony_alignment,
                "instrument_detection": instrument_detection,
                "style_pack": style_pack,
                "fill_detection": fill_detection,
                "limitations": limitations}
    write_json(project / "analysis.json", analysis)
    harmony = sheetsage.get("structured") if sheetsage else None
    # Keep exact note events in analysis.json for inspection. style.json is a
    # reusable arrangement description and must not carry the reference melody.
    style_harmony = ({key: harmony.get(key) for key in (
        "source", "score_format", "model_tempo_bpm", "meter", "key", "key_changes",
        "measure_count", "chords_by_bar", "chord_progression", "structure_sections",
        "melody_profiles", "event_count") if harmony and key in harmony} if harmony else None)
    if style_harmony is not None:
        style_harmony["alignment"] = {key: harmony_alignment.get(key) for key in (
            "status", "score_bar_count", "grid_bar_count", "score_to_grid_scale",
            "score_bar_offset", "alignment_score", "alignment_margin", "coverage",
            "confidence_kind", "by_section", "key_changes_aligned", "reason")}
    style = make_style(source_info.get("name") or "Style", {
        "bpm": grid.get("bpm"), "meter": grid.get("meter"), "duration": grid.get("duration"),
        "grid_confidence": grid.get("grid_confidence"), "sections": sections,
        "patterns": catalog, "limitations": limitations,
        "tempo_estimate": grid.get("tempo_estimate"),
        "tempo_ambiguous": grid.get("tempo_ambiguous", False),
        "tempo_hypotheses": grid.get("tempo_hypotheses", []),
        "rhythm_consensus": rhythm_consensus,
        "harmony": style_harmony,
        "style_pack": style_pack,
        "fills": fill_detection["clusters"] if fill_detection else [],
        "instrument_detection": instrument_detection,
    })
    write_json(project / "style.json", style)
    stage("saving", 0.98)
    logger.info("Análise concluída: BPM=%s, compasso=%s, compassos=%d, padrões=%d",
                grid.get("bpm"), grid.get("meter"), len(bars), len(catalog))
    return {"cached": False}
