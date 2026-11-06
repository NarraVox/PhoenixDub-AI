"""Rhythm-grid estimation and beat-synchronous bar descriptors."""
import numpy as np


def _tempo_candidates(onset, sr, hop, hint=None, secondary_onset=None):
    """Compare beat-tracker hypotheses at half/base/double tempo using audio evidence."""
    import librosa

    if hint:
        centers = [float(hint)]
        source = "user_bpm"
    else:
        base, _ = librosa.beat.beat_track(onset_envelope=onset, sr=sr,
                                          hop_length=hop, trim=False)
        base = float(np.asarray(base).reshape(-1)[0])
        if not np.isfinite(base) or base <= 0:
            return []
        centers = [base]
        source = "librosa"
    candidates = sorted({round(float(bpm), 3) for center in centers
                         for bpm in (center / 2, center, center * 2)
                         if 40 <= bpm <= 240})
    scored = []
    onset = np.asarray(onset, dtype=float)
    onset = np.maximum(onset, 0)
    mean_onset = float(onset.mean()) + 1e-9
    if secondary_onset is not None:
        secondary_onset = np.maximum(np.asarray(secondary_onset, dtype=float), 0)
        secondary_onset = secondary_onset[:len(onset)]
        secondary_mean = float(secondary_onset.mean()) + 1e-9
    else:
        secondary_mean = None
    for bpm in candidates:
        _, frames = librosa.beat.beat_track(onset_envelope=onset, sr=sr,
                                            hop_length=hop, bpm=bpm,
                                            tightness=100, trim=False)
        frames = np.asarray(frames, dtype=int)
        frames = frames[(frames >= 0) & (frames < len(onset))]
        if len(frames) < 5:
            continue
        intervals = np.diff(frames)
        regularity = float(np.clip(1 - np.std(intervals) / (np.mean(intervals) + 1e-9), 0, 1))
        intervals_seconds = intervals.astype(float) * hop / sr
        ordered_intervals = np.sort(intervals_seconds)
        trim = int(len(ordered_intervals) * 0.10)
        stable_intervals = ordered_intervals[trim:len(ordered_intervals) - trim] if trim else ordered_intervals
        measured_bpm = 60.0 / max(float(np.mean(stable_intervals)), 1e-9)
        pulse_ratio = float(np.mean(onset[frames]) / mean_onset)
        pulse_evidence = float(np.clip(pulse_ratio / 2.0, 0, 1))
        lag = max(1, int(round(60 * sr / bpm / hop)))
        if lag < len(onset):
            centered = onset - onset.mean()
            autocorr = float(np.dot(centered[:-lag], centered[lag:]) /
                             (np.dot(centered, centered) + 1e-9))
            autocorr_evidence = float(np.clip((autocorr + 0.1) / 0.6, 0, 1))
        else:
            autocorr = -1.0
            autocorr_evidence = 0.0
        # Repeated phase-locking and interval stability matter more than a tempo prior.
        drum_score = 0.40 * regularity + 0.35 * pulse_evidence + 0.25 * autocorr_evidence
        mix_score = None
        if secondary_onset is not None and len(secondary_onset) > lag:
            mix_pulse = float(np.mean(secondary_onset[np.minimum(frames, len(secondary_onset)-1)]) / secondary_mean)
            mix_pulse_evidence = float(np.clip(mix_pulse / 2.0, 0, 1))
            mix_centered = secondary_onset - secondary_onset.mean()
            mix_autocorr = float(np.dot(mix_centered[:-lag], mix_centered[lag:]) /
                                 (np.dot(mix_centered, mix_centered) + 1e-9))
            mix_autocorr_evidence = float(np.clip((mix_autocorr + 0.1) / 0.6, 0, 1))
            mix_score = 0.35 * regularity + 0.35 * mix_pulse_evidence + 0.30 * mix_autocorr_evidence
            score = 0.70 * drum_score + 0.30 * mix_score
        else:
            score = drum_score
        pulse = onset[frames]
        meter_hypotheses = []
        for candidate_meter in (2, 3, 4):
            phase_scores = []
            for candidate_phase in range(candidate_meter):
                accents = pulse[candidate_phase::candidate_meter]
                others = np.delete(pulse, np.arange(candidate_phase, len(pulse), candidate_meter))
                if len(accents) and len(others):
                    accent = float((np.mean(accents) - np.mean(others)) /
                                   (np.max(pulse) + 1e-9))
                    phase_scores.append((accent, candidate_phase))
            if phase_scores:
                accent, candidate_phase = max(phase_scores)
                meter_hypotheses.append({"meter": candidate_meter, "phase": candidate_phase,
                                         "accent_score": round(accent, 4)})
        scored.append({"bpm": bpm, "measured_bpm": round(measured_bpm, 3),
                       "score": round(score, 4),
                       "drum_score": round(drum_score, 4),
                       "mix_score": round(mix_score, 4) if mix_score is not None else None,
                       "regularity": round(regularity, 4),
                       "pulse_ratio": round(pulse_ratio, 4),
                       "autocorrelation": round(autocorr, 4),
                       "meter_hypotheses": meter_hypotheses,
                       "beat_frames": frames, "source": source})
    return sorted(scored, key=lambda x: x["score"], reverse=True)


def build_grid(audio, sr, bpm_hint=None, meter_hint=None, offset=None, secondary_audio=None):
    import librosa
    hop = 256
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    onset = librosa.onset.onset_strength(y=audio, sr=sr, hop_length=hop)
    mix_onset = None
    if secondary_audio is not None:
        secondary_audio = np.asarray(secondary_audio, dtype=np.float32).reshape(-1)
        if len(secondary_audio) and np.max(np.abs(secondary_audio), initial=0) > 1e-5:
            mix_onset = librosa.onset.onset_strength(y=secondary_audio, sr=sr, hop_length=hop)
    duration = len(audio) / sr
    if len(audio) < sr * 4 or np.max(np.abs(audio), initial=0) < 1e-5:
        return {"bpm": None, "beats": [], "bars": [], "meter": None,
                "grid_confidence": 0.0, "grid_method": "insufficient_audio",
                "duration": duration, "tempo_hypotheses": []}
    scored = _tempo_candidates(onset, sr, hop, bpm_hint, mix_onset)
    if not scored:
        return {"bpm": None, "beats": [], "bars": [], "meter": None,
                "grid_confidence": 0.0, "grid_method": "no_stable_pulse",
                "duration": duration, "tempo_hypotheses": []}
    best = scored[0]
    frames = best["beat_frames"]
    beats = librosa.frames_to_time(frames, sr=sr, hop_length=hop)
    if len(beats) < 5:
        return {"bpm": None, "beats": [], "bars": [], "meter": None,
                "grid_confidence": 0.0, "grid_method": "no_stable_pulse",
                "duration": duration, "tempo_hypotheses": []}

    intervals = np.diff(beats)
    interval_regularity = float(np.clip(1 - np.std(intervals) / (np.mean(intervals) + 1e-9), 0, 1))
    pulse = onset[np.minimum(frames, len(onset) - 1)]
    meter_candidates = []
    # Keep the legacy drum-grid candidates (3/4 and 4/4) as the raw reading.
    # 2/4 is still evaluated per-tempo hypothesis above and may be selected by
    # multimodal consensus when its bar duration matches the observed grid.
    for meter in ([int(meter_hint)] if meter_hint else [3, 4]):
        for phase in range(meter):
            accents = pulse[phase::meter]
            others = np.delete(pulse, np.arange(phase, len(pulse), meter))
            if not len(accents) or not len(others):
                continue
            accent_score = float((np.mean(accents) - np.mean(others)) /
                                 (np.max(pulse) + 1e-9))
            meter_candidates.append((accent_score, meter, phase))
    meter_candidates.sort(reverse=True)
    best_accent, meter, phase = meter_candidates[0] if meter_candidates else (0.0, 4, 0)
    accent_margin = max(0.0, best_accent - (meter_candidates[1][0] if len(meter_candidates) > 1 else 0))
    phase_evidence = float(np.clip(0.45 + best_accent + accent_margin, 0, 1))
    tempo_margin = max(0.0, best["score"] - (scored[1]["score"] if len(scored) > 1 else 0))
    tempo_ambiguous = len(scored) > 1 and tempo_margin < 0.02
    tempo_quality = float(np.clip(best["score"], 0, 1))
    # A close half/double contender lowers confidence instead of being hidden.
    tempo_disambiguation = float(np.clip(tempo_margin / 0.18, 0, 1))
    tempo_confidence = 0.60 * tempo_quality + 0.40 * tempo_disambiguation
    grid_confidence = float(np.clip(tempo_confidence * (0.65 + 0.35 * phase_evidence) * interval_regularity, 0, 1))
    method = "audio_evidence_half_base_double_ambiguous" if tempo_ambiguous else "audio_evidence_half_base_double"
    if bpm_hint:
        method = "user_bpm_audio_compared_half_base_double"
        grid_confidence = float(np.clip((0.65 * tempo_quality + 0.35 * interval_regularity) *
                                        (0.75 + 0.25 * phase_evidence), 0, 1))
    if offset is not None:
        index = int(np.argmin(np.abs(beats - offset)))
        beats = beats + (float(offset) - float(beats[index]))
        phase = index % meter
        method += "_user_downbeat"
    if meter_hint:
        method += "_user_meter"
    downbeats = beats[phase::meter]
    downbeats = downbeats[(downbeats >= 0) & (downbeats <= duration)]
    bars = [{"start_seconds": float(a), "end_seconds": float(b), "bar": i + 1}
            for i, (a, b) in enumerate(zip(downbeats[:-1], downbeats[1:]))]
    hypotheses = []
    for candidate in scored:
        item = {k: v for k, v in candidate.items() if k != "beat_frames"}
        item["beat_times"] = librosa.frames_to_time(candidate["beat_frames"], sr=sr,
                                                      hop_length=hop).tolist()
        hypotheses.append(item)
    return {"bpm": None if tempo_ambiguous else round(float(best["measured_bpm"]), 3),
            "tempo_estimate": round(float(best["measured_bpm"]), 3),
            "tempo_ambiguous": tempo_ambiguous,
            "tempo_tracker_hypothesis": round(float(best["bpm"]), 3),
            "beats": beats[(beats >= 0) & (beats <= duration)].tolist(),
            "bars": bars, "meter": f"{meter}/4",
            "grid_confidence": round(grid_confidence, 3),
            "grid_method": method, "duration": duration,
            "meter_is_hypothesis": not bool(meter_hint),
            "downbeats": downbeats.tolist(),
            "tempo_hypotheses": hypotheses,
            "meter_hypotheses": [{"meter": int(meter), "phase": int(candidate_phase),
                                  "accent_score": round(float(accent), 4)}
                                 for accent, meter, candidate_phase in meter_candidates],
            "grid_source": "drums_with_mix_corroboration" if mix_onset is not None else "drums",
            "grid_evidence": {"tempo_quality": round(tempo_quality, 4),
                              "tempo_margin": round(tempo_margin, 4),
                              "tempo_ambiguity_threshold": 0.02,
                              "tempo_disambiguation": round(tempo_disambiguation, 4),
                              "interval_regularity": round(interval_regularity, 4),
                              "phase_evidence": round(phase_evidence, 4)}}


def bar_features(audio, sr, bars, meter):
    import librosa
    hop = 256
    spectrum = np.abs(librosa.stft(audio, n_fft=1024, hop_length=hop))
    frequencies = librosa.fft_frequencies(sr=sr, n_fft=1024)
    envelopes = []
    for low, high in [(30, 180), (180, 2500), (2500, sr / 2 + 1)]:
        band = spectrum[(frequencies >= low) & (frequencies < high)]
        flux = np.maximum(np.diff(band, axis=1, prepend=band[:, :1]), 0).mean(axis=0)
        envelopes.append(flux)
    times = librosa.frames_to_time(np.arange(spectrum.shape[1]), sr=sr, hop_length=hop)
    from scipy.ndimage import gaussian_filter1d
    # Keep equal temporal resolution for bars when equivalent 2/4 at half
    # tempo and 4/4 at double tempo describe the same physical bar duration.
    # A meter-dependent vector size made pattern novelty change when only the
    # half/double interpretation changed.
    bins = 32
    result = []
    for bar in bars:
        start, end = bar["start_seconds"], bar["end_seconds"]
        edges = np.linspace(start, end, bins + 1)
        bands = []
        for env in envelopes:
            values = [float(np.max(env[(times >= a) & (times < b)], initial=0))
                      for a, b in zip(edges[:-1], edges[1:])]
            bands.append(gaussian_filter1d(values, 0.6, mode="wrap"))
        raw = np.asarray(bands)
        vector = raw.flatten()
        vector /= max(float(np.linalg.norm(vector)), 1e-9)
        samples = audio[int(start * sr):int(end * sr)]
        rms = float(np.sqrt(np.mean(samples ** 2))) if len(samples) else 0
        combined = raw.sum(axis=0)
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(np.r_[0, combined, 0],
                              height=max(float(combined.max()) * 0.22, 1e-8), distance=2)
        attacks = [(int(p) - 1) / 8 for p in peaks if 0 < p <= bins]
        result.append({**bar, "vector": vector.tolist(), "rms": rms,
                       "density": len(attacks), "attacks_beats": attacks})
    return result
