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
import subprocess
import logging
import re
import hashlib
from pydub import AudioSegment, effects

def speedup_audio(audio_segment, speed_factor):
    """Acelera o áudio sem alterar o pitch usando o filtro profissional atempo do FFmpeg (sem cortes)."""
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
    """
    [v2026.VOICE_SHIELD] Identifica se um segmento é grito, ruído, música ou recusa do LLM.
    """
    texto_bruto = str(seg.get('manual_edit_text') or seg.get('sanitized_text') or seg.get('translated_text') or seg.get('text_pt') or seg.get('original_text', seg.get('text', '')))
    if any(ord(char) > 0x3000 for char in texto_bruto):
        return True
        
    # [v2026.ASR_NOISE_SHIELD] Identifica alucinações de ruído e caracteres repetidos/georgianos
    if any('\u10a0' <= c <= '\u10ff' for c in texto_bruto):
        return True
    if re.search(r'([^\s.,!?_#*\-~])\1{3,}', texto_bruto):
        return True
        
    meta_patterns = [
        "texto fornecido", "não é em", "som de", "grito", "gemido", "traduzido", "traduzida", 
        "tradução", "legenda", "o texto", "cannot translate", "not in english", "análise:", "analise:",
        "não pode ser", "não é possível", "erro de digitação", "de digitação", "não é uma frase", 
        "mistura complexa", "caracteres japoneses", "caracteres asiáticos", "reconhecível", "de origem"
    ]
    texto_limpo = texto_bruto.lower()
    # [v2026.META_SHIELD_FIX] Evita falsos positivos em palavras válidas como "gritos" dentro de frases normais.
    # Apenas rejeita se o padrão for a frase inteira, estiver em colchetes/parênteses ou for um prefixo de erro explícito do LLM.
    for pat in meta_patterns:
        if texto_limpo == pat:
            return True
        if re.search(r'[\(\[\{]' + re.escape(pat) + r'[\)\]\}]', texto_limpo):
            return True
        # Mensagens de recusa/erro do LLM
        if pat in ["texto fornecido", "não é em", "cannot translate", "not in english", "análise:", "analise:", "mistura complexa", "não pode ser", "não é possível"]:
            if pat in texto_limpo:
                return True
        
    only_letters = re.sub(r'[^a-zA-Z]', '', texto_bruto).lower()
    if len(only_letters) > 3 and (
        len(set(only_letters)) <= 2 or 
        "aaa" in only_letters or "ooo" in only_letters or "uuu" in only_letters or "eee" in only_letters or "iii" in only_letters
    ):
        return True
        
    REACTION_WORDS = {
        "yeah", "yes", "ah", "oh", "uh", "hmm", "hm", "wow", "haha", "ha ha", "huh", "hã", "é", "ok", "ops", "oops", "ah!", "oh!", "yeah!",
        "mmm", "mmm.", "mmm...", "mm-hmm", "mm-mm", "uhu", "uh-huh", "uh-oh", "shh", "ts", "tsc"
    }
    palavras = re.sub(r'[^a-zA-Z0-9 ]', '', texto_limpo).strip().split()
    if palavras and all(p in REACTION_WORDS for p in palavras):
        return True
        
    if seg.get('emotion') == 'CANTORIA':
        return True
        
    text_orig = str(seg.get('original_text', seg.get('text', ''))).lower()
    text_pt_br = texto_limpo
    music_indicators = ['♪', '♫', '[music]', '(music)', '[singing]', '(singing)', '[canto]', '(canto)', '[cantando]', '[música]', '[musica]']
    if any(ind in text_orig for ind in music_indicators) or any(ind in text_pt_br for ind in music_indicators):
        return True
    return False

def get_best_encoder():
    """Detecta NVIDIA NVENC (RTX) ou Intel QuickSync (i5) para aceleração master."""
    try:
        cmd_nv = ['ffmpeg', '-f', 'lavfi', '-i', 'color=c=black:s=64x64', '-frames:v', '1', '-c:v', 'h264_nvenc', '-f', 'null', '-']
        if subprocess.run(cmd_nv, capture_output=True, timeout=2).returncode == 0:
            logging.info("🚀 [HARDWARE] NVIDIA NVENC Ativo! Renderização via RTX 3050.")
            return 'h264_nvenc'
        
        cmd_qsv = ['ffmpeg', '-f', 'lavfi', '-i', 'color=c=black:s=64x64', '-frames:v', '1', '-c:v', 'h264_qsv', '-f', 'null', '-']
        if subprocess.run(cmd_qsv, capture_output=True, timeout=2).returncode == 0:
            return 'h264_qsv'
    except:
        pass
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

def silent_subprocess(cmd, cwd=None):
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd, startupinfo=startupinfo)
