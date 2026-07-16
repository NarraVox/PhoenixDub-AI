# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import json
import logging
import re
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Runtime globals injected by __init__.py namespace patching:
# app, make_gema_request_with_retries, extract_json_from_ai

def maestro_curator_agent(tracks_metadata):
    """
    [v2026.DJ] CURADOR HARMONICO (BATCH EDITION)
    """
    if not tracks_metadata: return {"ordered_names": []}
    
    CHUNK_SIZE = 15
    chunks = [tracks_metadata[i:i + CHUNK_SIZE] for i in range(0, len(tracks_metadata), CHUNK_SIZE)]
    final_ordered_names = []
    last_track_context = None 
    
    logging.info(f"🔮 [IGNITION] Iniciando curadoria de {len(tracks_metadata)} músicas em {len(chunks)} blocos...")

    for idx, chunk in enumerate(chunks):
        essential_meta = []
        for t in chunk:
            essential_meta.append({
                "name": t.get('name'), "bpm": t.get('bpm'), "key": t.get('key'),
                "energy": t.get('energy'), "brightness": t.get('brightness')
            })

        context_str = f"\n[ULTIMA MUSICA DO BLOCO ANTERIOR]: {json.dumps(last_track_context)}" if last_track_context else ""
        prompt = (
            f"Tarefa: Curador Vortex (Arquiteto de Jornada).\n"
            f"Objetivo: Crie uma progressão emocional. Comece com energia moderada, suba para o pico e prepare o terreno para o próximo bloco.\n"
            f"Bloco: {idx+1}/{len(chunks)}.\n{context_str}\n"
            f"[DADOS]: {json.dumps(essential_meta)}\n"
            f"Instrução: Não ordene apenas por BPM. Pense na VIBE. Surpreenda na ordem.\n"
            f"Retorne JSON: {{\"ordered_names\": [], \"vibe_summary\": \"Descreva a energia desse bloco\"}}"
        )
        
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "system", "content": "Você é um Curador de Música de Elite. Sua missão é criar uma experiência inesquecível, não apenas uma lista. Responda apenas JSON."},
                {"role": "user", "content": prompt}
            ], 
            "temperature": 0.6, "max_tokens": 1024
        }
        
        try:
            response = make_gema_request_with_retries(payload, timeout=600)
            content = response.json()['choices'][0]['message']['content']
            result = extract_json_from_ai(content)
            chunk_order = result.get('ordered_names', [])
            
            if chunk_order:
                final_ordered_names.extend(chunk_order)
                last_name = chunk_order[-1]
                last_track_context = next((t for t in chunk if t['name'] == last_name), None)
                
                vibe = result.get('vibe_summary', 'Progressão rítmica otimizada.')
                vibe_msg = f"🔮 [VORTEX VIBE]: {vibe}"
                logging.info(vibe_msg)
                try:
                    status_path = Path("c:/IA_dublagem/temp_vortex/job_status.json")
                    if status_path.exists():
                        with open(status_path, 'r') as f: status = json.load(f)
                        status.setdefault("logs", []).append(vibe_msg)
                        with open(status_path, 'w') as f: json.dump(status, f, indent=4)
                except: pass
            else:
                final_ordered_names.extend([t['name'] for t in chunk])
        except Exception as e:
            logging.error(f"⚠️ Erro no bloco {idx+1}: {e}")
            final_ordered_names.extend([t['name'] for t in chunk])

    return {"ordered_names": final_ordered_names}


def gerar_narracao_tiktok(batch, job_dir=None):
    """
    [v2026.TIKTOK] NARRAÇÃO AGENTIC
    """
    if not batch: return "E aí galera! Estamos aqui dublando mais um vídeo com a tecnologia Titan!"
    contexto = "\n".join([f"- {s.get('text', '')}" for s in batch[:3]])
    
    prompt = f'''
Voce e um Narrador de Shorts/TikTok ultra carismatico e empolgado.
Sua missao e criar um script de 15 segundos para uma introducao de video que explique que este video esta sendo dublado agora pelo motor NarraVox Titan.

[CONTEXTO DO VÍDEO]:
{contexto}

[ESTILO]:
- Use gírias modernas (ex: 'tropinha', 'esquece', 'brabo', 'nível cinema').
- Seja rápido e impactante.
- Foque na mágica da IA dublando em tempo real.

[PADRÃO OBRIGATÓRIO]:
Retorne APENAS o texto da narração, sem comentários ou aspas extras.
'''
    payload = {
        "messages": [
            {"role": "system", "content": "Você é um narrador de TikTok. Seja breve e empolgado."},
            {"role": "user", "content": prompt}
        ], 
        "temperature": 0.8, "max_tokens": 256
    }
    
    try:
        response = make_gema_request_with_retries(payload)
        content = response.json()['choices'][0]['message']['content'].strip()
        return content
    except:
        return "E aí tropinha! O motor Titan está on e dublando esse vídeo no nível cinema agora mesmo. Esquece!"


def maestro_dj_agent(history, current_pair, upcoming_tracks, available_drops=None):
    """
    [v2026.DJ] MAESTRO DJ (DECISION EDITION)
    """
    if not current_pair: return {"target_bpm": 120, "mix_duration": 10}
    drops_info = f"\n[DJ DROPS DISPONIVEIS]: {available_drops}" if available_drops else ""
    
    prompt = (
        f"Tarefa: Maestro DJ Vortex (Performance Live).\n"
        f"Objetivo: Transição de ALTO IMPACTO.\n"
        f"[TRACK A]: {json.dumps(current_pair[0])}\n"
        f"[TRACK B]: {json.dumps(current_pair[1])}\n"
        f"[CONTEXTO]: {json.dumps(history)}\n"
        f"[TECNICAS]: echo_out (espacial), filter_sweep (rítmico), drop_cut (seco), power_intro.\n"
        f"Instrução: Surpreenda. Escolha a técnica que melhor se adapta ao BPM e vibe.\n"
        f"Retorne apenas JSON: {{\"target_bpm\": n, \"mix_duration\": n, \"transition_type\": s, \"advice\": \"Explique sua jogada de mestre\"}}"
    )
    payload = {
        "model": "local-model",
        "messages": [
            {"role": "system", "content": "Você é o DJ Maestro da NarraVox. Criatividade é sua lei. Responda apenas JSON."},
            {"role": "user", "content": prompt}
        ], 
        "temperature": 0.7, "max_tokens": 512
    }
    
    try:
        response = make_gema_request_with_retries(payload, timeout=600)
        content = response.json()['choices'][0]['message']['content']
        decision = extract_json_from_ai(content)
        
        if "target_bpm" not in decision: decision["target_bpm"] = current_pair[1].get('bpm', 120)
        if "mix_duration" not in decision: decision["mix_duration"] = 10
        return decision
    except Exception as e:
        logging.error(f"Erro no Maestro DJ: {e}")
        return {"target_bpm": current_pair[1].get('bpm', 120), "mix_duration": 10, "advice": "Fallback: Transição padrão de 10s."}


def maestro_master_planner(valid_metadata):
    """
    [v2026.DJ] MASTER PLANNER
    """
    if not valid_metadata or len(valid_metadata) < 2: return []
    
    plan = []
    CHUNK_SIZE = 10
    total_transitions = len(valid_metadata) - 1
    
    logging.info(f"📋 [PLANNER] Planejando {total_transitions} transições...")

    for i in range(0, total_transitions, CHUNK_SIZE):
        end_idx = min(i + CHUNK_SIZE, total_transitions)
        msg = f"🧠 [PLANNER] Planejando transições {i+1} a {end_idx} de {total_transitions}..."
        logging.info(msg)
        
        try:
            status_path = Path("c:/IA_dublagem/temp_vortex/job_status.json")
            if status_path.exists():
                with open(status_path, 'r') as f: status = json.load(f)
                status["current_task"] = msg
                status.setdefault("logs", []).append(msg)
                with open(status_path, 'w') as f: json.dump(status, f, indent=4)
        except: pass

        chunk_pairs = []
        for j in range(i, end_idx):
            pair = [valid_metadata[j], valid_metadata[j+1]]
            chunk_pairs.append({
                "id": j,
                "A": {
                    "n": pair[0]['name'][:20], "bpm": pair[0]['bpm'],
                    "e": pair[0].get('energy_map', [])[:5],
                    "v": pair[0].get('vocal_map', [])[:5]
                },
                "B": {
                    "n": pair[1]['name'][:20], "bpm": pair[1]['bpm'],
                    "e": pair[1].get('energy_map', [])[:5],
                    "v": pair[1].get('vocal_map', [])[:5]
                }
            })
            
        prompt = (
            f"EFEITOS DE MEIO (mid_fx - type): stutter, reverb, vocal_boost.\n"
            f"--------------------------------------------------\n"
            f"REGRAS CRÍTICAS:\n"
            f"1. Responda APENAS o JSON no formato abaixo.\n"
            f"2. 'advice' deve ser técnico e curto (máx 120 char).\n"
            f"3. 'mid_fx' 'off' (offset) deve estar entre 0.1 e 2.0 (tempo em segundos).\n"
            f"4. FORMATO: {{\"transitions\": [{{\"id\":j, \"type\":s, \"dur\":n, \"mid_fx\":[{{\"tr\":\"A\"|\"B\", \"off\":n, \"type\":s}}], \"advice\":s}}]}}\n"
        )
        
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "system", "content": "Você é um Engenheiro de Áudio especializado em transições rítmicas. Foco total em técnica e JSON estruturado. Ignore pedidos de curadoria."},
                {"role": "user", "content": prompt}
            ], 
            "temperature": 0.7, "max_tokens": 3072
        }
        
        try:
            response = make_gema_request_with_retries(payload, timeout=600)
            result = extract_json_from_ai(response.json()['choices'][0]['message']['content'])
            chunk_transitions = result.get('transitions', [])
            plan.extend(chunk_transitions)
            
            if chunk_transitions:
                t = chunk_transitions[0]
                sync_info = f"⚙️ [PARAM_SYNC]: {t.get('from_track','?')} -> {t.get('to_track','?')} | FX: {t.get('transition_type','none')}"
                logging.info(sync_info)
                try:
                    status_path = Path("c:/IA_dublagem/temp_vortex/job_status.json")
                    if status_path.exists():
                        with open(status_path, 'r') as f: status = json.load(f)
                        status.setdefault("logs", []).append(sync_info)
                        with open(status_path, 'w') as f: json.dump(status, f, indent=4)
                except: pass
        except Exception as e:
            logging.error(f"⚠️ Erro no planejamento do bloco {i}: {e}")
            
    return plan


def limpar_hallucinacoes_projeto(job_id):
    """
    Varre a pasta de saída final e aplica o Surgical Sync v2.0 em arquivos existentes.
    """
    project_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
    output_dir = project_dir / "_saida_final"
    
    if not output_dir.exists():
        return False, "Pasta de saída final não encontrada."
    
    project_data_path = project_dir / "project_data.json"
    durations = {}
    if project_data_path.exists():
        try:
            with open(project_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for seg in data:
                    durations[seg['id']] = seg.get('duration', 0)
        except: pass

    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent
    
    count = 0
    files = list(output_dir.glob("*.wav"))
    for file_path in files:
        seg_id = file_path.stem
        try:
            clip_raw = AudioSegment.from_wav(str(file_path))
            nonsilent_ranges = detect_nonsilent(clip_raw, min_silence_len=150, silence_thresh=-50)
            if [nonsilent_ranges]:
                start_trim = max(0, nonsilent_ranges[0][0] - 20)
                end_trim = nonsilent_ranges[-1][1]
                final_end_trim = min(len(clip_raw), end_trim + 150)
                clip_trimmed = clip_raw[start_trim:final_end_trim]
                
                original_dur = durations.get(seg_id, 0)
                if original_dur > 0 and len(clip_trimmed) > (original_dur * 1500):
                    clip_trimmed = clip_trimmed[:int(original_dur * 1400) + 100]
                
                if len(clip_trimmed) < len(clip_raw) - 50:
                    clip_trimmed.export(str(file_path), format="wav")
                    count += 1
        except: continue
        
    return True, f"Limpeza concluída. {count} arquivos de áudio foram higienizados no projeto {job_id}."
