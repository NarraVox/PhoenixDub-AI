# -*- coding: utf-8 -*-
# Vortex DJ Main Engine Entrypoint - [v2026.RTX_ULTRA]
# Optimized for RTX 3050 (6GB VRAM) and decoupled pipelines.
# Compliant with 2,000-token modular guidelines.

import os
import sys
import subprocess
import json
import logging
import time
import re
import shutil
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import nexus.core as core

# --- LOGS CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURATION OF CENTRAL FOLDERS ---
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
ENV_DIR = BASE_DIR / "env"
ENV_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
CORS(app)

@app.route('/api/health')
def health_check():
    return jsonify({"status": "online", "engine": "Vortex DJ"})

@app.route('/api/is_busy')
def api_is_busy():
    is_busy = False
    if 'dj_engine' in globals():
        is_busy = getattr(dj_engine, 'worker_busy', False) or getattr(dj_engine, 'generating_music', False)
    return jsonify({"busy": bool(is_busy)})

print("\n" + "="*50)
print("🌪️  VORTEX DJ ENGINE - [v2026.STABLE.MODULAR] - ACTIVE")
print("="*50 + "\n")

class VortexDJ:
    def __init__(self):
        self.projects_root = UPLOAD_FOLDER / "dj_projects"
        self.projects_root.mkdir(parents=True, exist_ok=True)
        self.generated_music_dir = UPLOAD_FOLDER / "generated_music"
        self.generated_music_dir.mkdir(parents=True, exist_ok=True)
        self.current_project_dir = None
        self.status_file = UPLOAD_FOLDER / "global_vortex_status.json"
        self.project_state = self.load_status()
        self.worker_busy = False
        self.generating_music = False
        self.current_worker_process = None 
        self.active_process = None
        self.ace_server_process = None
        self.ace_server_log_file = None
        from collections import deque
        self.live_logs = deque(maxlen=300)
        self.live_current_task = ""

    def stop_ace_server(self):
        if self.ace_server_process:
            try:
                self.ace_server_process.terminate()
                self.ace_server_process.wait(timeout=5)
            except:
                try: self.ace_server_process.kill()
                except: pass
            self.ace_server_process = None
        if hasattr(self, 'ace_server_log_file') and self.ace_server_log_file:
            try: self.ace_server_log_file.close()
            except: pass
            self.ace_server_log_file = None

    def init_project(self, name=None):
        if not name:
            name = f"job_vortex_{time.strftime('%Y%m%d_%H%M%S')}"
        self.current_project_dir = self.projects_root / name
        self.source_dir = self.current_project_dir / "source"
        self.stems_dir = self.current_project_dir / "stems"
        self.output_dir = self.current_project_dir / "output"
        self.status_file = self.current_project_dir / "job_status.json"

        for p in [self.source_dir, self.stems_dir, self.output_dir]:
            p.mkdir(parents=True, exist_ok=True)
            
        self.project_state = self.load_status()
        if not self.worker_busy:
            self.project_state["current_task"] = ""
        self.save_status()
        logging.info(f"📁 [PROJETO] Nucleo ativo em: {name}")
        return name

    def load_status(self):
        if self.status_file and self.status_file.exists():
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "tracks" not in data: data["tracks"] = {}
                    if "completed_mixes" not in data: data["completed_mixes"] = []
                    return data
            except: pass
        return {"tracks": {}, "completed_mixes": [], "logs": []}

    def save_status(self):
        if self.status_file:
            try:
                with open(self.status_file, 'w', encoding='utf-8') as f:
                    json.dump(self.project_state, f, indent=4)
            except Exception as e:
                logging.error(f"Erro ao salvar status: {e}")

    def process_upscale(self, input_path, output_path, ddim_steps=25, guidance_scale=3.5, progress_callback=None):
        from nexus.dj.vortex_utils import process_upscale_logic
        return process_upscale_logic(input_path, output_path, ddim_steps, guidance_scale, progress_callback, UPLOAD_FOLDER)

    def mix_tracks_professional(self, track_a_data, track_b_data, output_name, custom_output=None):
        from nexus.dj.vortex_utils import mix_tracks_professional_logic
        return mix_tracks_professional_logic(self, track_a_data, track_b_data, output_name, custom_output)

    def separate_stems(self, track_path):
        from nexus.dj.vortex_utils import separate_stems_logic
        return separate_stems_logic(self, track_path)

    def run_music_generation_flow(self, title, style, lyrics, mode='text2music', source_audio='', cover_strength=0.6, extend_duration=30, enable_mastering=True, steps=30, cfg_scale=4.0, duration=60, batch_count=1, upscale_steps=25):
        from nexus.dj.vortex_music import run_music_generation_flow_logic
        return run_music_generation_flow_logic(self, title, style, lyrics, mode, source_audio, cover_strength, extend_duration, enable_mastering, steps, cfg_scale, duration, batch_count, upscale_steps)

    def ignite_mix_lot(self, valid_metadata):
        from nexus.dj.vortex_mix import ignite_mix_lot_logic
        return ignite_mix_lot_logic(self, valid_metadata)

    def _auto_schedule_fx(self, track_name, track_data):
        from nexus.dj.vortex_curator import auto_schedule_fx_logic
        return auto_schedule_fx_logic(self, track_name, track_data)

    def curate_set_fast(self):
        from nexus.dj.vortex_curator import curate_set_fast_logic
        return curate_set_fast_logic(self)

    def _check_vocal_conflict(self, data_a, data_b):
        from nexus.dj.vortex_curator import check_vocal_conflict_logic
        return check_vocal_conflict_logic(self, data_a, data_b)

    def transcribe_lot(self, track_paths):
        import threading
        self.worker_busy = True
        def run():
            temp_list = [str(p) for p in track_paths]
            temp_list_path = UPLOAD_FOLDER / f"whisper_queue_{int(time.time())}.json"
            with open(temp_list_path, 'w') as f:
                json.dump(temp_list, f)
            cmd = [sys.executable, __file__, "--worker-whisper", str(temp_list_path), str(self.status_file)]
            self.current_worker_process = subprocess.Popen(cmd)
            self.current_worker_process.wait()
            try: os.remove(temp_list_path)
            except: pass
            self.worker_busy = False
        threading.Thread(target=run).start()

    def analyze_lot(self, track_paths):
        import threading
        self.worker_busy = True
        def run():
            temp_list = [str(p) for p in track_paths]
            temp_list_path = UPLOAD_FOLDER / f"analysis_queue_{int(time.time())}.json"
            with open(temp_list_path, 'w') as f:
                json.dump(temp_list, f)
            cmd = [sys.executable, __file__, "--worker-analysis", str(temp_list_path), str(self.status_file)]
            self.current_worker_process = subprocess.Popen(cmd)
            self.current_worker_process.wait()
            try: os.remove(temp_list_path)
            except: pass
            self.worker_busy = False
        threading.Thread(target=run).start()

    def stop_current_worker(self):
        if self.current_worker_process:
            try:
                self.current_worker_process.terminate()
                self.current_worker_process.wait(timeout=5)
            except:
                try: self.current_worker_process.kill()
                except: pass
            self.current_worker_process = None
        self.worker_busy = False
        self.project_state["current_task"] = None
        self.save_status()

    def download_file_with_progress(self, url, dest_path, task_name, status_callback):
        import requests
        temp_dest = dest_path.with_suffix(".tmp")
        try:
            r = requests.get(url, stream=True, timeout=30)
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            with open(temp_dest, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        downloaded += len(chunk)
                        f.write(chunk)
                        if total_size > 0:
                            pct = int((downloaded / total_size) * 100)
                            status_callback(f"⬇️ Baixando {task_name}: {pct}%", f"Progresso: {pct}% | {downloaded // 1024 // 1024}MB de {total_size // 1024 // 1024}MB")
            if temp_dest.exists():
                shutil.move(str(temp_dest), str(dest_path))
        except Exception as e:
            if temp_dest.exists(): os.remove(temp_dest)
            raise e

dj_engine = VortexDJ()

# Register routes using the web app module
from nexus.dj.vortex_app import register_routes
register_routes(app, dj_engine, UPLOAD_FOLDER)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        from nexus.dj.vortex_workers import run_transcription, run_analysis
        if sys.argv[1] == "--worker-whisper":
            run_transcription(sys.argv[2], sys.argv[3])
            sys.exit(0)
        elif sys.argv[1] == "--worker-analysis":
            run_analysis(sys.argv[2], sys.argv[3])
            sys.exit(0)

    app.run(host="127.0.0.1", port=5005, debug=False, use_reloader=False)
