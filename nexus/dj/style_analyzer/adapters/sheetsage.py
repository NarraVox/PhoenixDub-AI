"""SheetSage2 adapter for the bundled audio.cpp runtime."""
import json
import os
import re
import subprocess
from pathlib import Path


def availability(root):
    root = Path(root)
    model = root / "MODELS/SheetSage2-GGUF/sheetsage2-orig.gguf"
    cli = root / "env/tools_yue2/audio-v0.8.0-bin-windows-x64-cuda12.4/audiocpp_cli.exe"
    return {"available": model.is_file() and cli.is_file(), "model": str(model), "cli": str(cli),
            "model_size": model.stat().st_size if model.is_file() else None,
            "message": "SheetSage2 disponível: score ABC, eventos, tonalidade, acordes, melodia e estrutura."}


def _select_backend(backend):
    if backend != "auto":
        return backend
    try:
        import torch
        if torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info(0)
            # The 6-GB RTX 3050 has passed a real short transcription with the
            # reduced arenas below. Require 5 GiB free before selecting it.
            if total >= 6 * 1024**3 and free >= 5 * 1024**3:
                return "cuda"
    except Exception:
        pass
    return "cpu"


def _unwrap_artifact(path):
    """Unwrap audio.cpp's custom JSON artifact envelope when present."""
    text = Path(path).read_text(encoding="utf-8").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(data, dict) and isinstance(data.get("payload_hex"), str):
        payload = bytes.fromhex(data["payload_hex"]).decode("utf-8")
        return payload
    return text


def _abc_score(output):
    candidates = [Path(output) / "score.abc", Path(output) / "score.json", Path(output) / "score"]
    candidates.extend(Path(output).glob("**/score.abc"))
    candidates.extend(Path(output).glob("**/score.json"))
    for candidate in candidates:
        if candidate.is_file():
            text = _unwrap_artifact(candidate)
            if text.startswith("X:") or "\nK:" in text:
                return text
    raise RuntimeError("SheetSage2 terminou sem score ABC; confira sheetsage.log")


def _event_payload(output):
    candidates = [Path(output) / "events.json", *Path(output).glob("**/events.json")]
    for candidate in candidates:
        if candidate.is_file():
            try:
                data = json.loads(_unwrap_artifact(candidate))
                if isinstance(data, dict) and isinstance(data.get("events"), list):
                    return data
            except (ValueError, UnicodeDecodeError):
                continue
    return None


def _parse_score(abc, events_data=None):
    """Extract a compact, traceable musical summary from ABC + timed notes."""
    meter = None
    tempo = None
    key = None
    voice = None
    bar_index = -1
    bars = []
    sections = []
    pending_section = None
    key_changes = []
    for line in abc.splitlines():
        line = line.strip()
        if line.startswith("%"):
            label = line[1:].strip()
            if label:
                pending_section = label
            continue
        if line.startswith("V:"):
            voice = line[2:].strip().split()[0] if line[2:].strip() else None
            continue
        if line.startswith("M:"):
            meter = line[2:].strip()
            continue
        if line.startswith("Q:"):
            match = re.search(r"=\s*(\d+(?:\.\d+)?)", line)
            if match:
                tempo = float(match.group(1))
            continue
        if line.startswith("K:"):
            parsed_key = line[2:].strip()
            # ABC repeats K: directives at voice/section boundaries. Keep the
            # first declaration as the global key and record only real changes.
            if key is None:
                key = parsed_key
            if not key_changes or key_changes[-1]["key"] != parsed_key:
                key_changes.append({"after_bar": max(bar_index + 1, 0), "key": parsed_key})
            continue
        if not line or line.startswith(("X:", "T:", "L:")) or voice != "Vocal":
            continue
        # The model serializes chord labels in the vocal staff. Bars delimit
        # score measures; preserve every measure even when it has no chord label.
        chunks = line.split("|")
        for chunk in chunks[:-1]:
            bar_index += 1
            chord_symbols = [s.strip() for s in re.findall(r'"([^"\n]+)"', chunk) if s.strip()]
            item = {"bar": bar_index + 1, "chords": chord_symbols}
            if pending_section:
                sections.append({"start_bar": item["bar"], "label": pending_section})
                pending_section = None
            bars.append(item)

    progression = []
    previous = None
    for bar in bars:
        for chord in bar["chords"]:
            if chord != previous:
                progression.append({"bar": bar["bar"], "chord": chord})
                previous = chord

    events = (events_data or {}).get("events", [])
    notes = []
    for event in events:
        event_time = event.get("time")
        for note in event.get("notes", []):
            try:
                pitch = int(note["pitch"])
                start = float(event_time)
                end = float(note.get("end_time", start))
            except (KeyError, TypeError, ValueError):
                continue
            track_id = int(note.get("track", 0))
            notes.append({"start_seconds": start, "end_seconds": end, "midi_pitch": pitch,
                          "track": "vocal" if track_id == 0 else "instrumental_melody"})

    profiles = {}
    for track in ("vocal", "instrumental_melody"):
        pitches = [note["midi_pitch"] for note in notes if note["track"] == track]
        profiles[track] = {"note_count": len(pitches),
                           "pitch_min": min(pitches) if pitches else None,
                           "pitch_max": max(pitches) if pitches else None}

    root = re.match(r"^([A-G](?:#|b)?)(.*)$", key or "")
    key_info = {"symbol": key, "root": root.group(1) if root else None,
                "mode": "minor" if root and root.group(2).lower().startswith("m") else
                        ("major" if root else None)}
    return {"source": "sheetsage2_audio_cpp", "score_format": "abc",
            "model_tempo_bpm": tempo, "meter": meter, "key": key_info,
            "key_changes": key_changes, "measure_count": len(bars),
            "chords_by_bar": bars, "chord_progression": progression,
            "structure_sections": sections, "melody_profiles": profiles,
            "melody_notes": notes,
            "event_count": len(events),
            "timing_note": "Chord labels are grouped by ABC measure; melody note times come from SheetSage2 event output."}


def transcribe(root, audio, output, backend="auto"):
    info = availability(root)
    if not info["available"]:
        return {"status": "unavailable", **info}
    root = Path(root)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    backend = _select_backend(backend)
    if backend == "cuda":
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA foi solicitada para SheetSage2, mas não está disponível")
    binary_dir = Path(info["cli"]).parent
    dll_dir = root / "env/tools_yue2/audio-v0.8.0-cudart-windows-x64-cuda12.4"
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join([str(binary_dir), str(dll_dir), env.get("PATH", "")])
    # The upstream C++ model spec's 1-GiB weight arena is too small for this
    # 2.52-GiB FP32 checkpoint. Short clips on 6-GiB GPUs need a larger graph
    # arena and bounded decoder allocation; the 74-s Forró Perfeito input
    # reproduced ggml allocator asserts with the default 768-MiB arena.
    weight_arena = "3072" if backend == "cuda" else "4096"
    audio_duration = None
    try:
        import soundfile as sf
        audio_duration = sf.info(str(audio)).duration
    except Exception:
        pass
    short_cuda_audio = backend == "cuda" and audio_duration is not None and audio_duration <= 120
    graph_arena = "1536" if short_cuda_audio else ("768" if backend == "cuda" else "1536")
    command = [info["cli"], "--family", "sheetsage2", "--task", "midi",
               "--backend", backend, "--threads", "4", "--model", info["model"],
               "--session-option", f"weight_context_mb={weight_arena}",
               "--session-option", f"decoder_graph_arena_mb={graph_arena}",
               "--audio", str(Path(audio).resolve()), "--out-dir", str(output.resolve()), "--log"]
    if short_cuda_audio:
        command.extend(["--max-tokens", "2048"])
    log_path = output / "sheetsage.log"
    try:
        with log_path.open("w", encoding="utf-8") as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=7200,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.CalledProcessError:
        # On the 6-GiB CUDA runtime, some short (<300 s) clips hit a ggml
        # context/graph allocation assert with the default 768-MiB graph
        # arena. Retry only those explicit allocator failures with a larger
        # arena and a bounded decoder budget; long recordings retain the
        # proven default configuration and full output limit.
        failure_log = log_path.read_text(encoding="utf-8", errors="replace")
        allocator_assertions = ("GGML_ASSERT(ctx->mem_buffer != NULL)",
                                "GGML_ASSERT(galloc->node_allocs != NULL)")
        duration = audio_duration
        if backend == "cuda" and not short_cuda_audio and any(
                marker in failure_log for marker in allocator_assertions):
            try:
                import soundfile as sf
                duration = sf.info(str(audio)).duration
            except Exception:
                pass
        if backend != "cuda" or duration is None or duration >= 300:
            raise
        retry_command = command.copy()
        graph_option = next(i for i, value in enumerate(retry_command)
                            if value.startswith("decoder_graph_arena_mb="))
        retry_command[graph_option] = "decoder_graph_arena_mb=1536"
        retry_command.extend(["--max-tokens", "2048"])
        with log_path.open("a", encoding="utf-8") as log:
            log.write("\nSheetSage2 retry: CUDA allocator assertion on short clip; "
                      "decoder_graph_arena_mb=1536, max_tokens=2048.\n")
            log.flush()
            subprocess.run(retry_command, env=env, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=7200,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    abc = _abc_score(output)
    score_path = output / "score.abc"
    score_path.write_text(abc, encoding="utf-8")
    events = _event_payload(output)
    if events is not None:
        with (output / "events.json").open("w", encoding="utf-8") as stream:
            json.dump(events, stream, ensure_ascii=False, separators=(",", ":"))
    structured = _parse_score(abc, events)
    return {"status": "completed", "backend": backend, "score": "score.abc",
            "events": "events.json" if events is not None else None,
            "model_size": info["model_size"], "structured": structured,
            "alignment_used": False,
            "message": "ABC e eventos SheetSage2 preservados; dados harmônicos incorporados à análise."}
