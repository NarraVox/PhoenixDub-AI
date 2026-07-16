# -*- coding: utf-8 -*-
# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import time
import subprocess
import logging
import json
import re
import threading
import hashlib
import gc
import shutil
import torch
import traceback
import struct
import datetime
from pathlib import Path
from datetime import timedelta
from collections import OrderedDict
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
from pydub import AudioSegment, effects

# --- IMPORTAÇÃO DO CÉREBRO (NEXUS CORE) ---
try:
    import nexus.core as core
except ImportError:
    print("[ERRO CRÍTICO] nexus.core não encontrado!")
    sys.exit(1)

# --- DEPENDÊNCIAS DE ENGENHARIA ---
try:
    import vpk
except ImportError:
    vpk = None
try:
    import fsb5
except ImportError:
    fsb5 = None

# --- CONFIGURAÇÕES DE DIRETÓRIO DINÂMICAS ---
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
UPLOAD_FOLDER = BASE_DIR / "uploads"
BACKUP_DIR = UPLOAD_FOLDER / "arch_manager_backups"
MODS_FINALIZADOS_DIR = UPLOAD_FOLDER / "mods_finalizados"
VGMSTREAM_PATH = BASE_DIR / "tools" / "vgmstream-cli" / "vgmstream-cli.exe"
KNOWN_ARCH_MAGICS = [b'Arch01\x00\x00', b'Arch00\x00\x00', b'LTAR\x03\x00\x00\x00']

# --- CONFIGURAÇÕES DE LOGS ---
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "nexus_dub_games.log"

# --- CONFIGURAÇÕES DE SINCRONIA ---
CPS_TARGET = 16.0      # Caracteres por Segundo (Padrão Confortável e Natural)
MAX_SPEEDUP = 1.55      # Limite de aceleração (55%) para manter a naturalidade e evitar truncamento físico
MIN_GAP = 0.1          # Gap mínimo entre frases em segundos

_active_game_jobs = set()
_active_video_jobs = set()

# =================================================================
# PARTE 1: UTILITÁRIOS E SEGURANÇA (VIDEO UTILS) - IMPORTADOS
# =================================================================
from nexus.dub.utils import (
    speedup_audio,
    is_reaction_or_noise,
    get_best_encoder,
    calcular_hash_sha1,
    sanitize_archive_name,
    silent_subprocess
)


# =================================================================
# PARTE 2: LÓGICA DE EXTRAÇÃO E REPACK (GAMES)
# =================================================================

def analisar_vpk_logic(caminho_vpk):
    if not vpk: return False, "Biblioteca 'vpk' não instalada."
    try:
        hash_orig = calcular_hash_sha1(caminho_vpk)
        if not hash_orig: return False, "Erro calc hash."
        pak = vpk.open(caminho_vpk)
        info_vpk = OrderedDict([('caminho_original', caminho_vpk), ('nome_arquivo', os.path.basename(caminho_vpk)), ('hash_sha1_original', hash_orig), ('type', 'vpk'), ('status', 'done'), ('arquivos_internos', [])])
        for filepath in pak:
            safe_name = filepath.replace('\\', '/')
            info_vpk['arquivos_internos'].append({'safe_name': safe_name, 'size': 0})
        
        os.makedirs(BACKUP_DIR, exist_ok=True)
        with open(os.path.join(BACKUP_DIR, f"backup_{hash_orig}.json"), 'w', encoding='utf-8') as f:
            json.dump(info_vpk, f, indent=4)
        return True, f"VPK Analisado: {len(info_vpk['arquivos_internos'])} arquivos."
    except Exception as e: return False, f"Erro VPK: {e}"

def analisar_pck_logic(caminho_pck):
    try:
        hash_orig = calcular_hash_sha1(caminho_pck)
        info_pck = OrderedDict([('caminho_original', caminho_pck), ('nome_arquivo', os.path.basename(caminho_pck)), ('hash_sha1_original', hash_orig), ('type', 'pck'), ('status', 'done'), ('arquivos_internos', [])])
        with open(caminho_pck, 'rb') as f:
            magic = f.read(4)
            if magic != b'AKPK': return False, "Não é AKPK."
            header_size, unk, lang_size, bank_size, sound_size, ext_size = struct.unpack('<IIIIII', f.read(24))
            if sound_size > 0:
                f.seek(0x1C + lang_size + bank_size)
                num_sounds = struct.unpack('<I', f.read(4))[0]
                for i in range(num_sounds):
                    sid, align, size, offset, lang_id = struct.unpack('<IIIII', f.read(20))
                    info_pck['arquivos_internos'].append({'safe_name': f"sound_{sid}.wem", 'size': size, 'offset': offset * align})
        
        os.makedirs(BACKUP_DIR, exist_ok=True)
        shutil.copy2(caminho_pck, os.path.join(BACKUP_DIR, f"original_{hash_orig}_{os.path.basename(caminho_pck)}"))
        with open(os.path.join(BACKUP_DIR, f"backup_{hash_orig}.json"), 'w', encoding='utf-8') as f:
            json.dump(info_pck, f, indent=4)
        return True, f"PCK Analisado: {len(info_pck['arquivos_internos'])} sons."
    except Exception as e: return False, f"Erro PCK: {e}"

def reempacotar_pck_logic(input_folder, mod_data):
    try:
        backup_json = os.path.join(BACKUP_DIR, f"backup_{mod_data['original_hash']}.json")
        with open(backup_json, 'r') as f: backup_data = json.load(f)
        caminho_original = backup_data['caminho_original']
        caminho_backup_pck = os.path.join(BACKUP_DIR, f"original_{mod_data['original_hash']}_{os.path.basename(caminho_original)}")
        output_pck = os.path.join(input_folder, "repack_" + os.path.basename(caminho_original))
        
        with open(caminho_backup_pck, 'rb') as f_in, open(output_pck, 'wb') as f_out:
            f_in.seek(0); magic = f_in.read(4)
            h_vals = struct.unpack('<IIIIII', f_in.read(24))
            lang_map = f_in.read(h_vals[2])
            num_banks = struct.unpack('<I', f_in.read(4))[0]
            banks = [list(struct.unpack('<IIIII', f_in.read(20))) for _ in range(num_banks)]
            num_sounds = struct.unpack('<I', f_in.read(4))[0]
            sounds = [list(struct.unpack('<IIIII', f_in.read(20))) for _ in range(num_sounds)]
            
        shutil.copy2(output_pck, caminho_original)
        return True, "Repack PCK Silencioso Concluído!"
    except Exception as e: return False, f"Erro Repack: {e}"

# =================================================================
# PARTE 3: PIPELINE DE DUB DE VÍDEO
# =================================================================

def pipeline_video_master(video_path, job_id, game_profile='padrao', source_lang='auto', target_lang='pt', narrative_mode=False, stop_at_stage=None):
    job_dir = UPLOAD_FOLDER / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    start_time = time.time()
    status_path = job_dir / "job_status.json"
    etapas = ["Extraindo Áudio", "Transcrição/Diarização", "Tradução Agente (Gemma)", "Sincronização", "Geração de Voz (Titan Qwen3)", "Merge Final"]

    def cb(p, etapa_idx, s=None, **kwargs): 
        core.set_progress(job_id, p, etapa_idx, start_time, etapas, s, **kwargs)
        loc_status = core.safe_json_read(status_path) or {
            "job_id": job_id, "video_path": str(video_path), "start_time": start_time, 
            "status": "iniciado", "progress": 0, "message": "Iniciando..."
        }
        loc_status.update({"progress": p, "message": s, "status": etapas[etapa_idx], "start_time": start_time})
        loc_status.update(kwargs)
        core.safe_json_write(loc_status, status_path)

    logging.info("🧹 [SISTEMA] Realizando faxina preventiva de VRAM (PRE-FLIGHT)...")
    cb(5, 0, "Limpando VRAM para o novo motor...")
    core.unload_whisper_model()
    core.unload_qwen3_model()
    core.unload_local_gemma_engine()
    import gc, torch
    gc.collect()
    if torch.cuda.is_available(): torch.cuda.empty_cache()

    cb(2, 0, "Preparando motores Titan...")
    
    existing_status = core.safe_json_read(status_path)
    if existing_status and "total_elapsed_secs" in existing_status:
        total_elapsed = float(existing_status["total_elapsed_secs"])
        start_time = time.time() - total_elapsed
        logging.info(f"⏱️ [RESUME] Cronômetro recuperado: Acumulando {int(total_elapsed)} segundos anteriores.")

    status_initial = {
        "job_id": job_id,
        "video_path": str(video_path),
        "start_time": start_time,
        "status": "iniciado",
        "progress": 0,
        "message": "Preparando motores Titan..."
    }
    core.safe_json_write(status_initial, status_path)

    try:
        profile_data = core.load_game_profile(game_profile)
        audio_cfg = profile_data.get('audio_settings', {})
        ln_filter = audio_cfg.get('loudnorm', 'I=-14:TP=-1.5:LRA=11')

        cb(2, 0, "[SISTEMA] Espelhando vídeo original...")
        ext = os.path.splitext(str(video_path))[1] or ".mp4"
        video_mirror_name = Path(video_path).name
        if len(video_mirror_name) > 100:
             video_mirror_name = video_mirror_name[:90] + "_" + hashlib.md5(video_mirror_name.encode()).hexdigest()[:4] + Path(video_path).suffix
             
        video_mirror = job_dir / video_mirror_name
        if not video_mirror.exists():
            shutil.copy2(str(video_path), str(video_mirror))

        vocals_path = job_dir / "vocals.wav"
        instrumental_path = job_dir / "instrumental.wav"
        
        if vocals_path.exists() and vocals_path.stat().st_size > 10000:
            cb(10, 0, "[Cache] Áudio (Vocais) detectado. Pulando extração.")
        else:
            temp_raw_audio = job_dir / "_raw_audio.wav"
            if temp_raw_audio.exists() and temp_raw_audio.stat().st_size > 10000:
                cb(5, 0, "[Cache] Áudio bruto detectado. Pulando extração...")
            else:
                cb(5, 0, f"[FFmpeg] Extraindo áudio (Modo Turbo)...")
                cmd = [
                    'ffmpeg', '-y', '-hide_banner', '-nostats',
                    '-i', str(video_mirror), 
                    '-vn', '-sn', '-dn', '-map', '0:a:0',
                    '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', 
                    '-f', 'wav', '-threads', '0',
                    str(temp_raw_audio)
                ]
                subprocess.run(cmd, capture_output=True, check=True)
            
            cb(0, 0, "[OpenUnmix] Separando Vocais/Fundo...")
            core.separar_vocal_instrumental(temp_raw_audio, job_dir, cb)
            gc.collect()

        if stop_at_stage == 'separation':
            cb(100, 0, "Etapa de Separação de Áudio concluída!")
            return str(vocals_path)

        project_data_path = job_dir / "project_data.json"
        voice_folders_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
        backup_texto_dir = job_dir / "_backup_texto_final"
        backup_texto_dir.mkdir(exist_ok=True)
        
        existing_data = core.safe_json_read(project_data_path)
        voices_missing = True
        
        if existing_data and "segments" in existing_data and len(existing_data["segments"]) > 0:
            has_voice_dir = voice_folders_dir.exists() and any(voice_folders_dir.iterdir())
            if not has_voice_dir:
                core.recriar_pastas_de_voz(job_dir, vocals_path, existing_data["segments"])
            else:
                # [v2026.SYNC_MANUAL_DIARIZATION] Sincroniza correções de diarização manual das pastas de voz de volta para o project_data
                logging.info("🔄 Sincronizando alterações manuais de oradores das pastas de voz...")
                seg_map = {s['id']: s for s in existing_data["segments"]}
                updated = False
                for wav_file in voice_folders_dir.rglob("*.wav"):
                    if wav_file.name.startswith("seg_") and not wav_file.name.startswith("_REF_"):
                        seg_id = wav_file.stem
                        current_spk = wav_file.parent.name
                        if seg_id in seg_map and seg_map[seg_id].get('speaker') != current_spk:
                            logging.info(f"Orador de {seg_id} alterado manualmente de {seg_map[seg_id].get('speaker')} para {current_spk}")
                            seg_map[seg_id]['speaker'] = current_spk
                            updated = True
                if updated:
                    core.safe_json_write(existing_data, project_data_path)
            
            cb(15, 1, "[Check-up] Preparando amostras de clonagem...")
            core.prepare_video_speaker_references(job_dir)
            
            try:
                first_spk = existing_data["segments"][0]["speaker"]
                sample_seg = voice_folders_dir / first_spk / "seg_0.wav"
                if not sample_seg.exists():
                    core.recriar_pastas_de_voz(job_dir, vocals_path, existing_data["segments"])
            except: pass
                
            cb(20, 1, "[Check-up] Sistema íntegro. Pulando Diarização.")
            segments = existing_data["segments"]
            voices_missing = False
        else:
            voices_missing = True

        if voices_missing:
            cb(0, 1, "[Diarização/Whisper] Mapeando vozes e roteiro...")
            segments = core.transcrever_e_diarizar(vocals_path, job_dir=job_dir, cb=cb, source_lang=source_lang) 
            core.unload_whisper_model()
            gc.collect()

            if not segments:
                raise Exception("❌ ERRO CRÍTICO: A Transcrição falhou!")

            project_data = {"job_id": job_id, "segments": segments, "status": "transcribed"}
            core.safe_json_write(project_data, project_data_path)
            existing_data = project_data

        if stop_at_stage == 'transcription':
            cb(100, 1, "Etapa de Transcrição concluída!")
            return str(project_data_path)

        def get_cache_name(sid):
            clean_id = str(sid).replace("seg_seg_", "seg_")
            return f"{clean_id}.json" if clean_id.startswith("seg_") else f"seg_{clean_id}.json"

        pending_segments = [s for s in segments if not (backup_texto_dir / get_cache_name(s['id'])).exists()]
        translated_batch = []
        total_planned_tr = len(segments)
        cached_count_tr = total_planned_tr - len(pending_segments)
        translation_cache_hit = (cached_count_tr / total_planned_tr) * 100 if total_planned_tr > 0 else 0

        if not pending_segments:
            cb(100, 2, "✅ [Cache] Tradução completa detectada. Pulando motor IA...", translation_cache_hit=100.0)
            for s in segments:
                cached_seg = core.safe_json_read(backup_texto_dir / get_cache_name(s['id']))
                translated_batch.append(cached_seg or s)
        else:
            for s in segments:
                if s['id'] not in [p['id'] for p in pending_segments]:
                    cached_seg = core.safe_json_read(backup_texto_dir / get_cache_name(s['id']))
                    if cached_seg:
                        translated_batch.append(cached_seg)
            
            cb(0, 2, "[Gemma 4] Preparando tradução...")
            while True:
                try:
                    if core.get_local_gemma_engine():
                        break
                    else:
                        msg_alerta = "⚠️ ERRO: MODELO GGUF NÃO ENCONTRADO EM _MODELS_!"
                        cb(40, 2, msg_alerta)
                        time.sleep(4)
                except Exception as e:
                    time.sleep(5)

            lore_file = job_dir / "lore_global.json"
            lore_global = ""
            if lore_file.exists():
                lore_data = core.safe_json_read(lore_file) or {}
                lore_global = lore_data.get("lore", "").strip()
                
            if not lore_global:
                while not core.get_local_gemma_engine():
                    msg_alerta = "⚠️ COLOQUE O MODELO GEMMA GGUF NA PASTA _MODELS_ PARA GERAR A LORE!"
                    cb(40, 2, msg_alerta)
                    time.sleep(4)

                cb(40, 2, "[Gemma 4] Analisando Lore Global...")
                video_title = os.path.basename(video_path) if video_path else None
                lore_global = core.gerar_lore_global(segments, video_title=video_title)
                core.safe_json_write({"lore": lore_global}, lore_file)
            
            core.unload_whisper_model()
            core.unload_qwen3_model()
            gc.collect()
            
        batch_size = 1
        consecutive_failures = 0
        
        REACTION_WORDS_M = {
            "mm", "mm.", "mmm", "ah", "ah.", "oh", "oh.", "hum", "hum.", "hm", "hm.", 
            "uh", "uh.", "uhhuh", "mmhmm", "mhm", "mhm.", "hmm", "wow", "haha", "ha ha", "huh", 
            "hã", "é", "ok", "ops", "oops", "ui", "ai", "ai!", "ui!", "ah!", "oh!", 
            "yeah", "yeah!", "ooh", "aah", "woah"
        }

        for b_idx in range(0, len(pending_segments), batch_size):
            batch = pending_segments[b_idx : b_idx + batch_size]
            first_seg = batch[0]
            clean_text = re.sub(r'[^\w\s]', '', first_seg.get('original_text', first_seg.get('text', '')).lower()).strip()
            
            if clean_text in REACTION_WORDS_M or len(clean_text) <= 1:
                first_seg['text_pt'] = first_seg.get('original_text', first_seg.get('text', ''))
                first_seg['emotion'] = "NORMAL"
                translated_batch.append(first_seg)
                core.safe_json_write(first_seg, backup_texto_dir / get_cache_name(first_seg['id']))
                continue

            first_seg = batch[0]
            i_orig = segments.index(first_seg)
            
            # [v2026.SYNC_MANUAL_DIARIZATION] Calculate gap to the next segment
            gap = 999.0
            if i_orig + 1 < len(segments):
                next_seg = segments[i_orig + 1]
                gap = float(next_seg.get('start', 0.0)) - float(first_seg.get('end', 0.0))
            first_seg['gap_to_next'] = gap

            start_ctx = max(0, i_orig - 4)
            end_ctx = min(len(segments), i_orig + 3)
            
            ctx_lines = []
            for s in segments[start_ctx:end_ctx]:
                speaker = s.get('speaker', 'desconhecido')
                is_current = s['id'] in [b['id'] for b in batch]
                
                if is_current:
                    line = f"{speaker} (fala atual): \"{s.get('original_text', s.get('text', ''))}\""
                else:
                    cached_file = backup_texto_dir / f"seg_{s['id']}.json"
                    text_val = s.get('original_text', s.get('text', ''))
                    if cached_file.exists():
                        cached_data = core.safe_json_read(cached_file)
                        if cached_data and 'text_pt' in cached_data:
                            text_val = cached_data['text_pt']
                    line = f"{speaker}: \"{text_val}\""
                ctx_lines.append(line)
            
            orig_text = batch[0].get('original_text', batch[0].get('text', ''))
            word_count = len(orig_text.split())
            if word_count <= 3:
                ctx_str = "[FRASE CURTA - TRADUÇÃO DIRETA OBRIGATÓRIA]"
            else:
                ctx_str = "\n".join(ctx_lines)

            current_count = b_idx + len(batch)
            total_total = len(pending_segments)
            stage_p = (current_count / total_total * 100)
            p_msg = f"[Gemma 4] Frase {current_count}/{total_total}"
            cb(stage_p, 2, p_msg, current_seg=current_count, total_seg=total_total, translation_cache_hit=translation_cache_hit)

            if not core.get_local_gemma_engine():
                 cb(stage_p, 2, "⚠️ MOTOR IA DESCARREGADO!")
                 time.sleep(5)

            try:
                results_map = core.gema_batch_processor_v2(batch, ctx_str, glossary={'lore_global': lore_global}, profile_id=game_profile, job_dir=job_dir, target_lang=target_lang)
                batch_failed = True
                for seg in batch:
                    s_id_str = str(seg['id']).lower()
                    res = results_map.get(s_id_str)
                    if res:
                        seg['text_pt'] = res['text']
                        seg['emotion'] = res.get('emotion', 'NORMAL')
                        batch_failed = False
                        consecutive_failures = 0
                        status_info = res.get('status', '')
                        if status_info:
                            p_msg_status = f"[Gemma 4] Frase {current_count}/{total_total} ({status_info})"
                            cb(stage_p, 2, p_msg_status, current_seg=current_count, total_seg=total_total, translation_cache_hit=translation_cache_hit)
                    else:
                        seg['text_pt'] = seg.get('original_text', seg.get('text', ''))
                        seg['emotion'] = "NORMAL"

                    translated_batch.append(seg)
                    core.safe_json_write(seg, backup_texto_dir / get_cache_name(seg['id']))

                if batch_failed:
                    consecutive_failures += 1
                if consecutive_failures >= 3:
                    raise Exception("❌ ERRO CRÍTICO: 3 lotes seguidos falharam.")
            except Exception as e:
                raise e

        core.unload_local_gemma_engine()
        gc.collect()

        translated_batch.sort(key=lambda x: float(x.get('start', 0.0)))
        project_data = {"job_id": job_id, "segments": translated_batch, "status": "translated"}
        core.safe_json_write(project_data, job_dir / "project_data.json")

        if stop_at_stage == 'translation':
            cb(100, 2, "Etapa de Tradução concluída!")
            return str(project_data_path)

        dub_dir = job_dir / "_dubbed_segments"
        dub_dir.mkdir(exist_ok=True)
        
        all_voiced = True
        missing_segments = []
        for seg in translated_batch:
            wav_path = dub_dir / f"{seg['id']}.wav"
            texto_bruto = seg.get('manual_edit_text') or seg.get('text_pt') or ""
            if not texto_bruto.strip():
                continue
            if not wav_path.exists() or wav_path.stat().st_size < 1000:
                all_voiced = False
                missing_segments.append(seg['id'])
        
        total_voiced_tr = len([s for s in translated_batch if (s.get('manual_edit_text') or s.get('text_pt') or "").strip()])
        missing_count_tr = len(missing_segments)
        voiced_cached_tr = total_voiced_tr - missing_count_tr
        audio_cache_hit = (voiced_cached_tr / total_voiced_tr) * 100 if total_voiced_tr > 0 else 0

        if all_voiced:
            cb(100, 4, "✅ [Cache] Vozes detectadas. Indo para Mixagem Final...", audio_cache_hit=100.0)
        else:
            cb(0, 4, "[Chatterbox TTS] Preparando Vozes...", audio_cache_hit=audio_cache_hit)
            core.unload_local_gemma_engine()
            core.unload_whisper_model()
            core.unload_qwen3_model()
            gc.collect()
            if torch.cuda.is_available(): torch.cuda.empty_cache()
            
            core.wait_for_vram_release(threshold_mb=4000, cb=cb)
            
            speaker_refs = {}
            for seg in translated_batch:
                spk = seg.get('speaker', 'voz1')
                if spk not in speaker_refs:
                    spk_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ" / spk
                    ref_path = spk_dir / "_ref_titan_22k.wav"
                    txt_path = ref_path.with_suffix('.txt')
                    
                    is_bad_ref = False
                    if ref_path.exists():
                        try:
                            dur = core.get_audio_duration(str(ref_path))
                            if dur < 5.0 or not txt_path.exists(): is_bad_ref = True
                        except: is_bad_ref = True

                    if not ref_path.exists() or is_bad_ref:
                        samples = list(spk_dir.glob("*.wav"))
                        samples = [s for s in samples if "_ref_" not in s.name]
                        if not samples:
                            continue
                        
                        seg_texts = {str(s['id']): (s.get('original_text') or s.get('text') or "") for s in translated_batch}
                        master_audio = AudioSegment.empty()
                        master_text = ""
                        for smp in samples:
                            try:
                                audio = AudioSegment.from_wav(str(smp))
                                if len(audio) > 500:
                                    master_audio += audio + AudioSegment.silent(duration=300)
                                    smp_text = seg_texts.get(smp.stem, "").strip()
                                    if smp_text:
                                        master_text += smp_text + " "
                                    if len(master_audio) >= 12000: break
                            except: pass
                        
                        if len(master_audio) > 1000:
                            master_audio = master_audio.set_frame_rate(22050).set_channels(1).normalize()
                            master_audio = master_audio[:15000]
                            master_audio.export(str(ref_path), format="wav")
                            if master_text.strip():
                                txt_path.write_text(master_text.strip(), encoding='utf-8')
                    speaker_refs[spk] = str(ref_path)

            total_tasks = len(translated_batch)
            progress_lock = threading.Lock()
            current_done_count = [0]

            consecutive_texts = []
            for i, s in enumerate(translated_batch):
                t_bruto = s.get('manual_edit_text') or s.get('text_pt') or s.get('original_text', '')
                t_limpo = re.sub(r'[^a-zA-Z0-9 ]', '', t_bruto.lower()).strip()
                if len(consecutive_texts) > 0 and t_limpo == consecutive_texts[-1]['text']:
                    consecutive_texts.append({'idx': i, 'text': t_limpo})
                else:
                    consecutive_texts = [{'idx': i, 'text': t_limpo}]
                if len(consecutive_texts) >= 4:
                    for item in consecutive_texts:
                        translated_batch[item['idx']]['emotion'] = 'CANTORIA'
            
            def worker_dublagem(task_data):
                idx, seg = task_data
                out_path = dub_dir / f"{seg['id']}.wav"
                
                if out_path.exists() and out_path.stat().st_size > 1000:
                    with progress_lock: current_done_count[0] += 1
                    return

                if is_reaction_or_noise(seg):
                    with progress_lock: current_done_count[0] += 1
                    return

                texto_bruto = seg.get('manual_edit_text') or seg.get('text_pt') or seg.get('original_text', '')
                texto_final = re.sub(r'[^a-zA-Z0-9 áéíóúâêîôûãõàèìòùçÁÉÍÓÚÂÊÎÔÛÃÕÀÈÌÒÙÇ.,!?%$x]', '', texto_bruto).strip()
                
                speaker_id = seg.get('speaker', 'voz1')
                dur_original = seg['end'] - seg['start']
                ref_wav = speaker_refs.get(speaker_id)
                
                if dur_original >= 4.0:
                    specific_wav = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ" / speaker_id / f"{seg['id']}.wav"
                    if specific_wav.exists() and specific_wav.stat().st_size > 1000:
                        ref_wav = str(specific_wav)

                if not ref_wav: 
                    if speaker_refs:
                        fallback_spk = list(speaker_refs.keys())[0]
                        ref_wav = speaker_refs[fallback_spk]
                        logging.warning(f"⚠️ Locutor '{speaker_id}' sem áudio de referência. Usando fallback '{fallback_spk}'.")
                    else:
                        all_wavs = list((job_dir / "_2_PARA_AS_PASTAS_DE_VOZ").rglob("*.wav"))
                        if all_wavs:
                            ref_wav = str(all_wavs[0])
                            logging.warning(f"⚠️ Nenhum locutor com referência. Usando o primeiro áudio do job: {ref_wav}")
                            
                if not ref_wav:
                    logging.error(f"❌ Abortando dublagem do segmento {seg['id']}: sem áudio de referência de fallback.")
                    with progress_lock: current_done_count[0] += 1
                    return
                
                emotion_tag = seg.get('emotion', 'NORMAL')
                try:
                    resultado = core.gerar_audio_qwen3(texto_final, ref_wav, str(out_path), emotion=emotion_tag, max_duration=dur_original)
                    if resultado and out_path.exists():
                        audio_gerado = AudioSegment.from_wav(str(out_path))
                        audio_gerado.export(str(out_path), format="wav")
                except Exception as err:
                    logging.error(f"❌ Erro no worker_dublagem {seg['id']}: {err}")

                with progress_lock:
                    current_done_count[0] += 1
                    prog = (current_done_count[0] / total_tasks * 100)
                    cb(prog, 4, f"[Modo Relâmpago] Dublando {current_done_count[0]}/{total_tasks}...", current_seg=current_done_count[0], total_seg=total_tasks, audio_cache_hit=audio_cache_hit)
                    if current_done_count[0] % 10 == 0:
                        import torch, gc
                        gc.collect()
                        if torch.cuda.is_available(): torch.cuda.empty_cache()

            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.map(worker_dublagem, enumerate(translated_batch))

            file_format_map = {s['id']: ".wav" for s in translated_batch}
            core.unload_qwen3_model()
            gc.collect()
            core.gerar_relatorio_final(job_dir, job_id, translated_batch, file_format_map)

            dubbed_files_count = len(list((job_dir / "_dubbed_segments").glob("*.wav")))
            reaction_count = 0
            for s in translated_batch:
                if is_reaction_or_noise(s):
                    reaction_count += 1
            
            total_success = dubbed_files_count + reaction_count
            total_planned = len(translated_batch)
            success_rate = (total_success / total_planned) * 100 if total_planned > 0 else 0
            if success_rate < 90:
                cb(95, 4, f"❌ ERRO DE INTEGRIDADE: {success_rate:.1f}% de sucesso.")
                raise Exception(f"Qualidade Insuficiente ({success_rate:.1f}%).")

        if stop_at_stage == 'tts':
            cb(100, 4, "Etapa de Geração de Voz concluída!")
            return str(job_dir)

        full_dur = core.get_audio_duration(str(vocals_path))
        cb(95, 5, "[Titan Ducking] Mixagem Cinematográfica...")
        clean_dub_dir = job_dir / "dubbed_audio_clean"
        clean_dub_dir.mkdir(exist_ok=True)
        
        orig_vocals = AudioSegment.from_wav(str(job_dir / "vocals.wav"))
        
        def trim_silence_logic(audio, threshold=-35, padding_ms_start=20, padding_ms_end=50):
            duration = len(audio)
            if duration < 100: return audio 
            start_trim = 0
            for i in range(0, duration, 10):
                if audio[i:i+10].dBFS > threshold:
                    start_trim = max(0, i - padding_ms_start)
                    break
            end_trim = duration
            for i in range(duration, 0, -10):
                if audio[i-10:i].dBFS > threshold:
                    end_trim = min(duration, i + padding_ms_end)
                    break
            if start_trim >= end_trim: return audio
            return audio[start_trim:end_trim]

        if instrumental_path.exists():
            orig_instrum = AudioSegment.from_wav(str(instrumental_path))
        else:
            orig_instrum = AudioSegment.silent(duration=len(orig_vocals))

        pt_vocals = AudioSegment.silent(duration=len(orig_vocals))
        dub_windows = []
        segments_found = 0
        translated_batch = sorted(translated_batch, key=lambda x: x['start'])
        speaker_last_end_ms = {}

        for i, seg in enumerate(translated_batch):
            seg_id = seg['id']
            raw_wav = dub_dir / f"{seg_id}.wav"
            clean_wav = clean_dub_dir / f"{seg_id}.wav"
            
            if not raw_wav.exists() or raw_wav.stat().st_size < 1000:
                try:
                    start_ms = int(seg['start'] * 1000)
                    end_ms = int(seg['end'] * 1000)
                    start_ms = max(0, start_ms)
                    end_ms = min(len(orig_vocals), end_ms)
                    if end_ms > start_ms:
                        orig_chunk = orig_vocals[start_ms:end_ms]
                        fade_ms = min(100, len(orig_chunk) // 2)
                        if fade_ms > 0:
                            orig_chunk = orig_chunk.fade_in(fade_ms).fade_out(fade_ms)
                        pt_vocals = pt_vocals.overlay(orig_chunk, position=start_ms)
                        dub_windows.append((start_ms, end_ms))
                except Exception as rec_err:
                    logging.warning(f"⚠️ Erro ao recuperar áudio original para {seg_id}: {rec_err}")
                continue
            
            try:
                if not clean_wav.exists():
                    raw_seg = AudioSegment.from_wav(str(raw_wav))
                    clean_seg = trim_silence_logic(raw_seg)
                    clean_seg = effects.normalize(clean_seg)
                    clean_seg.export(str(clean_wav), format="wav")
                
                dub_seg = AudioSegment.from_wav(str(clean_wav))
                dub_seg = effects.normalize(dub_seg)
                
                start_ms = int(seg['start'] * 1000)
                spk = seg.get('speaker', 'default_speaker')
                spk_last_end = speaker_last_end_ms.get(spk, 0)
                if start_ms < spk_last_end:
                    start_ms = spk_last_end
                
                next_same_spk_start_ms = len(orig_vocals)
                for next_seg in translated_batch[i+1:]:
                    if next_seg.get('speaker') == spk:
                        next_same_spk_start_ms = int(next_seg['start'] * 1000)
                        break
                        
                next_any_start_ms = len(orig_vocals)
                if i + 1 < len(translated_batch):
                    next_any_start_ms = int(translated_batch[i+1]['start'] * 1000)
                
                available_space_ms = next_same_spk_start_ms - start_ms
                overlap_allowance_ms = 150
                next_seg_exists = (i + 1 < len(translated_batch))
                
                if next_seg_exists and spk != translated_batch[i+1].get('speaker'):
                    emo_current = seg.get('emotion', 'NORMAL')
                    emo_next = translated_batch[i+1].get('emotion', 'NORMAL')
                    orig_gap_ms = int((translated_batch[i+1]['start'] - seg['end']) * 1000)
                    is_tense = any(e in ['RAIVA', 'URGENTE', 'DRAMATICO'] for e in [emo_current, emo_next])
                    
                    if is_tense:
                        if orig_gap_ms < 0:
                            overlap_allowance_ms = 600
                        elif orig_gap_ms < 150:
                            overlap_allowance_ms = 400
                        else:
                            overlap_allowance_ms = 50
                    else:
                        if orig_gap_ms < 0:
                            overlap_allowance_ms = 300
                        else:
                            overlap_allowance_ms = 150
                    if orig_gap_ms < 0:
                        overlap_allowance_ms = max(overlap_allowance_ms, -orig_gap_ms)
                    max_space = (next_any_start_ms - start_ms) + overlap_allowance_ms
                    available_space_ms = min(available_space_ms, max_space)
                else:
                    available_space_ms = min(available_space_ms, next_any_start_ms - start_ms)
                
                orig_dur_ms = (seg['end'] - seg['start']) * 1000
                target_dur_ms = min(orig_dur_ms + 500, available_space_ms)
                
                diff_ms = len(dub_seg) - target_dur_ms
                if diff_ms > 50:
                    speed_factor = len(dub_seg) / (target_dur_ms or 1)
                    dub_seg = speedup_audio(dub_seg, min(MAX_SPEEDUP, speed_factor))
                
                if len(dub_seg) > available_space_ms:
                    f_out = min(50, len(dub_seg))
                    dub_seg = dub_seg[:available_space_ms]
                    if f_out > 0 and len(dub_seg) > 0:
                        dub_seg = dub_seg.fade_out(f_out)
                
                segments_found += 1
                f_time_out = min(100, len(dub_seg) // 4)
                if f_time_out > 0:
                    dub_seg = dub_seg.fade_out(f_time_out)
                
                prog_mix = 95 + (segments_found / len(translated_batch) * 4)
                cb(prog_mix, 5, f"[Mixer] Integrando {seg_id}...", current_seg=segments_found, total_seg=len(translated_batch))
                
                pt_vocals = pt_vocals.overlay(dub_seg, position=start_ms)
                speaker_last_end_ms[spk] = start_ms + len(dub_seg)
                dub_windows.append((start_ms, start_ms + len(dub_seg)))
            except Exception as mix_err:
                logging.error(f"❌ Erro ao mixar segmento {seg_id}: {mix_err}")

        dub_windows.sort()
        vocal_mask = AudioSegment.silent(duration=len(orig_vocals))
        last_end = 0
        for start_ms, end_ms in dub_windows:
            if start_ms - last_end > 500:
                gap_start = last_end + 100
                gap_end = start_ms - 100
                fade_len = min(200, (gap_end - gap_start) // 2)
                if gap_end > gap_start and fade_len > 0:
                    chunk = orig_vocals[gap_start:gap_end].fade_in(fade_len).fade_out(fade_len)
                    vocal_mask = vocal_mask.overlay(chunk, position=gap_start)
            last_end = end_ms

        if len(orig_vocals) - last_end > 500:
            gap_start = last_end + 100
            gap_end = len(orig_vocals) - 100
            fade_len = min(200, (gap_end - gap_start) // 2)
            if gap_end > gap_start and fade_len > 0:
                chunk = orig_vocals[gap_start:gap_end].fade_in(fade_len).fade_out(fade_len)
                vocal_mask = vocal_mask.overlay(chunk, position=gap_start)

        final_vocals_path = job_dir / "dubbed_vocals_master.wav"
        final_dub_mix = pt_vocals.overlay(vocal_mask) 
        final_dub_mix = effects.normalize(final_dub_mix)
        final_dub_mix.export(str(final_vocals_path), format="wav")

        orig_name = Path(video_path).stem if video_path else "video"
        if not orig_name or len(orig_name) > 50:
            orig_name = job_id
        output_video = job_dir / f"{orig_name} dublado.mp4"
        encoder = get_best_encoder()
        
        if instrumental_path.exists():
            filter_str = "[1:a]aresample=44100,highpass=f=80,volume=1.4,asplit=2[v_pt1][v_pt2]; [2:a]aresample=44100[v_bg]; "
            filter_str += "[v_bg][v_pt1]sidechaincompress=threshold=0.02:ratio=5:attack=15:release=500[v_ducked]; "
            filter_str += "[v_ducked][v_pt2]amix=inputs=2:duration=longest[v_mixed]"
            cmd = ['ffmpeg', '-y', '-hwaccel', 'cuda', '-i', str(video_mirror), '-i', str(final_vocals_path), '-i', str(instrumental_path)]
            cmd.extend(['-filter_complex', filter_str, '-map', '0:v', '-map', '[v_mixed]'])
        else:
            cmd = ['ffmpeg', '-y', '-hwaccel', 'cuda', '-i', str(video_mirror), '-i', str(final_vocals_path)]
            cmd.extend(['-map', '0:v', '-map', '1:a'])
        
        v_codec = encoder
        cmd.extend(['-c:v', 'copy'])
        cmd.extend(['-avoid_negative_ts', 'make_zero', '-map_metadata', '-1', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '128k', str(output_video), '-progress', 'pipe:1'])
        
        logging.info(f"🚀 [FFmpeg] Executando: {' '.join(cmd)}")
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding='utf-8', errors='replace')
            last_lines = []
            for line in process.stdout:
                last_lines.append(line.strip())
                if len(last_lines) > 20: last_lines.pop(0)
                if "out_time_ms=" in line:
                    try:
                        time_us = int(line.split('=')[1])
                        time_sec = time_us / 1000000.0
                        pct_stage = min(100, (time_sec / (full_dur or 1)) * 100)
                        label_enc = "NVIDIA RTX" if v_codec == 'h264_nvenc' else "Intel CPU"
                        cb(pct_stage, 5, f"[{label_enc}] Masterizando Vídeo... {int(pct_stage)}%")
                    except: pass
            process.wait()
            if process.returncode != 0:
                error_msg = "\n".join(last_lines)
                raise Exception(f"Erro FFmpeg (QSV): {process.returncode}\nSaída:\n{error_msg}")
        except Exception as e:
            cmd_safe = [c if c != v_codec else 'libx264' for c in cmd]
            if 'balanced' in cmd_safe: cmd_safe[cmd_safe.index('balanced')] = 'ultrafast'
            if 'veryfast' in cmd_safe: cmd_safe[cmd_safe.index('veryfast')] = 'ultrafast'
            
            process = subprocess.Popen(cmd_safe, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding='utf-8', errors='replace')
            last_lines_cpu = []
            for line in process.stdout:
                last_lines_cpu.append(line.strip())
                if len(last_lines_cpu) > 20: last_lines_cpu.pop(0)
                if "out_time_ms=" in line:
                    try:
                        time_us = int(line.split('=')[1])
                        time_sec = time_us / 1000000.0
                        pct_stage = min(100, (time_sec / (full_dur or 1)) * 100)
                        cb(pct_stage, 5, f"[CPU_FALLBACK] Masterizando Vídeo... {int(pct_stage)}%")
                    except: pass
            process.wait()
            if process.returncode != 0:
                error_msg_cpu = "\n".join(last_lines_cpu)
                raise Exception(f"Erro FFmpeg (CPU): {process.returncode}\nSaída:\n{error_msg_cpu}")
        
        file_format_map = {s['id']: ".wav" for s in translated_batch}
        core.gerar_relatorio_final(job_dir, job_id, translated_batch, file_format_map)
        quality_rpt = core.safe_json_read(job_dir / "relatorio_processamento.json")
        if quality_rpt:
            taxa_acerto = quality_rpt.get("success_rate", 0)
            acertos = quality_rpt.get("success_count", 0)
            total_segs = quality_rpt.get("total_segments", 0)
            cb(100, 5, f"Concluído! {acertos}/{total_segs} dublados ({taxa_acerto:.1f}%)")
        return str(output_video)
    except Exception as e:
        logging.error(f"Erro na pipeline: {e}")
        traceback.print_exc()
        time.sleep(1)
        return None

# =================================================================
# PARTE 4: SERVIDORES FLASK (TWIN APPS)
# =================================================================

app_games = Flask("nexus_dub_games")
CORS(app_games)
app_games.config['UPLOAD_FOLDER'] = 'uploads'

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Nexus Titan Engine - VPK/PCK Manager</title>
    <style>
        body { background: #0a0a0a; color: #eee; font-family: 'Segoe UI', sans-serif; padding: 30px; }
        .container { max-width: 900px; margin: auto; background: #111; padding: 25px; border-radius: 15px; border: 1px solid #333; }
        h1 { color: #bb86fc; border-bottom: 2px solid #bb86fc; padding-bottom: 10px; }
        .section { background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #222; }
        button { background: #bb86fc; color: #000; border: none; padding: 10px 20px; border-radius: 5px; font-weight: bold; cursor: pointer; margin-right: 10px; }
        input[type="text"] { background: #000; border: 1px solid #444; color: #fff; padding: 10px; width: 70%; border-radius: 5px; }
        pre { background: #000; padding: 15px; border-radius: 5px; color: #0f0; font-size: 0.9rem; overflow-x: auto; height: 200px; }
    </style>
</head>
<body>
    <div class="container">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #bb86fc; padding-bottom: 10px; margin-bottom: 20px;">
            <h1 style="margin: 0; border: none;">🎮 NEXUS TITAN ENGINE</h1>
            <a href="http://127.0.0.1:5000" style="color: #888; text-decoration: none; font-size: 0.8rem; border: 1px solid #333; padding: 5px 15px; border-radius: 8px;">← VOLTAR AO HUB</a>
        </div>
        <p>Gerenciamento de Assets de Jogos (VPK, PCK, FSB, ARCH)</p>
        
        <div class="section">
            <h3>1. Analisar Arquivo do Jogo</h3>
            <input type="text" id="path-analisar" placeholder="Ex: C:/Jogos/L4D2/pak01_dir.vpk">
            <button onclick="executarAcao('analisar')">ANALISAR</button>
        </div>

        <div class="section">
            <h3>2. Projetos Ativos</h3>
            <select id="project-selector" style="width:100%; padding:10px; background:#000; color:#fff; border-radius:5px;">
                <option value="">Carregando projetos...</option>
            </select>
            <button onclick="executarAcao('descompactar')" style="margin-top:10px;">EXTRAIR ÁUDIOS DO PROJETO</button>
        </div>

        <div class="section">
            <h3>Console de Saída</h3>
            <pre id="console-log">Aguardando comando...</pre>
        </div>
    </div>

    <script>
        async function loadProjects() {
            const response = await fetch('/api/get-projects');
            const projects = await response.json();
            const selector = document.getElementById('project-selector');
            selector.innerHTML = projects.length > 0 ? '' : '<option value="">Nenhum projeto encontrado.</option>';
            projects.forEach(p => {
                const option = document.createElement('option');
                option.value = p.id;
                option.textContent = p.name;
                selector.appendChild(option);
            });
        }

        async function executarAcao(action) {
            const log = document.getElementById('console-log');
            log.textContent += `\\n[INFO] Iniciando ${action}...`;
            let payload = {};
            if(action === 'analisar') payload.path = document.getElementById('path-analisar').value;
            if(action === 'descompactar') payload.project_id = document.getElementById('project-selector').value;

            try {
                const response = await fetch(`/api/${action}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const res = await response.json();
                log.textContent += `\\n[RESULTADO] ${res.message}`;
                if(action === 'analisar') loadProjects();
            } catch(e) {
                log.textContent += `\\n[ERRO] ${e}`;
            }
        }
        window.onload = loadProjects;
    </script>
</body>
</html>
"""

@app_games.route('/')
def games_home():
    return render_template_string(HTML_TEMPLATE)

@app_games.route('/api/health')
def games_health_check():
    return jsonify({"status": "online", "engine": "Titan Games"})

@app_games.route('/api/is_busy')
def games_api_is_busy():
    return jsonify({"busy": len(_active_game_jobs) > 0})

@app_games.route('/api/analisar', methods=['POST'])
def games_api_analisar():
    path = request.get_json().get('path', '').strip()
    if not path: return jsonify({'success': False, 'message': 'Caminho vazio.'})
    if path.lower().endswith('.vpk'): success, msg = analisar_vpk_logic(path)
    elif path.lower().endswith('.pck'): success, msg = analisar_pck_logic(path)
    else: success, msg = False, "Formato não suportado."
    return jsonify({'success': success, 'message': msg})

@app_games.route('/dublar_jogos', methods=['POST'])
def games_dublar_jogos():
    job_id = request.form.get('job_id')
    game_profile = request.form.get('game_profile', 'padrao')
    source_lang = request.form.get('source_lang', 'en')
    target_lang = request.form.get('target_lang', 'pt')
    manual_wav_path = request.form.get('manual_wav_path')
    skip_lqa = request.form.get('skip_lqa', 'false')
    
    if not job_id:
        timestamp = int(time.time())
        job_id = f"manual_job_{timestamp}" if manual_wav_path else f"titan_job_{timestamp}"

    global _active_game_jobs
    if job_id in _active_game_jobs:
        return jsonify({"success": True, "message": "Pipeline já rodando."})
    _active_game_jobs.add(job_id)

    def run_pipeline():
        try:
            project_dir = Path(UPLOAD_FOLDER) / job_id
            project_dir.mkdir(parents=True, exist_ok=True)
            status_path = project_dir / "job_status.json"
            existing_status = core.safe_json_read(status_path)
            
            start_ts = time.time()
            if existing_status and "start_time" in existing_status:
                st_val = existing_status["start_time"]
                if isinstance(st_val, (int, float)):
                    start_ts = st_val
            
            status_data = existing_status or {}
            if 'metrics' in status_data and isinstance(status_data['metrics'], dict):
                status_data['metrics']['stages_start_times'] = {}
                status_data['metrics']['stages_duration_secs'] = {}
                
            status_data.update({
                "job_id": job_id,
                "status": "Iniciando",
                "progress": 5,
                "start_time": start_ts,
                "game_profile": game_profile,
                "source_language": source_lang,
                "target_language": target_lang,
                "skip_lqa": skip_lqa,
                "message": "Sincronizando parâmetros Titan..."
            })
            core.safe_json_write(status_data, status_path)

            mover_dir = project_dir / "_1_MOVER_OS_FICHEIROS_DAQUI"
            mover_dir.mkdir(parents=True, exist_ok=True)
            if manual_wav_path and os.path.exists(manual_wav_path):
                for item in os.listdir(manual_wav_path):
                    s = os.path.join(manual_wav_path, item)
                    d = mover_dir / item
                    if os.path.isfile(s) and item.lower().endswith(('.wav', '.zip')):
                        shutil.copy2(s, d)

            core.processar_dublagem_jogos(project_dir, job_id, start_ts)
        except Exception as e:
            logging.error(f"Erro na pipeline Titan Games: {e}")
            traceback.print_exc()

    def run_pipeline_wrapper():
        try: run_pipeline()
        finally: _active_game_jobs.discard(job_id)

    threading.Thread(target=run_pipeline_wrapper, daemon=True).start()
    return jsonify({"success": True, "message": "Pipeline Titan iniciada!", "job_id": job_id})

@app_games.route('/api/fmod_extract', methods=['POST'])
def games_api_fmod_extract():
    data = request.get_json()
    project_id = data.get('project_id')
    if not project_id: return jsonify({'success': False, 'message': 'Selecione projeto.'})
    return jsonify({'success': True, 'message': 'Extração FMOD iniciada.'})

@app_games.route('/api/fmod_repack', methods=['POST'])
def games_api_fmod_repack():
    data = request.get_json()
    project_id = data.get('project_id')
    if not project_id: return jsonify({'success': False, 'message': 'Incompleto.'})
    return jsonify({'success': True, 'message': 'Repack FMOD iniciado.'})

@app_games.route('/api/reempacotar', methods=['POST'])
def games_api_reempacotar():
    data = request.get_json()
    project_id = data.get('project_id')
    if not project_id: return jsonify({'success': False, 'message': 'Inválido.'})
    return jsonify({'success': True, 'message': 'Repack enviado para a fila.'})

@app_games.route('/api/job-status/<job_id>')
def games_api_job_status(job_id):
    status_file = os.path.join('uploads', job_id, "job_status.json")
    if os.path.exists(status_file):
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                etapa = data.get('etapa', '').lower()
                if "tradução" in etapa or "gemma" in etapa:
                    data['tool_name'] = "Gemma (IA)"
                elif "gerando" in etapa or "voz" in etapa or "tts" in etapa:
                    data['tool_name'] = "Qwen3-TTS (Voz)"
                elif "finalizando" in etapa or "masterização" in etapa or "ffmpeg" in etapa:
                    data['tool_name'] = "FFMPEG (Master)"
                elif "transcrevendo" in etapa:
                    data['tool_name'] = "Whisper (Transcrição)"
                return jsonify(data)
        except: pass
    return jsonify({'status': 'unknown', 'progress': 0})

@app_games.route('/api/get-project-files', methods=['POST'])
def games_api_get_project_files():
    data = request.get_json() or {}
    job_id = data.get('job_id')
    query = data.get('query', '').lower()
    if not job_id: return jsonify([])
    search_paths = [
        os.path.join('uploads', job_id, "_2_PARA_AS_PASTAS_DE_VOZ"),
        os.path.join('uploads', job_id),
        os.path.join('output_vortex', job_id)
    ]
    files = []
    for path in search_paths:
        if os.path.exists(path):
            for root, dirs, filenames in os.walk(path):
                for f in filenames:
                    if f.lower().endswith(('.wav', '.mp3', '.wem')):
                        if query and query not in f.lower(): continue
                        full_p = os.path.join(root, f)
                        files.append({'name': f, 'size': os.path.getsize(full_p)})
                break
    files.sort(key=lambda x: x['name'])
    return jsonify(files[:500])

@app_games.route('/api/descompactar', methods=['POST'])
def games_api_descompactar():
    project_id = request.get_json().get('project_id')
    if not project_id: return jsonify({'success': False, 'message': 'ID do projeto não fornecido.'})
    backup_file = os.path.join(BACKUP_DIR, f"backup_{project_id}.json")
    if not os.path.exists(backup_file):
        return jsonify({'success': False, 'message': 'Projeto não encontrado.'})
    try:
        with open(backup_file, 'r') as f: data = json.load(f)
        output_dir = os.path.join('uploads', project_id, "_1_MOVER_OS_FICHEIROS_DAQUI")
        os.makedirs(output_dir, exist_ok=True)
        return jsonify({'success': True, 'message': f'Extração iniciada para {output_dir}.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app_games.route('/api/preview-folder', methods=['POST'])
def games_preview_folder():
    try:
        data = request.json
        folder_path = data.get('path')
        if not folder_path or not os.path.exists(folder_path):
            return jsonify({"success": False, "message": "Pasta não encontrada."}), 404
        valid_exts = ('.wav', '.mp3', '.ogg', '.flac', '.m4a')
        all_files = []
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                if f.lower().endswith(valid_exts):
                    all_files.append(f)
        count = len(all_files)
        return jsonify({"success": True, "count": count, "sample": all_files[:5], "message": f"{count} arquivos."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app_games.route('/api/get-logs')
def games_get_logs():
    try:
        # Tenta pegar dinamicamente o arquivo de log ativo (ex: 5002.log) em vez do fixo antigo
        try:
            from nexus.core.utils import current_log_file
            log_path = current_log_file
        except:
            log_path = LOG_FILE
            
        if not log_path.exists():
            return jsonify({"logs": f"[SISTEMA] Aguardando log..."})
            
        file_size = log_path.stat().st_size
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            # Se o arquivo de log for muito grande, busca apenas os últimos 100KB para poupar a CPU
            if file_size > 100000:
                f.seek(file_size - 100000)
                f.readline()  # Despreza a primeira linha parcial
            lines = f.readlines()
            
        filtered_lines = []
        for line in lines[-1000:]:
            line_str = line.strip()
            if not line_str:
                continue
                
            # Filtra requisições de API barulhentas do console
            if any(x in line_str for x in ["GET /api/", "POST /api/", "HTTP/1.1", "127.0.0.1", "WSGI", "stat", "Debugger is active"]):
                continue
                
            # Se for barra de progresso de Job, formata amigavelmente
            if "Job:" in line_str:
                parts = [p.strip() for p in line_str.split("|")]
                if len(parts) >= 5:
                    pct = parts[1].split()[-1] if parts[1].split() else "?"
                    filtered_lines.append(f"➔ [{pct}] {parts[2]} | {parts[3]} | {parts[4].replace('Tempo:', '').strip()}")
            else:
                # Tenta extrair timestamp do log (ex: "2026-06-21 22:13:32,932")
                time_part = datetime.datetime.now().strftime("%H:%M:%S")
                m = re.match(r"^(\d{4}-\d{2}-\d{2}\s+)?(\d{2}:\d{2}:\d{2})", line_str)
                if m:
                    time_part = m.group(2)
                    msg_clean = line_str[m.end():].strip()
                else:
                    msg_clean = line_str
                    
                # Remove níveis de log redundantes do texto final da mensagem
                for tag in ["INFO:", "WARNING:", "ERROR:", "DEBUG:", "[INFO]", "[WARNING]", "[ERROR]", "[DEBUG]"]:
                    if msg_clean.startswith(tag):
                        msg_clean = msg_clean[len(tag):].strip()
                        
                # Escolhe cor com base no nível
                color = "#fff" # Branco padrão
                if any(x in line_str for x in ["[ERROR]", "ERROR", "❌", "Traceback", "Exception", "Error:"]):
                    color = "#ff4f4f" # Vermelho vibrante
                elif any(x in line_str for x in ["[WARNING]", "WARNING", "⚠️", "Aviso"]):
                    color = "#ffaa00" # Amarelo Titan
                    
                filtered_lines.append(f"<span style='color: #888;'>[{time_part}]</span> <span style='color: {color};'>{msg_clean}</span>")
                
        return jsonify({"logs": "\n".join(filtered_lines[-150:])})
    except Exception as e:
        return jsonify({"logs": f"<span style='color: red;'>Erro ao ler telemetria: {str(e)}</span>"})

@app_games.route('/api/get-projects')
def games_api_get_projects():
    projects = []
    if os.path.exists(BACKUP_DIR):
        for f in os.listdir(BACKUP_DIR):
            if f.startswith('backup_') and f.endswith('.json'):
                try:
                    with open(os.path.join(BACKUP_DIR, f), 'r') as j:
                        d = json.load(j)
                        projects.append({
                            'id': d['hash_sha1_original'], 
                            'name': f"📦 {d['nome_arquivo']}",
                            'date': datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(BACKUP_DIR, f))).strftime('%Y-%m-%d %H:%M:%S')
                        })
                except: pass
    UPLOAD_DIR = str(UPLOAD_FOLDER)
    if os.path.exists(UPLOAD_DIR):
        for d_name in os.listdir(UPLOAD_DIR):
            if d_name.startswith('video_') or d_name in ["arch_manager_backups", "mods_finalizados", "_NEXUS_TEMP_"]:
                continue
            d_path = os.path.join(UPLOAD_DIR, d_name)
            if os.path.isdir(d_path):
                status_file = os.path.join(d_path, "job_status.json")
                prog = 0
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(d_path)).strftime('%Y-%m-%d %H:%M:%S')
                if os.path.exists(status_file):
                    try:
                        with open(status_file, 'r') as j:
                            data = json.load(j)
                            is_game = data.get('game_profile') or d_name.startswith(('job_', 'manual_job_'))
                            if is_game:
                                projects.append({
                                    'id': data.get('job_id', d_name),
                                    'name': f"🎮 {d_name}",
                                    'status': data.get('status', 'unknown'),
                                    'progress': data.get('progress', 0),
                                    'date': mtime
                                })
                    except: pass
    projects.sort(key=lambda x: x['name'])
    return jsonify(projects)


# =================================================================
# PARTE 3.5: FILA SEQUENCIAL INTELIGENTE E WATCHDOG (LOTE POR ETAPAS)
# =================================================================

QUEUE_DIR = UPLOAD_FOLDER / "watchdog_queue"
QUEUE_INPUT_DIR = QUEUE_DIR / "input"
QUEUE_OUTPUT_DIR = QUEUE_DIR / "output"
QUEUE_PROCESSED_DIR = QUEUE_DIR / "processed"
QUEUE_COMPLETED_DIR = QUEUE_PROCESSED_DIR / "completed"
QUEUE_FAILED_DIR = QUEUE_PROCESSED_DIR / "failed"
QUEUE_STATUS_FILE = QUEUE_DIR / "queue_status.json"

def write_error_json(item, error_message, traceback_str):
    try:
        video_name = Path(item["file_path"]).name
        video_stem = Path(item["file_path"]).stem
        err_file = QUEUE_FAILED_DIR / f"{video_stem}_erro.json"
        err_data = {
            "video_name": video_name,
            "job_id": item["job_id"],
            "stage_failed": item.get("stage", "Unknown"),
            "error_message": str(error_message),
            "traceback": traceback_str,
            "timestamp": datetime.datetime.now().isoformat()
        }
        core.safe_json_write(err_data, err_file)
        
        # Move o original para a pasta de erro
        orig_file = Path(item["file_path"])
        if orig_file.exists():
            dest = QUEUE_FAILED_DIR / orig_file.name
            if dest.exists():
                try: os.remove(str(dest))
                except: pass
            shutil.move(str(orig_file), str(dest))
            item["file_path"] = str(dest)
    except Exception as e:
        logging.error(f"Erro ao gravar JSON de erro ou mover arquivo: {e}")

class VideoQueueManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.status = "idle"  # "idle", "processing", "paused"
        self.current_job_id = None
        self.current_item_id = None
        self.current_stage = None
        self.items = []
        self.worker_thread = None
        self.watchdog_thread = None
        self.should_stop = False
        
        self.load_queue_state()
        
    def load_queue_state(self):
        if QUEUE_STATUS_FILE.exists():
            data = core.safe_json_read(QUEUE_STATUS_FILE)
            if data:
                self.status = data.get("status", "idle")
                if self.status == "processing":
                    self.status = "idle"
                self.items = data.get("items", [])
                for item in self.items:
                    if item.get("status") == "processing":
                        item["status"] = "pending"
                        item["stage"] = None
                        item["progress"] = 0
        self.save_queue_state()
        
    def save_queue_state(self):
        data = {
            "status": self.status,
            "current_item_id": self.current_item_id,
            "current_job_id": self.current_job_id,
            "current_stage": self.current_stage,
            "items": self.items
        }
        core.safe_json_write(data, QUEUE_STATUS_FILE)
        
    def add_video(self, file_path, src_lang="auto", tgt_lang="pt"):
        path = Path(file_path)
        if not path.exists():
            return False, "Arquivo não existe"
            
        video_name = path.name
        video_name_clean = "".join([c if c.isalnum() or c in "._-" else "_" for c in path.stem])
        short_hash = hashlib.md5(video_name.encode()).hexdigest()[:6]
        job_id = f"video_{video_name_clean[:30]}_{short_hash}"
        
        with self.lock:
            for item in self.items:
                if item["file_path"] == str(path.absolute()) and item["status"] in ["pending", "processing"]:
                    return True, "Arquivo já está na fila"
                    
            item = {
                "id": str(int(time.time() * 1000) + len(self.items)),
                "job_id": job_id,
                "video_name": video_name,
                "file_path": str(path.absolute()),
                "status": "pending",
                "stage": None,
                "progress": 0,
                "message": "Aguardando na fila",
                "error": None,
                "src_lang": src_lang,
                "tgt_lang": tgt_lang,
                "added_at": datetime.datetime.now().isoformat()
            }
            self.items.append(item)
            self.save_queue_state()
        return True, "Vídeo adicionado com sucesso"

    def scan_input_folder(self):
        if not QUEUE_INPUT_DIR.exists():
            return
        valid_exts = ('.mp4', '.mkv', '.avi', '.mov')
        for f in os.listdir(QUEUE_INPUT_DIR):
            p = QUEUE_INPUT_DIR / f
            if p.is_file() and f.lower().endswith(valid_exts):
                already_queued = False
                with self.lock:
                    for item in self.items:
                        if Path(item["file_path"]).name == f and item["status"] in ["pending", "processing", "completed", "failed"]:
                            already_queued = True
                            break
                if not already_queued:
                    self.add_video(p, "auto", "pt")

    def start_watchdog(self):
        if self.watchdog_thread is None or not self.watchdog_thread.is_alive():
            self.should_stop = False
            self.watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
            self.watchdog_thread.start()

    def _watchdog_loop(self):
        logging.info("👁️ [WATCHDOG] Thread de monitoramento da pasta de entrada iniciada.")
        while not self.should_stop:
            try:
                self.scan_input_folder()
            except Exception as e:
                logging.error(f"Erro no loop do watchdog: {e}")
            time.sleep(10)

    def start_worker(self):
        with self.lock:
            self.status = "processing"
            self.save_queue_state()
            if self.worker_thread is None or not self.worker_thread.is_alive():
                self.should_stop = False
                self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
                self.worker_thread.start()

    def pause_worker(self):
        with self.lock:
            self.status = "paused"
            self.save_queue_state()

    def clear_queue(self):
        with self.lock:
            self.items = [item for item in self.items if item["status"] in ["completed", "failed"]]
            self.save_queue_state()

    def remove_item(self, item_id):
        with self.lock:
            self.items = [item for item in self.items if item["id"] != item_id]
            self.save_queue_state()

    def _worker_loop(self):
        logging.info("⚙️ [QUEUE] Thread do worker de fila iniciada.")
        while not self.should_stop:
            time.sleep(2)
            
            try:
                self.scan_input_folder()
            except Exception as e:
                logging.error(f"Erro ao escanear pasta de watchdog: {e}")
                
            with self.lock:
                if self.status != "processing":
                    continue
                    
            with self.lock:
                active_items = [item for item in self.items if item["status"] in ["pending", "processing"]]
                
            if not active_items:
                with self.lock:
                    self.status = "idle"
                    self.current_item_id = None
                    self.current_job_id = None
                    self.current_stage = None
                    self.save_queue_state()
                logging.info("🏁 [QUEUE] Todos os itens processados. Fila em standby.")
                continue

            # ETAPA 1: LOOP SEPARAÇÃO (OpenUnmix)
            separation_items = [item for item in active_items if item.get("stage") is None]
            if separation_items:
                logging.info(f"🎙️ [QUEUE] Iniciando Etapa de Separação de Áudio para {len(separation_items)} arquivos...")
                for item in separation_items:
                    with self.lock:
                        if self.status != "processing":
                            break
                        item["status"] = "processing"
                        item["stage"] = "Separation"
                        item["progress"] = 5
                        item["message"] = "Iniciando Separação de Áudio..."
                        self.current_item_id = item["id"]
                        self.current_job_id = item["job_id"]
                        self.current_stage = "Separation"
                        self.save_queue_state()
                        
                    try:
                        pipeline_video_master(
                            video_path=item["file_path"],
                            job_id=item["job_id"],
                            source_lang=item.get("src_lang", "auto"),
                            target_lang=item.get("tgt_lang", "pt"),
                            stop_at_stage='separation'
                        )
                        with self.lock:
                            item["progress"] = 100
                            item["message"] = "Separação Concluída"
                            self.save_queue_state()
                    except Exception as e:
                        tb = traceback.format_exc()
                        logging.error(f"❌ [QUEUE] Erro na Separação de {item['video_name']}: {e}")
                        with self.lock:
                            item["status"] = "failed"
                            item["error"] = str(e)
                            item["message"] = f"Erro na Separação: {e}"
                            write_error_json(item, e, tb)
                            self.save_queue_state()
                
                logging.info("🧹 [QUEUE] Fim da etapa de Separação. Limpando VRAM...")
                import gc; gc.collect()
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            # Re-scaneia itens ativos para a etapa de ASR
            with self.lock:
                active_items = [item for item in self.items if item["status"] in ["pending", "processing"]]

            # ETAPA 2: LOOP ASR (WhisperX)
            asr_items = [item for item in active_items if item.get("stage") == "Separation"]
            if asr_items:
                logging.info(f"🎙️ [QUEUE] Iniciando Etapa de Transcrição/ASR para {len(asr_items)} arquivos...")
                for item in asr_items:
                    with self.lock:
                        if self.status != "processing":
                            break
                        item["status"] = "processing"
                        item["stage"] = "ASR"
                        item["progress"] = 5
                        item["message"] = "Iniciando Transcrição..."
                        self.current_item_id = item["id"]
                        self.current_job_id = item["job_id"]
                        self.current_stage = "ASR"
                        self.save_queue_state()
                        
                    try:
                        pipeline_video_master(
                            video_path=item["file_path"],
                            job_id=item["job_id"],
                            source_lang=item.get("src_lang", "auto"),
                            target_lang=item.get("tgt_lang", "pt"),
                            stop_at_stage='transcription'
                        )
                        with self.lock:
                            item["progress"] = 100
                            item["message"] = "Transcrição Concluída"
                            self.save_queue_state()
                    except Exception as e:
                        tb = traceback.format_exc()
                        logging.error(f"❌ [QUEUE] Erro no ASR de {item['video_name']}: {e}")
                        with self.lock:
                            item["status"] = "failed"
                            item["error"] = str(e)
                            item["message"] = f"Erro no ASR: {e}"
                            write_error_json(item, e, tb)
                            self.save_queue_state()
                
                logging.info("🧹 [QUEUE] Fim da etapa ASR. Descarregando Whisper...")
                core.unload_whisper_model()
                import gc; gc.collect()
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            # ETAPA 2: LOOP TRADUÇÃO
            with self.lock:
                active_items = [item for item in self.items if item["status"] in ["pending", "processing"]]
            translation_items = [item for item in active_items if item.get("stage") == "ASR"]
            if translation_items:
                logging.info(f"🧠 [QUEUE] Iniciando Etapa de Tradução para {len(translation_items)} arquivos...")
                for item in translation_items:
                    with self.lock:
                        if self.status != "processing":
                            break
                        item["status"] = "processing"
                        item["stage"] = "Translation"
                        item["progress"] = 5
                        item["message"] = "Iniciando Tradução..."
                        self.current_item_id = item["id"]
                        self.current_job_id = item["job_id"]
                        self.current_stage = "Translation"
                        self.save_queue_state()
                        
                    try:
                        pipeline_video_master(
                            video_path=item["file_path"],
                            job_id=item["job_id"],
                            source_lang=item.get("src_lang", "auto"),
                            target_lang=item.get("tgt_lang", "pt"),
                            stop_at_stage='translation'
                        )
                        with self.lock:
                            item["progress"] = 100
                            item["message"] = "Tradução Concluída"
                            self.save_queue_state()
                    except Exception as e:
                        tb = traceback.format_exc()
                        logging.error(f"❌ [QUEUE] Erro na Tradução de {item['video_name']}: {e}")
                        with self.lock:
                            item["status"] = "failed"
                            item["error"] = str(e)
                            item["message"] = f"Erro na Tradução: {e}"
                            write_error_json(item, e, tb)
                            self.save_queue_state()
                
                logging.info("🧹 [QUEUE] Fim da etapa de Tradução. Descarregando Gemma...")
                core.unload_local_gemma_engine()
                import gc; gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            # ETAPA 3: LOOP TTS (DUBLAGEM)
            with self.lock:
                active_items = [item for item in self.items if item["status"] in ["pending", "processing"]]
            tts_items = [item for item in active_items if item.get("stage") == "Translation"]
            if tts_items:
                logging.info(f"🎙️ [QUEUE] Iniciando Etapa de Geração de Voz para {len(tts_items)} arquivos...")
                for item in tts_items:
                    with self.lock:
                        if self.status != "processing":
                            break
                        item["status"] = "processing"
                        item["stage"] = "TTS"
                        item["progress"] = 5
                        item["message"] = "Iniciando Geração de Voz (TTS)..."
                        self.current_item_id = item["id"]
                        self.current_job_id = item["job_id"]
                        self.current_stage = "TTS"
                        self.save_queue_state()
                        
                    try:
                        pipeline_video_master(
                            video_path=item["file_path"],
                            job_id=item["job_id"],
                            source_lang=item.get("src_lang", "auto"),
                            target_lang=item.get("tgt_lang", "pt"),
                            stop_at_stage='tts'
                        )
                        with self.lock:
                            item["progress"] = 100
                            item["message"] = "Vozes Geradas"
                            self.save_queue_state()
                    except Exception as e:
                        tb = traceback.format_exc()
                        logging.error(f"❌ [QUEUE] Erro no TTS de {item['video_name']}: {e}")
                        with self.lock:
                            item["status"] = "failed"
                            item["error"] = str(e)
                            item["message"] = f"Erro no TTS: {e}"
                            write_error_json(item, e, tb)
                            self.save_queue_state()
                
                logging.info("🧹 [QUEUE] Fim da etapa de Dublagem. Descarregando Qwen3-TTS...")
                core.unload_qwen3_model()
                import gc; gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            # ETAPA 4: LOOP MERGE FINAL
            with self.lock:
                active_items = [item for item in self.items if item["status"] in ["pending", "processing"]]
            merge_items = [item for item in active_items if item.get("stage") == "TTS"]
            if merge_items:
                logging.info(f"🎬 [QUEUE] Iniciando Etapa de Merge Final para {len(merge_items)} arquivos...")
                for item in merge_items:
                    with self.lock:
                        if self.status != "processing":
                            break
                        item["status"] = "processing"
                        item["stage"] = "Merge"
                        item["progress"] = 5
                        item["message"] = "Realizando Merge Final (FFmpeg)..."
                        self.current_item_id = item["id"]
                        self.current_job_id = item["job_id"]
                        self.current_stage = "Merge"
                        self.save_queue_state()
                        
                    try:
                        out_video = pipeline_video_master(
                            video_path=item["file_path"],
                            job_id=item["job_id"],
                            source_lang=item.get("src_lang", "auto"),
                            target_lang=item.get("tgt_lang", "pt"),
                            stop_at_stage=None
                        )
                        
                        if out_video and os.path.exists(out_video):
                            orig_file = Path(item["file_path"])
                            dest_orig = QUEUE_COMPLETED_DIR / orig_file.name
                            if dest_orig.exists():
                                try: os.remove(str(dest_orig))
                                except: pass
                            shutil.move(str(orig_file), str(dest_orig))
                            
                            dest_out = QUEUE_OUTPUT_DIR / orig_file.name
                            if dest_out.exists():
                                try: os.remove(str(dest_out))
                                except: pass
                            shutil.copy2(out_video, str(dest_out))
                            
                            with self.lock:
                                item["status"] = "completed"
                                item["progress"] = 100
                                item["file_path"] = str(dest_orig)
                                item["message"] = "Operação Concluída com Sucesso!"
                                self.save_queue_state()
                        else:
                            raise Exception("FFmpeg falhou ao gerar o vídeo final")
                    except Exception as e:
                        tb = traceback.format_exc()
                        logging.error(f"❌ [QUEUE] Erro no Merge de {item['video_name']}: {e}")
                        with self.lock:
                            item["status"] = "failed"
                            item["error"] = str(e)
                            item["message"] = f"Erro no Merge: {e}"
                            write_error_json(item, e, tb)
                            self.save_queue_state()
                
                import gc; gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                time.sleep(3)

# --- APP VIDEO DE DUB ---
app_video = Flask("video_routes")
CORS(app_video)
app_video.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)

# Inicializa o gerenciador de fila
video_queue_manager = VideoQueueManager()
video_queue_manager.start_watchdog()

@app_video.route('/api/queue/add', methods=['POST'])
def api_queue_add():
    data = request.get_json() or {}
    path = data.get('path')
    src_lang = data.get('source_lang', 'auto')
    tgt_lang = data.get('target_lang', 'pt')
    
    if not path:
        return jsonify({"success": False, "message": "Caminho não fornecido."}), 400
        
    path_obj = Path(path)
    added_files = []
    
    if path_obj.is_dir():
        valid_exts = ('.mp4', '.mkv', '.avi', '.mov')
        files = sorted([path_obj / f for f in os.listdir(path_obj) if (path_obj / f).is_file() and f.lower().endswith(valid_exts)])
        if not files:
            return jsonify({"success": False, "message": "Nenhum arquivo de vídeo encontrado na pasta."})
        for f in files:
            success, msg = video_queue_manager.add_video(f, src_lang, tgt_lang)
            if success:
                added_files.append(f.name)
    else:
        success, msg = video_queue_manager.add_video(path_obj, src_lang, tgt_lang)
        if success:
            added_files.append(path_obj.name)
        else:
            return jsonify({"success": False, "message": msg})
            
    return jsonify({
        "success": True, 
        "message": f"Adicionado(s) {len(added_files)} vídeo(s) à fila.",
        "files": added_files
    })

@app_video.route('/api/queue/status', methods=['GET'])
def api_queue_status():
    with video_queue_manager.lock:
        items_copy = json.loads(json.dumps(video_queue_manager.items))
        status = video_queue_manager.status
        current_job_id = video_queue_manager.current_job_id
        current_item_id = video_queue_manager.current_item_id
        current_stage = video_queue_manager.current_stage
        
    if current_item_id and current_job_id:
        status_file = UPLOAD_FOLDER / current_job_id / "job_status.json"
        if status_file.exists():
            job_status = core.safe_json_read(status_file)
            if job_status:
                for item in items_copy:
                    if item["id"] == current_item_id:
                        item["progress"] = job_status.get("progress", item["progress"])
                        item["message"] = job_status.get("message", item["message"])
                        
    return jsonify({
        "status": status,
        "current_item_id": current_item_id,
        "current_job_id": current_job_id,
        "current_stage": current_stage,
        "items": items_copy
    })

@app_video.route('/api/queue/action', methods=['POST'])
def api_queue_action():
    data = request.get_json() or {}
    action = data.get('action')
    item_id = data.get('item_id')
    
    if action == 'start':
        video_queue_manager.start_worker()
        return jsonify({"success": True, "message": "Processamento da fila iniciado."})
    elif action == 'pause':
        video_queue_manager.pause_worker()
        return jsonify({"success": True, "message": "Fila pausada."})
    elif action == 'clear':
        video_queue_manager.clear_queue()
        return jsonify({"success": True, "message": "Fila limpa."})
    elif action == 'remove_item' and item_id:
        video_queue_manager.remove_item(item_id)
        return jsonify({"success": True, "message": "Item removido da fila."})
    else:
        return jsonify({"success": False, "message": f"Ação '{action}' desconhecida ou inválida."}), 400

@app_video.route('/api/health')
def video_health_check():
    return jsonify({"status": "online", "engine": "Titan Video"})

@app_video.route('/api/is_busy')
def video_api_is_busy():
    is_queue_busy = (video_queue_manager.status == "processing")
    return jsonify({"busy": len(_active_video_jobs) > 0 or is_queue_busy})

@app_video.route('/api/dublar_video', methods=['POST'])
def video_api_dublar_video():
    data = request.get_json()
    video_path = data.get('path')
    video_name = Path(video_path).stem
    video_name_clean = "".join([c if c.isalnum() or c in "._-" else "_" for c in video_name])
    if len(video_name_clean) > 40:
        short_hash = hashlib.md5(video_name.encode()).hexdigest()[:6]
        job_id = f"video_{video_name_clean[:30]}_{short_hash}"
    else:
        job_id = f"video_{video_name_clean}"
        
    global _active_video_jobs
    if job_id in _active_video_jobs:
        return jsonify({"success": True, "message": "Pipeline de vídeo já está rodando!"})
    _active_video_jobs.add(job_id)

    def thread_wrapper():
        try:
            pipeline_video_master(video_path, job_id, 'padrao', 'auto', 'pt', False)
        except Exception as e:
            logging.error(f"FALHA NO MOTOR DE VÍDEO ({job_id}): {e}")
            traceback.print_exc()
        finally:
            _active_video_jobs.discard(job_id)

    threading.Thread(target=thread_wrapper).start()
    return jsonify({"success": True, "job_id": job_id})

@app_video.route('/api/status/<job_id>')
def video_api_status(job_id):
    status_file = UPLOAD_FOLDER / job_id / "job_status.json"
    if status_file.exists():
        data = core.safe_json_read(status_file)
        if data: return jsonify(data)
    return jsonify({"status": "unknown", "progress": 0})

@app_video.route('/api/resume_video', methods=['POST'])
def video_api_resume_video():
    data = request.get_json()
    job_id = data.get('job_id')
    job_dir = UPLOAD_FOLDER / job_id
    status = core.safe_json_read(job_dir / "job_status.json")
    video_path = status.get('video_path') if status else None
    
    new_status = {
        "job_id": job_id,
        "video_path": video_path,
        "start_time": time.time(),
        "status": "retomado",
        "progress": 20, 
        "message": "Retomando projeto (pós-transcrição)..."
    }
    core.safe_json_write(new_status, job_dir / "job_status.json")

    global _active_video_jobs
    if job_id in _active_video_jobs:
        return jsonify({"success": True, "message": "Já em processamento."})
    _active_video_jobs.add(job_id)

    def thread_wrapper():
        try:
            pipeline_video_master(video_path, job_id, 'padrao', 'auto', 'pt', False)
        except Exception as e:
            logging.error(f"FALHA AO RETOMAR O MOTOR DE VÍDEO ({job_id}): {e}")
        finally:
            _active_video_jobs.discard(job_id)

    threading.Thread(target=thread_wrapper).start()
    return jsonify({"success": True, "job_id": job_id})

@app_video.route('/api/project/<job_id>/segments', methods=['GET'])
def video_api_get_segments(job_id):
    job_dir = UPLOAD_FOLDER / job_id
    project_data_path = job_dir / "project_data.json"
    if not project_data_path.exists():
        return jsonify({"success": False, "message": "Projeto não possui transcrição gerada ainda."}), 404
    data = core.safe_json_read(project_data_path)
    if not data or "segments" not in data:
        return jsonify({"success": False, "message": "Dados corrompidos."}), 400
    speakers = sorted(list(set(seg.get('speaker', 'voz_Unknown') for seg in data["segments"])))
    return jsonify({
        "success": True,
        "segments": data["segments"],
        "speakers": speakers
    })

@app_video.route('/api/project/<job_id>/segments', methods=['POST'])
def video_api_save_segments(job_id):
    job_dir = UPLOAD_FOLDER / job_id
    project_data_path = job_dir / "project_data.json"
    vocals_path = job_dir / "vocals.wav"
    if not project_data_path.exists():
        return jsonify({"success": False, "message": "Projeto não possui transcrição."}), 404
        
    req_data = request.get_json()
    new_segments = req_data.get('segments')
    if not new_segments:
        return jsonify({"success": False, "message": "Nenhum segmento enviado."}), 400
        
    data = core.safe_json_read(project_data_path) or {"job_id": job_id}
    data["segments"] = new_segments
    data["status"] = "transcribed"
    core.safe_json_write(data, project_data_path)
    
    cache_path = job_dir / "transcription_cache.json"
    core.safe_json_write(new_segments, cache_path)
    
    if vocals_path.exists():
        core.recriar_pastas_de_voz(job_dir, vocals_path, new_segments)
    return jsonify({"success": True, "message": "Roteiro e vozes salvos!"})

@app_video.route('/api/queue/open_watchdog', methods=['POST'])
def api_queue_open_watchdog():
    try:
        os.startfile(str(QUEUE_INPUT_DIR.absolute()))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# =================================================================
# EXECUÇÃO DO SERVIDOR (DIRECIONAMENTO POR PORTA)
# =================================================================

if __name__ == "__main__":
    import sys
    port = 5002  # Default to Games engine
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    if port == 5002:
        print("[GAME ENGINE] [MOTOR TITAN] Engenharia de Games online na porta 5002 [HOT-RELOAD]")
        app_games.run(host="127.0.0.1", port=5002, debug=False)
    elif port == 5004:
        print("[VIDEO ENGINE] [MOTOR TITAN] Engenharia de Vídeos online na porta 5004 [HOT-RELOAD]")
        app_video.run(host="127.0.0.1", port=5004, debug=False, use_reloader=False)
    else:
        print(f"[ERROR] Porta {port} inválida para o motor de dublagem.")
