# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import os
import re
import json
import shutil
import logging
import subprocess
from pathlib import Path
import numpy as np
import torch
import soundfile as sf
import torchaudio

# Pre-load torchaudio
try:
    import torchaudio
except Exception:
    pass

GAME_PROFILES = {
    "padrao": {
        "name": "Estilo Padrão",
        "ai_instructions": "Estilo: Localização profissional e orgânica (PT-BR). Fuja de traduções literais robóticas. Priorize como um brasileiro falaria naturalmente naquela situação (use gírias de games/combate se necessário). A intenção da fala e o impacto emocional são mais importantes que as palavras exatas.",
        "lore": "Gênero: Jogo de Aventura/Ação (Autodetecção Ativada)",
        "glossary": {},
        "audio_settings": {
            "loudnorm": "I=-16:TP=-1.5:LRA=11",
            "volume_boost_default": 0
        }
    },
    "cod": {
        "name": "Call of Duty (MW3 Style)",
        "ai_instructions": "Estilo: Militar e Adrenalina. Foco no desespero de combate. Mantenha APENAS nomes próprios como Frost, Soap, Price, Ghost, Task Force 141 e Delta Force em Inglês. Callsigns como 'Metal 04' devem ser mantidos. TRADUZA TODO O RESTO para o Português (ex: 'upload' vira 'envio' ou 'carregamento', 'checkpoint' vira 'ponto de controle', 'copy that' vira 'entendido', 'roger' vira 'na escuta'). NUNCA suavize fatalidades: 'KIA' deve ser 'Abatidos'. O tom deve ser seco e profissional.",
        "lore": "CALL OF COD: Ambiente militar, combate intenso. O tom deve ser direto, profissional, com protocolos de rádio ('Roger', 'Over'). Urgência total.",
        "glossary": {"Frost": "Frost", "Soap": "Soap", "Price": "Price", "Ghost": "Ghost"},
        "audio_settings": {
            "loudnorm": "I=-10:TP=-0.5:LRA=11",
            "acompressor": "threshold=-18dB:ratio=4:attack=5:release=50:makeup=2",
            "bass": "g=3:f=100[bassout];[bassout]treble=g=2:f=3500",
            "volume_boost_default": 10.0
        }
    },
    "bioshock": {
        "name": "BioShock (Dystopian 50s)",
        "ai_instructions": "Estilo: Retro-Futurista e Sombrio. Narrativa teatral e densa. Mantenha nomes como Andrew Ryan, Fontaine e Little Sisters.",
        "lore": "BIOSHOCK: Um ambiente de terror subaquático em Rapture. O tom deve ser misterioso, levemente claustrofóbico e focado na atmosfera de 1960. Use termos como 'Splice' e 'Adam'.",
        "glossary": {"Andrew Ryan": "Andrew Ryan", "Fontaine": "Fontaine"},
        "audio_settings": {
            "loudnorm": "I=-14:TP=-1.0:LRA=11",
            "volume_boost_default": 12.0
        }
    },
    "rpg": {
        "name": "RPG (Natural/Medieval)",
        "ai_instructions": "Estilo: Diálogos imersivos e épicos para Fantasia/Aventura (Ex: Witcher).",
        "lore": "RPG: Ambiente fantástico, medieval. Tom heróico ou camponês.",
        "glossary": {"Geralt": "Geralt", "Yennefer": "Yennefer"},
        "audio_settings": {
            "loudnorm": "I=-20:TP=-1.5:LRA=7",
            "volume_boost_default": 4.0
        }
    },
    "xcom": {
        "name": "The Bureau: XCOM Declassified",
        "ai_instructions": "Estilo: Anos 1960, Invasão Alienígena e Investigação de Agentes Especiais. O tom deve ser tático, mais formal e com suspense de Guerra Fria. Mantenha gírias de época e formalidade militar onde adequado.",
        "lore": "XCOM: Guerra tática contra invasão alienígena. Tom profissional, militar, focado em estratégia e relatórios de campo.",
        "glossary": {
            "The Bureau": "The Bureau",
            "Carter": "Carter",
            "Outsider": "Forasteiro",
            "Sleepwalker": "Sonâmbulo",
            "Sectoid": "Sectoid",
            "Muton": "Muton"
        },
        "audio_settings": {
            "loudnorm": "I=-16:TP=-1.5:LRA=11",
            "volume_boost_default": 0.0
        }
    },
    "state_of_decay": {
        "name": "State of Decay (Survival Style)",
        "ai_instructions": "Estilo: Apocalipse Zumbi e Sobrevivência. O tom deve ser de cansaço, tensionamento constante e urgência. Use gírias de sobreviventes. Mantenha termos como 'Zeds', 'Ferals', 'Screamers' e 'Juggernauts' se o contexto pedir, ou use traduções consagradas.",
        "lore": "STATE OF DECAY: Apocalipse zumbi, sobrevivência cooperativa. O tom alterna entre o pânico absoluto e o humor ácido dos sobreviventes.",
        "glossary": {
            "Zeds": "Zeds",
            "Feral": "Selvagem",
            "Screamer": "Gritador",
            "Bloater": "Inchado",
            "Juggernaut": "Juggernaut",
            "Infestation": "Infestação"
        },
        "audio_settings": {
            "loudnorm": "I=-12:TP=-1.0:LRA=11",
            "acompressor": "threshold=-20dB:ratio=3:attack=5:release=50",
            "volume_boost_default": 8.0
        }
    }
}

def load_game_profile(profile_id):
    return GAME_PROFILES.get(profile_id, GAME_PROFILES.get('padrao'))

def robust_audio_load(path):
    data, rate = sf.read(str(path))
    audio = torch.from_numpy(data).float()
    if len(audio.shape) == 1: 
        audio = audio.unsqueeze(0)
    else: 
        audio = audio.transpose(0, 1)
    return audio, rate

def get_audio_duration(file_path):
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(file_path)], capture_output=True, text=True, check=True)
        stdout_val = result.stdout.strip()
        if stdout_val == 'N/A' or not stdout_val:
            return 0.0
        return float(stdout_val)
    except Exception as e:
        logging.error(f"Erro ao obter a duração de {file_path} com ffprobe: {e}")
        return 0.0

def get_audio_metadata(file_path):
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=sample_rate,channels,bit_rate', '-of', 'json', str(file_path)], capture_output=True, text=True, check=True)
        stream_data = json.loads(result.stdout).get('streams', [{}])[0]
        bit_rate = stream_data.get('bit_rate')
        if not bit_rate or bit_rate == 'N/A':
            result_format = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=bit_rate', '-of', 'json', str(file_path)], capture_output=True, text=True, check=True)
            bit_rate = json.loads(result_format.stdout).get('format', {}).get('bit_rate')
        return stream_data.get('sample_rate', '44100'), stream_data.get('channels', 1), bit_rate
    except Exception as e:
        logging.error(f"Erro ao obter metadados de {file_path}: {e}")
        return '44100', 1, None

def get_audio_peak_dbfs(file_path):
    try:
        threads = str(max(1, (os.cpu_count() or 4) // 2))
        cmd = ['ffmpeg', '-threads', threads, '-i', str(file_path), '-af', 'volumedetect', '-vn', '-sn', '-dn', '-f', 'null', 'NUL']
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr
        match = re.search(r"max_volume:\s*(-?[\d\.]+)\s*dB", output)
        if match:
            return float(match.group(1))
        return None
    except Exception as e:
        logging.error(f"Erro ao detectar pico de áudio em {file_path}: {e}")
        return None

def find_best_audio_profile(audio_data, job_dir):
    temp_dir = job_dir / "_temp_detection"
    temp_dir.mkdir(exist_ok=True)
    output_path = temp_dir / "test.wav"
    
    profiles = [
        {'name': 'native_wav'},
        {'f': 'mp3', 'name': 'MP3_em_WAV'},
        {'f': 's16le', 'ar': '44100', 'ac': '2', 'name': 's16le_44100Hz_Estereo'},
        {'f': 's16le', 'ar': '22050', 'ac': '2', 'name': 's16le_22050Hz_Estereo'},
        {'f': 's16le', 'ar': '44100', 'ac': '1', 'name': 's16le_44100Hz_Mono'},
        {'f': 's16le', 'ar': '22050', 'ac': '1', 'name': 's16le_22050Hz_Mono'},
        {'c:a': 'adpcm_ms', 'ar': '44100', 'ac': '2', 'name': 'adpcm_ms_44100Hz_Estereo'},
        {'c:a': 'adpcm_ms', 'ar': '22050', 'ac': '2', 'name': 'adpcm_ms_22050Hz_Estereo'},
    ]

    for profile in profiles:
        logging.info(f"Tentando perfil de áudio: {profile['name']}")
        threads = str(max(1, (os.cpu_count() or 4) // 2))
        cmd = ['ffmpeg', '-threads', threads, '-y']
        
        profile_params = {k: v for k, v in profile.items() if k != 'name'}
        for key, value in profile_params.items():
            cmd.extend([f'-{key}', value])

        cmd.extend(['-i', 'pipe:0', '-c:a', 'pcm_s16le', str(output_path)])
        
        try:
            subprocess.run(cmd, input=audio_data, check=True, capture_output=True)
            if output_path.exists() and output_path.stat().st_size > 0 and get_audio_duration(output_path) > 0.01:
                logging.info(f"SUCESSO! Melhor perfil de áudio detectado: {profile['name']}")
                shutil.rmtree(temp_dir)
                return profile
        except subprocess.CalledProcessError:
            continue
            
    shutil.rmtree(temp_dir)
    return None

def corrigir_sotaque_pt_br(texto):
    if not texto: return ""
    try:
        from num2words import num2words
        padrao_nums = re.compile(r'\b\d+([.,]\d+)?\b')
        
        def substituir_num(match):
            num_str = match.group(0).replace(',', '.')
            try:
                val = float(num_str)
                return num2words(val, lang='pt_BR')
            except:
                return num_str
        
        texto_final = padrao_nums.sub(substituir_num, texto)
        return texto_final
    except:
        return texto

def is_junk_text(text):
    if not text: return True
    t = text.lower().strip()
    words = t.split()
    if len(words) > 5:
        if all(w == words[0] for w in words[:5]): 
            return True
            
    clean_chars = t.replace(" ", "")
    if len(clean_chars) > 15:
        from collections import Counter
        counts = Counter(clean_chars)
        if counts:
            most_common_sum = sum(v for k, v in counts.most_common(2))
            if most_common_sum / len(clean_chars) > 0.85:
                return True
            
    junk_patterns = [
        "thanks for watching", "subtitles by", "amara.org", "please subscribe",
        "da da da", "la la la", "ha ha ha", "pa pa pa", "huh huh", "um um um"
    ]
    for p in junk_patterns:
        if p in t: return True
    return False

def sanitize_tts_text(text):
    if not text: return ""
    prompt_labels = r"(?im)^(Contexto|Resposta|Original|Tradução|Style|Timing|Scenario|Note|Tradução Adaptada|Texto).*?:.*?\n?"
    text = re.sub(prompt_labels, "", text)
    text = text.replace("...", " ").replace("..", " ").replace("—", " ")
    
    contracoes = {
        r"\bnum\b": "em um", r"\bnuma\b": "em uma", r"\bnums\b": "em uns", r"\bnumas\b": "em umas",
        r"\bNum\b": "Em um", r"\bNuma\b": "Em uma", r"\bNums\b": "Em uns", r"\bNumas\b": "Em umas",
        r"\bNUM\b": "EM UM", r"\bNUMA\b": "EM UMA", r"\bNUMS\b": "EM UNS", r"\bNUMAS\b": "EM UMAS",
        r"\bpara o\b": "pro", r"\bpara a\b": "pra", r"\bpara os\b": "pros", r"\bpara as\b": "pras",
        r"\bPara o\b": "Pro", r"\bPara a\b": "Pra", r"\bPara os\b": "Pros", r"\bPara as\b": "Pras",
        r"\bpara mim\b": "pra mim", r"\bPara mim\b": "Pra mim", r"\bpara você\b": "pra você", r"\bPara você\b": "Pra você",
        r"\bestá\b": "tá", r"\bEstá\b": "Tá", r"\bestou\b": "tô", r"\bEstou\b": "Tô",
        r"\bestava\b": "tava", r"\bEstava\b": "Tava", r"\bestavam\b": "tavam", r"\bEstavam\b": "Tavam",
        r"\bestávamos\b": "távamos", r"\bEstávamos\b": "Távamos",
        r"\bvc\b": "você", r"\bVc\b": "Você", r"\bvcs\b": "vocês", r"\bVcs\b": "Vocês",
        r"\btbm\b": "também", r"\bTbm\b": "Também", r"\bpq\b": "porque", r"\bPq\b": "Porque",
        r"\bblz\b": "beleza", r"\bBlz\b": "Beleza", r"\bpfv\b": "por favor", r"\bPfv\b": "Por favor",
        r"\bnet\b": "internet", r"\bNet\b": "Internet", r"\bwhats\b": "whatsapp", r"\bWhats\b": "WhatsApp"
    }
    for pattern, replacement in contracoes.items():
        text = re.sub(pattern, replacement, text)

    ordinais = {
        r"\b1[ªa]\b": "primeira", r"\b1[ºo]\b": "primeiro",
        r"\b2[ªa]\b": "segunda", r"\b2[ºo]\b": "segundo",
        r"\b3[ªa]\b": "terceira", r"\b3[ºo]\b": "terceiro",
        r"\b4[ªa]\b": "quarta", r"\b4[ºo]\b": "quarto",
        r"\b5[ªa]\b": "quinta", r"\b5[ºo]\b": "quinto",
        r"\b1[0][ªa]\b": "décima", r"\b1[0][ºo]\b": "décimo"
    }
    for pattern, replacement in ordinais.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    nums_map = {"1": "um", "2": "dois", "3": "três", "4": "quatro", "5": "cinco", "10": "dez"}
    for n, p in nums_map.items():
        text = re.sub(r'\b' + n + r'\b', p, text)

    text = re.sub(r'(\d+),(\d{1,3})(?!\d)', r'\1 vírgula \2', text)
    text = re.sub(r'(\d+(?:\s+vírgula\s+\d+)?)\s*%', r'\1 por cento', text)
    text = re.sub(r'(\d+)\s*[xX]\b(?!\w)', r'\1 vezes', text)
    text = re.sub(r'\$\s*(\d)', r'\1 dólares ', text)

    text = re.sub(r'[^\w\s\,\!\?\-\%\$\+\@áéíóúâêîôûãõàèìòùçÁÉÍÓÚÂÊÎÔÛÃÕÀÈÌÒÙÇ]', '', text)
    text = text.replace(",!", "!").replace("!,", "!").replace("?,", "?").replace(",?", "?")
    text = text.replace(".", "")
    text = text.replace(" ato", "ato").replace(" ado", "ado").replace(" ote", "ote")
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r',+', ',', text)
    if text and not text.endswith(('!', '?')):
        text += "!"
    return text
