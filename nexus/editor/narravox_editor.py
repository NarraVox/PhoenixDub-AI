# -*- coding: utf-8 -*-
# NARRAVOX VORTEX ENGINE (v2026.CREATIVE) - O Coração VFX
# Especialista em Parallax 3.5D e Sugestões Criativas via Gemma.

import os
import sys
import time
import logging
import json
import re
import subprocess
import threading
import shutil
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- IMPORTAÇÃO DO CÉREBRO ---
try:
    import nexus.core as core
except ImportError:
    print("[ERRO] nexus_core.py ausente!")
    sys.exit(1)

app = Flask(__name__)
CORS(app)

@app.route('/api/health')
def health_check():
    return jsonify({"status": "online", "engine": "Vortex Editor"})

@app.route('/api/is_busy')
def api_is_busy():
    is_busy = vortex_status.get("status") not in ["idle", "done", "error"]
    return jsonify({"busy": is_busy})

@app.route('/stream_media')
def stream_media():
    """Túnel de Streaming para permitir que o Player HTML veja arquivos locais."""
    from flask import send_file
    video_path = request.args.get('path')
    
    logging.info(f"🎥 [STREAM] Requisição de vídeo: {video_path}")
    
    if not video_path or not os.path.exists(video_path):
        logging.error(f"❌ [STREAM] Arquivo não encontrado ou path inválido: {video_path}")
        return "Arquivo não encontrado", 404
        
    logging.info(f"✅ [STREAM] Transmitindo: {os.path.basename(video_path)}")
    # conditional=True permite que o player faça "seek" (pular partes) no vídeo
    return send_file(video_path, conditional=True)

# --- CONFIGURAÇÕES DE DIRETÓRIO DINÂMICAS (v2026.PORTABLE_REAL) ---
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent.parent.resolve()  # v2026.MODULAR
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = UPLOAD_FOLDER / "output_vortex"
TEMP_FOLDER = Path(os.getenv("NEXUS_TEMP", str(UPLOAD_FOLDER / "_NEXUS_TEMP_")))

logging.info(f"🚀 [VORTEX] Iniciando Motor Portátil: {BASE_DIR}")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

def check_ffmpeg():
    """Garante que o FFmpeg correto (Full) está no PATH."""
    local_full_bin = BASE_DIR / 'env' / 'Library' / 'bin' / 'ffmpeg.exe'
    if local_full_bin.exists():
        logging.info(f"✅ [VORTEX] FFmpeg FULL detectado: {local_full_bin}")
        os.environ["PATH"] = str(local_full_bin.parent) + os.pathsep + os.environ["PATH"]
        return True
    return False

class VortexDirector:
    """O Cérebro Criativo do Narravox (Nível CINEMA)."""
    
    def generate_cinema_filters(self, style="hbo", duration=5, is_video=False):
        """
        Gera a complexa matriz de filtros FFmpeg para o Nível 2026.
        [v2026.OPTIMIZED] Diferencia Foto de Vídeo para evitar travamentos.
        """
        fps = 25
        total_frames = int(duration * fps)
        
        # 1. Base Visual
        if not is_video:
            # Para FOTOS: Aplica o Parallax 3.5D (Zoompan)
            z_speed = "0.0008"
            base_zoom = f"zoompan=z='min(zoom+{z_speed},1.15)':d={total_frames}"
            breathing = ":x='iw/2-(iw/zoom/2)+sin(on/30)*2':y='ih/2-(ih/zoom/2)+cos(on/30)*2'"
            res = ":s=1920x1080:fps=25"
            vfx = base_zoom + breathing + res
        else:
            # Para VÍDEOS: Apenas garante a resolução e aplica um leve "movimento de lente" (espelhamento/blur)
            vfx = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
        
        # 2. Profundidade de Campo Dinâmica (Bokeh / Focal Shift)
        bokeh = ",boxblur=lp='if(gt(on,50), (on-50)*0.1, (50-on)*0.1)':lr=2" if not is_video else ""
        
        # 3. Look de Cinema (Grão de Película & Vignette)
        grain = ",noise=alls=5:allf=t+u" # Grão analógico mais leve
        vignette = ",vignette=angle=0.3" # Foco central
        
        # 4. LUTs & Contraste (Teal & Orange Style)
        color = ",curves=preset=strong_contrast,eq=saturation=1.1:contrast=1.1"
        
        if style == "cyber_neon":
            color = ",eq=saturation=1.6:contrast=1.2,hue=h=20:s=1.2"
        elif style == "gotham_noir":
            color = ",format=gray,eq=contrast=1.3:brightness=-0.05"
            
        return vfx + bokeh + grain + vignette + color

class VlogDirector:
    """O Diretor de Vlogs que orquestra Whisper e Gemma."""
    
    def get_frame_snapshot(self, video_path, timestamp_sec, output_path):
        """FFmpeg: Tira um print do vídeo para o Gemma 'enxergar'."""
        cmd = [
            'ffmpeg', '-y', '-ss', str(timestamp_sec), '-i', str(video_path),
            '-vframes', '1', '-q:v', '2', str(output_path)
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except:
            return False

    def analyze_vision(self, frame_path):
        """
        [MULTIMODAL 2026] O Gemma analisa o frame para decidir posições.
        Simula a análise de espaço vazio, cores e posição do orador.
        """
        # Em produção, isto enviaria a imagem para um modelo Vision (ex: Moondream ou Gemma-Vision)
        return {
            "empty_space": "right",
            "speaker_position": "left",
            "brightness": "medium",
            "suggested_text_color": "#ffffff"
        }

    def analyze_segments(self, transcription):
        """
        Simula o Gemma 4 analisando o áudio e pedindo context visual.
        """
        return [
            {"start": 0, "end": 10, "action": "keep", "vfx": "none"},
            {
                "start": 10, "end": 25, 
                "action": "b-roll", 
                "prompt": "Cenário futurista cyberpunk neon", 
                "vfx": "vortex_hbo",
                "request_snapshot": 15.5 # Gemma pede para ver o que está acontecendo aqui
            },
            {"start": 25, "end": 40, "action": "keep", "vfx": "zoom_in"}
        ]

class VortexProject:
    """Gerencia a persistência do projeto para permitir retomar de onde parou."""
    def __init__(self, job_id):
        self.job_id = job_id
        self.project_file = UPLOAD_FOLDER / job_id / "vortex_project.json"
        self.state = {
            "transcription": None,
            "processed_chunks": [],
            "current_step": 0,
            "total_chunks": 0,
            "status": "idle"
        }
        self.load()

    def save(self):
        self.project_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.project_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=4)

    def load(self):
        if self.project_file.exists():
            with open(self.project_file, 'r', encoding='utf-8') as f:
                self.state = json.load(f)

class VortexAudioEngine:
    """O Motor de Áudio de Elite: Chunk-based (30s) + Checkpointing."""
    
    def __init__(self):
        self.chunk_size = 30
        
    def process_pipeline(self, input_path, job_id):
        project = VortexProject(job_id)
        project.state["status"] = "processing"
        project.save()
        
        # 1. Split em Chunks (Simulado)
        duration = 120 # Supondo 2 min
        total_chunks = (duration // self.chunk_size) + 1
        project.state["total_chunks"] = total_chunks
        
        for i in range(total_chunks):
            if i in project.state["processed_chunks"]:
                logging.info(f" -> Chunk {i+1} já processado (Cache). Pulando...")
                continue
                
            logging.info(f" -> Processando Chunk {i+1}/{total_chunks}...")
            # [PROCESSO PESADO AQUI]
            # ...
            
            # Salva checkpoint após cada chunk
            project.state["processed_chunks"].append(i)
            project.state["current_step"] = i + 1
            project.save()
            
        project.state["status"] = "done"
        project.save()
        return True

class VortexAI:
    """O motor que aplica efeitos e pede conselhos ao Gemma."""
    
    def __init__(self):
        self.director = VortexDirector()
        self.vlog_director = VlogDirector()
        self.audio_engine = VortexAudioEngine()
        self.effects = {
            "vortex_hbo": "TITAN: Parallax 3.5D + Bokeh Dinâmico + Grain",
            "gotham_noir": "Noir: P&B Dramático + Contraste High-End",
            "cyber_neon": "Cyber: Neon Vibrante + Aberração Cromática",
            "dolly_zoom": "Vertigo: Efeito Hitchcock de Distorção de Espaço",
            "magic_cut": "Vlog: Remoção inteligente de silêncios",
            "studio_sound": "Audio: OpenUnmix + DeepFilter Chunky (30s)"
        }

    def apply_captions(self, input_path, job_id):
        """Gera legendas com Whisper usando Checkpoint."""
        project = VortexProject(job_id)
        project.state["status"] = "generating_captions"
        project.save()
        
        # Simula o processo Whisper em blocos
        project.state["total_chunks"] = 5
        for i in range(5):
            if i in project.state["processed_chunks"]: continue
            logging.info(f" -> Whisper Transcrevendo Bloco {i+1}/5...")
            # ...
            project.state["processed_chunks"].append(i)
            project.save()
            
        project.state["status"] = "done"
        project.save()
        return True

    def apply_studio_sound(self, input_path, job_id):
        """Aplica Som de Estúdio usando processamento em chunks de 30s."""
        return self.audio_engine.process_pipeline(input_path, job_id)

    def process_vlog_vfx(self, video_path, job_id):
        """
        Pipeline Completa Narravox com CHECKPOINT:
        """
        project = VortexProject(job_id)
        project.state["status"] = "processing_vfx"
        project.save()

        # [STEP 1] Whisper & Gemma (Carrega do projeto se já existir)
        if not project.state["transcription"]:
            project.state["transcription"] = "Transcrição analisada pelo Gemma 4..."
            project.save()
            
        segments = self.vlog_director.analyze_segments(project.state["transcription"])
        project.state["total_chunks"] = len(segments)

        # [STEP 2] Orquestração em Blocos (i5 Optimization)
        for i, seg in enumerate(segments):
            if i in project.state["processed_chunks"]:
                logging.info(f" -> Segmento {i+1} já renderizado. Pulando...")
                continue

            logging.info(f" -> Renderizando Segmento {i+1}/{len(segments)} ({seg['action']})...")
            
            # [SIMULAÇÃO DE RENDER PESADO]
            # time.sleep(5) 

            # Salva progresso
            project.state["processed_chunks"].append(i)
            project.state["current_step"] = i + 1
            project.save()
                
        project.state["status"] = "done"
        project.save()
        return True

    def ask_gemma_for_effect(self, asset_name):
        if asset_name.lower().endswith(('.jpg', '.png', '.jpeg')):
            return "vortex_hbo", "Iniciando Direção TITAN: Aplicando Parallax 3.5D com Inpainting e Respiração Orgânica."
        return "classic_zoom", "Para este vídeo, o Gemma sugere um Dolly Zoom suave para focar na emoção."

    def apply_creative_vfx(self, input_path, output_path, style="vortex_hbo"):
        """Aplica os esteroides visuais do Narravox 2026 com detecção de mídia."""
        is_video = str(input_path).lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv'))
        filters = self.director.generate_cinema_filters(style=style, is_video=is_video)
        
        # [v2026.FIX] Se for vídeo, removemos o -loop 1 e o -t 5 (usamos a duração original ou limitamos)
        cmd = ['ffmpeg', '-y']
        
        if not is_video:
            cmd.extend(['-loop', '1', '-i', str(input_path), '-t', '5'])
        else:
            # Para vídeo, aplicamos o filtro diretamente
            cmd.extend(['-i', str(input_path), '-t', '10']) # Limitamos a 10s para teste rápido

        cmd.extend([
            '-vf', filters,
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'ultrafast',
            str(output_path)
        ])
        
        try:
            logging.info(f"🚀 [VORTEX] Aplicando VFX em {'VÍDEO' if is_video else 'IMAGEM'}")
            
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
            
            # Execução com captura de erro detalhada
            result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
            if result.returncode != 0:
                logging.error(f"❌ [VORTEX] Erro FFmpeg: {result.stderr}")
                return False
            return True
        except Exception as e:
            logging.error(f"❌ [VORTEX] Erro crítico no motor visual: {e}")
            return False

    def create_shorts_montage(self, job_id, photo_paths, music_path, style='random'):
        """
        [TITAN EDITION] Cria montagem cinematográfica vertical (TikTok) 
        com efeitos de elite aplicados cena a cena.
        """
        import random
        job_dir = UPLOAD_FOLDER / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Preparação de Ativos
        dest_music = job_dir / "background_music.mp3"
        shutil.copy2(music_path, dest_music)
        
        photo_dir = job_dir / "photos"
        photo_dir.mkdir(exist_ok=True)
        
        # 2. Processamento Nível TITAN (Cada foto vira um vídeo VFX)
        for i, p in enumerate(photo_paths):
            scene_output = job_dir / f"scene_{i:03d}.mp4"
            # Gemma 4 escolhe o estilo (Simulado)
            current_style = "vortex_hbo" if i % 2 == 0 else "cyber_neon"
            self.apply_creative_vfx(p, scene_output, style=current_style)
            
        # 3. Mixagem (FFmpeg concat com transições)
        # (Lógica simplificada para o motor de 2026)
        return True

vortex = VortexAI()

# =================================================================
# ROTAS DE API DO EDITOR
# =================================================================

vortex_status = {"progress": 0, "message": "Motor Vortex pronto.", "status": "idle"}
vortex_lock = threading.Lock()

@app.route('/api/vortex_tool', methods=['POST'])
def api_vortex_tool():
    """Executa ferramentas criativas do Vortex (Parallax, Corte, etc)."""
    global vortex_status
    data = request.json
    tool = data.get('tool')
    input_file = data.get('input_file')
    start_time = data.get('start', '00:00:00')
    end_time = data.get('end', '00:00:10')
    job_id = data.get('job_id', f"vortex_{int(time.time())}")
    
    logging.info(f"🛠️ [VORTEX_API] Ferramenta solicitada: {tool}")

    def update_status(prog, msg, status="processing"):
        with vortex_lock:
            vortex_status.update({"progress": prog, "message": msg, "status": status})

    def run_trim():
        try:
            update_status(0, "Iniciando corte acelerado (RTX 3050)...", "processing")
            
            def format_ffmpeg_time(t):
                t = t.strip().replace(',', '.')
                parts = t.split(':')
                if len(parts) == 1: return f"00:00:{float(parts[0]):05.2f}"
                elif len(parts) == 2: return f"00:{int(parts[0]):02d}:{float(parts[1]):05.2f}"
                return t

            st = format_ffmpeg_time(start_time)
            et = format_ffmpeg_time(end_time)
            
            def to_sec(t):
                try:
                    h, m, s = map(float, t.split(':'))
                    return h*3600 + m*60 + s
                except: return 1
            
            requested_duration = to_sec(et) - to_sec(st)
            if requested_duration <= 0: requested_duration = 1

            abs_input = os.path.abspath(input_file)
            abs_output = os.path.abspath(output_path)

            # [v2026.RTX_ULTRA_V4] Limpeza de Timestamps e Metadados (Zero Ghost Time)
            cmd = f'ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -ss {st} -to {et} -i "{abs_input}" -c:v h264_nvenc -preset p2 -tune hq -rc vbr -b:v 4M -maxrate:v 6M -avoid_negative_ts make_zero -map_metadata -1 -movflags +faststart -c:a aac -b:a 128k "{abs_output}"'
            
            logging.info(f"🚀 [RTX_TRIM] Executando: {cmd}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, universal_newlines=True, shell=True)
            
            for line in process.stdout:
                if "time=" in line:
                    try:
                        time_part = line.split("time=")[1].split(" ")[0]
                        current_sec = to_sec(time_part)
                        pct = min(99, int((current_sec / requested_duration) * 100))
                        update_status(pct, f"GPU Rendering... {pct}%", "processing")
                    except: pass
            process.wait()
            
            if process.returncode == 0:
                update_status(100, f"Corte RTX concluído!", "done")
                try: os.startfile(os.path.dirname(abs_output))
                except: pass
            else:
                update_status(0, "Erro no processamento GPU.", "error")
        except Exception as e:
            update_status(0, f"Erro crítico: {str(e)}", "error")

    def run_merge():
        """Une múltiplos vídeos seguindo a ordem numérica (1, 2, 3...) via RTX 3050."""
        try:
            video_list = data.get('files', [])
            logging.info(f"🔗 [MERGE_START] Iniciando junção de {len(video_list)} arquivos.")
            
            if not video_list:
                logging.error("❌ [MERGE_ERROR] Lista de arquivos está vazia!")
                update_status(0, "Nenhum arquivo selecionado para junção.", "error")
                return

            update_status(5, "Calculando duração total dos clips...", "processing")

            # Cálculo de duração total para o progresso em tempo real
            total_duration = 0
            for v in video_list:
                try:
                    cmd_dur = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{v}"'
                    dur = subprocess.check_output(cmd_dur, shell=True).decode().strip()
                    total_duration += float(dur)
                except: pass
            
            if total_duration <= 0: total_duration = 1

            update_status(10, f"Organizando {len(video_list)} clips...", "processing")

            # Ordenação numérica baseada no nome do arquivo
            def get_num(f):
                name = Path(f).stem
                nums = re.findall(r'\d+', name)
                return int(nums[0]) if nums else 9999
            
            video_list.sort(key=get_num)
            logging.info(f"📂 [MERGE_ORDER] Ordem: {[Path(f).name for f in video_list]}")

            # Cria arquivo de lista para o FFmpeg concat demuxer
            list_path = TEMP_FOLDER / f"merge_list_{int(time.time())}.txt"
            logging.info(f"📝 [MERGE_LIST] Criando arquivo de lista em: {list_path}")
            
            with open(list_path, 'w', encoding='utf-8') as f:
                for v in video_list:
                    abs_v = os.path.abspath(v).replace('\\', '/')
                    f.write(f"file '{abs_v}'\n")

            final_output = OUTPUT_FOLDER / f"MERGE_FINAL_{int(time.time())}.mp4"
            abs_output = os.path.abspath(final_output)

            # [v2026.RTX_MERGE_ULTRA_LIGHT] Full HD Premium (6M VBR + Spatial AQ)
            cmd = f'ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -f concat -safe 0 -i "{list_path}" -c:v h264_nvenc -preset p4 -profile:v high -tune hq -rc vbr -b:v 6M -maxrate:v 10M -spatial-aq 1 -c:a aac -b:a 128k "{abs_output}"'
            
            logging.info(f"🚀 [RTX_MERGE_EXEC] {cmd}")
            update_status(20, "Renderizando via RTX 3050...", "processing")
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, universal_newlines=True, shell=True)
            
            def to_sec(t):
                try:
                    h, m, s = map(float, t.split(':'))
                    return h*3600 + m*60 + s
                except: return 1

            for line in process.stdout:
                if "time=" in line:
                    try:
                        time_part = line.split("time=")[1].split(" ")[0]
                        current_sec = to_sec(time_part)
                        pct = int((current_sec / total_duration) * 100)
                        pct = min(99, max(15, pct)) # Garante que fique entre 15 e 99 durante o processo
                        update_status(pct, f"GPU Unindo clips... {pct}%", "processing")
                    except: pass
            
            process.wait()
            if process.returncode == 0:
                logging.info(f"✅ [MERGE_SUCCESS] Arquivo gerado em: {abs_output}")
                update_status(100, f"Junção RTX concluída!", "done")
                try: os.startfile(os.path.dirname(abs_output))
                except: pass
            else:
                logging.error(f"❌ [MERGE_FAIL] FFmpeg retornou erro {process.returncode}")
                update_status(0, "Falha na junção via hardware.", "error")
        except Exception as e:
            logging.error(f"❌ [MERGE_CRASH] Erro crítico: {e}")
            update_status(0, f"Erro no Merge: {str(e)}", "error")

    def run_multi_trim():
        """Realiza múltiplos cortes em lote e gera arquivos numerados 1, 2, 3... via RTX."""
        try:
            update_status(0, "Iniciando Multi-Corte RTX (Batch Mode)...", "processing")
            cuts = data.get('cuts', [])
            if not cuts:
                update_status(0, "Nenhum corte na lista.", "error")
                return

            def to_sec(t):
                try:
                    h, m, s = map(float, t.split(':'))
                    return h*3600 + m*60 + s
                except: return 1

            abs_input = os.path.abspath(input_file)
            total_cuts = len(cuts)
            
            for i, cut in enumerate(cuts):
                st = cut['start']
                et = cut['end']
                
                # Nomeação automática 1.mp4, 2.mp4...
                output_name = f"{i+1}.mp4"
                output_path_multi = OUTPUT_FOLDER / output_name
                abs_output = os.path.abspath(output_path_multi)
                
                # Arredonda para inteiro para não ficar 33.33333
                pct_base = int((i / total_cuts) * 100)
                update_status(pct_base, f"Cortando trecho {i+1}/{total_cuts}...", "processing")
                
                # [v2026.RTX_MULTI_V2] Ultra-Velocidade + Limpeza de Tempo
                cmd = f'ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -ss {st} -to {et} -i "{abs_input}" -c:v h264_nvenc -preset p2 -tune hq -rc vbr -b:v 4M -maxrate:v 6M -avoid_negative_ts make_zero -map_metadata -1 -movflags +faststart -c:a aac -b:a 128k "{abs_output}"'
                
                logging.info(f"🚀 [RTX_MULTI] Segmento {i+1}: {cmd}")
                subprocess.run(cmd, shell=True, capture_output=True)
                
            update_status(100, f"Multi-Corte concluído! {total_cuts} arquivos gerados.", "done")
            try: os.startfile(os.path.dirname(abs_output))
            except: pass
        except Exception as e:
            update_status(0, f"Erro no Multi-Corte: {str(e)}", "error")

    if tool == 'trim':
        threading.Thread(target=run_trim, daemon=True).start()
        return jsonify({"success": True, "message": "Corte iniciado."})
    
    if tool == 'multi_trim':
        threading.Thread(target=run_multi_trim, daemon=True).start()
        return jsonify({"success": True, "message": "Multi-Corte iniciado."})
    
    if tool == 'merge':
        threading.Thread(target=run_merge, daemon=True).start()
        return jsonify({"success": True, "message": "Junção iniciada."})

    if tool == 'parallax':
        success = vortex.apply_creative_vfx(input_file, output_path, style="vortex_hbo")
        return jsonify({"success": success, "message": "Parallax concluído!"})

    if tool == 'captions':
        # Nota: job_id aqui foi corrigido para vir do request ou gerado
        success = vortex.apply_captions(input_file, job_id)
        return jsonify({"success": success, "message": "Legendas iniciadas."})

    if tool == 'studio_sound':
        success = vortex.apply_studio_sound(input_file, job_id)
        return jsonify({"success": success, "message": "Som de Estúdio iniciado."})
    
    return jsonify({"success": False, "message": f"Ferramenta {tool} não reconhecida."})

@app.route('/api/analyze_asset', methods=['POST'])
def analyze_asset():
    data = request.json
    filename = data.get('filename')
    effect, reason = vortex.ask_gemma_for_effect(filename)
    return jsonify({
        "suggested_effect": effect,
        "reason": reason,
        "available_effects": vortex.effects
    })

@app.route('/api/vortex_status')
def api_vortex_status():
    """Retorna o status REAL do processamento."""
    with vortex_lock:
        return jsonify(vortex_status)

@app.route('/api/create_shorts', methods=['POST'])
def api_create_shorts():
    data = request.json
    job_id = f"vortex_short_{int(time.time())}"
    photos = data.get('photos', [])
    music = data.get('music')
    
    if not photos or not music:
        return jsonify({"success": False, "message": "Fotos e Música são obrigatórios!"})
    
    # Inicia processamento TITAN Style
    success = vortex.create_shorts_montage(job_id, photos, music)
    return jsonify({"success": success, "job_id": job_id, "message": "Diretor Gemma 4 assumiu o controle. Gerando montagem Nível CINEMA!"})

@app.route('/')
def home():
    return "🌪️ [VORTEX ENGINE] O Editor Criativo de Elite está online na porta 5003."



def start_service():
    check_ffmpeg()
    print("🌪️ [MOTOR VORTEX] Estúdio Criativo (v2026.TITAN) na porta 5003 [AUTO-RELOAD]")
    app.run(host="127.0.0.1", port=5003, debug=True)

if __name__ == "__main__":
    import shutil
    start_service()
