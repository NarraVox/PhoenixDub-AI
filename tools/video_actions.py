# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import os
import sys
import json
import logging
import subprocess
import threading
from pathlib import Path
from flask import Blueprint, jsonify, request

import tools.video_services as services

logger = logging.getLogger("AiderDashboard.VideoActions")
video_actions = Blueprint('video_actions', __name__)

@video_actions.route("/api/video_copilot/quick_action", methods=["POST"])
def api_video_copilot_quick_action():
    data = request.json
    if not data or "action" not in data:
        return jsonify({"success": False, "error": "Ação inválida"}), 400
        
    action = data["action"]
    if services.render_process is not None and services.render_process.poll() is None:
        return jsonify({"success": False, "error": "Uma ação já está em andamento!"}), 400
        
    config_file = services.ROOT_DIR / "scratch" / "video_editor_config.json"
    current_config = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                current_config = json.load(f)
        except: pass
            
    video_path = current_config.get("video_path")
    project_folder = current_config.get("project_folder")
    
    if not video_path or not project_folder:
        return jsonify({"success": False, "error": "Selecione um vídeo primeiro!"}), 400
        
    video_path_obj = Path(video_path)
    project_folder_path = Path(project_folder)
    base_name = video_path_obj.stem
    
    try: services.RENDER_LOG.write_text("", encoding="utf-8")
    except: pass
        
    ffmpeg_bin = r"C:\IA_dublagem\env\Library\bin\ffmpeg.exe"
    if not os.path.exists(ffmpeg_bin):
        ffmpeg_bin = "ffmpeg"
        
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    python_bin = sys.executable
    
    if action == "extract_audio":
        output_mp3 = str((project_folder_path / f"{base_name}_audio.mp3").resolve())
        try:
            services.RENDER_LOG.write_text(f"[INFO] Extraindo áudio original do vídeo...\nEntrada: {video_path}\nSaída: {output_mp3}\n\n", encoding="utf-8")
            log_file = open(services.RENDER_LOG, "a", encoding="utf-8")
            cmd = [ffmpeg_bin, "-y", "-i", video_path, "-vn", "-c:a", "libmp3lame", "-q:a", "2", output_mp3]
            
            services.render_process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, creationflags=creationflags)
            
            def log_success_watcher(p, path):
                p.wait()
                try:
                    with open(services.RENDER_LOG, "a", encoding="utf-8") as lf:
                        if p.returncode == 0:
                            lf.write(f"\n[SUCESSO] Áudio extraído!\nSalvo em: {path}\n")
                        else:
                            lf.write(f"\n[ERRO] Falha ao extrair áudio. Retorno: {p.returncode}\n")
                except: pass
            threading.Thread(target=log_success_watcher, args=(services.render_process, output_mp3), daemon=True).start()
            return jsonify({"success": True, "msg": "Extração de áudio iniciada!"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
            
    elif action == "render_preview":
        try:
            if "options" not in current_config:
                current_config["options"] = {}
            current_config["options"]["preview_mode"] = True
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(current_config, f, indent=2, ensure_ascii=False)
                
            from tools.video_routes import api_video_copilot_render
            return api_video_copilot_render()
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
            
    elif action == "speedup_125":
        output_speedup = str((project_folder_path / f"{base_name}_acelerado.mp4").resolve())
        try:
            services.RENDER_LOG.write_text(f"[INFO] Acelerando vídeo original para 1.25x...\nEntrada: {video_path}\nSaída: {output_speedup}\n\n", encoding="utf-8")
            log_file = open(services.RENDER_LOG, "a", encoding="utf-8")
            
            def run_speedup_thread():
                cmd_gpu = [
                    ffmpeg_bin, "-y", "-hwaccel", "cuda", "-i", video_path,
                    "-filter_complex", "[0:v]setpts=0.8*PTS[v];[0:a]atempo=1.25[a]",
                    "-map", "[v]", "-map", "[a]",
                    "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "24",
                    "-c:a", "aac", "-b:a", "192k",
                    output_speedup
                ]
                services.render_process = subprocess.Popen(cmd_gpu, stdout=log_file, stderr=subprocess.STDOUT, creationflags=creationflags)
                ret = services.render_process.wait()
                
                if ret != 0:
                    with open(services.RENDER_LOG, "a", encoding="utf-8") as lf:
                        lf.write("\n[AVISO] GPU NVENC falhou. Iniciando fallback via CPU...\n")
                    cmd_cpu = [
                        ffmpeg_bin, "-y", "-i", video_path,
                        "-filter_complex", "[0:v]setpts=0.8*PTS[v];[0:a]atempo=1.25[a]",
                        "-map", "[v]", "-map", "[a]",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-c:a", "aac", "-b:a", "192k",
                        output_speedup
                    ]
                    services.render_process = subprocess.Popen(cmd_cpu, stdout=log_file, stderr=subprocess.STDOUT, creationflags=creationflags)
                    ret_cpu = services.render_process.wait()
                    with open(services.RENDER_LOG, "a", encoding="utf-8") as lf:
                        if ret_cpu == 0:
                            lf.write(f"\n[SUCESSO] Vídeo acelerado via CPU!\nSalvo em: {output_speedup}\n")
                        else:
                            lf.write(f"\n[ERRO] Falha na aceleração via CPU. Retorno: {ret_cpu}\n")
                else:
                    with open(services.RENDER_LOG, "a", encoding="utf-8") as lf:
                        lf.write(f"\n[SUCESSO] Vídeo acelerado via GPU!\nSalvo em: {output_speedup}\n")
                        
            threading.Thread(target=run_speedup_thread, daemon=True).start()
            return jsonify({"success": True, "msg": "Aceleração de vídeo iniciada!"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
            
    elif action == "denoise":
        output_denoise = str((project_folder_path / f"{base_name}_limpo.mp4").resolve())
        try:
            services.RENDER_LOG.write_text(f"[INFO] Aplicando redução de ruído...\nEntrada: {video_path}\nSaída: {output_denoise}\n\n", encoding="utf-8")
            log_file = open(services.RENDER_LOG, "a", encoding="utf-8")
            
            def run_denoise_thread():
                cmd_gpu = [
                    ffmpeg_bin, "-y", "-hwaccel", "cuda", "-i", video_path, "-af", "afftdn",
                    "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "24", "-c:a", "aac", "-b:a", "192k",
                    output_denoise
                ]
                services.render_process = subprocess.Popen(cmd_gpu, stdout=log_file, stderr=subprocess.STDOUT, creationflags=creationflags)
                ret = services.render_process.wait()
                
                if ret != 0:
                    with open(services.RENDER_LOG, "a", encoding="utf-8") as lf:
                        lf.write("\n[AVISO] GPU NVENC falhou. Iniciando fallback via CPU...\n")
                    cmd_cpu = [
                        ffmpeg_bin, "-y", "-i", video_path, "-af", "afftdn",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", "-b:a", "192k",
                        output_denoise
                    ]
                    services.render_process = subprocess.Popen(cmd_cpu, stdout=log_file, stderr=subprocess.STDOUT, creationflags=creationflags)
                    ret_cpu = services.render_process.wait()
                    with open(services.RENDER_LOG, "a", encoding="utf-8") as lf:
                        if ret_cpu == 0:
                            lf.write(f"\n[SUCESSO] Redução de ruído concluída via CPU!\n")
                        else:
                            lf.write(f"\n[ERRO] Falha no noise filter. Retorno: {ret_cpu}\n")
                else:
                    with open(services.RENDER_LOG, "a", encoding="utf-8") as lf:
                        lf.write(f"\n[SUCESSO] Redução de ruído concluída via GPU!\n")
                        
            threading.Thread(target=run_denoise_thread, daemon=True).start()
            return jsonify({"success": True, "msg": "Redução de ruído iniciada!"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
            
    elif action == "translate_en":
        txt_path = project_folder_path / "transcricao_video.txt"
        if not txt_path.exists():
            return jsonify({"success": False, "error": "Transcrição não encontrada."}), 400
            
        config = services.load_config()
        host = config.get("host", "127.0.0.1")
        port = config.get("port", 1234)
        
        if not services.check_server_online(host, port):
            return jsonify({"success": False, "error": "Servidor de IA local está OFFLINE!"}), 400
            
        try:
            services.RENDER_LOG.write_text("[INFO] Iniciando tradução para inglês...\n\n", encoding="utf-8")
            log_file = open(services.RENDER_LOG, "a", encoding="utf-8")
            
            # Escape strings to protect python code generation from path injection
            escaped_project_folder = str(project_folder_path).replace("\\", "\\\\").replace('"', '\\"')
            escaped_host = str(host).replace('"', '\\"')
            
            code = f"""
import sys
import requests
from pathlib import Path

project_folder = "{escaped_project_folder}"
host = "{escaped_host}"
port = {port}

txt_path = Path(project_folder) / "transcricao_video.txt"
en_txt_path = Path(project_folder) / "transcricao_video_en.txt"
text_content = txt_path.read_text(encoding="utf-8")

print("[INFO] Traduzindo...")
url = f"http://{{host}}:{{port}}/v1/chat/completions"
prompt = (
    "Voce e um tradutor profissional de videos. Traduza o seguinte texto transcrito de um video em portugues "
    "para o ingles, preservando o significado natural. Retorne APENAS a traducao direta sem comentarios.\\n\\n"
    f"Texto:\\n{{text_content}}"
)
payload = {{
    "model": "openai/gemma-4",
    "messages": [{{'role': 'user', 'content': prompt}}],
    "temperature": 0.3
}}
try:
    res = requests.post(url, json=payload, timeout=90)
    if res.status_code == 200:
        translation = res.json()["choices"][0]["message"]["content"]
        en_txt_path.write_text(translation, encoding="utf-8")
        print("\\n[SUCESSO] Tradução concluída!")
        print(translation)
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)
"""
            services.render_process = subprocess.Popen([python_bin, "-u", "-c", code], stdout=log_file, stderr=subprocess.STDOUT, creationflags=creationflags)
            return jsonify({"success": True, "msg": "Tradução iniciada!"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    else:
        return jsonify({"success": False, "error": "Ação desconhecida"}), 400

@video_actions.route("/api/video_copilot/analyze_clips", methods=["POST"])
def api_video_copilot_analyze_clips():
    config_file = services.ROOT_DIR / "scratch" / "video_editor_config.json"
    current_config = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                current_config = json.load(f)
        except: pass
            
    project_folder = current_config.get("project_folder")
    if not project_folder:
        return jsonify({"success": False, "error": "Projeto não selecionado"}), 400
        
    txt_path = Path(project_folder) / "transcricao_video.txt"
    if not txt_path.exists():
        return jsonify({"success": False, "error": "Transcrição não encontrada."}), 400
        
    config = services.load_config()
    host = config.get("host", "127.0.0.1")
    port = config.get("port", 1234)
    
    if not services.check_server_online(host, port):
        return jsonify({"success": False, "error": "Servidor de IA local está OFFLINE!"}), 400
        
    try:
        text_content = txt_path.read_text(encoding="utf-8")
        import requests
        url = f"http://{host}:{port}/v1/chat/completions"
        prompt = (
            "Você é um especialista em marketing digital e edição de vídeos.\n"
            "Analise a seguinte transcrição de vídeo e retorne um objeto JSON contendo:\n"
            "1. 'scripted_hooks': Lista de 3 hooks curtos de 3 segundos em texto.\n"
            "2. 'existing_hook': Descrição textual do melhor momento de impacto inicial.\n"
            "3. 'recommended_clips': Lista contendo até 3 sugestões de clips de Shorts (15 a 30s) com 'title', 'start', 'end', 'reason'.\n"
            "Retorne APENAS o JSON puro, sem marcações markdown ou blocos de código.\n\n"
            f"Transcrição:\n{text_content}"
        )
        payload = {
            "model": "openai/gemma-4",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        res = requests.post(url, json=payload, timeout=90)
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                lines = content.split("\n")
                if lines[0].startswith("```"): lines = lines[1:]
                if lines[-1].startswith("```"): lines = lines[:-1]
                content = "\n".join(lines).strip()
            try:
                analysis_data = json.loads(content)
                return jsonify({"success": True, "analysis": analysis_data})
            except Exception as parse_err:
                return jsonify({"success": False, "error": "Falha ao processar JSON retornado pela IA.", "raw": content}), 500
        else:
            return jsonify({"success": False, "error": f"Erro do servidor de IA: {res.status_code}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@video_actions.route("/api/video_copilot/cut_clip", methods=["POST"])
def api_video_copilot_cut_clip():
    data = request.json
    if not data or "start" not in data or "end" not in data or "format" not in data:
        return jsonify({"success": False, "error": "Parâmetros inválidos"}), 400
        
    start_time = float(data["start"])
    end_time = float(data["end"])
    fmt = data["format"]
    duration = end_time - start_time
    
    if duration <= 0:
        return jsonify({"success": False, "error": "Duração do clipe inválida"}), 400
        
    if services.render_process is not None and services.render_process.poll() is None:
        return jsonify({"success": False, "error": "Uma ação já está em andamento!"}), 400
        
    config_file = services.ROOT_DIR / "scratch" / "video_editor_config.json"
    current_config = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                current_config = json.load(f)
        except: pass
            
    video_path = current_config.get("video_path")
    project_folder = current_config.get("project_folder")
    
    if not video_path or not project_folder:
        return jsonify({"success": False, "error": "Selecione um vídeo primeiro!"}), 400
        
    project_folder_path = Path(project_folder)
    clips_dir = project_folder_path / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    output_clip = str((clips_dir / f"clip_{start_time:.1f}_{end_time:.1f}_{fmt}.mp4").resolve())
    
    try: services.RENDER_LOG.write_text("", encoding="utf-8")
    except: pass
        
    ffmpeg_bin = r"C:\IA_dublagem\env\Library\bin\ffmpeg.exe"
    if not os.path.exists(ffmpeg_bin):
        ffmpeg_bin = "ffmpeg"
        
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    services.RENDER_LOG.write_text(f"[INFO] Recortando clipe ({fmt})...\nEntrada: {video_path}\nSaída: {output_clip}\nTimings: {start_time:.2f}s -> {end_time:.2f}s\n\n", encoding="utf-8")
    log_file = open(services.RENDER_LOG, "a", encoding="utf-8")
    
    def run_cut_thread():
        v_filter = "crop=w=ih*9/16:h=ih,scale=1080:1920" if fmt == "vertical" else ""
        if v_filter:
            cmd_gpu = [ffmpeg_bin, "-y", "-hwaccel", "cuda", "-ss", f"{start_time:.3f}", "-t", f"{duration:.3f}", "-i", video_path, "-vf", v_filter, "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "24", "-c:a", "aac", "-b:a", "192k", output_clip]
        else:
            cmd_gpu = [ffmpeg_bin, "-y", "-hwaccel", "cuda", "-ss", f"{start_time:.3f}", "-t", f"{duration:.3f}", "-i", video_path, "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "24", "-c:a", "aac", "-b:a", "192k", output_clip]
            
        services.render_process = subprocess.Popen(cmd_gpu, stdout=log_file, stderr=subprocess.STDOUT, creationflags=creationflags)
        ret = services.render_process.wait()
        
        if ret != 0:
            with open(services.RENDER_LOG, "a", encoding="utf-8") as lf:
                lf.write("\n[AVISO] GPU NVENC falhou. Tentando via CPU...\n")
            if v_filter:
                cmd_cpu = [ffmpeg_bin, "-y", "-ss", f"{start_time:.3f}", "-t", f"{duration:.3f}", "-i", video_path, "-vf", v_filter, "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", "-b:a", "192k", output_clip]
            else:
                cmd_cpu = [ffmpeg_bin, "-y", "-ss", f"{start_time:.3f}", "-t", f"{duration:.3f}", "-i", video_path, "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", "-b:a", "192k", output_clip]
                
            services.render_process = subprocess.Popen(cmd_cpu, stdout=log_file, stderr=subprocess.STDOUT, creationflags=creationflags)
            ret_cpu = services.render_process.wait()
            with open(services.RENDER_LOG, "a", encoding="utf-8") as lf:
                if ret_cpu == 0: lf.write(f"\n[SUCESSO] Clipe exportado via CPU!\nSalvo em: {output_clip}\n")
                else: lf.write(f"\n[ERRO] Falha ao exportar clipe via CPU. Retorno: {ret_cpu}\n")
        else:
            with open(services.RENDER_LOG, "a", encoding="utf-8") as lf:
                lf.write(f"\n[SUCESSO] Clipe exportado via GPU!\nSalvo em: {output_clip}\n")
                
    threading.Thread(target=run_cut_thread, daemon=True).start()
    return jsonify({"success": True, "msg": "Corte de clipe iniciado!"})
