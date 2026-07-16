# -*- coding: utf-8 -*-
# Vortex DJ Mix Engine Module - [v2026.RTX_ULTRA]
# Orchestrates professional multi-track transitions and Super-Mix.

import logging
import time
import shutil
import subprocess
from pathlib import Path
import nexus.core as core

def ignite_mix_lot_logic(dj, valid_metadata):
    """Fase 2: MAESTRO (ASSÍNCRONO)."""
    import threading
    
    logging.info("🔒 [GUARD] BLOQUEANDO CPU PARA TRABALHO PESADO (MIXING)...")
    dj.worker_busy = True
    total_steps = len(valid_metadata) - 1
    
    def run():
        try:
            dj.project_state["current_task"] = "🚀 Inicializando motor Vortex..."
            if "error" in dj.project_state: del dj.project_state["error"]
            dj.save_status()

            dj.project_state["current_task"] = "🔬 Analisando espectro e agendando efeitos..."
            curation = dj.curate_set_fast()
            master_plan = []
            for i, step in enumerate(curation):
                trans = step['transition']
                if trans.get('is_super'):
                    logging.info(f"🔥 [SUPER MIX] AGENDADA: {step['track_a']} ➔ {step['track_b']}")
                    dj.project_state.setdefault("logs", []).append(f"🔥 [SUPER MIX] AGENDADA: {step['track_a']} ➔ {step['track_b']}")
                
                master_plan.append({
                    "id": i,
                    "track_a": step['track_a'],
                    "track_b": step['track_b'],
                    "type": trans['type'],
                    "dur": trans['duration'],
                    "target_bpm": trans['target_bpm'],
                    "mid_fx": trans.get('fx_a', []) + trans.get('fx_b', []),
                    "advice": trans.get('advice', "Auto-Mix")
                })

            dj.project_state["master_plan"] = master_plan
            dj.save_status()

            current_track_data = valid_metadata[0]
            for i in range(len(valid_metadata) - 1):
                track_a = valid_metadata[i]
                track_b = valid_metadata[i+1]
                
                is_super = False
                bpm_diff = abs(track_a.get('bpm', 120) - track_b.get('bpm', 120))
                if bpm_diff < 4 and track_a.get('energy', 0) > 0.05:
                    is_super = True
                    logging.info(f"🔥 [SUPER MIX] DETECTADA: {track_a['name']} ➔ {track_b['name']} será épica!")
                    dj.project_state.setdefault("logs", []).append(f"🔥 [SUPER MIX] ATIVADA: {track_a['name']} ➔ {track_b['name']}")
                
                if not dj.worker_busy:
                    logging.warning("🛑 [VORTEX] Interrupção detectada no worker de mixagem.")
                    break

                current_pair = [track_a, track_b]
                use_instrumental = dj._check_vocal_conflict(current_pair[0], current_pair[1])
                
                track_a_name = current_pair[0]['name'].split('.')[0]
                track_b_name = current_pair[1]['name'].split('.')[0]
                
                if is_super:
                    dj.project_state["current_task"] = f"🎙️ [SUPER MIX] Isolando Stems de A e B..."
                    dj.save_status()
                    for track in [current_pair[0], current_pair[1]]:
                        t_name = track['name'].split('.')[0]
                        vocal_p = dj.stems_dir / f"{t_name}_vocals.mp3"
                        instr_p = dj.stems_dir / f"{t_name}_instrumental.mp3"
                        if not vocal_p.exists() or not instr_p.exists():
                            dj.separate_stems(track['path'])
                        track['vocal_path'] = str(vocal_p) if vocal_p.exists() else track['path']
                        track['instr_path'] = str(instr_p) if instr_p.exists() else track['path']
                
                if use_instrumental and not is_super:
                    dj.project_state["current_task"] = f"🎙️ Isolando Instrumental: {track_b_name}..."
                    dj.save_status()
                    instr_path = dj.stems_dir / f"{track_b_name}_instrumental.mp3"
                    if not instr_path.exists():
                        dj.separate_stems(current_pair[1]['path'])
                    if instr_path.exists():
                        current_pair[1]['path'] = str(instr_path)
                
                dj.project_state["current_task"] = f"🎧 Mixando: {track_a_name} ➔ {track_b_name} ({i+1}/{total_steps}) | ⏳ 0%"
                dj.save_status()
                
                mix_id = f"mix_{i}_{track_a_name}_to_{track_b_name}"
                final_track_a_name = f"{i+1:02d} - {track_a_name}.mp3"
                next_temp_base = f"base_for_next_{i}.mp3"
                
                file_exists = (dj.output_dir / next_temp_base).exists()
                if mix_id in dj.project_state.get("completed_mixes", []) and file_exists:
                    logging.info(f"♻️ [RESTORE] Pulando Mix {i+1} (Já existe no disco)")
                    current_track_data = {"path": str(dj.output_dir / next_temp_base), "name": next_temp_base, "bpm": current_pair[1]['bpm']}
                    continue

                decision = next((p for p in master_plan if p.get('id') == i), None)
                if not decision: decision = {"target_bpm": current_pair[1].get('bpm', 120), "dur": 10, "type": "crossfade", "advice": "Standard."}
                
                advice = decision.get('advice', "Transição fluída.")
                dj.project_state["current_task"] = f"🧠 Estratégia: {advice} ({i+1}/{total_steps})"
                dj.save_status()

                t_type = decision.get('type', decision.get('transition_type', 'crossfade'))
                mix_dur = decision.get('dur', decision.get('mix_duration', 10))
                
                raw_mid_fx = decision.get('mid_fx', decision.get('mid_track_fx', []))
                normalized_fx = []
                for fx in raw_mid_fx:
                    fx_type = fx.get('type', 'stutter').lower()
                    if fx_type == 'aecho': fx_type = 'reverb'
                    normalized_fx.append({
                        "track": fx.get('tr', fx.get('track', 'B')),
                        "time_offset": fx.get('off', fx.get('time_offset', 0)),
                        "type": fx_type
                    })

                next_track_data = {**current_pair[1], "transition_type": t_type, "mix_duration": mix_dur, "mid_track_fx": normalized_fx}
                temp_mix_name = f"temp_mix_{i}.mp3"
                temp_mix_path = dj.output_dir / temp_mix_name
                
                dj.mix_tracks_professional(current_track_data, next_track_data, temp_mix_name, custom_output=temp_mix_path)
                
                dj.project_state["current_task"] = f"🔪 Finalizando Mix {i+1}..."
                dj.save_status()
                
                bpm_a = current_track_data.get('bpm', 120)
                target_bpm = decision.get('target_bpm', bpm_a)
                speed_a = target_bpm / bpm_a if bpm_a > 0 else 1.0
                
                dur_in_raw = core.get_audio_duration(current_track_data['path'])
                dur_in_adjusted = dur_in_raw / speed_a
                
                mix_dur_final = decision.get('dur', decision.get('mix_duration', 10))
                split_point = max(0.1, dur_in_adjusted - (mix_dur_final / 2))
                
                logging.info(f"✂️ [SLICE] Speed A: {speed_a:.3f} | Adjusted Dur: {dur_in_adjusted:.2f}s | Split: {split_point:.2f}s")
                
                mix_actual_dur = core.get_audio_duration(temp_mix_path)
                safe_split = min(split_point, mix_actual_dur - 0.1)
                
                logging.info(f"✂️ [SLICE] Real Dur: {mix_actual_dur}s | Target Split: {safe_split}s")

                mastering = "alimiter=limit=0.9"
                clean_name = track_a_name.replace("_", " ")
                subprocess.run(['ffmpeg', '-y', '-i', str(temp_mix_path), '-t', str(safe_split), '-af', mastering, '-map_metadata', '-1', '-metadata', f'title={clean_name}', '-c:a', 'libmp3lame', '-q:a', '2', str(dj.output_dir / final_track_a_name)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['ffmpeg', '-y', '-i', str(temp_mix_path), '-ss', str(safe_split), '-map_metadata', '-1', '-c:a', 'libmp3lame', '-q:a', '2', str(dj.output_dir / next_temp_base)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                if not (dj.output_dir / next_temp_base).exists():
                    logging.error(f"❌ Erro: Falha ao gerar base para a próxima música ({next_temp_base})")
                    raise Exception(f"Erro no fatiamento da trilha {i+1}")

                dj.project_state.setdefault("transition_history", []).append({
                    "pair": f"{track_a_name} -> {track_b_name}",
                    "type": t_type, "duration": mix_dur, "advice": decision.get('advice', "")
                })
                dj.project_state.setdefault("completed_mixes", []).append(mix_id)
                dj.save_status()
                
                current_track_data = {"path": str(dj.output_dir / next_temp_base), "name": next_temp_base, "bpm": decision.get('target_bpm', current_pair[1].get('bpm', 120))}

            final_song_idx = len(valid_metadata)
            final_song_name = f"{final_song_idx:02d} - {valid_metadata[-1]['name']}"
            if (dj.output_dir / next_temp_base).exists():
                logging.info(f"💾 [FINAL] Salvando trilha de encerramento: {final_song_name}")
                shutil.copy(dj.output_dir / next_temp_base, dj.output_dir / final_song_name)

            dj.project_state["current_task"] = "✅ Mixagem concluída com sucesso!"
            dj.save_status()

        except Exception as e:
            err_msg = f"❌ ERRO CRÍTICO: {str(e)}"
            logging.error(err_msg)
            dj.project_state["current_task"] = err_msg
            dj.project_state.setdefault("logs", []).append(err_msg)
            dj.save_status()
        finally:
            dj.worker_busy = False

    threading.Thread(target=run).start()
