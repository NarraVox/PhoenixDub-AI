# -*- coding: utf-8 -*-
# NARRAVOX VORTEX ENGINE (v2026.TITAN) - Editor Criativo & Conversor de Mídia
# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo

import os
import sys
import time
import logging
import json
import re
import subprocess
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from nexus.editor.vortex_vfx import VortexAI, UPLOAD_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER
from nexus.editor.media_converter import MediaConverter, ConversionBatchQueue, detect_nvenc_hevc, probe_media_file, calculate_conversion_plan

app = Flask(__name__)
CORS(app)

CONVERSIONS_FOLDER = UPLOAD_FOLDER / "conversoes"
os.makedirs(CONVERSIONS_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

vortex = VortexAI()
batch_queue = ConversionBatchQueue(max_workers=4, output_dir=str(CONVERSIONS_FOLDER))

vortex_status = {"progress": 0, "message": "Motor Vortex pronto.", "status": "idle"}
vortex_lock = threading.Lock()

def check_ffmpeg():
    """Garante que o FFmpeg está no PATH."""
    local_full_bin = UPLOAD_FOLDER.parent / 'env' / 'Library' / 'bin' / 'ffmpeg.exe'
    if local_full_bin.exists():
        os.environ["PATH"] = str(local_full_bin.parent) + os.pathsep + os.environ["PATH"]
        return True
    return False

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "online",
        "engine": "Vortex Editor",
        "hevc_nvenc": detect_nvenc_hevc()
    })

@app.route('/api/is_busy')
def api_is_busy():
    is_busy = (vortex_status.get("status") not in ["idle", "done", "error"]) or batch_queue.is_running
    return jsonify({"busy": is_busy})

@app.route('/stream_media')
def stream_media():
    video_path = request.args.get('path')
    if not video_path or not os.path.exists(video_path):
        return "Arquivo não encontrado", 404
    return send_file(video_path, conditional=True)

# ── ENDPOINTS DE CONVERSÃO DE MÍDIA (ÁUDIO 160k PADRÃO & VÍDEO H.265) ────────

@app.route('/api/probe_media_batch', methods=['POST'])
def api_probe_media_batch():
    """Analisa arquivos previamente selecionados calculando resolução original, codec e estimativa de tamanho/economia."""
    data = request.json or {}
    paths = data.get('paths', [])
    target_codec = data.get('target_codec', 'h265')
    max_res = data.get('max_res', '1080p')
    audio_bitrate = data.get('audio_bitrate', '160k')
    skip_if_less_10_pct = data.get('skip_if_less_10_pct', True)

    results = []
    for p in paths:
        if not p:
            continue
        info = probe_media_file(p)
        plan = calculate_conversion_plan(
            info,
            target_codec=target_codec,
            max_res=max_res,
            audio_bitrate=audio_bitrate,
            skip_if_less_10_pct=skip_if_less_10_pct
        )
        results.append({
            'path': p,
            'info': info,
            'plan': plan
        })
    return jsonify({"success": True, "results": results})

@app.route('/api/convert_batch', methods=['POST'])
def api_convert_batch():
    """Adiciona múltiplos arquivos à fila de conversão e inicia o processamento."""
    data = request.json or {}
    items = data.get('items', [])
    if not items:
        return jsonify({"success": False, "message": "Nenhum arquivo fornecido para conversão."}), 400

    added = batch_queue.add_items(items)
    if not added:
        return jsonify({"success": False, "message": "Nenhum arquivo válido adicionado."}), 400

    started = batch_queue.start_batch()
    return jsonify({
        "success": True,
        "added": len(added),
        "started": started,
        "message": f"{len(added)} arquivo(s) enfileirado(s) com sucesso."
    })

@app.route('/api/conversion_status')
def api_conversion_status():
    """Retorna telemetria da fila de conversão em lote."""
    return jsonify(batch_queue.get_status())

@app.route('/api/conversion_cancel', methods=['POST'])
def api_conversion_cancel():
    batch_queue.cancel_batch()
    return jsonify({"success": True, "message": "Cancelamento de conversão solicitado."})

@app.route('/api/conversion_clear', methods=['POST'])
def api_conversion_clear():
    ok = batch_queue.clear_queue()
    return jsonify({"success": ok, "message": "Fila limpa." if ok else "Fila em execução, não foi possível limpar."})

@app.route('/api/open_output_folder', methods=['GET', 'POST'])
def api_open_output_folder():
    """Abre a pasta de arquivos convertidos no Windows Explorer."""
    folder = str((CONVERSIONS_FOLDER).resolve())
    try:
        Path(folder).mkdir(parents=True, exist_ok=True)
        if sys.platform != "win32":
            raise OSError("A abertura da pasta requer Windows.")
        explorer = Path(os.environ.get("WINDIR", "C:/Windows")) / "explorer.exe"
        subprocess.Popen([str(explorer), "/n,", str(folder)])
        return jsonify({"success": True, "folder": folder})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "folder": folder}), 500


# ── FERRAMENTAS VORTEX LEGADAS (CORTE, MERGE, PARALLAX) ──────────────────────

def update_status(prog, msg, status="processing"):
    with vortex_lock:
        vortex_status.update({"progress": prog, "message": msg, "status": status})

@app.route('/api/vortex_tool', methods=['POST'])
def api_vortex_tool():
    data = request.json or {}
    tool = data.get('tool')
    input_file = data.get('input_file')
    start_time = data.get('start', '00:00:00')
    end_time = data.get('end', '00:00:10')
    job_id = data.get('job_id', f"vortex_{int(time.time())}")

    def run_trim():
        try:
            update_status(0, "Iniciando corte acelerado (RTX 3050)...", "processing")
            def format_time(t):
                t = t.strip().replace(',', '.')
                parts = t.split(':')
                if len(parts) == 1: return f"00:00:{float(parts[0]):05.2f}"
                elif len(parts) == 2: return f"00:{int(parts[0]):02d}:{float(parts[1]):05.2f}"
                return t

            st = format_time(start_time)
            et = format_time(end_time)
            
            def to_sec(t):
                try:
                    h, m, s = map(float, t.split(':'))
                    return h*3600 + m*60 + s
                except Exception: return 1.0

            requested_duration = max(1.0, to_sec(et) - to_sec(st))
            abs_input = os.path.abspath(input_file)
            output_name = f"TRIM_{int(time.time())}.mp4"
            abs_output = str((OUTPUT_FOLDER / output_name).resolve())

            # Detecta encoder HEVC disponível (hevc_nvenc → libx265 fallback)
            try:
                result = subprocess.run(
                    ['ffmpeg', '-f', 'lavfi', '-i', f'color=c=black:s=320x240:d=1',
                     '-c:v', 'hevc_nvenc', '-f', 'null', '-'], capture_output=True, timeout=5
                )
                has_gpu_hevc = result.returncode == 0
            except:
                has_gpu_hevc = False

            if has_gpu_hevc:
                cmd = (
                    f'ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -ss {st} -to {et} -i "{abs_input}" '
                    f'-c:v hevc_nvenc -preset p4 -tune hq -rc vbr -b:v 2500k -maxrate:v 5000k -bufsize:v 3750k '
                    f'-avoid_negative_ts make_zero -map_metadata -1 -movflags +faststart -c:a aac -b:a 160k "{abs_output}"'
                )
            else:
                cmd = (
                    f'ffmpeg -y -ss {st} -to {et} -i "{abs_input}" '
                    f'-c:v libx265 -preset medium -tune null -rc vbr -b:v 2500k -maxrate:v 5000k -bufsize:v 3750k '
                    f'-avoid_negative_ts make_zero -map_metadata -1 -movflags +faststart -c:a aac -b:a 160k "{abs_output}"'
                )
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
            for line in process.stdout:
                if "time=" in line:
                    try:
                        time_part = line.split("time=")[1].split(" ")[0]
                        current_sec = to_sec(time_part)
                        pct = min(99, int((current_sec / requested_duration) * 100))
                        update_status(pct, f"GPU Rendering... {pct}%", "processing")
                    except Exception: pass
            process.wait()

            if process.returncode == 0:
                update_status(100, "Corte RTX concluído!", "done")
                try: os.startfile(os.path.dirname(abs_output))
                except Exception: pass
            else:
                update_status(0, "Erro no processamento GPU.", "error")
        except Exception as e:
            update_status(0, f"Erro crítico: {str(e)}", "error")

    def run_merge():
        try:
            video_list = data.get('files', [])
            if not video_list:
                update_status(0, "Nenhum arquivo selecionado.", "error")
                return

            update_status(10, f"Organizando {len(video_list)} clips...", "processing")
            list_path = TEMP_FOLDER / f"merge_list_{int(time.time())}.txt"
            with open(list_path, 'w', encoding='utf-8') as f:
                for v in video_list:
                    abs_v = os.path.abspath(v).replace('\\', '/')
                    f.write(f"file '{abs_v}'\n")

            final_output = OUTPUT_FOLDER / f"MERGE_FINAL_{int(time.time())}.mp4"
            abs_output = str(final_output.resolve())

            # Detecta encoder HEVC disponível (hevc_nvenc → libx265 fallback)
            try:
                result = subprocess.run(
                    ['ffmpeg', '-f', 'lavfi', '-i', f'color=c=black:s=320x240:d=1',
                     '-c:v', 'hevc_nvenc', '-f', 'null', '-'], capture_output=True, timeout=5
                )
                has_gpu_hevc = result.returncode == 0
            except:
                has_gpu_hevc = False

            if has_gpu_hevc:
                cmd = (
                    f'ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -f concat -safe 0 -i "{list_path}" '
                    f'-c:v hevc_nvenc -preset p4 -tune hq -rc vbr -b:v 2500k -maxrate:v 5000k -bufsize:v 3750k '
                    f'-spatial-aq 1 -avoid_negative_ts make_zero -c:a aac -b:a 160k "{abs_output}"'
                )
            else:
                cmd = (
                    f'ffmpeg -y -f concat -safe 0 -i "{list_path}" '
                    f'-c:v libx265 -preset medium -tune null -rc vbr -b:v 2500k -maxrate:v 5000k -bufsize:v 3750k '
                    f'-spatial-aq 1 -avoid_negative_ts make_zero -c:a aac -b:a 160k "{abs_output}"'
                )
            update_status(20, "Renderizando via RTX 3050...", "processing")
            res = subprocess.run(cmd, shell=True, capture_output=True)
            if res.returncode == 0:
                update_status(100, "Junção RTX concluída!", "done")
                try: os.startfile(os.path.dirname(abs_output))
                except Exception: pass
            else:
                update_status(0, "Falha na junção via hardware.", "error")
        except Exception as e:
            update_status(0, f"Erro no Merge: {str(e)}", "error")

    def run_multi_trim():
        """Renderiza múltiplos trechos sequencialmente, atualizando o progresso."""
        try:
            cuts = data.get('cuts', [])
            if not cuts:
                update_status(0, "Nenhum corte definido.", "error")
                return

            total_cuts = len(cuts)
            update_status(0, f"Renderizando {total_cuts} cortes...", "processing")

            for i, cut in enumerate(cuts):
                start_time = cut.get('start', '00:00:00')
                end_time = cut.get('end', '00:00:10')
                progress_step = 100 // total_cuts

                update_status(0, f"Corte {i+1}/{total_cuts}: Iniciando...", "processing")

                def format_time(t):
                    t = t.strip().replace(',', '.')
                    parts = t.split(':')
                    if len(parts) == 1:
                        return f"00:00:{float(parts[0]):05.2f}"
                    elif len(parts) == 2:
                        return f"00:{int(parts[0]):02d}:{float(parts[1]):05.2f}"
                    return t

                st = format_time(start_time)
                et = format_time(end_time)

                def to_sec(t):
                    try:
                        h, m, s = map(float, t.split(':'))
                        return h*3600 + m*60 + s
                    except Exception:
                        return 1.0

                requested_duration = max(1.0, to_sec(et) - to_sec(st))
                abs_input = os.path.abspath(input_file)
                output_name = f"TRIM_{int(time.time())}_{i+1:03d}.mp4"
                abs_output = str((OUTPUT_FOLDER / output_name).resolve())

                try:
                    result = subprocess.run(
                        ['ffmpeg', '-f', 'lavfi', '-i', f'color=c=black:s=320x240:d=1',
                         '-c:v', 'hevc_nvenc', '-f', 'null', '-'], capture_output=True, timeout=5
                    )
                    has_gpu_hevc = result.returncode == 0
                except:
                    has_gpu_hevc = False

                if has_gpu_hevc:
                    cmd = (
                        f'ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -ss {st} -to {et} -i "{abs_input}" '
                        f'-c:v hevc_nvenc -preset p4 -tune hq -rc vbr -b:v 2500k -maxrate:v 5000k -bufsize:v 3750k '
                        f'-avoid_negative_ts make_zero -map_metadata -1 -movflags +faststart -c:a aac -b:a 160k "{abs_output}"'
                    )
                else:
                    cmd = (
                        f'ffmpeg -y -ss {st} -to {et} -i "{abs_input}" '
                        f'-c:v libx265 -preset medium -tune null -rc vbr -b:v 2500k -maxrate:v 5000k -bufsize:v 3750k '
                        f'-avoid_negative_ts make_zero -map_metadata -1 -movflags +faststart -c:a aac -b:a 160k "{abs_output}"'
                    )

                update_status(10 + (i * progress_step), f"Corte {i+1}/{total_cuts}: Renderizando...", "processing")
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)

                for line in process.stdout:
                    if "time=" in line:
                        try:
                            time_part = line.split("time=")[1].split(" ")[0]
                            current_sec = to_sec(time_part)
                            pct = min(99, int((current_sec / requested_duration) * 100))
                            update_status(10 + (i * progress_step) + pct, f"Corte {i+1}/{total_cuts}: {pct}%", "processing")
                        except Exception:
                            pass
                process.wait()

                if process.returncode == 0:
                    update_status(100 + (i * progress_step), f"Corte {i+1}/{total_cuts}: OK!", "done")
                    try:
                        os.startfile(os.path.dirname(abs_output))
                    except Exception:
                        pass
                else:
                    update_status(100 + (i * progress_step), f"Corte {i+1}/{total_cuts}: ERRO", "error")

            update_status(100, f"Renderizar Todos concluído! {total_cuts} cortes processados.", "done")

        except Exception as e:
            update_status(0, f"Erro no Multi-Trim: {str(e)}", "error")

    if tool == 'multi_trim':
        threading.Thread(target=run_multi_trim, daemon=True).start()
        return jsonify({"success": True, "message": "Renderizar Todos iniciado."})

    if tool == 'trim':
        threading.Thread(target=run_trim, daemon=True).start()
        return jsonify({"success": True, "message": "Corte iniciado."})
    if tool == 'merge':
        threading.Thread(target=run_merge, daemon=True).start()
        return jsonify({"success": True, "message": "Junção iniciada."})
    if tool == 'parallax':
        out_parallax = OUTPUT_FOLDER / f"parallax_{int(time.time())}.mp4"
        success = vortex.apply_creative_vfx(input_file, str(out_parallax), style="vortex_hbo")
        return jsonify({"success": success, "message": "Parallax concluído!"})
    if tool == 'captions':
        success = vortex.apply_captions(input_file, job_id)
        return jsonify({"success": success, "message": "Legendas iniciadas."})
    if tool == 'studio_sound':
        success = vortex.apply_studio_sound(input_file, job_id)
        return jsonify({"success": success, "message": "Som de Estúdio iniciado."})

    return jsonify({"success": False, "message": f"Ferramenta {tool} não reconhecida."})

@app.route('/api/analyze_asset', methods=['POST'])
def analyze_asset():
    data = request.json or {}
    filename = data.get('filename', '')
    effect, reason = vortex.ask_gemma_for_effect(filename)
    return jsonify({"suggested_effect": effect, "reason": reason, "available_effects": vortex.effects})

@app.route('/api/vortex_status')
def api_vortex_status():
    with vortex_lock:
        return jsonify(vortex_status)

@app.route('/api/create_shorts', methods=['POST'])
def api_create_shorts():
    data = request.json or {}
    job_id = f"vortex_short_{int(time.time())}"
    photos = data.get('photos', [])
    music = data.get('music')
    if not photos or not music:
        return jsonify({"success": False, "message": "Fotos e Música são obrigatórios!"})
    success = vortex.create_shorts_montage(job_id, photos, music)
    return jsonify({"success": success, "job_id": job_id, "message": "Montagem concluída!"})

@app.route('/')
def home():
    return "🌪️ [VORTEX ENGINE] Editor Criativo & Conversor de Mídia na porta 5003."

def start_service():
    check_ffmpeg()
    print("🌪️ [MOTOR VORTEX] Estúdio Criativo & Conversor (v2026.TITAN) na porta 5003")
    app.run(host="127.0.0.1", port=5003, debug=False)

if __name__ == "__main__":
    start_service()
