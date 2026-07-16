# -*- coding: utf-8 -*-
# Vortex DJ Curation Module - [v2026.RTX_ULTRA]
# Automatic playlist curation, spectral analysis, and vocal conflict resolution.

import logging

def auto_schedule_fx_logic(dj, track_name, track_data):
    """Analisa o espectro e agenda efeitos estratégicos (Build-ups, Drops, Scratches)."""
    fx_list = []
    energy_map = track_data.get('energy_map', [])
    duration = track_data.get('duration', 200)
    if not energy_map: return []

    # 1. BUILD-UP: Detecta subida brusca para Sweep/Flanger
    for i in range(1, len(energy_map)):
        if energy_map[i] > energy_map[i-1] * 1.4:
            time_at = (i / len(energy_map)) * duration
            fx_list.append({"type": "filter_sweep", "time_offset": max(0, time_at - 4), "track": "B"})
            break

    # 2. DROP & SCRATCH: Localiza o pico máximo e aplica o "DJ Hero Scratch"
    max_idx = energy_map.index(max(energy_map))
    drop_time = (max_idx / len(energy_map)) * duration
    
    # Scratch agressivo 1 segundo antes do drop
    fx_list.append({"type": "scratch", "time_offset": max(0, drop_time - 1), "track": "A"})
    # Stutter rítmico no impacto do drop
    fx_list.append({"type": "stutter", "time_offset": drop_time, "track": "B"})
            
    # 3. AMBIENT MODS (DJ Hero Vibe): Efeitos aleatórios rítmicos ao longo da música
    for i in range(2, len(energy_map) - 2):
        if i % 3 == 0: # Adiciona um "tempero" a cada ~10-15s
            time_at = (i / len(energy_map)) * duration
            fx_type = "bitcrush" if i % 2 == 0 else "pulsar"
            fx_list.append({"type": fx_type, "time_offset": time_at, "track": "A"})

    # 4. VOCAL INTELLIGENCE (Whisper Reaction): Reage a palavras fortes ou fim de frases
    transcription = track_data.get('transcription', "")
    if transcription:
        strong_words = ["dale", "vai", "agora", "now", "go", "fire", "beat", "drop"]
        words = transcription.lower().split()
        if any(sw in words for sw in strong_words):
            fx_list.append({"type": "echo_out", "time_offset": duration / 2, "track": "A"})
            
    return fx_list

def curate_set_fast_logic(dj):
    """Versão Turbo: Curadoria instantânea e mapeamento de Auto-FX."""
    logging.info("🚀 [VORTEX MASTER] Planejando setlist e efeitos via análise de espectro...")
    tracks = dj.project_state.get("tracks", {})
    if not tracks: return []
    
    sorted_tracks = sorted(tracks.items(), key=lambda x: x[1].get('bpm', 120))
    sequence = []
    for i in range(len(sorted_tracks) - 1):
        name_a, data_a = sorted_tracks[i]
        name_b, data_b = sorted_tracks[i+1]
        
        # Agenda efeitos matemáticos
        fx_a = dj._auto_schedule_fx(name_a, data_a)
        fx_b = dj._auto_schedule_fx(name_b, data_b)
        
        # [v2026.PERSONALITY] Escolhe o humor do set baseado na energia média
        avg_energy = (data_a.get('energy', 0) + data_b.get('energy', 0)) / 2
        if avg_energy > 0.08: personality = "festival"
        elif avg_energy > 0.05: personality = "agressivo"
        else: personality = "suave"
        
        if personality == "festival":
            t_type, dur = "filter_sweep", 40 # Extended Mix de Festival (20-40s)
            advice = "🎪 MODO FESTIVAL: Extended Mashup & Silêncio Épico"
            is_super = True
            fx_a.append({"type": "silence_pre_drop", "time_offset": dur - 0.5, "track": "A"})
            fx_a.append({"type": "echo_out", "time_offset": dur - 3, "track": "A"})
        elif personality == "agressivo":
            t_type, dur = "drop_cut", 6
            advice = "💥 MODO AGRESSIVO: Cortes Rápidos & Scratches"
            is_super = False
        else:
            t_type, dur = "acrossfade", 12
            advice = "🍃 MODO SUAVE: Transições Orgânicas"
            is_super = False
        
        sequence.append({
            "track_a": name_a, "track_b": name_b,
            "transition": {
                "type": t_type, "duration": dur, "target_bpm": data_b.get('bpm', 120),
                "fx_a": fx_a, "fx_b": fx_b, "advice": advice, "is_super": is_super,
                "personality": personality
            }
        })
    return sequence

def check_vocal_conflict_logic(dj, data_a, data_b):
    """Verifica se há conflito de vozes na transição (v2026.STEM_LOGIC)."""
    v_a = data_a.get('vocal_map', [])
    v_b = data_b.get('vocal_map', [])
    if not v_a or not v_b: return False
    
    # Olha os últimos 20% da A e os primeiros 20% da B
    if v_a[-1] > 2000 and v_b[0] > 2000:
        logging.warning(f"🎙️ [VOCAL CONFLICT] Detectado! Ativando lógica de Stems...")
        return True
    return False
