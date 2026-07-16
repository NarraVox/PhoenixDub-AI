# -*- coding: utf-8 -*-
# Vortex DJ Web Server & Routes - [v2026.RTX_ULTRA]
# Contains all REST API endpoints for the Vortex dashboard.

import os
import json
import logging
import time
import shutil
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

def register_routes(app, dj_engine, UPLOAD_FOLDER):
    """Registers all Flask routes for the Vortex DJ engine using closure scope."""

    @app.route('/api/init_session', methods=['POST'])
    def init_session():
        data = request.json
        files = data.get('files', [])
        project_id = data.get('project_id')
        
        if not files and not project_id: 
            return jsonify({"error": "Nenhum dado para iniciar ou retomar"}), 400
        
        project_name = dj_engine.init_project(project_id)
        copied_count = 0
        if not project_id:
            for file_info in files:
                if isinstance(file_info, str):
                    f_name = file_info
                    src = UPLOAD_FOLDER / f_name
                else:
                    f_name = file_info.get('name')
                    src = Path(file_info.get('path'))
                    
                dst = dj_engine.source_dir / f_name
                if src.exists():
                    logging.info(f"🚚 [COPY] Movendo {f_name} para projeto...")
                    shutil.copy(src, dst)
                    if f_name not in dj_engine.project_state["tracks"]:
                        dj_engine.project_state["tracks"][f_name] = {}
                    copied_count += 1
            dj_engine.save_status()
        else:
            copied_count = len(list(dj_engine.source_dir.glob("*")))
                
        return jsonify({
            "success": True, 
            "project": project_name, 
            "copied": copied_count,
            "resumed": project_id is not None
        })

    @app.route('/api/list_uploads', methods=['GET'])
    def list_uploads():
        files = [f.name for f in UPLOAD_FOLDER.glob("*") if f.suffix.lower() in ['.mp3', '.wav']]
        return jsonify({"success": True, "files": files})

    @app.route('/api/upload_audio_file', methods=['POST'])
    def upload_audio_file():
        if 'audio' not in request.files:
            return jsonify({"error": "Nenhum arquivo de áudio foi enviado."}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "Nome de arquivo vazio."}), 400
            
        from werkzeug.utils import secure_filename
        filename = secure_filename(audio_file.filename)
        if not filename:
            filename = f"local_upload_{int(time.time())}.wav"
            
        dest_path = UPLOAD_FOLDER / filename
        audio_file.save(str(dest_path))
        return jsonify({"success": True, "filename": filename})

    @app.route('/api/get_job_status', methods=['GET'])
    def get_job_status():
        live_logs = list(dj_engine.live_logs)
        live_task = dj_engine.live_current_task
        
        if not live_logs and not live_task:
            status = dj_engine.load_status()
            status["worker_busy"] = dj_engine.worker_busy
            return jsonify(status)
        
        return jsonify({
            "logs": live_logs,
            "current_task": live_task,
            "worker_busy": dj_engine.worker_busy,
            "last_generated_song": dj_engine.project_state.get("last_generated_song", "")
        })

    @app.route('/api/transcribe_tracks', methods=['GET'])
    def transcribe_tracks():
        if not dj_engine.source_dir: return jsonify({"error": "Projeto não iniciado"}), 400
        dj_engine.project_state = dj_engine.load_status()

        if dj_engine.worker_busy:
            logging.warning("⚠️ [GUARD] BLOQUEIO ATIVO: Transcrição negada para evitar sobrecarga.")
            return jsonify({"success": True, "msg": "Worker já está ocupado.", "count": 0})
        
        files = list(dj_engine.source_dir.glob("*"))
        audio_files = [f for f in files if f.suffix.lower() in ['.mp3', '.wav']]
        
        to_transcribe = []
        for f in audio_files:
            track_data = dj_engine.project_state.get("tracks", {}).get(f.name, {})
            if not track_data.get("whisper_done") and not track_data.get("transcription") and not track_data.get("lyrics"):
                to_transcribe.append(f)
        
        if to_transcribe:
            dj_engine.transcribe_lot(to_transcribe)
        return jsonify({"success": True, "count": len(to_transcribe)})

    @app.route('/api/scan_tracks', methods=['GET'])
    def scan_tracks():
        if not dj_engine.source_dir: return jsonify({"error": "Projeto não iniciado"}), 400
        if dj_engine.worker_busy:
            logging.info("⏳ [GUARD] Fila ativa: Aguardando conclusão da tarefa anterior.")
            return jsonify({"success": True, "msg": "CPU Ocupada. A tarefa entrará na fila.", "count": 0})

        dj_engine.project_state = dj_engine.load_status()
        files = list(dj_engine.source_dir.glob("*"))
        audio_files = [f for f in files if f.suffix.lower() in ['.mp3', '.wav']]
        
        to_analyze = []
        for f in audio_files:
            track_data = dj_engine.project_state.get("tracks", {}).get(f.name, {})
            if not all(k in track_data for k in ["bpm", "beats", "energy_map"]):
                to_analyze.append(f)
        
        if to_analyze:
            dj_engine.analyze_lot(to_analyze)
        
        metadata_batch = []
        for f_path in audio_files:
            meta = dj_engine.project_state["tracks"].get(f_path.name, {})
            metadata_batch.append({"name": f_path.name, **meta})
        return jsonify({"success": True, "metadata": metadata_batch, "count": len(to_analyze)})

    @app.route('/api/curate_set', methods=['POST'])
    def curate_set():
        setlist = dj_engine.curate_set_fast()
        dj_engine.project_state["setlist"] = setlist
        dj_engine.save_status()
        return jsonify({"success": True, "setlist": setlist})

    @app.route('/api/ignite_mix', methods=['POST'])
    def ignite_mix():
        data = request.json
        ordered_metadata = data.get('ordered_metadata', [])
        
        if not ordered_metadata:
            logging.warning("⚠️ ordered_metadata vazio. Carregando do estado salvo...")
            current_state = dj_engine.load_status()
            saved_order = current_state.get("ordered_names", [])
            tracks = current_state.get("tracks", {})
            
            if saved_order:
                ordered_metadata = []
                for name in saved_order:
                    if name in tracks:
                        ordered_metadata.append({"name": name, **tracks[name]})
            
            if not ordered_metadata and tracks:
                ordered_metadata = [{"name": name, **meta} for name, meta in tracks.items()]
                ordered_metadata.sort(key=lambda x: x.get('bpm', 120))
            
            if not ordered_metadata:
                return jsonify({"error": "Sem músicas analisadas para mixar."}), 400

        if dj_engine.worker_busy:
            return jsonify({"error": "CPU Ocupada.", "details": "Aguarde a tarefa terminar."}), 429

        pending_analysis = []
        for m in ordered_metadata:
            has_energy = m.get('energy_map')
            has_text = m.get('transcription') or m.get('lyrics') or m.get('whisper_done')
            if not has_energy or not has_text:
                pending_analysis.append(m['name'])
                
        if pending_analysis:
            return jsonify({"error": "Aguarde o Scan Técnico terminar.", "details": f"Ainda analisando: {', '.join(pending_analysis[:3])}..."}), 429

        valid_metadata = [m for m in ordered_metadata if m and isinstance(m, dict) and 'name' in m]
        dj_engine.ignite_mix_lot(valid_metadata)
        return jsonify({"success": True, "msg": "Mixagem iniciada."})

    @app.route('/api/generate_music', methods=['POST'])
    def generate_music():
        data = request.json
        title = data.get('title', 'Desert Bass')
        style = data.get('style', 'Arabic Deep House')
        lyrics = data.get('lyrics', '')
        mode = data.get('mode', 'text2music')
        source_audio = data.get('source_audio', '')
        cover_strength = data.get('cover_strength', 0.6)
        extend_duration = data.get('extend_duration', 30)
        enable_mastering = data.get('enable_mastering', True)
        upscale_steps = int(data.get('upscale_steps', 25))
        steps = int(data.get('steps', 50))
        cfg_scale = float(data.get('cfg_scale', 4.0))
        duration = int(data.get('duration', 180))
        batch_count = int(data.get('batch_count', 1))
        
        if dj_engine.worker_busy:
            return jsonify({"error": "O motor Vortex já está ocupado com outra tarefa."}), 429
            
        dj_engine.worker_busy = True
        dj_engine.generating_music = True
        dj_engine.project_state["current_task"] = "🚀 Preparando motores para geração..."
        dj_engine.project_state["logs"] = []
        dj_engine.save_status()
        
        threading.Thread(
            target=dj_engine.run_music_generation_flow, 
            args=(title, style, lyrics, mode, source_audio, cover_strength, extend_duration, enable_mastering, steps, cfg_scale, duration, batch_count, upscale_steps)
        ).start()
        return jsonify({"success": True, "msg": "Fluxo de geração iniciado."})

    @app.route('/api/list_generated_songs', methods=['GET'])
    def list_generated_songs():
        history_file = dj_engine.generated_music_dir / "history.json"
        songs = []
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f: songs = json.load(f)
            except: pass
        return jsonify({"success": True, "songs": songs})

    def run_on_demand_mastering(filename, song_item):
        try:
            def update_status(task_msg, log_msg=None):
                logging.info(f"[STATUS] {task_msg} | {log_msg}")
                dj_engine.project_state.setdefault("logs", []).append(log_msg or task_msg)
                dj_engine.project_state["current_task"] = task_msg
                dj_engine.save_status()
                
            update_status("✨ [5%] Iniciando Masterização Sob Demanda...", "Carregando arquivos de áudio...")
            input_mp3_path = dj_engine.generated_music_dir / filename
            if not input_mp3_path.exists(): raise FileNotFoundError("Arquivo original não encontrado.")
                
            temp_wav_out = dj_engine.generated_music_dir / f"demand_master_{int(time.time())}.wav"
            upscale_steps = 25
            
            def progress_callback(block_idx, total_blocks):
                pct = 10 + int((block_idx / total_blocks) * 80)
                update_status(f"✨ [{pct}%] Masterizando: Bloco {block_idx}/{total_blocks}...", f"AudioSR: Bloco {block_idx} de {total_blocks}.")
                
            # Cirurgia + Upscale para On Demand:
            # Primeiro, fazemos o filtro passa-baixa em 13kHz para tirar o ruído metálico do MP3 bruto
            filtered_temp_path = dj_engine.generated_music_dir / f"filtered_demand_{int(time.time())}.wav"
            from nexus.dj.vortex_music import apply_lowpass_filter
            apply_lowpass_filter(input_mp3_path, filtered_temp_path, cutoff_hz=13000)
            
            # Depois, passamos no AudioSR para gerar o WAV com agudos limpos
            dj_engine.process_upscale(filtered_temp_path, temp_wav_out, ddim_steps=upscale_steps, progress_callback=progress_callback)
            
            update_status("✨ [92%] Convertendo áudio Hi-Fi...", "Executando FFmpeg para exportar MP3 masterizado...")
            clean_title = song_item["title"].replace(" (Sem Master)", "")
            new_filename = filename.replace("_raw_", "_mastered_")
            if new_filename == filename:
                base, ext = os.path.splitext(filename)
                new_filename = f"{base}_mastered{ext}"
                
            output_mp3_path = dj_engine.generated_music_dir / new_filename
            ffmpeg_cmd = ["ffmpeg", "-y", "-i", str(temp_wav_out), "-c:a", "libmp3lame", "-q:a", "2", str(output_mp3_path)]
            subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if temp_wav_out.exists(): os.remove(temp_wav_out)
            if filtered_temp_path.exists(): os.remove(filtered_temp_path)
            if input_mp3_path.exists(): os.remove(input_mp3_path)
                
            history_file = dj_engine.generated_music_dir / "history.json"
            if history_file.exists():
                try:
                    with open(history_file, "r", encoding="utf-8") as f: history = json.load(f)
                    for item in history:
                        if item.get("filename") == filename:
                            item["filename"] = new_filename
                            item["title"] = clean_title
                            item["mastered"] = True
                            break
                    with open(history_file, "w", encoding="utf-8") as f: json.dump(history, f, indent=4)
                except Exception as e:
                    logging.error(f"[ERR] Falha ao atualizar histórico: {e}")
                    
            dj_engine.project_state["last_generated_song"] = new_filename
            update_status("✅ [100%] Música masterizada com sucesso!", f"Pronto! '{clean_title}' agora está Hi-Fi.")
            
        except Exception as e:
            err_msg = f"❌ ERRO MASTERIZAÇÃO: {str(e)}"
            logging.error(err_msg)
            dj_engine.project_state.setdefault("logs", []).append(err_msg)
            dj_engine.project_state["current_task"] = err_msg
            dj_engine.save_status()
        finally:
            dj_engine.generating_music = False
            dj_engine.worker_busy = False
            dj_engine.save_status()

    @app.route('/api/master_song', methods=['POST'])
    def master_song():
        if dj_engine.generating_music or dj_engine.worker_busy:
            return jsonify({"error": "O motor de IA está ocupado."}), 400
            
        data = request.json or {}
        filename = data.get("filename")
        if not filename: return jsonify({"error": "Arquivo não fornecido."}), 400
            
        history_file = dj_engine.generated_music_dir / "history.json"
        if not history_file.exists(): return jsonify({"error": "Histórico não encontrado."}), 404
            
        try:
            with open(history_file, "r", encoding="utf-8") as f: history = json.load(f)
        except Exception as e:
            return jsonify({"error": f"Falha ao ler histórico: {str(e)}"}), 500
            
        song_item = None
        for item in history:
            if item.get("filename") == filename:
                song_item = item
                break
                
        if not song_item: return jsonify({"error": "Música não encontrada."}), 404
        if song_item.get("mastered") is True: return jsonify({"error": "Música já masterizada."}), 400
            
        dj_engine.worker_busy = True
        dj_engine.generating_music = True
        dj_engine.project_state["logs"] = []
        dj_engine.project_state["current_task"] = "✨ Preparando masterização sob demanda..."
        dj_engine.save_status()
        
        threading.Thread(target=run_on_demand_mastering, args=(filename, song_item)).start()
        return jsonify({"success": True, "msg": "Masterização iniciada."})

    @app.route('/generated/<path:filename>')
    def serve_generated_song(filename):
        return send_from_directory(str(dj_engine.generated_music_dir), filename)
