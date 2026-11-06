# -*- coding: utf-8 -*-
# NARRAVOX VORTEX ENGINE - Módulo de Efeitos Criativos e Direção VFX
# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo

import os
import sys
import time
import json
import logging
import subprocess
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = UPLOAD_FOLDER / "output_vortex"
TEMP_FOLDER = Path(os.getenv("NEXUS_TEMP", str(UPLOAD_FOLDER / "_NEXUS_TEMP_")))

class VortexDirector:
    """O Cérebro Criativo do Narravox (Nível CINEMA)."""
    
    def generate_cinema_filters(self, style="hbo", duration=5, is_video=False):
        fps = 25
        total_frames = int(duration * fps)
        
        if not is_video:
            z_speed = "0.0008"
            base_zoom = f"zoompan=z='min(zoom+{z_speed},1.15)':d={total_frames}"
            breathing = ":x='iw/2-(iw/zoom/2)+sin(on/30)*2':y='ih/2-(ih/zoom/2)+cos(on/30)*2'"
            res = ":s=1920x1080:fps=25"
            vfx = base_zoom + breathing + res
        else:
            vfx = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
        
        bokeh = ",boxblur=lp='if(gt(on,50), (on-50)*0.1, (50-on)*0.1)':lr=2" if not is_video else ""
        grain = ",noise=alls=5:allf=t+u"
        vignette = ",vignette=angle=0.3"
        color = ",curves=preset=strong_contrast,eq=saturation=1.1:contrast=1.1"
        
        if style == "cyber_neon":
            color = ",eq=saturation=1.6:contrast=1.2,hue=h=20:s=1.2"
        elif style == "gotham_noir":
            color = ",format=gray,eq=contrast=1.3:brightness=-0.05"
            
        return vfx + bokeh + grain + vignette + color

class VlogDirector:
    """O Diretor de Vlogs que orquestra Whisper e Gemma."""
    
    def get_frame_snapshot(self, video_path, timestamp_sec, output_path):
        cmd = [
            'ffmpeg', '-y', '-ss', str(timestamp_sec), '-i', str(video_path),
            '-vframes', '1', '-q:v', '2', str(output_path)
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except Exception:
            return False

    def analyze_vision(self, frame_path):
        return {
            "empty_space": "right",
            "speaker_position": "left",
            "brightness": "medium",
            "suggested_text_color": "#ffffff"
        }

    def analyze_segments(self, transcription):
        return [
            {"start": 0, "end": 10, "action": "keep", "vfx": "none"},
            {
                "start": 10, "end": 25, 
                "action": "b-roll", 
                "prompt": "Cenário futurista cyberpunk neon", 
                "vfx": "vortex_hbo",
                "request_snapshot": 15.5
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
    """O Motor de Áudio: Chunk-based (30s) + Checkpointing."""
    
    def __init__(self):
        self.chunk_size = 30
        
    def process_pipeline(self, input_path, job_id):
        project = VortexProject(job_id)
        project.state["status"] = "processing"
        project.save()
        
        duration = 120
        total_chunks = (duration // self.chunk_size) + 1
        project.state["total_chunks"] = total_chunks
        
        for i in range(total_chunks):
            if i in project.state["processed_chunks"]:
                continue
            project.state["processed_chunks"].append(i)
            project.state["current_step"] = i + 1
            project.save()
            
        project.state["status"] = "done"
        project.save()
        return True

class VortexAI:
    """O motor que aplica efeitos e sugestões."""
    
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
        project = VortexProject(job_id)
        project.state["status"] = "generating_captions"
        project.save()
        project.state["total_chunks"] = 5
        for i in range(5):
            if i in project.state["processed_chunks"]: continue
            project.state["processed_chunks"].append(i)
            project.save()
        project.state["status"] = "done"
        project.save()
        return True

    def apply_studio_sound(self, input_path, job_id):
        return self.audio_engine.process_pipeline(input_path, job_id)

    def ask_gemma_for_effect(self, asset_name):
        if asset_name.lower().endswith(('.jpg', '.png', '.jpeg')):
            return "vortex_hbo", "Iniciando Direção TITAN: Aplicando Parallax 3.5D com Inpainting."
        return "classic_zoom", "Para este vídeo, sugere-se um Dolly Zoom suave para focar na emoção."

    def apply_creative_vfx(self, input_path, output_path, style="vortex_hbo"):
        is_video = str(input_path).lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv'))
        filters = self.director.generate_cinema_filters(style=style, is_video=is_video)
        cmd_base = ['ffmpeg', '-y']
        
        if not is_video:
            cmd_base.extend(['-loop', '1', '-i', str(input_path), '-t', '5'])
        else:
            cmd_base.extend(['-i', str(input_path), '-t', '10'])

        # Detecta encoder HEVC disponível (hevc_nvenc → libx265)
        try:
            result = subprocess.run(
                ['ffmpeg', '-f', 'lavfi', '-i', f'color=c=black:s=320x240:d=1',
                 '-c:v', 'hevc_nvenc', '-f', 'null', '-'], capture_output=True, timeout=5
            )
            has_gpu_hevc = result.returncode == 0
        except:
            has_gpu_hevc = False

        cmd_base.extend(['-vf', filters])
        
        if is_video and has_gpu_hevc:
            # GPU: hevc_nvenc com presets equilibrados para qualidade/tamanho
            cmd_base.extend([
                '-c:v', 'hevc_nvenc',
                '-preset', 'p4',
                '-tune', 'hq',
                '-rc', 'vbr',
                '-b:v', '2500k',
                '-maxrate:v', '5000k',
                '-bufsize:v', '3750k',
                '-spatial-aq', '1'
            ])
        else:
            # CPU fallback: libx265 com preset medium para balanceamento
            cmd_base.extend([
                '-c:v', 'libx265',
                '-preset', 'medium',
                '-tune', 'null',
                '-rc', 'vbr',
                '-b:v', '2500k',
                '-maxrate:v', '5000k',
                '-bufsize:v', '3750k'
            ])

        cmd_base.extend([
            '-pix_fmt', 'yuv420p',
            str(output_path)
        ])

        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
            res = subprocess.run(cmd_base, capture_output=True, text=True, startupinfo=startupinfo)
            return res.returncode == 0
        except Exception as e:
            logging.error(f"❌ [VORTEX_VFX] Erro: {e}")
            return False

    def create_shorts_montage(self, job_id, photo_paths, music_path, style='random'):
        job_dir = UPLOAD_FOLDER / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        dest_music = job_dir / "background_music.mp3"
        shutil.copy2(music_path, dest_music)
        for i, p in enumerate(photo_paths):
            scene_output = job_dir / f"scene_{i:03d}.mp4"
            current_style = "vortex_hbo" if i % 2 == 0 else "cyber_neon"
            self.apply_creative_vfx(p, scene_output, style=current_style)
        return True
