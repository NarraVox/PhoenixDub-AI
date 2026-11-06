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
# See the License for the specific language governing permissions and the limitations of the License.

import os
import sys
import subprocess
import logging
import re
import hashlib
from pydub import AudioSegment, effects

def speedup_audio(audio_segment, speed_factor, max_speed_factor=1.20):
    """Acelera o áudio sem alterar o pitch usando o filtro profissional atempo do FFmpeg (sem cortes)."""
    speed_factor = min(float(speed_factor), float(max_speed_factor))
    if speed_factor <= 1.0: return audio_segment
    try:
        temp_dir = "C:/IA_dublagem/uploads/_NEXUS_TEMP_"
        os.makedirs(temp_dir, exist_ok=True)
        import tempfile
        fd_in, path_in = tempfile.mkstemp(suffix=".wav", dir=temp_dir)
        fd_out, path_out = tempfile.mkstemp(suffix=".wav", dir=temp_dir)
        os.close(fd_in)
        os.close(fd_out)
        
        audio_segment.export(path_in, format="wav")
        cmd = [
            "ffmpeg", "-y", "-i", path_in,
            "-filter:a", f"atempo={speed_factor}",
            "-vn", path_out
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        if os.path.exists(path_out) and os.path.getsize(path_out) > 0:
            speeded_audio = AudioSegment.from_wav(path_out)
            try:
                os.remove(path_in)
                os.remove(path_out)
            except: pass
            return speeded_audio
    except Exception as e:
        logging.warning(f"⚠️ Falha ao acelerar áudio com FFmpeg: {e}. Usando fallback Pydub...")
        
    try:
        return effects.speedup(audio_segment, playback_speed=speed_factor, chunk_size=120, crossfade=20)
    except Exception as err:
        logging.error(f"❌ Falha crítica no fallback de aceleração: {err}")
        return audio_segment

def is_reaction_or_noise(seg):
    """Identifica reações, ruído e respostas meta que não devem ser dubladas."""
    texto_bruto = str(seg.get('manual_edit_text') or seg.get('sanitized_text') or seg.get('translated_text') or seg.get('text_pt') or seg.get('original_text', seg.get('text', '')))
    if any(ord(char) > 0x3000 for char in texto_bruto):
        return True
    if any('\u10a0' <= char <= '\u10ff' for char in texto_bruto):
        return True
    if re.search(r'([^\s.,!?_#*\-~])\1{3,}', texto_bruto):
        return True

    texto_limpo = texto_bruto.lower()
    meta_patterns = [
        "texto fornecido", "não é em", "som de", "grito", "gemido", "traduzido", "traduzida",
        "tradução", "legenda", "o texto", "cannot translate", "not in english", "análise:", "analise:",
        "não pode ser", "não é possível", "erro de digitação", "de digitação", "não é uma frase",
        "mistura complexa", "caracteres japoneses", "caracteres asiáticos", "reconhecível", "de origem"
    ]
    for pattern in meta_patterns:
        if texto_limpo == pattern or re.search(r'[\(\[\{]' + re.escape(pattern) + r'[\)\]\}]', texto_limpo):
            return True
        if pattern in {"texto fornecido", "não é em", "cannot translate", "not in english", "análise:", "analise:", "mistura complexa", "não pode ser", "não é possível"} and pattern in texto_limpo:
            return True

    for word in texto_limpo.split():
        letters = re.sub(r'[^a-zA-Z]', '', word)
        if len(letters) >= 3 and (re.search(r'([a-zA-Z])\1{2,}', letters) or len(set(letters)) == 1):
            return True

    reaction_words = {
        "yeah", "yes", "ah", "oh", "uh", "hmm", "hm", "wow", "haha", "ha ha", "huh", "hã", "é", "ok", "ops", "oops", "ah!", "oh!", "yeah!",
        "mmm", "mmm.", "mmm...", "mm-hmm", "mm-mm", "uhu", "uh-huh", "uh-oh", "shh", "ts", "tsc"
    }
    words = re.sub(r'[^a-zA-Z0-9 ]', '', texto_limpo).strip().split()
    if words and all(word in reaction_words for word in words):
        return True
    if seg.get('emotion') == 'CANTORIA':
        return True

    original = str(seg.get('original_text', seg.get('text', ''))).lower()
    music_markers = ['♪', '♫', '[music]', '(music)', '[singing]', '(singing)', '[canto]', '(canto)', '[cantando]', '[música]', '[musica]']
    return any(marker in original or marker in texto_limpo for marker in music_markers)

def detect_encoder_priority():
    """Detecta encoders NVENC HEVC primeiro, depois outros encoders disponíveis."""
    priority_encoders = ['hevc_nvenc', 'h264_nvenc', 'h264_qsv', 'libx265', 'libx264']

    for encoder in priority_encoders:
        try:
            # Testa se o encoder está disponível
            if encoder.startswith('hevc'):
                duration = 0.5  # HEVC precisa de duração mínima para inicializar NVENC
                cmd = ['ffmpeg', '-f', 'lavfi', '-i', f'color=c=black:s=320x240:d={duration}',
                       '-c:v', encoder, '-an', '-f', 'null', '-']
            else:
                duration = 1.0
                cmd = ['ffmpeg', '-f', 'lavfi', '-i', f'color=c=black:s=64x64:d={duration}',
                       '-frames:v', '1', '-c:v', encoder, '-an', '-f', 'null', '-']

            result = subprocess.run(cmd, capture_output=True, timeout=3)
            if result.returncode == 0:
                return encoder
        except Exception:
            continue

    # Fallback para libx265 (CPU) se FFmpeg tiver suporte
    try:
        cmd_libx265 = ['ffmpeg', '-f', 'lavfi', '-i', 'color=c=black:s=320x240:d=1',
                       '-c:v', 'libx265', '-an', '-f', 'null', '-']
        subprocess.run(cmd_libx265, capture_output=True, timeout=3)
        logging.info("🚀 [CPU] libx265 disponível para fallback")
        return 'libx265'
    except:
        pass

    # Fallback final
    logging.warning("⚠️ Nenhum encoder de vídeo detectado. Usando libx264 (CPU).")
    return 'libx264'

def get_best_encoder():
    """Detecta NVIDIA NVENC (RTX) ou Intel QuickSync (i5) para aceleração master."""
    try:
        # Prioridade 1: HEVC NVENC (H.265) - melhor compressão, requer GPU NVIDIA
        cmd_hevc = ['ffmpeg', '-f', 'lavfi', '-i', f'color=c=black:s=320x240:d=0.5',
                    '-c:v', 'hevc_nvenc', '-an', '-f', 'null', '-']
        result = subprocess.run(cmd_hevc, capture_output=True, timeout=3)

        if result.returncode == 0:
            logging.info("🚀 [HARDWARE] NVIDIA NVENC Ativo! Renderização via RTX 3050 em HEVC.")
            return 'hevc_nvenc'

        # Prioridade 2: H.264 NVENC (se HEVC não estiver disponível)
        cmd_h264 = ['ffmpeg', '-f', 'lavfi', '-i', f'color=c=black:s=64x64:d=1',
                    '-frames:v', '1', '-c:v', 'h264_nvenc', '-an', '-f', 'null', '-']
        result = subprocess.run(cmd_h264, capture_output=True, timeout=3)

        if result.returncode == 0:
            logging.info("🚀 [HARDWARE] NVIDIA NVENC Ativo! Renderização via RTX 3050.")
            return 'h264_nvenc'
    except Exception as e:
        logging.warning(f"⚠️ Falha ao detectar encoder NVIDIA: {e}")

    # Prioridade 3: Intel QuickSync (iGPU)
    try:
        cmd_qsv = ['ffmpeg', '-f', 'lavfi', '-i', f'color=c=black:s=64x64:d=1',
                   '-frames:v', '1', '-c:v', 'h264_qsv', '-an', '-f', 'null', '-']
        result = subprocess.run(cmd_qsv, capture_output=True, timeout=3)
        
        if result.returncode == 0:
            logging.info("🚀 [HARDWARE] Intel QSV Ativo!")
            return 'h264_qsv'
    except Exception:
        pass

    # Fallback para CPU (libx265 ou libx264)
    try:
        cmd_cpu = ['ffmpeg', '-f', 'lavfi', '-i', f'color=c=black:s=320x240:d=1',
                   '-c:v', 'libx265', '-an', '-f', 'null', '-']
        result = subprocess.run(cmd_cpu, capture_output=True, timeout=3)

        if result.returncode == 0:
            logging.info("🚀 [CPU] libx265 disponível.")
            return 'libx265'
    except Exception:
        pass

    # Fallback final para libx264
    logging.warning("⚠️ Nenhum encoder acelerado detectado. Usando CPU (libx264).")
    return 'libx264'

def calcular_hash_sha1(path):
    sha1 = hashlib.sha1()
    try:
        with open(path, 'rb') as f:
            while chunk := f.read(8192): sha1.update(chunk)
        return sha1.hexdigest()
    except: return None

def sanitize_archive_name(name: str) -> str:
    if not name: return ''
    name = name.replace('\x00', '').replace('\\', '/')
    parts = [p for p in name.split('/') if p and p != '..']
    return os.path.join(*parts) if parts else ''

def build_hevc_command(input_file, output_file, video_bitrate="2500k", max_bitrate="5000k", audio_bitrate="160k", use_gpu=True):
    """
    Constrói comando FFmpeg com prioridade em hevc_nvenc e fallback para libx265.
    - GPU: hevc_nvenc (p4, hq, vbr, spatial-aq=1)
    - CPU fallback: libx265 (medium, null, vbr)
    Não inclui hwaccel_output_format cuda pois filtros de CPU requerem descarregamento.
    """
    cmd = ['ffmpeg', '-y']

    # Detecta se GPU está disponível
    try:
        result = subprocess.run(['ffmpeg', '-f', 'lavfi', '-i', f'color=c=black:s=320x240:d=0.5', '-c:v', 'hevc_nvenc', '-an', '-f', 'null', '-'], capture_output=True, timeout=3)
        has_gpu_hevc = result.returncode == 0
    except:
        has_gpu_hevc = False

    # Prioridade: hevc_nvenc → libx265
    if use_gpu and has_gpu_hevc:
        encoder = 'hevc_nvenc'
        preset = 'p4'
        tune = 'hq'
        rc_mode = 'vbr'
        spatial_aq = 1
        hwaccel = ['-hwaccel', 'cuda']
        # Necessário descarregar CUDA para filtros de CPU
        download_cuda = ',hwdownload,format=nv12' if input_file != output_file else ''
    else:
        encoder = 'libx265'
        preset = 'medium'
        tune = None
        rc_mode = 'vbr'
        spatial_aq = 0
        download_cuda = ''

    # Constrói comando base com hwaccel se disponível
    cmd.extend(['-i', str(input_file)])
    if use_gpu and has_gpu_hevc:
        cmd.extend(hwaccel)

    # Codec de vídeo HEVC
    cmd.extend([
        '-c:v', encoder,
        '-preset', preset,
        '-tune', tune or 'null',
        '-rc', rc_mode if use_gpu else None,  # libx265 não usa -rc
        '-b:v', video_bitrate,
        '-maxrate:v', max_bitrate,
        '-bufsize:v', str(int(max_bitrate.rstrip('k')) * 1.5) + 'k',
    ])
    if encoder == 'hevc_nvenc':
        cmd.extend(['-spatial-aq', '1'])

    # Filtro de download CUDA se necessário
    if use_gpu and has_gpu_hevc:
        scale_filter = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
        cmd.extend(['-vf', f"{download_cuda},{scale_filter}"])
    else:
        scale_filter = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
        cmd.extend(['-vf', scale_filter])

    cmd.extend([
        '-pix_fmt', 'yuv420p',
        '-avoid_negative_ts', 'make_zero'
    ])

    # Áudio AAC
    cmd.extend(['-c:a', 'aac', '-b:a', audio_bitrate])

    cmd.append(str(output_file))
    return cmd


def silent_subprocess(cmd, cwd=None):
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd, startupinfo=startupinfo)
