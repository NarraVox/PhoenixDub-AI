"""Compile arrangement plans into YuE2's documented ABC/style controls."""
import json
import math

from .planning import validate_arrangement


def _style_character(arrangement):
    pack = arrangement.get("style_pack") or {}
    name = str(pack.get("name") or (arrangement.get("source_style") or {}).get("name") or "")
    drums = arrangement.get("drums") or {}
    bass = arrangement.get("bass") or {}
    keys = arrangement.get("keyboard_accompaniment") or {}
    instruments = arrangement.get("instrumentation") or []
    suggestions = []
    for item in instruments:
        if isinstance(item, dict):
            suggestions.extend(map(str, item.get("suggestions", [])))
    timbres = keys.get("timbre_suggestions", [])
    suggestions.extend(map(str, timbres))
    # Style is a broad timbral/groove hint. Step events and exact source patterns
    # remain preserved in arrangement.json, not misrepresented as YuE2 controls.
    descriptors = ["forró eletrônico dance-band character" if "for" in name.lower() else "dance-band character"]
    descriptors.extend(["steady syncopated percussion groove" if drums else "steady percussion groove",
                        "pulsing bass supporting the new chord roots and fifths" if bass else "bass supporting the harmony",
                        "offbeat keyboard and accordion-style accompaniment" if keys else "harmonic accompaniment"])
    if suggestions:
        descriptors.append("timbres: " + ", ".join(dict.fromkeys(suggestions)))
    return "; ".join(descriptors)


def compile_yue2_request(arrangement, abc_file=None):
    """Create direct YuE2 fields plus broad style text; ABC carries score controls."""
    if not isinstance(arrangement, dict):
        raise ValueError("arrangement.json deve conter um objeto JSON")
    validate_arrangement(arrangement)
    bpm = int(round(float(arrangement["tempo_bpm"])))
    duration = float(arrangement["duration_estimate_seconds"])
    if not math.isfinite(duration) or not 1 <= duration <= 600:
        raise ValueError("Duração do arrangement precisa estar entre 1 e 600 segundos")
    meter = str(arrangement.get("meter") or "4/4")
    tokens = max(1, round(duration * 25))
    # The previous 10%, 1.5x and 3x caps were reached by real sampled runs.
    # Use 6x (minimum +512) so the semantic decoder can end naturally instead
    # of treating the intended duration estimate as a hard generation cutoff.
    semantic_max = max(round(tokens * 6), tokens + 512)
    style = (f"{_style_character(arrangement)}. Tempo {bpm:g} BPM, meter {meter}. "
             "Follow the supplied ABC score for the new vocal melody, chord symbols and form. "
             "Keep the accompaniment in the described genre and timbral palette.")
    lyrics = arrangement.get("lyrics") or "[instrumental]"
    return {
        "lyrics": lyrics,
        "style_prompt": style,
        "target_duration_seconds": round(duration, 2),
        "target_tokens": tokens,
        "direct_controls": {
            "backend": "cuda", "task": "gen", "family": "yue2",
            "lyrics": lyrics, "style": style, "cot": "full", "abc_file": abc_file,
            "semantic_min_tokens": int(tokens * .9), "semantic_max_tokens": semantic_max,
        },
        "prompt_only": ["style/groove character", "instrumentation and timbres", "broad accompaniment behavior"],
        "score_conditioned": ["Vocal melody", "Ins monophonic instrumental line", "chord symbols", "key", "meter", "tempo", "barline/form layout"],
        "not_directly_supported": ["independent Drums/Bass/Comp ABC voices", "exact drum hits", "polyphonic chord voicings", "section-specific dynamics automation"],
        "limitations": ["YuE2 may reinterpret score rather than obey each note/bar exactly.",
                        "Drum attacks, accompaniment steps and dynamics remain plan evidence, not dedicated YuE2 controls.",
                        "Duration is approximate; semantic max is an upper bound, not a duration guarantee."],
        "arrangement_sha256": __import__("hashlib").sha256(json.dumps(arrangement, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest(),
    }


def qwen_enrich_prompt(arrangement, base_prompt, generator=None):
    """Optional local Qwen prompt refinement under arrangement constraints."""
    system = ("Convert this plan into an English YuE2 style prompt. Preserve tempo, meter, broad form, "
              "instrument roles and new harmony. Do not invent exact note sequences or quote reference melody. "
              "Return only the concise style prompt.")
    user = json.dumps({"arrangement": arrangement, "draft_prompt": base_prompt}, ensure_ascii=False)
    if generator is None:
        from nexus.core import qwen_loader
        llm = qwen_loader.get_qwen_model()
        if llm and llm != "standalone_server":
            model_path = str(getattr(llm, "model_path", "")).lower()
            template = (f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n"
                        if "qwen" in model_path else f"<start_of_turn>user\n{system}\n\n{user}<end_of_turn>\n<start_of_turn>model\n")
            result = llm(template, temperature=0.2, max_tokens=900,
                         stop=["<|im_end|>", "<|im_start|>"] if "qwen" in model_path else ["<end_of_turn>"])
            text = result["choices"][0].get("text", "")
        else:
            import requests
            text, last_error = "", None
            for url in ("http://127.0.0.1:8080/v1/completions", "http://127.0.0.1:1234/v1/completions"):
                try:
                    response = requests.post(url, json={"prompt": f"{system}\n\n{user}", "temperature": 0.2,
                                                        "max_tokens": 900, "model": "local-model"}, timeout=120)
                    response.raise_for_status()
                    text = response.json()["choices"][0]["text"]
                    break
                except Exception as exc:
                    last_error = exc
            if not text:
                raise RuntimeError(f"Qwen local indisponível: {last_error}")
    else:
        text = generator(system, user)
    text = str(text).strip()
    if len(text) < 40:
        raise ValueError("Qwen retornou um prompt vazio ou curto demais")
    return text + "\n" + base_prompt
