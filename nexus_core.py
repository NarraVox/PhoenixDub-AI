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


# =====================================================================
# [v2026.INTEL] OPTIMIZATION LAYER (SKYLAKE READY)
# =====================================================================
import os
import sys
import pathlib
import shutil
import logging

import numpy as np
# [v2026.NUMPY_FIX] Conserto global para o bug do Numpy 2.0+ que quebra o Pyannote nativo
if not hasattr(np, 'NAN'):
    np.NAN = np.nan
# [v2026.ENVIRONMENT_PURGE] Remove apenas bibliotecas externas "impostoras"
try:
    import sys
    from pathlib import Path
    
    # Define o caminho do nosso ambiente de elite
    base_env = Path(sys.executable).parent.parent
    local_site = base_env / "Lib" / "site-packages"
    
    # Limpeza Seletiva: Remove APENAS o site-packages do AppData (onde moram os impostores)
    # Mas mantém a pasta 'Lib' (onde moram o glob, asyncio, etc)
    sys.path = [p for p in sys.path if not ("AppData" in p and "site-packages" in p)]
    
    # Insere o nosso site-packages como a PRIORIDADE ZERO
    if str(local_site) not in sys.path:
        sys.path.insert(0, str(local_site))
        
    print(f"🛡️ [NEXUS_ISOLATION] Ambiente blindado e seletivo. Local: {local_site.name}")

except Exception as e:
    print(f"⚠️ [FALHA_ISOLAMENTO] Erro ao limpar caminhos: {e}")

# [v2026.DLL_PANIC_FIX] Força bruta para encontrar a RTX 3050
try:
    import sys
    import ctypes
    import time
    from pathlib import Path
    
    print("\n" + "🚀" * 15)
    print("  [NEXUS_HARDWARE] Iniciando ponte de hardware RTX...")
    
    # Caminhos Ultra-Específicos para o seu ambiente
    base_env = Path(sys.executable).parent.parent
    site_packages = base_env / "Lib" / "site-packages"
    
    dll_paths = [
        site_packages / "llama_cpp" / "lib",
        site_packages / "nvidia" / "cublas" / "bin",
        site_packages / "nvidia" / "cuda_runtime" / "bin",
        site_packages / "nvidia" / "cuda_nvrtc" / "bin"
    ]
    
    found = False
    for p in dll_paths:
        if p.exists():
            os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                try: os.add_dll_directory(str(p))
                except: pass
            try: ctypes.windll.kernel32.SetDllDirectoryW(str(p))
            except: pass
            print(f"  ✅ [RTX_LINK] Vinculado: {p.name}")
            found = True
    
    if found:
        print("  ⏳ [RTX_WAIT] Aguardando estabilização do driver (2s)...")
        time.sleep(2) # [v2026.SYNC] O tempo que a GPU precisa para "acordar"
        print("  🔥 [RTX_READY] Hardware pronto para ignição!")
    else:
        print("  ⚠️ [ALERTA] Nenhuma peça NVIDIA encontrada no caminho esperado.")
    print("🚀" * 15 + "\n")

    os.environ["LLAMA_CUDA"] = "1"
    os.environ["GGML_CUDA_NO_PINNED"] = "1"

except Exception as e:
    print(f"⚠️ [FALHA_RTX] Erro na injeção de hardware: {e}")

# --- PATCH DE COMPATIBILIDADE MASTER: WINDOWS SYMLINK BYPASS (v2026.90) ---
# Resolve o WinError 1314 interceptando o Path.symlink_to globalmente.
# Se falhar ao criar link, ele faz uma cópia física.
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import torch
import gc
def _patched_symlink_to(self, target, target_is_directory=False):
    try:
        _original_symlink_to(self, target, target_is_directory)
    except OSError as e:
        # Erro 1314 = Privilégio de cliente insuficiente (atalhos no Windows)
        if getattr(e, 'winerror', 0) == 1314:
            # Resolve o caminho do alvo (target pode ser relativo ao diretório do link)
            target_path = pathlib.Path(target)
            if not target_path.is_absolute():
                abs_target = (self.parent / target_path).resolve()
            else:
                abs_target = target_path.resolve()
            
            # Se o alvo existe, fazemos a cópia física
            if abs_target.exists():
                if abs_target.is_dir():
                    shutil.copytree(abs_target, self, dirs_exist_ok=True)
                else:
                    shutil.copy2(abs_target, self)
            else:
                # Se o alvo não existe, apenas ignora (link quebrado)
                pass
        else:
            raise
pathlib.Path.symlink_to = _patched_symlink_to

# --- PATCH DE COMPATIBILIDADE API: HUGGINGFACE HUB (v2026.RTX) ---
# Resolve o conflito 'use_auth_token' vs 'token' e blinda contra erros 404 de arquivos opcionais.
try:
    import huggingface_hub
    _original_hf_hub_download = huggingface_hub.hf_hub_download
    def _patched_hf_hub_download(*args, **kwargs):
        # 1. Ajuste de Parâmetros (Novo vs Antigo)
        if 'use_auth_token' in kwargs:
            kwargs['token'] = kwargs.pop('use_auth_token')
        
        # 2. Proteção Anti-404 para arquivos secundários (custom.py)
        try:
            return _original_hf_hub_download(*args, **kwargs)
        except Exception as e:
            arg_str = str(args) + str(kwargs)
            if "custom.py" in arg_str or "404" in str(e):
                logging.warning(f"⚠️ [HF_PATCH] Ignorando falha em arquivo opcional: {e}")
                # Retorna um caminho vazio ou levanta erro capturável dependendo do contexto
                raise FileNotFoundError("Arquivo opcional não encontrado no servidor.")
            raise e
            
    huggingface_hub.hf_hub_download = _patched_hf_hub_download
except:
    pass
# ----------------------------------------------------------------
# --------------------------------------------------------------------------

import platform

# Força o uso do Intel MKL e OpenMP para máxima performance no i5-6400
os.environ["KMP_AFFINITY"] = "granularity=fine,compact,1,0"
os.environ["OMP_NUM_THREADS"] = str(os.cpu_count() or 4)
os.environ["MKL_NUM_THREADS"] = str(os.cpu_count() or 4)
os.environ["KMP_BLOCKTIME"] = "1" 

import torch
# --- BANNER DE ALTA PERFORMANCE (v2026.RTX) ---
cuda_st = "ATIVO (NVIDIA)" if torch.cuda.is_available() else "OFFLINE"
vram_info = ""
if torch.cuda.is_available():
    v_props = torch.cuda.get_device_properties(0)
    vram_info = f" | VRAM: {v_props.total_memory // (1024**2)}MB"

print("\n" + "💠 " * 15)
print(f"  [v2026.RTX] CUDA: {cuda_st}{vram_info}")

import threading
# Travas de segurança globais (v2026.RTX)
gema_lock = threading.Lock()
chatterbox_lock = threading.Lock()

# Instâncias globais de modelos para limpeza segura
gema_instance = None
gema_tokenizer = None
gema_model = None
print("  [v2026.CINE] MOTOR CINEMATOGRÁFICO READY")
print("💠 " * 15 + "\n")
# [v2026.CPU_LOCK] Garante que o Torch use todos os núcleos físicos
torch.set_num_threads(os.cpu_count() or 4)
torch.set_num_interop_threads(1)

try:
    import intel_extension_for_pytorch as ipex
except ImportError:
    pass
# =====================================================================

import requests
import json
import types
import logging
import warnings
# [v2026.10 FIX] Esconde avisos chatos do SpeechBrain que parecem erros mas não são
warnings.filterwarnings("ignore", category=UserWarning, module="speechbrain")
warnings.filterwarnings("ignore", message="Module 'speechbrain.*' was deprecated")

# [v2026.HALFIX] Stub global ultra-robusto usando MockModule para neutralizar o erro de lazy-import do SpeechBrain 1.1.0 no Windows.
# Ele absorve qualquer acesso a atributos ou chamadas de função em k2_fsa e numba sem levantar exceções.
import sys
import types

class MockModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        return MockModule(name)
    def __call__(self, *args, **kwargs):
        return MockModule("dummy")

stubs = [
    'speechbrain.integrations.numba', 
    'speechbrain.integrations.numba.transducer_loss',
    'speechbrain.integrations.k2_fsa',
    'speechbrain.integrations.nlp',
    'speechbrain.integrations.huggingface',
    'speechbrain.integrations.huggingface.wordemb',
    'speechbrain.integrations.huggingface.g2p',
    'speechbrain.integrations.huggingface.whisper'
]
for stub in stubs:
    sys.modules[stub] = MockModule(stub)

# [v2026.DLL_COLLISION_PREVENT] Pré-carregamento precoce do torchaudio.
# Importar a biblioteca de áudio ANTES que o llama.cpp carregue suas DLLs CUDA na memória
# evita a colisão dinâmica de DLLs no Windows (OSError WinError 127).
try:
    import torchaudio
except:
    pass

import random
import re
import os
import sys
import time
import subprocess
import threading
import torch
import gc
import soundfile as sf
import torchaudio

def robust_audio_load(path):
    """Carregamento de áudio à prova de falhas para Windows."""
    data, rate = sf.read(str(path))
    audio = torch.from_numpy(data).float()
    if len(audio.shape) == 1: audio = audio.unsqueeze(0)
    else: audio = audio.transpose(0, 1)
    return audio, rate
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Timer, Thread
import hashlib
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import zipfile # [NOVO] Para upload de lotes grandes
import re
import webbrowser
import stat
import random
import numpy as np
import librosa # [NEW] Motor de análise espectral para LQA Nexus
from enum import Enum
from sklearn.metrics.pairwise import cosine_similarity
# from sklearn.cluster import AgglomerativeClustering # [NOVO] Para clustering fixo

from flask import Flask, send_from_directory, request, jsonify, make_response
try:
    from flask_cors import CORS # [NEW] Suporte a Cross-Origin
    HAS_CORS = True
except ImportError:
    HAS_CORS = False
    print("[AVISO] flask_cors não instalado. O painel web pode ter problemas de acesso se rodar em portas diferentes.")
    print("Para corrigir, use: pip install flask-cors")
from pydub.silence import split_on_silence

try:
    from llama_cpp import Llama
    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False
    logging.warning("llama-cpp-python não instalado. O sistema usará LM Studio para IA.")

# --- GLOSSÁRIO FONÉTICO GLOBAL ---
PHONETIC_CORRECTIONS = {}

def corrigir_sotaque_pt_br(texto):
    """
    Normaliza o texto para o motor TTS.
    Converte números para extenso em PT-BR para evitar leitura em inglês.
    O motor Multilíngue cuida de termos em inglês (ex: upload) nativamente.
    """
    if not texto: return ""
    
    import re
    try:
        from num2words import num2words
        # Encontra números no texto
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
        # Se falhar/não tiver num2words, retorna o original sem travar
        return texto

# --- CONFIGURAÇÕES DE AMBIENTE (OFFLINE-FIRST) ---
os.environ["HF_HUB_OFFLINE"] = "0"        # [FIX] Permitir download inicial de modelos
os.environ["TRANSFORMERS_OFFLINE"] = "0"  # [FIX] Permitir download inicial de modelos
os.environ["SPEECHBRAIN_FETCH_STRATEGY"] = "COPY"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["COQUI_TOS_AGREED"] = "1"

# --- CONFIGURAÇÃO DE LOGGING (DYNAMIC PER MOTOR) ---
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Detecta o nome do script atual para criar um log único (evita WinError 32)
script_name = Path(sys.argv[0]).stem
log_path = Path("c:/IA_dublagem/logs")
log_path.mkdir(exist_ok=True)
current_log_file = log_path / f"{script_name}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(str(current_log_file), encoding='utf-8', maxBytes=2*1024*1024, backupCount=1) # Aumentado para 2MB
    ]
)

# [v2026.SILENCE] Silencia avisos técnicos do Chatterbox que não são erros
logging.getLogger("chatterbox").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*Reference mel length is not equal.*")
warnings.filterwarnings("ignore", message=".*is_causal.*")

def log_uncaught(exctype, value, tb):
    logging.critical("ERRO NÃO TRATADO (CRASH):", exc_info=(exctype, value, tb))

sys.excepthook = log_uncaught

# --- SILENCE NOISY LOGGERS ---
logging.getLogger('numba').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('torchaudio').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# PATCH: Correção para Torchaudio movida para uso local
# try:
#     import torchaudio
#     if not hasattr(torchaudio, 'list_audio_backends'):
#         def _list_audio_backends():
#             return ['soundfile'] 
#         torchaudio.list_audio_backends = _list_audio_backends
# except ImportError:
#     pass

try:
    from pydub import AudioSegment, effects # [NEW] Effects para speedup
    from werkzeug.utils import secure_filename
    from werkzeug.utils import secure_filename
    # from faster_whisper import WhisperModel
    import requests
    # import torch
    import psutil
    # from TTS.api import TTS
    # from TTS.tts.configs.Chatterbox_config import ChatterboxConfig
    # from TTS.tts.models.Chatterbox import ChatterboxAudioConfig, ChatterboxArgs
    # from TTS.config.shared_configs import BaseDatasetConfig
    # from TTS.tts.layers.Chatterbox.tokenizer import VoiceBpeTokenizer
    from collections import OrderedDict
    # import torch.serialization
except ImportError as e:
    logging.critical(f"Erro: Dependência essencial não encontrada - {e}.")
    logging.critical("Certifique-se de que todas as dependências estão instaladas corretamente.")
    sys.exit(1)

# [CLOUD-SYNC FIX] Centraliza todos os arquivos temporários para facilitar exclusão no MEGA
# Agora tudo o que o programa cria fica em uploads/_NEXUS_TEMP_
GLOBAL_TEMP_DIR = Path(os.getenv("NEXUS_TEMP", "uploads/_NEXUS_TEMP_"))
if not GLOBAL_TEMP_DIR.exists():
    GLOBAL_TEMP_DIR.mkdir(parents=True, exist_ok=True)

# --- [v12.75] VERIFICAÇÃO DE DEPENDÊNCIAS CRÍTICAS ---
def check_ffmpeg():
    """Tenta localizar o FFmpeg Full (com suporte a MP3/Lame)."""
    # [v2026 FIX] Prioridade total para a pasta local onde o usuário deve colocar o Full
    local_full_bin = os.path.join(os.getcwd(), 'env', 'Library', 'bin', 'ffmpeg.exe')
    
    if os.path.exists(local_full_bin):
        logging.info(f"FFmpeg FULL detectado na pasta local: {local_full_bin}")
        os.environ["PATH"] = os.path.dirname(local_full_bin) + os.pathsep + os.environ["PATH"]
        return True

    try:
        # Verifica se o ffmpeg do PATH tem suporte a libmp3lame
        output = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, shell=True)
        if 'libmp3lame' in output.stdout:
            logging.info("FFmpeg (Full c/ MP3) encontrado no PATH.")
            return True
        else:
            logging.warning("⚠️ FFmpeg do PATH não tem suporte a MP3 (libmp3lame).")
    except:
        pass

    logging.error("❌ ERRO CRÍTICO: FFmpeg FULL não encontrado!")
    print("\n" + "!"*60)
    print("ERRO: Sua versão do FFmpeg é limitada e não suporta MP3.")
    print("Para resolver:")
    print("1. Baixe o 'FFmpeg Full' no Gyan.dev")
    print("2. Extraia o ffmpeg.exe para: env\\Library\\bin\\")
    print("Siga o manual: MANUAL_FFMPEG_FULL.md")
    print("!"*60 + "\n")
    return False

def check_lm_studio():
    """Verifica se o modelo GGUF local existe, já que não usamos mais o LM Studio externo."""
    # [ORGANIZATION FIX] Modelos movidos para uploads/_MODELS_ para facilitar exclusão no MEGA
    model_path = Path("uploads/_MODELS_/gemma-4-E4B-it-Q4_K_M.gguf")
    if model_path.exists():
        logging.info(f"Cérebro IA (Gemma 4) detectado localmente: {model_path}")
        return True
    else:
        logging.warning(f"⚠️ AVISO: Modelo GGUF não encontrado em {model_path}")
        logging.warning("O 'Cérebro IA' (Gema Local) não funcionará. Coloque o arquivo .gguf na pasta Models.")
        return False

# [v12.70] PERFIS DE JOGO MOVIDOS PARA: nexus_dub_games.py
# --- [v12.70] DICIONÁRIO DE CONFIGURAÇÕES POR JOGO (AUTÊNTICO) ---
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
        "lore": "CALL OF DUTY: Ambiente militar, combate intenso. O tom deve ser direto, profissional, com protocolos de rádio ('Roger', 'Over'). Urgência total.",
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
        "ai_instructions": "Estilo: Imersivo e Épico. Diálogos naturais para Fantasia/Aventura (Ex: Witcher).",
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
        "ai_instructions": "Estilo: Apocalipse Zumbi e Sobrevivência. O tom deve ser de cansaço, tensão constante e urgência. Use gírias de sobreviventes. Mantenha termos como 'Zeds', 'Ferals', 'Screamers' e 'Juggernauts' se o contexto pedir, ou use traduções consagradas (ex: Zumbis, Selvagens, Gritadores).",
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
    """
    [v12.70] Carrega as configurações de IA e Som de um perfil específico.
    """
    return GAME_PROFILES.get(profile_id, GAME_PROFILES.get('padrao'))

# --- FUNÇÃO DE PRÉ-PROCESSAMENTO DE ÁUDIO (NOVO) ---
def preprocess_audio_for_diarization(input_path, output_path):
    """
    Aplica tratamento de áudio.
    1. Tenta DeepFilterNet (OBRIGATÓRIO para redução de ruído).
    2. Se não tiver, APENAS normaliza (dynaudnorm) sem filtros destrutivos.
    """
    try:
        # [REQ] Tenta importar DeepFilterNet (Melhor qualidade)
        import librosa
        
        y_check, sr_check = librosa.load(str(input_path), sr=16000, duration=5.0)
        rms = librosa.feature.rms(y=y_check)[0]
        mean_rms = np.mean(rms)
        
        # [ESTRATÉGIA DE ATIVAÇÃO CONDICIONAL - JOGOS (Nexus)]
        if mean_rms > 0.025: # Jogo tolera mais efeitos de rádio e sujeira. Threshold mais agressivo.
             logging.info(f"RMS: {mean_rms:.3f}. Ruído pesado detectado. Aplicando DeepFilterNet.")
             from df.enhance import enhance, init_df, load_audio, save_audio
             model, df_state, _ = init_df()
             audio, _ = load_audio(input_path, sr=df_state.sr())
             enhanced = enhance(model, df_state, audio)
             save_audio(output_path, enhanced, df_state.sr())
             return True
        else:
             logging.info(f"RMS: {mean_rms:.3f}. Som limpo/intencional (Rádio/Eco). Bypass DeepFilterNet.")
             raise ImportError("Bypass condicional DeepFilterNet via librosa") # Pula direto pro Fallback (Dynaudnorm conservador)
             
    except ImportError as e:
        if "Bypass condicional" not in str(e):
             logging.warning("="*60)
             logging.warning("[AVISO] DeepFilterNet não encontrado!")
             logging.warning("Instale com: pip install deepfilternet")
             logging.warning("="*60)
        logging.warning("O áudio será apenas normalizado, SEM redução de ruído.")
        logging.warning("Instale com: pip install deepfilternet")
        logging.warning("="*60)
        
        # Fallback: APENAS Normalização (Sem filtros destrutivos do FFmpeg)
        # Respeitando pedido do usuário para não usar 'tapa-buraco'
        try:
            threads = str(max(1, (os.cpu_count() or 4) // 2))
            
            # Apenas converte para 16k mono e normaliza volume
            # SEM highpass/lowpass/afftdn
            af_filter = "dynaudnorm=f=150:g=15" 
            
            cmd = [
                'ffmpeg', '-threads', threads, '-y', 
                '-i', str(input_path),
                '-af', af_filter,
                '-ar', '16000', 
                '-ac', '1',     
                str(output_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except:
             # Se até o FFmpeg falhar, copia
             pass

    except Exception as e:
        logging.error(f"Erro no pré-processamento (DeepFilterNet): {e}")

    # Fallback final: Copia o original
    try:
        shutil.copy(str(input_path), str(output_path))
    except: pass
    return False

    return False

class SimpleDiarizer:
    def __init__(self, source="speechbrain/spkrec-ecapa-voxceleb", device="cpu"):
        try:
            import torchaudio
            if not hasattr(torchaudio, 'list_audio_backends'):
                def _list_audio_backends(): return ['soundfile']
                torchaudio.list_audio_backends = _list_audio_backends

            from speechbrain.inference.speaker import EncoderClassifier
            self.encoder = EncoderClassifier.from_hparams(source=source, run_opts={"device": device})
            self.device = device
        except ImportError:
             logging.error("SpeechBrain não encontrado. Diarização falhará.")
             self.encoder = None

    def get_file_embedding(self, audio_path):
        """Gera um embedding único para o arquivo inteiro. Com Filtro de Banda."""
        import torchaudio

        load_path = str(audio_path)

        try:
            signal, fs = torchaudio.load(load_path)

            # Resample se necessário (ECAPA espera 16kHz)
            if fs != 16000:
                import torchaudio.transforms as T
                resampler = T.Resample(fs, 16000)
                signal = resampler(signal)
                fs = 16000

            # Garante mono
            if signal.shape[0] > 1:
                signal = signal.mean(dim=0, keepdim=True)

            # [TUNING] Filtro de Frequência "Telefônico" (300Hz - 3400Hz)
            # CRÍTICO PARA JOGOS: Remove música de fundo e efeitos que confundem a IA.
            try:
                import torchaudio.functional as F
                signal = F.highpass_biquad(signal, fs, 300)
                signal = F.lowpass_biquad(signal, fs, 3400)
            except Exception as e_filter:
                logging.warning(f"Erro no filtro de banda: {e_filter}")

            # Embed
            embeddings = self.encoder.encode_batch(signal)

            return embeddings[0, 0].numpy()

        except Exception as e:
            logging.error(f"Erro ao gerar embedding: {e}")
            return None

    def cluster_batch_embeddings(self, embeddings_dict, num_speakers=None):
        from sklearn.cluster import AgglomerativeClustering
        import numpy as np
        
        if not embeddings_dict: return {}

        filenames = list(embeddings_dict.keys())
        matrix = np.array([embeddings_dict[f] for f in filenames])

        # [AUTO MODE]
        if not num_speakers or num_speakers < 2:
            logging.info("Clustering Automático (Agglomerative, Threshold=0.45)...")
            clusterer = AgglomerativeClustering(n_clusters=None, distance_threshold=0.45, metric='cosine', linkage='average')
        else:
            # [FIXED MODE]
            if len(filenames) < num_speakers:
                logging.warning("Menos arquivos que falantes. Clusterização cancelada.")
                return {f: 'voz1' for f in filenames}
            clusterer = AgglomerativeClustering(n_clusters=num_speakers, metric='cosine', linkage='average')

        labels = clusterer.fit_predict(matrix)

        results = {}
        for i, label in enumerate(labels):
            results[filenames[i]] = f"voz{label+1}"

        return results

# --- DIARIZAÇÃO PROFISSIONAL (v2026.RTX - Pyannote 3.1) ---
class PyannoteDiarizer:
    def __init__(self, device="cpu"):
        from pyannote.audio import Pipeline
        import torch
        
        token = os.environ.get("HF_TOKEN", True) 
        
        try:
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=token
            )
            # [v2026.SENSITIVE_DIARIZATION] Ajusta o threshold de agrupamento de vozes para ser equilibrado.
            # O padrão do Pyannote 3.1 é ~0.704, ajustamos para 0.70 para evitar fragmentação
            # excessiva do mesmo orador (como uma mulher mudando de voz no meio da cena).
            self.pipeline.instantiate({
                "clustering": {
                    "method": "centroid",
                    "min_cluster_size": 12,
                    "threshold": 0.70
                }
            })
            if device == "cuda" and torch.cuda.is_available():
                self.pipeline.to(torch.device("cuda"))
            self.device = device
            logging.info("✅ Diarizador Pyannote 3.1 (Elite) carregado com sensibilidade 0.55.")
        except Exception as e:
            logging.error(f"❌ Erro ao carregar Pyannote: {e}")
            self.pipeline = None
            raise e

    def diarize(self, audio_path, progress_cb=None):
        if not self.pipeline: return None
        return self.pipeline(str(audio_path))

    def get_file_embedding_from_signal(self, signal_tensor):
        """
        [v2026.ELITE_FIX] Extrai o embedding (DNA) diretamente de um tensor de áudio.
        Usa o modelo de embedding autônomo do Pyannote para evitar bugs no pipeline nativo.
        """
        import torch
        try:
            if not hasattr(self, "_embedding_inference"):
                from pyannote.audio import Model, Inference
                import os
                token = os.environ.get("HF_TOKEN", True)
                
                # Instancia o extrator de DNA puro do Pyannote (usado internamente pelo 3.1)
                emb_model = Model.from_pretrained("pyannote/embedding", use_auth_token=token)
                if emb_model is None: return None
                
                emb_model.to(self.device)
                # window="whole" extrai um único vetor consolidado do pedaço inteiro (ideal pra fatias curtas)
                self._embedding_inference = Inference(emb_model, window="whole")
            
            with torch.no_grad():
                # Formata para o Inference: shape [channels, samples]
                if len(signal_tensor.shape) == 1:
                    signal_tensor = signal_tensor.unsqueeze(0)
                elif len(signal_tensor.shape) > 2:
                    signal_tensor = signal_tensor.squeeze()
                    if len(signal_tensor.shape) == 1: signal_tensor = signal_tensor.unsqueeze(0)
                
                signal_tensor = signal_tensor.to(self.device)
                
                # A API do Pyannote Inference pede um dicionário com o waveform
                emb = self._embedding_inference({"waveform": signal_tensor, "sample_rate": 16000})
                
                if emb is not None:
                    # Retorna um array numpy 1D pronto para o AgglomerativeClustering
                    return emb.reshape(-1)
                return None
        except Exception as e:
            logging.warning(f"Erro ao extrair embedding Pyannote (Inference): {e}")
            return None

    def get_file_embedding(self, audio_path):
        """Gera um embedding único para o arquivo inteiro. Com Filtro de Banda."""
        import torchaudio
        load_path = str(audio_path)
        try:
            signal, fs = robust_audio_load(load_path)
            if fs != 16000:
                import torchaudio.transforms as T
                resampler = T.Resample(fs, 16000)
                signal = resampler(signal)
                fs = 16000
            if signal.shape[0] > 1:
                signal = signal.mean(dim=0, keepdim=True)
            try:
                import torchaudio.functional as F
                signal = F.highpass_biquad(signal, fs, 300)
                signal = F.lowpass_biquad(signal, fs, 3400)
            except: pass
            
            if self.encoder is None:
                logging.warning("⚠️ Diarizador não carregado. Pulando embedding.")
                return None
                
            embeddings = self.encoder.encode_batch(signal)
            return embeddings[0, 0].cpu().numpy()
        except Exception as e:
            logging.error(f"Erro ao gerar embedding: {e}")
            return None

    def cluster_batch_embeddings(self, embeddings_map, n_clusters=None, distance_threshold=0.55):
        """
        Agrupa uma coleção de arquivos por similaridade de voz (Agglomerative Clustering).
        [v2026.50] Agora usa distance_threshold para permitir descoberta dinâmica de oradores.
        """
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering
        
        if not embeddings_map: return {}
        
        fnames = list(embeddings_map.keys())
        embs = np.array([embeddings_map[fn] for fn in fnames])
        
        if len(fnames) < 2:
            return {fnames[0]: "voz1"}

        # Se não informou n_clusters e temos distance_threshold, usamos o modo dinâmico
        if n_clusters is None or n_clusters <= 1:
            logging.info(f"Clustering: Agrupando {len(fnames)} arquivos (Modo Dinâmico - Threshold {distance_threshold})...")
            model = AgglomerativeClustering(
                n_clusters=None, 
                distance_threshold=distance_threshold, 
                metric='cosine', 
                linkage='average'
            )
        else:
            logging.info(f"Clustering: Agrupando {len(fnames)} arquivos em {n_clusters} vozes (Modo Fixo)...")
            model = AgglomerativeClustering(n_clusters=n_clusters, metric='cosine', linkage='average')
            
        labels = model.fit_predict(embs)
        
        results = {}
        for i, label in enumerate(labels):
            results[fnames[i]] = f"voz{label+1}" # Padronizado como 'vozX'
        return results

    def detect_splits_surgical(self, audio_path):
        """
        [v10.60 SURGICAL VAD SPLIT]
        Detecta silêncios primeiro (Pydub) e analisa se houve troca de voz entre os blocos de fala.
        Garante que nunca corte no meio de uma palavra.
        """
        import torchaudio
        from scipy.spatial.distance import cosine
        from pydub import AudioSegment
        from pydub.silence import detect_nonsilent
        
        sound = AudioSegment.from_wav(str(audio_path))
        # Detecta trechos de fala (VAD simples mas eficaz)
        nonsilent_ranges = detect_nonsilent(sound, min_silence_len=300, silence_thresh=-40)
        
        if len(nonsilent_ranges) < 2: return []
        
        signal, fs = robust_audio_load(str(audio_path))
        if signal.shape[0] > 1: signal = signal.mean(dim=0, keepdim=True)
        if fs != 16000:
             import torchaudio.transforms as T
             resampler = T.Resample(fs, 16000)
             signal = resampler(signal)
             fs = 16000
        
        embeddings = []
        valid_ranges = []
        
        for start_ms, end_ms in nonsilent_ranges:
            s_start = int((start_ms / 1000.0) * fs)
            s_end = int((end_ms / 1000.0) * fs)
            
            if (end_ms - start_ms) < 500: continue
            
            try:
                chunk = signal[:, s_start:s_end]
                emb = self.encoder.encode_batch(chunk)
                embeddings.append(emb.squeeze().cpu().numpy())
                valid_ranges.append((start_ms, end_ms))
            except: continue
            
        if len(embeddings) < 2: return []
        
        splits_ms = []
        for i in range(len(embeddings) - 1):
            dist = cosine(embeddings[i], embeddings[i+1])
            if dist > 0.5: # Mudança de voz entre blocos detectada
                silence_start = valid_ranges[i][1]
                silence_end = valid_ranges[i+1][0]
                split_point = (silence_start + silence_end) / 2
                splits_ms.append(split_point / 1000.0)
        
        return splits_ms

    def process(self, audio_path, segments, similarity_threshold=0.65):
        """
        [v2026.MASTER] Processa segmentos do Whisper e atribui oradores.
        """
        import torchaudio
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity
        
        logging.info(f"Diarização: Analisando {len(segments)} segmentos...")
        
        try:
            signal, fs = robust_audio_load(str(audio_path))
            if signal.shape[0] > 1: signal = signal.mean(dim=0, keepdim=True)
            if fs != 16000:
                resampler = torchaudio.transforms.Resample(fs, 16000)
                signal = resampler(signal)
                fs = 16000
        except Exception as e:
            logging.error(f"Erro ao carregar áudio para diarização: {e}")
            return segments

        speaker_prototypes = {} # ID -> mean_embedding
        next_id = 1
        
        processed = []
        for seg in segments:
            start_s = getattr(seg, 'start', seg.get('start', 0))
            end_s = getattr(seg, 'end', seg.get('end', 0))
            text = getattr(seg, 'text', seg.get('text', ""))
            
            # Converte para samples
            s_start = int(start_s * fs)
            s_end = int(end_s * fs)
            
            # Garantir tamanho mínimo para embedding (mínimo 0.3s)
            if (s_end - s_start) < (0.3 * fs):
                # Segmento muito curto, tenta herdar do anterior ou marca como desconhecido
                seg_data = {"start": start_s, "end": end_s, "text": text, "speaker": processed[-1]['speaker'] if processed else "SPEAKER_01"}
                processed.append(seg_data)
                continue

            try:
                chunk = signal[:, s_start:s_end]
                emb = self.encoder.encode_batch(chunk).squeeze().cpu().numpy()
                
                best_speaker = None
                max_sim = -1.0
                
                # Compara com protótipos existentes
                for spk_id, proto in speaker_prototypes.items():
                    sim = cosine_similarity(emb.reshape(1, -1), proto.reshape(1, -1))[0][0]
                    if sim > max_sim:
                        max_sim = sim
                        best_speaker = spk_id
                
                if best_speaker and max_sim > similarity_threshold:
                    # Atualiza protótipo (média móvel leve)
                    speaker_prototypes[best_speaker] = (speaker_prototypes[best_speaker] * 0.8) + (emb * 0.2)
                else:
                    # Novo falante
                    best_speaker = f"SPEAKER_{next_id:02d}"
                    speaker_prototypes[best_speaker] = emb
                    next_id += 1
                
                processed.append({"start": start_s, "end": end_s, "text": text, "speaker": best_speaker})
            except:
                processed.append({"start": start_s, "end": end_s, "text": text, "speaker": "SPEAKER_01"})

        return processed

    def detect_splits_surgical(self, audio_path):
        """
        [v10.60 SURGICAL VAD SPLIT]
        Detecta silêncios primeiro (Pydub) e analisa se houve troca de voz entre os blocos de fala.
        Garante que nunca corte no meio de uma palavra.
        """
        import torchaudio
        from scipy.spatial.distance import cosine
        from pydub import AudioSegment
        from pydub.silence import detect_nonsilent
        
        sound = AudioSegment.from_wav(str(audio_path))
        # Detecta trechos de fala (VAD simples mas eficaz)
        # min_silence_len=300ms para garantir que é um espaço entre frases ou palavras longas
        nonsilent_ranges = detect_nonsilent(sound, min_silence_len=300, silence_thresh=-40)
        
        if len(nonsilent_ranges) < 2: return []
        
        signal, fs = robust_audio_load(str(audio_path))
        if signal.shape[0] > 1: signal = signal.mean(dim=0, keepdim=True)
        if fs != 16000:
             resampler = torchaudio.transforms.Resample(fs, 16000)
             signal = resampler(signal)
             fs = 16000
        
        embeddings = []
        valid_ranges = []
        
        for start_ms, end_ms in nonsilent_ranges:
            # Converte ms para samples (16kHz)
            s_start = int((start_ms / 1000.0) * fs)
            s_end = int((end_ms / 1000.0) * fs)
            
            # Se o trecho for muito curto (<meio segundo), ignoramos para estabilidade do embedding
            if (end_ms - start_ms) < 500: continue
            
            try:
                # Extrai embedding do bloco de fala inteiro
                chunk = signal[:, s_start:s_end]
                emb = self.encoder.encode_batch(chunk)
                embeddings.append(emb.squeeze().cpu().numpy())
                valid_ranges.append((start_ms, end_ms))
            except: continue
            
        if len(embeddings) < 2: return []
        
        # [v21.20] SENSIBILIDADE RECALIBRADA
        # Aumentado de 0.5 para 0.8 para evitar "falsos positivos" em frases curtas.
        # Só corta se a diferença de voz for gritante.
        splits_ms = []
        for i in range(len(embeddings) - 1):
            dist = cosine(embeddings[i], embeddings[i+1])
            if dist > 0.8: # Mudança de voz entre blocos detectada (Exige Certeza Absoluta)
                # O ponto de corte é no meio do silêncio entre os dois blocos
                silence_start = valid_ranges[i][1]
                silence_end = valid_ranges[i+1][0]
                split_point = (silence_start + silence_end) / 2
                splits_ms.append(split_point / 1000.0) # Retorna em segundos
        
        return splits_ms

def split_audio_by_speaker(audio_path, job_dir):
    """
    Analisa se houve troca de voz e divide o arquivo usando VAD Cirúrgico.
    """
    try:
        from pydub import AudioSegment
        # [v21.20] TRAVA DE SEGURANÇA: Áudios curtos (<6s) não devem ser picotados.
        # Geralmente são interações simples onde o Whisper acertou o grupo.
        duration = get_audio_duration(audio_path)
        if duration < 6.0:
            return False
            
        # Inicializa o diarizador (CPU para evitar conflito com generation se ocorrer em paralelo)
        diarizer = SimpleDiarizer(device="cpu")
        splits = diarizer.detect_splits_surgical(audio_path)
        
        if not splits: return False
        
        logging.info(f"Diarização Cirúrgica v10.60: detectadas {len(splits)} trocas de voz em '{audio_path.name}'.")
        sound = AudioSegment.from_wav(str(audio_path))
        
        # Corte real (Pontos em MS)
        points = [0] + [int(s * 1000) for s in splits] + [len(sound)]
        for i in range(len(points) - 1):
            start, end = points[i], points[i+1]
            if end - start < 300: continue # Ignora micro-cortes
            chunk = sound[start:end]
            # Exporta DIRETAMENTE na raiz da pasta (sem criar subpastas de _segmentos)
            chunk.export(audio_path.parent / f"{audio_path.stem}_p{i+1:02d}.wav", format="wav")
            
        # Move original para backup
        backup_dir = job_dir / "_0_ORIGINAIS_BACKUP"
        backup_dir.mkdir(exist_ok=True)
        shutil.move(str(audio_path), str(backup_dir / audio_path.name))
        return True
    except Exception as e:
        logging.error(f"Falha na Diarização Cirúrgica v10.60: {e}")
        return False

# --- FUNÇÕES DE ÁUDIO AUXILIARES ---

def speedup_audio(audio_segment, speed_factor):
    """Acelera o áudio sem alterar o pitch usando o filtro profissional atempo do FFmpeg (sem cortes)."""
    if speed_factor <= 1.0: return audio_segment
    
    import subprocess
    import tempfile
    import os
    
    try:
        # Cria pasta temporária
        temp_dir = "C:/IA_dublagem/uploads/_NEXUS_TEMP_"
        os.makedirs(temp_dir, exist_ok=True)
        
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
        logging.warning(f"⚠️ [CORE] Falha ao acelerar áudio com FFmpeg: {e}. Usando fallback Pydub...")
        
    try:
        return effects.speedup(audio_segment, playback_speed=speed_factor, chunk_size=120, crossfade=20)
    except Exception as err:
        logging.error(f"❌ [CORE] Falha no fallback de aceleração: {err}")
        return audio_segment

def consolidate_speaker_segments(job_dir, project_data, cb, etapa_idx):
    """
    [NEW] Consolidação Inteligente de Oradores (Portado do App_videos):
    1. Separa oradores em 'Válidos' (>10s) e 'Questionáveis' (<10s).
    2. Se houver Válidos, compara Questionáveis com eles via Embeddings.
    3. Se similaridade > 0.6 (Threshold), funde (merge).
    """
    logging.info("Iniciando Consolidação de Oradores...")
    
    voices_dir = job_dir / "voices" # Em jogos, as vozes ficam em subpastas? Não, aqui no jogos o fluxo é diferente.
    # Em jogos, as vozes já estão separadas em pastas no _2_PARA_AS_PASTAS_DE_VOZ ou similar.
    # Mas esta função é para limpar o JSON (project_data) baseada em referências.
    # NO APP_JOGOS: A estrutura é diferente. As vozes são pastas.
    # A função `unify_speaker_files` já faz algo parecido (merge de pastas).
    # ENTÃO: Talvez não precisemos de `consolidate_speaker_segments` exatamente como no App_videos,
    # mas sim melhorar a `unify_speaker_files`!
    
    # VOU ABORTAR A INSERÇÃO DESTA FUNÇÃO AQUI E MELHORAR A UNIFY_SPEAKER_FILES NA PRÓXIMA ETAPA.
    return project_data

def separar_vocal_instrumental(input_audio, job_dir, cb=None):
    """
    Separação Profissional por Chunks (60s) para máxima performance em GPU.
    Restaurado do App_videos.py para máxima estabilidade.
    """
    job_dir = Path(job_dir)
    temp_chunks_dir = job_dir / "_temp_umx_chunks"
    temp_chunks_dir.mkdir(exist_ok=True)
    
    vocals_final_path = job_dir / "vocals.wav"
    instrumental_final_path = job_dir / "instrumental.wav"

    try:
        # 1. Segmentar áudio original em chunks de 60s
        if cb: cb(5, 0, "[FFmpeg] Fatiando áudio para separação segura...")
        cmd_split = [
            'ffmpeg', '-y', '-i', str(input_audio), 
            '-f', 'segment', '-segment_time', '60', '-c', 'copy', 
            str(temp_chunks_dir / "chunk_%03d.wav")
        ]
        subprocess.run(cmd_split, check=True, capture_output=True)
        
        chunks = sorted(list(temp_chunks_dir.glob("chunk_*.wav")))
        if not chunks: return False

        import torch
        import torchaudio
        from openunmix import predict
        device = "cuda" if torch.cuda.is_available() else "cpu"

        v_chunks = []
        i_chunks = []

        logging.info(f"🔍 Iniciando separação de {len(chunks)} blocos no dispositivo: {device}")

        for idx, chunk_path in enumerate(chunks):
            # [v2026.RESUME] Verificação de Cache por Bloco
            v_path = temp_chunks_dir / f"vocal_bloco_{idx}.wav"
            i_path = temp_chunks_dir / f"instrumental_bloco_{idx}.wav"
            
            if v_path.exists() and i_path.exists() and v_path.stat().st_size > 1000:
                logging.info(f"✅ [CACHE] Bloco {idx+1}/{len(chunks)} já processado. Pulando...")
                v_chunks.append(v_path)
                i_chunks.append(i_path)
                continue

            msg = f"[OpenUnmix] Processando bloco {idx+1}/{len(chunks)}..."
            if cb: 
                # Progresso relativo de 0 a 100% para a etapa de separação
                pct_etapa = (idx / len(chunks)) * 100
                cb(pct_etapa, 0, msg)
            logging.info(msg)
            
            # [v2026.FIX] Carregamento Robusto
            audio, rate = robust_audio_load(chunk_path)
            logging.info(f"   -> Áudio carregado: {audio.shape} | Rate: {rate}")

            if rate != 44100:
                resampler = torchaudio.transforms.Resample(rate, 44100)
                audio = resampler(audio)
                rate = 44100

            # Inferência com monitoramento de tempo e TRAVA DE INFERÊNCIA
            t0 = time.time()
            with torch.no_grad():
                estimates = predict.separate(
                    audio[None], rate=rate, targets=['vocals', 'drums', 'bass', 'other'], residual=True, device=device
                )
            t1 = time.time()
            logging.info(f"   -> Bloco {idx+1} separado em {t1-t0:.2f}s")
            
            # [v2026.RTX_ULTRA_FLOW] Transferência ultra-rápida para CPU
            vocal_cpu = estimates['vocals'][0].cpu()
            instrum_cpu = (estimates['drums'][0] + estimates['bass'][0] + estimates['other'][0]).cpu()
            
            # [v2026.ASYNC_IO] Salvamento em Segundo Plano para não travar a GPU
            def save_worker(v_tensor, i_tensor, v_p, i_p):
                import soundfile as sf
                v_np = v_tensor.transpose(0, 1).numpy()
                i_np = i_tensor.transpose(0, 1).numpy()
                sf.write(str(v_p), v_np, 44100)
                sf.write(str(i_p), i_np, 44100)

            import threading
            threading.Thread(target=save_worker, args=(vocal_cpu, instrum_cpu, v_path, i_path)).start()

            v_chunks.append(v_path)
            i_chunks.append(i_path)

            # [v2026.SMART_PULSE] Limpa VRAM apenas a cada 5 blocos para manter a GPU ocupada
            if 'cuda' in str(device) and (idx + 1) % 5 == 0:
                del estimates
                torch.cuda.empty_cache()
            elif 'cuda' in str(device):
                del estimates # Deleta a referência mas não força o sync lento do empty_cache

        # 3. Unificar com Pydub (Safe Concat)
        if cb: cb(95, 0, "[Pydub] Costurando áudio masterizado...")
        final_v = AudioSegment.empty()
        final_i = AudioSegment.empty()
        
        for v_p in v_chunks: final_v += AudioSegment.from_wav(str(v_p))
        for i_p in i_chunks: final_i += AudioSegment.from_wav(str(i_p))
        
        # Exporta Vocals (16k mono para Whisper)
        final_v.set_frame_rate(16000).set_channels(1).export(str(vocals_final_path), format="wav")
        # Exporta Instrumental (44.1k stereo para Master)
        final_i.export(str(instrumental_final_path), format="wav")
        
        # Cleanup de arquivos e MEMÓRIA (v2026.RTX_ULTRA_CLEAN)
        shutil.rmtree(temp_chunks_dir)
        
        logging.info("🧹 [VRAM_PURGE] Limpando OpenUnmix da GPU...")
        try:
            if 'estimates' in locals(): del estimates
            import gc
            gc.collect()
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                torch.cuda.synchronize()
        except: pass
        
        return True

    except Exception as e:
        logging.error(f"Erro na separação chunked: {e}")
        shutil.copy(str(input_audio), str(vocals_final_path))
        return False

def run_openunmix_batch(source_dir, job_dir, cb):
    logging.info("Iniciando separação de áudio com OpenUnmix...")
    
    stem_vocal_dir = job_dir / "_0a_SEPARACAO_VOCAL"
    stem_bg_dir = job_dir / "_0b_SEPARACAO_FUNDO"
    stem_vocal_dir.mkdir(parents=True, exist_ok=True)
    stem_bg_dir.mkdir(parents=True, exist_ok=True)
    
    files = list(source_dir.rglob("*.wav"))
    if not files: return
    
    # Verifica se já processou tudo
    all_processed = True
    for file_path in files:
        rel_path = file_path.relative_to(source_dir)
        vocal_out = stem_vocal_dir / rel_path
        bg_out = stem_bg_dir / rel_path
        if not (vocal_out.exists() and bg_out.exists()):
            all_processed = False
            break
            
    if all_processed:
        logging.info("Separação OpenUnmix já realizada (cache encontrado).")
        cb(100, 1, "Separação já concluída (Cache).")
        return

    try:
        import torch
        import torchaudio
        from openunmix import predict
    except ImportError:
        logging.warning("OpenUnmix não encontrado. Tentando instalar...")
        try:
             cb(0, 1, "Instalando OpenUnmix (pode demorar)...")
             subprocess.check_call([sys.executable, "-m", "pip", "install", "openunmix", "torchaudio", "scikit-learn"])
             import torch
             import torchaudio
             from openunmix import predict
        except Exception as e:
             logging.error(f"Falha ao instalar OpenUnmix: {e}")
             cb(100, 1, "Erro: OpenUnmix não instalado.")
             return

    # Check CUDA
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logging.info(f"OpenUnmix usando dispositivo: {device}")
    
    for i, file_path in enumerate(files):
        cb((i / len(files)) * 100, 1, f"Separando Fundo/Voz: {file_path.name}")
        
        rel_path = file_path.relative_to(source_dir)
        vocal_out = stem_vocal_dir / rel_path
        bg_out = stem_bg_dir / rel_path
        
        vocal_out.parent.mkdir(parents=True, exist_ok=True)
        bg_out.parent.mkdir(parents=True, exist_ok=True)
        
        if vocal_out.exists() and bg_out.exists():
            continue

        try:
            audio, rate = robust_audio_load(file_path)
            if rate != 44100:
                resampler = torchaudio.transforms.Resample(rate, 44100)
                audio = resampler(audio)
                rate = 44100

            estimates = predict.separate(
                audio[None], rate=rate, targets=['vocals', 'drums', 'bass', 'other'], residual=True, device=device
            )
            
            vocal_audio = estimates['vocals'][0].cpu()
            bg_audio = (estimates['drums'][0] + estimates['bass'][0] + estimates['other'][0]).cpu()
            
            import soundfile as sf
            # Converte para [tempo, canais] para o soundfile
            v_data = vocal_audio.transpose(0, 1).numpy()
            bg_data = bg_audio.transpose(0, 1).numpy()
            sf.write(str(vocal_out), v_data, rate)
            sf.write(str(bg_out), bg_data, rate)
            
        except Exception as e:
            logging.error(f"Erro OpenUnmix em {file_path.name}: {e}")
            shutil.copy(file_path, vocal_out)

    cb(100, 1, "Separação de áudio concluída.")

def run_batch_cleaning(source_dir, dest_dir, cb):
    """
    Executa limpeza de áudio em LOTE usando DeepFilterNet.
    Lê de source_dir, salva em dest_dir.
    PULA arquivos que já existem em dest_dir (Cache).
    """
    if not source_dir.exists(): return
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    files = list(source_dir.rglob("*.wav"))
    if not files: return
    
    # Filtra apenas o que precisa ser processado
    to_process = []
    for f in files:
        dest_path = dest_dir / f.name
        if not dest_path.exists():
            to_process.append(f)
            
    if not to_process:
        cb(0, 1, "Todos os arquivos já estão limpos (Cache). Pulando DeepFilterNet.")
        return True

    cb(0, 1, f"Inicializando DeepFilterNet para limpar {len(to_process)} novos arquivos...")
    
    try:
        from df.enhance import enhance, init_df, load_audio, save_audio
        
        # Carrega modelo UMA VEZ
        model, df_state, _ = init_df()
        logging.info("Modelo DeepFilterNet carregado na memória.")
        
        total = len(to_process)
        success_count = 0
        
        for i, f in enumerate(to_process):
            dest_path = dest_dir / f.name
            try:
                # Carrega áudio
                audio, _ = load_audio(str(f), sr=df_state.sr())
                
                # [VAD/GATING FIX] Limita a atenuação a 18dB para evitar que a voz "suma" 
                # subitamente quando o fundo de rádio for muito forte.
                try:
                    enhanced = enhance(model, df_state, audio, atten_lim_db=18.0)
                except TypeError:
                    enhanced = enhance(model, df_state, audio)
                
                # [v10.65 CLEAN CLONE UPDATE]
                # Anteriormente usávamos 50/50 mix para manter ambiência, mas isso causa alucinações (eeee) no TTS.
                # Agora usamos 100% Clean para garantir que a referência de clonagem seja pura.
                # enhanced = (enhanced * 0.50) + (audio * 0.50) # [DEPRECATED v10.65]
                save_audio(str(dest_path), enhanced, df_state.sr()) 
                
                success_count += 1
                if i % 5 == 0: # Atualiza UI a cada 5
                    cb((i / total) * 100, 1, f"Limpando: {f.name} ({i+1}/{total})")
            except Exception as e_file:
                logging.error(f"Erro ao limpar {f.name}: {e_file}")
                # Fallback: Copia o original se falhar a limpeza
                try: shutil.copy(str(f), str(dest_path))
                except: pass
        
        cb(100, 1, f"Limpeza Concluída: {success_count}/{total} arquivos processados.")
        return True

    except ImportError:
        logging.warning("[BATCH] DeepFilterNet não instalado. Apenas copiando arquivos.")
        # Fallback: Copia tudo
        for f in to_process:
            try: shutil.copy(str(f), str(dest_dir / f.name))
            except: pass
        return False
    except Exception as e:
        logging.error(f"[BATCH] Erro fatal no DeepFilterNet: {e}")
        return False

def check_ffmpeg():
    """Verifica se o FFmpeg está instalado e acessível no PATH do sistema."""
    if not shutil.which("ffmpeg"):
        logging.critical("="*80)
        logging.critical("ERRO CRÍTICO: O FFmpeg não foi encontrado no PATH do sistema.")
        logging.critical("O FFmpeg é essencial para o funcionamento deste programa.")
        logging.critical("Por favor, instale o FFmpeg e certifique-se de que ele está no PATH.")
        logging.critical("Download: https://ffmpeg.org/download.html")
        logging.critical("="*80)
        sys.exit(1)
    logging.info("FFmpeg encontrado e pronto para uso.")

# --- VOICE GUARD (SISTEMA DE IDENTIDADE RIGOROSA) ---
class VoiceState(Enum):
    PROVISIONAL = "Provisória" 
    INSUFFICIENT = "Insuficiente"
    TRAINABLE = "Treinável"

class VoiceIdentity:
    def __init__(self, voice_id):
        self.id = voice_id
        self.embeddings = []
        self.mean_embedding = None
        self.total_duration = 0.0
        self.segments = []
        self.state = VoiceState.PROVISIONAL

    def add_segment(self, embedding, duration, segment_info=None):
        self.embeddings.append(embedding)
        self.total_duration += duration
        matrix = np.array(self.embeddings)
        self.mean_embedding = np.mean(matrix, axis=0)
        self.update_state()

    def update_state(self):
        if self.total_duration >= 10.0: # Jogos: arquivos curtos, limiar menor
            self.state = VoiceState.TRAINABLE
        elif self.total_duration >= 2.0:
            self.state = VoiceState.INSUFFICIENT
        else:
            self.state = VoiceState.PROVISIONAL

class VoiceGuard:
    def __init__(self, similarity_threshold=0.42, hysteresis_threshold=0.35):
        self.voices = {} 
        self.next_id_counter = 1
        self.similarity_threshold = similarity_threshold
        self.hysteresis_threshold = hysteresis_threshold 
        self.last_speaker_id = None

    def create_new_voice(self):
        new_id = f"voz{self.next_id_counter}"
        self.next_id_counter += 1
        self.voices[new_id] = VoiceIdentity(new_id)
        return new_id

    def process_segment(self, embedding, duration, start_time, end_time):
        from sklearn.metrics.pairwise import cosine_similarity
        best_match_id = None
        best_score = -1.0
        
        # [OPTIMIZATION] Verifica primeiro o último orador (Hysteresis Check)
        # Se a similaridade com o último for "ok" (> hysteresis_threshold), mantém!
        # Isso evita que pequenos ruídos ou pausas quebrem a continuidade.
        if self.last_speaker_id and self.last_speaker_id in self.voices:
            last_voice = self.voices[self.last_speaker_id]
            if last_voice.mean_embedding is not None:
                emb_a = embedding.reshape(1, -1)
                emb_b = last_voice.mean_embedding.reshape(1, -1)
                last_score = cosine_similarity(emb_a, emb_b)[0][0]
                
                if last_score >= self.hysteresis_threshold:
                    # [STICKY] Mantém o orador mesmo que não seja o "melhor de todos"
                    # desde que seja aceitável.
                    # logging.info(f"Hysteresis Active: Kept {self.last_speaker_id} (Score: {round(last_score, 2)})")
                    self.voices[self.last_speaker_id].add_segment(embedding, duration, {"start": start_time, "end": end_time})
                    return self.last_speaker_id

        # Se não caiu no hysteresis, procura o melhor match global
        for vid, voice in self.voices.items():
            if voice.mean_embedding is None: continue
            emb_a = embedding.reshape(1, -1)
            emb_b = voice.mean_embedding.reshape(1, -1)
            score = cosine_similarity(emb_a, emb_b)[0][0]
            if score > best_score:
                best_score = score
                best_match_id = vid
        
        result_id = None
        
        if best_match_id and best_score >= self.similarity_threshold:
            result_id = best_match_id
        else:
            result_id = self.create_new_voice()
        
        if result_id and result_id in self.voices:
            voice = self.voices[result_id]
            voice.add_segment(embedding, duration, {"start": start_time, "end": end_time})
        
        self.last_speaker_id = result_id
        return result_id

    def get_trainable_voices(self):
        return [v for v in self.voices.values() if v.state == VoiceState.TRAINABLE]

    # [NEW] Post-Processing Merge Logic
    # Verifica vozes muito parecidas que acabaram separadas e as une.
    def merge_similar_voices(self, threshold=0.65):
        """
        Une vozes duplicadas.
        Threshold: 0.65 (Mais alto que o de entrada, para garantir fusão segura).
        """
        import shutil
        from sklearn.metrics.pairwise import cosine_similarity
        
        merged_count = 0
        sorted_ids = sorted(self.voices.keys())
        
        # Compara todos contra todos
        # (Naive O(N^2), mas N é pequeno em jogos, < 20 speakers)
        for i in range(len(sorted_ids)):
            id_a = sorted_ids[i]
            if id_a not in self.voices: continue # Já foi mergeado
            
            voice_a = self.voices[id_a]
            if voice_a.mean_embedding is None: continue

            for j in range(i + 1, len(sorted_ids)):
                id_b = sorted_ids[j]
                if id_b not in self.voices: continue
                
                voice_b = self.voices[id_b]
                if voice_b.mean_embedding is None: continue
                
                # Calcula similaridade
                emb_a = voice_a.mean_embedding.reshape(1, -1)
                emb_b = voice_b.mean_embedding.reshape(1, -1)
                score = cosine_similarity(emb_a, emb_b)[0][0]
                
                if score > threshold:
                    # MERGE! (B -> A)
                    # logging.info(f"Merging {id_b} into {id_a} (Similarity: {round(score, 2)})")
                    
                    # 1. Transfere segmentos
                    voice_a.segments.extend(voice_b.segments)
                    voice_a.total_duration += voice_b.total_duration
                    voice_a.embeddings.extend(voice_b.embeddings)
                    
                    # 2. Recalcula média
                    matrix = np.array(voice_a.embeddings)
                    voice_a.mean_embedding = np.mean(matrix, axis=0)
                    
                    # 3. Importante: Atualiza o mapeamento para que o resto do código saiba
                    # (Isso requer que o caller use essa função e atualize seus dicionários)
                    # Aqui só atualizamos o estado interno do VoiceGuard
                    del self.voices[id_b]
                    merged_count += 1
                    
        return merged_count

# [SUCESSO] Limpeza concluída e classes unificadas.

# --- ETAPAS DO PROCESSO NA INTERFACE ---
ETAPAS_JOGOS = [
    "Iniciando",                      # 0
    "1. Diarização Automática",         # 1
    "2. Transcrição",                 # 2
    "3. Tradução (Gema)",             # 3
    "4. Sincronização (Gema)",        # 4
    "5. Adaptação para TTS",          # 5
    "6. Gerando Áudios (Chatterbox)", # 6
    "7. Refinamento e Auto-Regeneração Nexus (LQA Bruto)", # 7
    "8. Sincronia e Masterização Profissional", # 8
    "9. Auditoria Final Nexus (LQA Técnico)", # 9
    "10. Concluído"                    # 10
]
ETAPAS_CONVERSAO = [
    "Iniciando", "1. Convertendo Arquivos", "2. Concluído"
]
ETAPAS_TRANSCRICAO = [
    "Iniciando", "1. Transcrevendo com Whisper", "2. Gerando Arquivos Finais", "3. Concluído"
]
# Atualizado para refletir a mudança de ferramenta
ETAPAS_SEPARACAO = [
    "Iniciando", "1. Removendo Efeito de Rádio (FFmpeg)", "2. Finalizando", "3. Concluído"
]

# --- DICIONÁRIO DE TRADUÇÕES COMUNS ---
DICIONARIO_TRADUCOES = {
    "on it.": "Já vou.", "weapons free.": "Fogo à vontade.", "no way.": "nem pensar.",
    "get real.": "cai na real.", "not happening.": "sem chance.", "yes.": "sim.",
    "no.": "não.", "thanks.": "obrigado.", "thank you.": "obrigado.", "ok.": "ok."
}

# --- LISTA DE SIBILOS E SONS NÃO VERBAIS A IGNORAR ---
# [v2026.REACTION_FILTER] Expandido para preservar atuações originais em interjeições comuns.
SONS_A_IGNORAR = [
    'ah', 'ai', 'eh', 'ei', 'oh', 'oi', 'uh', 'ui', 'ahm', 'hmm', 'huh', 'hmpf',
    'tsk', 'tsr', 'ugh', 'uhm', 'shh', 'suspira', 'geme', 'gasp', 'ofega', 'grr', 'rrr',
    'click', 'breath', 'respira', 'chora', 'risos', 'haha', 'hahaha', 'hihi', 'hehe', 'ha', 'ha ha',
    'yeah', 'hey', 'yo', 'wow', 'uh-huh', 'nope', 'yep', 'huh', 'hm', 'mhm',
    'and', 'but', 'so', 'then', 'or', 'a', 'the', 'is', 'it'
]

def is_junk_text(text):
    if not text: return True
    t = text.lower().strip()
    
    # 1. Repetição de padrão curto (ex: "DA DA DA", "E E E")
    words = t.split()
    if len(words) > 5:
        # Se as primeiras 5 palavras forem idênticas, é lixo/alucinação
        if all(w == words[0] for w in words[:5]): 
            return True
            
    # 2. Heurística de Variedade de Caracteres (Anti-Hallucination)
    clean_chars = t.replace(" ", "")
    if len(clean_chars) > 15:
        from collections import Counter
        counts = Counter(clean_chars)
        # Se 1 ou 2 letras dominam 85% de um texto longo, é junk
        if counts:
            most_common_sum = sum(v for k, v in counts.most_common(2))
            if most_common_sum / len(clean_chars) > 0.85:
                return True
            
    # 3. Padrões de Alucinação Frequentes (Whisper Hallucination)
    junk_patterns = [
        "thanks for watching", "subtitles by", "amara.org", "please subscribe",
        "da da da", "la la la", "ha ha ha", "pa pa pa", "huh huh", "um um um"
    ]
    for p in junk_patterns:
        if p in t: return True
        
    return False

# --- VARIÁVEIS GLOBAIS E LOCKS (Adaptativo v18.6) ---
whisper_model = None
chatterbox_model = None
model_lock = Lock()
progress_dict, progress_lock = {}, Lock()
active_jobs_lock = Lock()
active_jobs = set()

# [v18.6] TRAVA DE SEGURANÇA: 1 vídeo por vez para estabilidade total.
# --- CONTROLE DE FILA (Otimização Estrita para i5) ---
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
Chatterbox_executor = ThreadPoolExecutor(max_workers=1) # SÓ 1: O mais pesado de todos
General_executor = ThreadPoolExecutor(max_workers=2)    # Máximo 2 para tarefas leves (arquivos/texto)

MAX_CONCURRENT_JOBS = 1 

# --- INICIALIZAÇÃO DO FLASK ---
app = Flask(__name__, template_folder='client', static_folder='client')
if HAS_CORS:
    CORS(app) # [NEW] Habilita CORS para o frontend local
else:
    print("[AVISO] Rodando sem CORS. Instale com: pip install flask-cors")
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024 
app.config['MAX_FORM_PARTS'] = 10000
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- FUNÇÕES DE SEGURANÇA ---
def safe_json_write(data, path, indent=4, ensure_ascii=False, retries=5, delay=0.2):
    path = Path(path)
    # [PRUDENCE FIX] Garante que a pasta existe antes de tentar escrever
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + '.tmp')
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
    except Exception as e:
        logging.error(f"ERRO CRÍTICO ao escrever no ficheiro temporário {temp_path}: {e}")
        return
    for attempt in range(retries):
        try:
            os.replace(temp_path, path)
            return
        except PermissionError as e:
            if attempt < retries - 1:
                logging.warning(f"Tentativa {attempt + 1}/{retries} falhou ao aceder {path}: {e}. A tentar novamente em {delay}s...")
                time.sleep(delay)
            else:
                logging.error(f"ERRO CRÍTICO na tentativa final de escrever em {path}: {e}")
        except Exception as e:
            logging.error(f"ERRO CRÍTICO inesperado ao substituir {path} com {temp_path}: {e}")
            break
    logging.error(f"NÃO FOI POSSÍvel escrever em {path} após {retries} tentativas.")

def safe_json_read(path, retries=5, delay=0.1):
    path = Path(path)
    for attempt in range(retries):
        try:
            if not path.exists(): return None
            # [v2026.READ_SHIELD] Se o arquivo tiver tamanho 0, significa que outro processo
            # abriu o arquivo para escrita mas ainda não gravou o buffer. Lançamos erro para tentar novamente.
            if path.stat().st_size == 0:
                raise json.JSONDecodeError("Ficheiro temporariamente vazio (sendo escrito)", "", 0)
                
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (PermissionError, OSError, json.JSONDecodeError) as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                if isinstance(e, json.JSONDecodeError):
                    logging.error(f"Ficheiro JSON corrompido detectado em {path} após {retries} tentativas: {e}")
                    corrupt_path = path.with_name(f"{path.stem}.corrupt_{int(time.time())}{path.suffix}")
                    try:
                        os.replace(path, corrupt_path)
                        logging.warning(f"Ficheiro corrompido movido para {corrupt_path}")
                    except Exception as move_e: 
                        logging.error(f"ERRO ao mover ficheiro corrompido {path}: {move_e}")
                else:
                    logging.error(f"ERRO inesperado ao ler o ficheiro JSON {path}: {e}")
                return None
        except Exception as e:
            logging.error(f"ERRO inesperado ao ler o ficheiro JSON {path}: {e}")
            return None

def sanitize_tts_text(text):
    if not isinstance(text, str): return ""
    match = re.match(r'^(.*?)(?=\n\n|\*\*Texto Original:|\*\*Texto Adaptado:)', text, re.DOTALL)
    clean_text = match.group(1).strip() if match else text.strip()
    # [FIX] Remove marcadores de lista que vazam do LLM: "(a) ", "1. ", "a) "
    clean_text = re.sub(r'(?:^|\s)[\(\[]?[0-9a-zA-Z]{1,2}[\)\]\.]\s+', ' ', clean_text)
    
    # [FIX] Remove marcadores de gênero (ex: "trancado(a)", "ele(a)")
    clean_text = re.sub(r'\([aoes]\)', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\s+\([aoes]\)', '', clean_text, flags=re.IGNORECASE)
    
    clean_text = re.sub(r'ponto de interrogação|ponto interroga(?:ç|t)ão|ponto inter[eo]gativo', '?', clean_text, flags=re.IGNORECASE)
    
    # [TTS OPTIMIZATION] Remove TODAS as vírgulas para evitar pausas indesejadas na fala.
    # O texto visual pode ter vírgula, mas o robô vai ler direto ("correndo").
    clean_text = clean_text.replace(',', ' ').replace('...', ' ').replace('.', ' ')
    
    clean_text = clean_text.replace('!', 'TEMP_EXCLAMATION').replace('?', 'TEMP_QUESTION')
    clean_text = clean_text.replace('TEMP_EXCLAMATION', '!').replace('TEMP_QUESTION', '?')
    
    # Remove espaços duplos criados pela remoção de pontuação
    return " ".join(clean_text.split()).strip()

def log_error_to_file(job_dir, file_id, original_text, etapa, resposta_falha, tentativas=1):
    error_log_path = job_dir / "erros.json"
    try:
        logs = safe_json_read(error_log_path) or []
        error_entry = { "timestamp": datetime.now().isoformat(), "file_id": file_id, "original_text": original_text,
                        "etapa_falha": etapa, "resposta_recebida": resposta_falha, "tentativas": tentativas }
        logs.append(error_entry)
        safe_json_write(logs, error_log_path)
    except Exception as e:
        logging.error(f"Não foi possível registar o erro no ficheiro {error_log_path}: {e}")

# --- FUNÇÕES DE LÓGICA DO PIPELINE ---
def _print_progress_to_cmd(job_id, progress, etapa, subetapa, tempo_decorrido, current_seg=None, total_seg=None):
    bar_length = 40
    filled_len = int(bar_length * progress / 100)
    bar = '█' * filled_len + '░' * (bar_length - filled_len)
    job_id_display = (job_id[:30] + '..') if len(job_id) > 32 else job_id
    etapa_display = (etapa[:35] + '..') if len(etapa) > 37 else etapa
    subetapa_display = (subetapa[:40] + '..') if subetapa and len(subetapa) > 42 else (subetapa or "")
    seg_display = f"[{current_seg:03d}/{total_seg:03d}]" if current_seg and total_seg else ""
    progress_line = f" Job: {job_id_display} | {bar} {progress:.1f}% {seg_display} | {etapa_display} | {subetapa_display} | Tempo: {tempo_decorrido}"
    
    # [v2026.UTF8_FIX] Garante que acentos não quebrem o terminal Windows
    try:
        sys.stdout.write(f"\r{progress_line.ljust(150)}")
        sys.stdout.flush()
    except UnicodeEncodeError:
        # Fallback para terminais sem suporte total a UTF-8 (CP850/ASCII)
        safe_line = progress_line.encode('ascii', 'replace').decode('ascii')
        sys.stdout.write(f"\r{safe_line.ljust(150)}")
        sys.stdout.flush()

_last_progress_info = {}

def set_progress(job_id, progress, etapa_idx, start_time, etapas_list, subetapa=None, tool_name=None, current_seg=None, total_seg=None, **kwargs):
    # Injeta automaticamente no título da janela do Windows
    if current_seg and total_seg:
        os.system(f"title NEXUS AI - {progress:.1f}% [{current_seg}/{total_seg}] - {subetapa or ''}")
    # [v2026.MEGA_SYNC_OPTIMIZED] Sincronização Inteligente (Alta Resolução)
    import time
    now = time.time()
    last_info = _last_progress_info.get(job_id, {})
    last_time = last_info.get('time', 0)
    last_subetapa = last_info.get('subetapa', "")
    
    # [v2026.ULTRA_RESPONSE] 
    # Força atualização se: 
    # 1. Subetapa mudou (ex: novo arquivo sendo processado)
    # 2. Passaram 2 segundos (Resolução aumentada de 10s para 2s)
    # 3. É a conclusão (100%)
    force_update = (subetapa != last_subetapa) or (progress >= 100)
    
    etapa_atual = etapas_list[etapa_idx] if etapa_idx < len(etapas_list) else "Desconhecida"
    elapsed_time = now - start_time
    tempo_str = str(timedelta(seconds=int(elapsed_time)))

    if progress < 100 and (now - last_time < 2) and not force_update:
        # Apenas imprime no CMD para feedback visual instantâneo local
        _print_progress_to_cmd(job_id, progress, etapa_atual, subetapa, tempo_str, current_seg, total_seg)
        return

    _last_progress_info[job_id] = {'time': now, 'subetapa': subetapa}
    with progress_lock:
        elapsed_time = now - start_time
        tempo_str = str(timedelta(seconds=int(elapsed_time)))
        progress_info = {
            'progress': round(progress, 2), 
            'etapa': etapa_atual, 
            'subetapa': subetapa, 
            'tempo_decorrido': tempo_str,
            'current_seg': current_seg,
            'total_seg': total_seg,
            'last_update': now,
            'start_time': start_time,
            'total_elapsed_secs': elapsed_time,
            'tool_name': tool_name
        }
        progress_info.update(kwargs)
        
        # [v12.72] Persistência em Disco para o Dashboard (Multi-Engine Path Fix)
        # Tenta encontrar o arquivo de status tanto na estrutura de Vídeo quanto na de Jogos
        status_path_video = Path(f"c:/IA_dublagem/uploads/{job_id}/job_status.json")
        status_path_games = Path(f"c:/IA_dublagem/jobs/{job_id}/job_status.json")
        
        status_path = None
        if status_path_video.exists(): status_path = status_path_video
        elif status_path_games.exists(): status_path = status_path_games
        
        if status_path:
            try:
                sdata = safe_json_read(status_path) or {}
                sdata['progress'] = progress_info['progress']
                sdata['etapa'] = progress_info['etapa']
                sdata['subetapa'] = progress_info['subetapa']
                sdata['current_seg'] = current_seg
                sdata['total_seg'] = total_seg
                sdata['total_elapsed_secs'] = elapsed_time
                # [v2026.TIMER] Adiciona o tempo formatado para o relógio da UI
                sdata['tempo_decorrido'] = str(timedelta(seconds=int(elapsed_time)))
                sdata['tool_name'] = tool_name
                
                # --- [TELEMETRIA DE PERFORMANCE] ---
                if 'metrics' not in sdata:
                    sdata['metrics'] = {
                        'stages_duration_secs': {},
                        'vram_peak_mb': {},
                        'cache_hit_rate': {},
                        'stages_start_times': {}
                    }
                elif 'stages_start_times' not in sdata['metrics']:
                    sdata['metrics']['stages_start_times'] = {}
                
                now_ts = time.time()
                old_etapa = sdata.get('etapa')
                
                # Inicializa a etapa atual nas métricas se necessário
                if etapa_atual not in sdata['metrics']['stages_start_times']:
                    sdata['metrics']['stages_start_times'][etapa_atual] = now_ts
                    # Se mudou de etapa, reseta o pico de VRAM do PyTorch para a nova etapa
                    if old_etapa and old_etapa != etapa_atual:
                        try:
                            import torch
                            if torch.cuda.is_available():
                                torch.cuda.reset_peak_memory_stats(0)
                        except: pass
                
                # Atualiza a duração da etapa atual
                start_t = sdata['metrics']['stages_start_times'][etapa_atual]
                sdata['metrics']['stages_duration_secs'][etapa_atual] = round(now_ts - start_t, 2)
                
                # Se mudou de etapa, finaliza o cálculo da etapa anterior
                if old_etapa and old_etapa != etapa_atual and old_etapa in sdata['metrics']['stages_start_times']:
                    old_start = sdata['metrics']['stages_start_times'][old_etapa]
                    sdata['metrics']['stages_duration_secs'][old_etapa] = round(now_ts - old_start, 2)
                
                # Captura pico de VRAM da GPU para a etapa atual
                try:
                    import torch
                    if torch.cuda.is_available():
                        peak_bytes = torch.cuda.max_memory_allocated(0)
                        peak_mb = int(peak_bytes / (1024 * 1024))
                        sdata['metrics']['vram_peak_mb'][etapa_atual] = peak_mb
                except: pass
                
                # Atualiza taxas de cache hit vindas do pipeline
                if 'translation_cache_hit' in kwargs:
                    sdata['metrics'].setdefault('cache_hit_rate', {})['traducao'] = round(kwargs['translation_cache_hit'], 2)
                if 'audio_cache_hit' in kwargs:
                    sdata['metrics'].setdefault('cache_hit_rate', {})['dublagem_tts'] = round(kwargs['audio_cache_hit'], 2)
                # ------------------------------------
                
                safe_json_write(sdata, status_path)
            except: pass
        
        # [v2026.SMART_TELEMETRY] Equilíbrio entre Performance e Visibilidade
        if progress < 100:
            current_time = time.time()
            last_p = getattr(set_progress, "last_p", -1)
            last_t = getattr(set_progress, "last_t", 0)
            
            # Condições para logar: Mudança de %, Mudança de Etapa ou 10 segundos de silêncio
            if int(progress) != last_p or (current_time - last_t) >= 10:
                logging.info(f"➔ [{progress:.1f}%] {etapa_atual} | {subetapa or 'Processando'}")
                set_progress.last_p = int(progress)
                set_progress.last_t = current_time

        progress_dict[job_id] = progress_info

    _print_progress_to_cmd(job_id, progress, etapa_atual, subetapa, tempo_str, current_seg, total_seg)
    
    if progress >= 100 and (etapa_idx == len(etapas_list) - 1):
        sys.stdout.write("\n")
        logging.info(f"Processo {job_id} concluído!")
        status_path = Path(app.config['UPLOAD_FOLDER']) / job_id / "job_status.json"
        status_data = safe_json_read(status_path) or {}
        status_data.update(progress_info)
        status_data['status'] = 'processing' if etapa_idx < len(etapas_list) - 1 else 'completed'
        safe_json_write(status_data, status_path)

def get_optimal_device():
    """
    Detecta o melhor hardware disponível (Adaptativo v12.7).
    [v12.7] Adicionada verificação rigorosa de device_count preventivamente para evitar
    o erro 'Attempting to deserialize object on CUDA device 0 but torch.cuda.device_count() is 0'.
    """
    import torch
    
    # Se PyTorch achar que tem CUDA, mas a contagem for 0, os drivers estão quebrados/incompatíveis.
    if torch.cuda.is_available() and torch.cuda.device_count() > 0:
        try:
            device_idx = torch.cuda.current_device()
            vram = torch.cuda.get_device_properties(device_idx).total_memory / (1024**3)
            if vram >= 3.5:
                # [v12.75] REQUISITO SPEECHBRAIN: Retornar dispositivo indexado (ex: cuda:0)
                logging.info(f"🚀 [HARDWARE] Placa NVIDIA detectada ({vram:.1f}GB VRAM). Ativando GPU!")
                return f"cuda:{device_idx}"
            else:
                logging.info(f"🐢 [HARDWARE] GPU detectada, mas é fraca ({vram:.1f}GB VRAM). Usando CPU.")
        except Exception as e:
            logging.warning(f"⚠️ Erro ao detectar VRAM ({e}). Drivers possivelmente corrompidos. Forçando CPU.")
    else:
        logging.info("💻 [HARDWARE] Nenhuma GPU válida detectada ou driver corrompido (count=0). Usando CPU.")
    return "cpu"

def get_whisper_model():
    global whisper_model
    with model_lock:
        if whisper_model is None:
            import torch
            from faster_whisper import WhisperModel
            
            device = get_optimal_device()
            import os
            total_threads = os.cpu_count() or 4
            
            if device.startswith("cuda"):
                logging.info(f"🚀 [HARDWARE] Whisper em CUDA (int8_float16) - MODO ULTRA: {total_threads} threads.")
                whisper_model = WhisperModel("small", device="cuda", compute_type="int8_float16", cpu_threads=total_threads)
            else:
                logging.info(f"💻 [HARDWARE] Whisper em CPU (int8) - MODO TOTAL: {total_threads} threads.")
                whisper_model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=total_threads)
                
            logging.info("Modelo faster-whisper carregado.")
    return whisper_model

def unload_whisper_model():
    global whisper_model
    with model_lock:
        if whisper_model is not None:
            logging.info("🧹 [VRAM_PURGE] Expulsando Whisper da GPU...")
            try:
                del whisper_model
                whisper_model = None
                import gc
                import torch
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
                    torch.cuda.synchronize()
                logging.info("✅ [VRAM_PURGE] Whisper descarregado com sucesso.")
            except Exception as e:
                logging.warning(f"⚠️ Falha na limpeza do Whisper: {e}")

# O motor ONNX foi removido para priorizar a qualidade de estúdio do modelo oficial.


def get_vram_usage():
    """Retorna o uso atual de VRAM em GB"""
    import torch
    if not torch.cuda.is_available(): return 0.0
    free_m, total_m = torch.cuda.mem_get_info()
    return (total_m - free_m) / (1024**3)

def ensure_vram_safety(label="Processo"):
    """[v2026.GUARD] Trava Real: Impede o avanço se a VRAM exceder 5.0GB"""
    import torch
    import time
    
    max_safe_gb = 5.0
    for attempt in range(5):
        used_gb = get_vram_usage()
        if used_gb <= max_safe_gb:
            return True
            
        logging.warning(f"⚠️ [GUARDIÃO VRAM] {label} bloqueado! Uso atual: {used_gb:.1f}GB. Limite: {max_safe_gb}GB.")
        unload_whisper_model()
        # [v20.2] Limpeza Profunda
        import gc; gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        time.sleep(2)
        
    final_usage = get_vram_usage()
    if final_usage > max_safe_gb:
        logging.error(f"❌ [ERRO CRÍTICO] VRAM Insuficiente ({final_usage:.1f}GB). Reduza o peso dos modelos ou feche outros apps.")
        return False
    return True

def get_optimal_device():
    import logging
    import torch
    
    # [v2026.RTX_ONLY] Prioridade Máxima e Obrigatória: NVIDIA (CUDA)
    if torch.cuda.is_available() and torch.cuda.device_count() > 0:
        device_idx = torch.cuda.current_device()
        logging.info(f"🚀 [RTX_LOCKED] Hardware Identificado. Usando CUDA:{device_idx} (RTX 3050).")
        return f"cuda:{device_idx}"

    # Fallback apenas se a placa física NÃO existir no sistema
    logging.info("💻 [MODO CPU] Usando processador apenas para infraestrutura (NVIDIA não detectada).")
    return "cpu"

# ==============================================================================
# MOTOR TITAN QWEN3-TTS (v2026.RTX_ULTRA)
# ==============================================================================

_QWEN3_INSTANCE = None

def get_qwen3_engine():
    """Inicializa o motor Qwen3-TTS otimizado para RTX 3050 com cache local."""
    global _QWEN3_INSTANCE
    with model_lock:
        if _QWEN3_INSTANCE is None:
            try:
                import torch
                from qwen_tts import Qwen3TTSModel
                from huggingface_hub import snapshot_download
                import os
                
                # [v2026.CPU_BALANCE] Limita threads internas de forma segura
                try:
                    torch.set_num_threads(1)
                except:
                    pass
                
                device = "cuda:0" if torch.cuda.is_available() else "cpu"
                # [v2026.ULTRA_SPEED] Usando a versão de 0.6B para velocidade máxima
                model_dir = "c:/IA_dublagem/_MODELS_/qwen3_0.6b"
                if not os.path.exists(os.path.join(model_dir, "model.safetensors")):
                    logging.info("⏳ Modelo Qwen3-0.6B (Ultra Rápido) não encontrado. Iniciando download (aprox. 1.2GB)...")
                    snapshot_download(
                        repo_id="Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                        local_dir=model_dir,
                        local_dir_use_symlinks=False
                    )
                    logging.info("✅ Download concluído! O motor Qwen3-0.6B agora é 100% local.")

                logging.info(f"🎙️ [NEXUS_VOICE] Despertando Qwen3-TTS em: {device}")
                
                # [v2026.GPU_JUICE] Espremendo a RTX 3050 ao máximo
                torch.cuda.set_device(0)
                dtype = torch.bfloat16 # Precisão nativa da arquitetura Ampere (RTX 30)
                
                # Inicializa o modelo com Turbo SDPA + GPU-First
                try:
                    # [v2026.CPU_IDLE] Processador em repouso, Placa em ação
                    try:
                        import psutil
                        p = psutil.Process(os.getpid())
                        p.nice(psutil.HIGH_PRIORITY_CLASS)
                    except:
                        pass

                    logging.info("🚀 [NEXUS_VOICE] SQUEEZE MODE: FasterQwen3TTS (CUDA Graphs) + BFloat16 Ampere...")
                    from faster_qwen3_tts import FasterQwen3TTS
                    _QWEN3_INSTANCE = FasterQwen3TTS.from_pretrained(
                        model_name=model_dir, 
                        device="cuda", 
                        dtype=dtype,
                        attn_implementation="sdpa",
                        max_seq_len=2048 # Otimizado para diálogos longos
                    )
                except Exception as turbo_err:
                    logging.warning(f"⚠️ [NEXUS_VOICE] Falha no Turbo Faster: {turbo_err}. Usando Modo Seguro...")
                    from qwen_tts import Qwen3TTSModel
                    _QWEN3_INSTANCE = Qwen3TTSModel.from_pretrained(
                        model_dir, 
                        device_map="cuda:0",
                        dtype=dtype,
                        attn_implementation="sdpa"
                    )
                
                logging.info("✅ [NEXUS_VOICE] Qwen3-TTS carregado com sucesso.")
            except Exception as e:
                import traceback
                logging.error(f"❌ Erro ao carregar Qwen3-TTS: {e}\n{traceback.format_exc()}")
                return None
    return _QWEN3_INSTANCE

def unload_qwen3_model():
    """Libera a VRAM ocupada pelo Qwen3 agressivamente."""
    global _QWEN3_INSTANCE
    with model_lock:
        if _QWEN3_INSTANCE is not None:
            logging.info("🧹 [VRAM_PURGE] Removendo Qwen3-TTS da GPU...")
            try:
                del _QWEN3_INSTANCE
                _QWEN3_INSTANCE = None
                import gc, torch
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                logging.info("✅ [VRAM_PURGE] Qwen3 descarregado.")
            except Exception as e:
                logging.warning(f"⚠️ Falha na limpeza do Qwen3: {e}")

# Cache global para DNA Vocal (Speaker Embeddings)
_VOICE_PROMPT_CACHE = {}

def gerar_audio_qwen3(text, ref_audio_path, output_path, language="Portuguese", emotion="NORMAL", max_duration=None):
    """Gera áudio usando clonagem de voz via FasterQwen3TTS + Emoções (Instruct) com blindagem ativa de duração."""
    engine = get_qwen3_engine()
    if not engine:
        logging.error("❌ Motor Qwen3 não disponível para geração.")
        return False
    
    global _VOICE_PROMPT_CACHE
    
    # [v2026.ACTING_MAP] Mapeia as emoções do Gemma para instruções do Qwen3
    # O Qwen3 entende melhor instruções em inglês
    EMOTION_MAP = {
        "RAIVA": "Angry, aggressive and loud",
        "TRISTE": "Sad, crying tone and low volume",
        "FELIZ": "Happy, energetic and smiling voice",
        "URGENTE": "Fast, anxious and breathless",
        "SUSPENSE": "Whispering, mysterious and low voice",
        "DRAMATICO": "Dramatic, emotional and intense",
        "NORMAL": ""
    }
    instruction = EMOTION_MAP.get(emotion.upper(), "")
    
    # [v2026.CODE_SWITCH_ENGINE] Se o texto contém aspas (injetadas pelo Gemma), 
    # força o motor a usar a fonética nativa americana nessas palavras.
    if "'" in text or '"' in text:
        accent_instr = "pronounce words inside quotes with a native American accent"
        instruction = f"{instruction}, and {accent_instr}" if instruction else accent_instr
    
    try:
        voice_key = hashlib.md5(ref_audio_path.encode()).hexdigest()
        
        if voice_key not in _VOICE_PROMPT_CACHE:
            logging.info(f"🧬 [DNA_VOCAL] Mapeando voz para FasterQwen: {os.path.basename(ref_audio_path)}...")
            logging.info("🔬 [X_VECTOR] O modo ICL requer biblioteca 'k2' (incompatível com Windows). Forçando X-Vector Seguro.")
            
            _VOICE_PROMPT_CACHE[voice_key] = engine.model.create_voice_clone_prompt(
                ref_audio=ref_audio_path,
                ref_text="",
                x_vector_only_mode=True
            )
        
        # [v2026.COMMA_FILTER] Remove vírgulas internas que adicionam pausas artificiais pesadas e quebram a sincronia!
        clean_text = text.replace(",", " ")
        clean_text = " ".join(clean_text.split()).strip()
        
        # [v2026.ACTING_PUNCTUATION] Mantém a pontuação final e adiciona respiro
        if not clean_text.endswith(('.', '!', '?')):
            clean_text += "."
        clean_text += " " 
        
        # [v2026.QWEN_TEMP_SHIELD] Temperatura dinâmica:
        # Frases curtas alucinam fácil em temp=0.7. Baixamos para 0.30 para estabilidade absoluta!
        temp_to_use = 0.30 if max_duration and max_duration < 4.0 else 0.50
        top_p_to_use = 0.70 if max_duration and max_duration < 4.0 else 0.80
        top_k_to_use = 20 if max_duration and max_duration < 4.0 else 40
        
        # [v2026.QWEN_TOKEN_GUARD] Limitador físico de tokens por tempo de cena.
        # O Qwen3-TTS opera nativamente a 12Hz (12 tokens = 1 segundo de áudio).
        # Definimos uma margem segura de 18 tokens por segundo.
        if max_duration:
            safe_sec = max(4.0, max_duration * 2.2)
        else:
            safe_sec = max(4.0, len(clean_text) / 8.0)
        max_tokens_to_gen = int(safe_sec * 18)
        
        # Blindagem de duração estrita
        limit_duration = max(6.0, max_duration * 2.5) if max_duration else None
        
        # Tentativa 1: Geração Padrão Estabilizada com Parâmetros Avançados (Zero-Slicing, Full Prefill)
        wavs, sr = engine.generate_voice_clone(
            text=clean_text,
            language=language,
            voice_clone_prompt=_VOICE_PROMPT_CACHE[voice_key],
            xvec_only=True,
            temperature=temp_to_use,
            top_k=top_k_to_use, # Foca o vocabulário, bloqueando silêncios/estalos de preenchimento
            top_p=top_p_to_use,
            repetition_penalty=1.20, # Penalidade ideal contra repetições sem robotizar
            max_new_tokens=max_tokens_to_gen, # Limita fisicamente a alucinação
            append_silence=False, # Impede o Qwen3 de adicionar silêncio artificial no fim
            non_streaming_mode=True, # Prefill do texto completo para evitar pausas/gargalos entre palavras
            instruct=instruction
        )
        
        # [v2026.HALLUCINATION_GATE] Detecta loops infinitos ou áudios gigantes
        if wavs is not None and len(wavs) > 0:
            audio_data = wavs[0]
            gen_dur = len(audio_data) / sr
            
            if limit_duration and gen_dur > limit_duration:
                logging.warning(f"⚠️ [QWEN3_GUARD] Áudio gigante detectado ({gen_dur:.1f}s vs limite {limit_duration:.1f}s). Regenerando em modo ultra-estável...")
                
                # Tentativa 2: Regeneração ultra-determinística para forçar encerramento limpo
                wavs, sr = engine.generate_voice_clone(
                    text=clean_text,
                    language=language,
                    voice_clone_prompt=_VOICE_PROMPT_CACHE[voice_key],
                    xvec_only=True,
                    temperature=0.05,
                    top_k=5,
                    top_p=0.3,
                    repetition_penalty=1.35,
                    max_new_tokens=max_tokens_to_gen,
                    append_silence=False,
                    non_streaming_mode=True,
                    instruct=instruction
                )
                
                if wavs is not None and len(wavs) > 0:
                    audio_data = wavs[0]
                    gen_dur = len(audio_data) / sr
                    logging.info(f"✅ [QWEN3_GUARD] Regeneração estável concluída ({gen_dur:.1f}s).")
                    
                    # Corta se mesmo assim o modelo persistir (truncamento físico seguro)
                    if gen_dur > limit_duration:
                        logging.warning(f"✂️ [QWEN3_GUARD] Áudio ainda excede o limite. Truncando fisicamente para {limit_duration:.1f}s.")
                        max_samples = int(limit_duration * sr)
                        audio_data = audio_data[:max_samples]
        
        if wavs is not None and len(wavs) > 0:
            import numpy as np
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                # [v2026.AUDIO_NORM] Normaliza matematicamente a amplitude do sinal, preservando 100% da dinâmica da voz
                audio_data = (audio_data / max_val) * 0.95
                
            sf.write(output_path, audio_data, sr)
            return True
        return False
    except Exception as e:
        import traceback
        logging.error(f"❌ Erro na geração Qwen3: {e}\n{traceback.format_exc()}")
        return False

def gerar_audio_batch_qwen3(batch_items, ref_audio_path, language="Portuguese"):
    """
    Gera um lote (batch) de áudios de uma vez para máxima performance.
    batch_items: Lista de dicionários {'text': str, 'output_path': str}
    """
    engine = get_qwen3_engine()
    if not engine or not batch_items:
        return False
    
    global _VOICE_PROMPT_CACHE
    
    try:
        # [v2026.DNA_CACHE] Reutiliza o DNA da voz para o lote todo
        voice_key = hashlib.md5(ref_audio_path.encode()).hexdigest()
        if voice_key not in _VOICE_PROMPT_CACHE:
            _VOICE_PROMPT_CACHE[voice_key] = engine.model.create_voice_clone_prompt(
                ref_audio=ref_audio_path, ref_text="", x_vector_only_mode=True
            )
        
        # Prepara a lista de textos com o "respiro" final
        texts = []
        for item in batch_items:
            t = item['text'].strip()
            if not t.endswith(('.', '!', '?', ',')): t += "."
            texts.append(t + " ")
            
        # [v2026.MEGA_SQUEEZE] Chamada em Lote (Batch)
        # A placa de vídeo processa todos os textos em paralelo!
        wav_list, sr = engine.generate_voice_clone(
            text=texts,
            language=language,
            voice_clone_prompt=_VOICE_PROMPT_CACHE[voice_key],
            xvec_only=True
        )
        
        # Salva os arquivos resultantes
        success_count = 0
        for i, wav in enumerate(wav_list):
            if wav is not None and len(wav) > 0:
                sf.write(batch_items[i]['output_path'], wav, sr)
                success_count += 1
        
        return success_count == len(batch_items)
        
    except Exception as e:
        logging.error(f"❌ Erro no Batch Qwen3: {e}")
        return False

def transcribe_audio(model, audio_path, source_lang='auto'):
    # [CPU OPTIMIZATION] beam_size=1 (Greedy Search) é 3x mais rápido que o padrão (5).
    # condition_on_previous_text=False previne alucinações e loops.
    # [v2026.i5_TURBO] beam_size=1 é 3x-5x mais rápido no i5-6400
    whisper_lang = source_lang if source_lang != 'auto' else None
    
    # [v2026.HALFIX] Silero VAD para ignorar silêncio e gritos/grunhidos de ação pura
    segments_generator, info = model.transcribe(
        audio_path, 
        beam_size=1, 
        condition_on_previous_text=False, 
        language=whisper_lang,
        vad_filter=True
    )
    return {
        "text": "".join(s.text for s in segments_generator).strip(),
        "detected_language": getattr(info, 'language', None)
    }

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
        # Executa o filtro volumedetect para encontrar o pico máximo
        # [CPU THOTTLE] Limita threads
        threads = str(max(1, (os.cpu_count() or 4) // 2))
        cmd = ['ffmpeg', '-threads', threads, '-i', str(file_path), '-af', 'volumedetect', '-vn', '-sn', '-dn', '-f', 'null', 'NUL']
        result = subprocess.run(cmd, capture_output=True, text=True)
        # A saída do volumedetect vai para stderr
        output = result.stderr
        
        # Procura por "max_volume: -XX.X dB"
        match = re.search(r"max_volume:\s*(-?[\d\.]+)\s*dB", output)
        if match:
            return float(match.group(1))
        return None
    except Exception as e:
        logging.error(f"Erro ao detectar pico de áudio em {file_path}: {e}")
        return None

def find_existing_project(files_hash):
    upload_folder = Path(app.config['UPLOAD_FOLDER'])
    for job_dir in upload_folder.iterdir():
        if job_dir.is_dir() and job_dir.name.startswith("job_jogos_"):
            status_file = job_dir / "job_status.json"
            if (status_data := safe_json_read(status_file)) and status_data.get('files_hash') == files_hash:
                logging.info(f"Projeto existente encontrado com o mesmo hash: {job_dir.name}")
                return job_dir.name
    return None

def find_best_audio_profile(audio_data, job_dir):
    temp_dir = job_dir / "_temp_detection"
    temp_dir.mkdir(exist_ok=True)
    output_path = temp_dir / "test.wav"
    
    profiles = [
        {'name': 'native_wav'}, # [v10.84] FIX: Tenta detectar como WAV normal PRIMEIRO, sem forçar taxa de amostragem
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
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.decode('utf-8', errors='ignore') if e.stderr else 'Nenhum erro reportado.'
            logging.warning(f"Perfil {profile['name']} falhou: {error_message}")
            continue
            
    shutil.rmtree(temp_dir)
    return None

def wait_for_diarization_manual(job_id, cb):
    source_dir = Path(app.config['UPLOAD_FOLDER']) / job_id / "_1_MOVER_OS_FICHEIROS_DAQUI"
    if not any(source_dir.iterdir()):
        logging.info("Nenhum arquivo para diarização manual.")
        return
        
    total_files_in_subdirs = len(list(source_dir.rglob("*.wav")))
    if total_files_in_subdirs == 0:
        logging.info("Nenhum arquivo para diarização manual.")
        return

    while True:
        num_files_remaining = len(list(source_dir.rglob("*.wav")))
        if num_files_remaining == 0:
            logging.info(f">>> Diarização manual para o job '{job_id}' concluída. Retomando pipeline. <<<")
            cb(100, 1, "Diarização manual concluída.")
            break
        else:
            msg = f"Arquivos longos foram separados. Organize todos os {num_files_remaining} segmentos/arquivos."
            sys.stdout.write(f"\r{''.ljust(150)}\r") 
            logging.warning(f">>> PAUSA: {msg} <<<")
            progress = ((total_files_in_subdirs - num_files_remaining) / total_files_in_subdirs) * 100 if total_files_in_subdirs > 0 else 0
            cb(progress, 1, msg)
            time.sleep(5)


def run_auto_diarization_batch(job_dir, job_id, cb):
    """
    Diarização Automática para Lotes de Arquivos (Jogos).
    Analisa cada arquivo como um segmento único e agrupa por voz.
    Suporta:
    1. Num Speakers Fixo (Clustering)
    2. Num Speakers == 1 (Bypass)
    3. Auto (VoiceGuard)
    """
    # [CACHE] Define pastas
    # [SAFEGUARD] A pasta abaixo é READ-ONLY. O sistema NUNCA deve apagar arquivos dela.
    # O usuário exigiu preservação total dos originais em "_1_MOVER_OS_FICHEIROS_DAQUI".
    source_dir = job_dir / "_1_MOVER_OS_FICHEIROS_DAQUI"
    clean_audio_dir = job_dir / "_1b_AUDIO_LIMPO"
    segmented_dir = job_dir / "_1c_AUDIO_SEGMENTADO" # [FIX] Definido explicitamente
    backup_dir = job_dir / "_backup_transcricao"     # [FIX] Definido explicitamente
    target_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
    
    # [FIX] Pular diarização inteira se já foi feita (Resumo do Projeto)
    marker_path = target_dir / "unification_done.marker"
    project_data_path = job_dir / "project_data.json"
    if marker_path.exists() and project_data_path.exists():
        logging.info("Diarização e unificação já concluídas neste projeto. Pulando Fase 1 inteira para acelerar o reinício.")
        cb(100, 1, "Diarização restaurada do cache.")
        return

    # Cria diretórios de trabalho
    clean_audio_dir.mkdir(parents=True, exist_ok=True)
    segmented_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    # [FEATURE] OpenUnmix: Verifica se deve separar fundo
    status_path = job_dir / "job_status.json"
    status_data = safe_json_read(status_path) or {}
    use_openunmix = str(status_data.get('preserve_background', 'false')).lower() == 'true'

    if use_openunmix:
        logging.info("[OPENUNMIX] Separação de Fundo ATIVADA. Iniciando...")
        run_openunmix_batch(source_dir, job_dir, cb)
        
        # Atualiza a fonte para a pasta de vocais isolados (assim o DeepFilter limpa só a voz)
        source_dir = job_dir / "_0a_SEPARACAO_VOCAL"
        logging.info(f"[OPENUNMIX] Fonte de áudio alterada para: {source_dir}")

    # 1. LIMPEZA DE ÁUDIO
    source_files = list(source_dir.rglob("*.wav"))
    if not source_files:
        logging.info("Nenhum arquivo para processar.")
        return

    run_batch_cleaning(source_dir, clean_audio_dir, cb)
    
    clean_files = sorted(list(clean_audio_dir.rglob("*.wav")))
    if not clean_files:
         clean_files = source_files # Fallback

    status_path = job_dir / "job_status.json"
    status_data = safe_json_read(status_path) or {}
    try:
        num_speakers = int(status_data.get('num_speakers', '0'))
    except: num_speakers = 0
    source_lang = status_data.get('source_language', 'auto') # [v10.99] Recomendado 'auto' para jogos multi-idioma (COD, etc)

    # 2. TRANSCRIÇÃO & SEGMENTAÇÃO (Phase 1)
    # Gera arquivos em _1c_AUDIO_SEGMENTADO e JSONs em _backup_transcricao
    cb(0, 1, "Fase 1: Transcrição e Segmentação...")
    
    import threading
    from concurrent.futures import ThreadPoolExecutor
    
    progress_lock = threading.Lock()
    completed_count = 0
    total_files = len(clean_files)
    
    # Pré-carrega o modelo Whisper de forma síncrona para inicialização limpa na GPU
    whisper_model = get_whisper_model()
    whisper_lang = source_lang if source_lang != 'auto' else None
    
    def worker_transcribe(audio_file):
        nonlocal completed_count
        try:
            duration = get_audio_duration(audio_file)
            should_split = duration > 25.0 and num_speakers != 1
            
            if not should_split:
                # Caso simples: Copia inteiro (Preserva arquivo original)
                dest_wav = segmented_dir / audio_file.name
                dest_json = backup_dir / f"{audio_file.stem}.json"
                
                if not (dest_wav.exists() and dest_json.exists()):
                    shutil.copy(str(audio_file), str(dest_wav))
                    
                    # Transcreve (com VAD ativo para evitar alucinações em silêncio)
                    segments, info = whisper_model.transcribe(str(dest_wav), beam_size=1, word_timestamps=False, language=whisper_lang, vad_filter=True)
                    text = "".join([s.text for s in list(segments)]).strip()
                    
                    safe_json_write({
                        "id": audio_file.stem,
                        "original_text": text,
                        "duration": duration,
                        "source_file": str(dest_wav),
                        "detected_language": getattr(info, 'language', None)
                    }, dest_json)
            else:
                # Caso complexo: Whisper Split
                related_jsons = list(backup_dir.glob(f"{audio_file.stem}_seg*.json"))
                if not related_jsons:
                    segments, info = whisper_model.transcribe(str(audio_file), beam_size=1, word_timestamps=False, language=whisper_lang, vad_filter=True)
                    segments = list(segments)
                    detected_lang = getattr(info, 'language', None)
                    
                    if segments:
                        from pydub import AudioSegment
                        audio_seg = AudioSegment.from_wav(str(audio_file))
                        grouped_chunks = []
                        current_group_start = -1
                        current_group_end = -1
                        
                        for seg in segments:
                            start_ms = max(0, int(seg.start * 1000) - 50)
                            end_ms = min(len(audio_seg), int(seg.end * 1000) + 50)
                            
                            if (end_ms - start_ms) < 200: continue
                            
                            if current_group_start == -1:
                                current_group_start = start_ms
                                current_group_end = end_ms
                            else:
                                proposed_duration = (end_ms - current_group_start) / 1000.0
                                if proposed_duration <= 25.0:
                                    current_group_end = end_ms
                                else:
                                    grouped_chunks.append((current_group_start, current_group_end))
                                    current_group_start = start_ms
                                    current_group_end = end_ms
                                    
                        if current_group_start != -1:
                            grouped_chunks.append((current_group_start, current_group_end))
                            
                        for idx, (g_start, g_end) in enumerate(grouped_chunks):
                            chunk = audio_seg[g_start:g_end]
                            chunk_name = f"{audio_file.stem}_seg{idx:03d}_{int(g_start/1000)}s.wav"
                            chunk_path = segmented_dir / chunk_name
                            chunk.export(chunk_path, format="wav")
                            
                            json_path = backup_dir / f"{chunk_path.stem}.json"
                            try:
                                c_segments, _ = whisper_model.transcribe(str(chunk_path), beam_size=1, word_timestamps=False, language=whisper_lang, vad_filter=True)
                                chunk_text = "".join([s.text for s in list(c_segments)]).strip()
                            except:
                                chunk_text = ""
                                
                            safe_json_write({
                                "id": chunk_path.stem,
                                "original_text": chunk_text,
                                "duration": len(chunk) / 1000.0,
                                "source_file": str(chunk_path),
                                "detected_language": detected_lang
                            }, json_path)
            
            with progress_lock:
                completed_count += 1
                cb((completed_count / total_files) * 40, 1, f"Transcrevendo [{completed_count}/{total_files}]: {audio_file.name}", current_seg=completed_count, total_seg=total_files)
        except Exception as e:
            logging.error(f"Erro ao processar {audio_file.name}: {e}")
            with progress_lock:
                completed_count += 1
                cb((completed_count / total_files) * 40, 1, f"Falha [{completed_count}/{total_files}]: {audio_file.name}", current_seg=completed_count, total_seg=total_files)
                
    # Executa a transcrição paralela com pool de 4 threads (Consumo ideal de VRAM para RTX 3050 6GB)
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(worker_transcribe, clean_files)
        
    # Purga da GPU e Coleta de Lixo real do Whisper
    unload_whisper_model()

    # 3. DIARIZAÇÃO & CLUSTERING (Phase 2)
    cb(40, 1, "Fase 2: Diarização Global...")
    
    diarizer = SimpleDiarizer()
    all_segments = sorted(list(segmented_dir.glob("*.wav")))
    
    if not all_segments:
        logging.warning("Fase 2 abortada: Nenhum segmento para diarizar.")
        return

    embeddings_map = {}
    
    # Gera Embeddings
    for i, seg_path in enumerate(all_segments):
        cb(40 + (i / len(all_segments)) * 30, 1, f"Analisando voz: {seg_path.name}", current_seg=i+1, total_seg=len(all_segments))
        emb = diarizer.get_file_embedding(str(seg_path))
        if emb is not None:
             embeddings_map[seg_path.name] = emb
             
    # Clusteriza
    cb(70, 1, "Agrupando Falantes...")
    if num_speakers == 1:
        file_to_voice = {f.name: 'voz1' for f in all_segments}
    else:
        n_clusters = num_speakers if num_speakers > 1 else None
        file_to_voice = diarizer.cluster_batch_embeddings(embeddings_map, n_clusters)
        
    # Move para Pastas Finais
    cb(80, 1, "Organizando pastas...")
    
    for seg_path in all_segments:
        fname = seg_path.name
        voice_id = file_to_voice.get(fname, "voz_desconhecida")
        
        # Destino
        voice_folder = target_dir / voice_id
        voice_folder.mkdir(parents=True, exist_ok=True)
        final_path = voice_folder / fname
        
        if not final_path.exists():
            shutil.copy(str(seg_path), str(final_path))
            
            
    cb(90, 1, "Finalizando: Gerando metadados do projeto...")
    
    # 4. RECONSTRUÇÃO DO PROJECT_DATA.JSON
    # Cruza os arquivos organizados nas pastas de voz com os backups de texto
    final_project_data = []
    
    # Garante que target_dir existe
    if target_dir.exists():
        for voice_folder in target_dir.iterdir():
            if not voice_folder.is_dir(): continue
            speaker_id = voice_folder.name
            
            for wav_path in voice_folder.glob("*.wav"):
                if wav_path.name.startswith("_REF_"): continue
                # Busca JSON de backup pelo nome do arquivo (stem igual)
                json_backup_path = backup_dir / f"{wav_path.stem}.json"
                
                original_text = ""
                duration = 0.0
                
                if json_backup_path.exists():
                    try:
                        meta = safe_json_read(json_backup_path)
                        original_text = meta.get('original_text', '')
                        duration = meta.get('duration', 0.0)
                    except: pass
                else:
                    # Fallback
                    try: duration = get_audio_duration(wav_path)
                    except: pass
                
                final_project_data.append({
                    "id": wav_path.stem,
                    "file_name": wav_path.name,
                    "original_text": original_text,
                    "translated_text": "",
                    "speaker": speaker_id,
                    "start_time": 0,
                    "end_time": duration,
                    "duration": duration,
                    "file_path": str(wav_path),
                    "status": "pending_translation" 
                })
    
    # Salva
    safe_json_write(final_project_data, job_dir / "project_data.json")
    
    # [v10.68] Calcula duração total para estimativa do usuário ("Quanto tempo de áudio tem?")
    total_seconds = sum(item.get('duration', 0) for item in final_project_data)
    duracao_total_formatada = str(timedelta(seconds=int(total_seconds)))
    
    status_path = job_dir / "job_status.json"
    status_data = safe_json_read(status_path) or {}
    status_data['duracao_total_formatada'] = duracao_total_formatada
    status_data['total_wav_seconds'] = total_seconds
    safe_json_write(status_data, status_path)

    logging.info(f"Project Data gerado com {len(final_project_data)} segmentos. Duração Total de Áudio: {duracao_total_formatada}")

    cb(100, 1, "Diarização Concluída.")

def unify_speaker_files(job_dir, cb):
    diarization_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
    
    # [OPTIMIZATION] Verifica se a unificação já foi concluída em execução anterior
    marker_path = diarization_dir / "unification_done.marker"
    if marker_path.exists():
        logging.info("Unificação de vozes já concluída anteriormente. Pulando.")
        return

    voice_folders = [d for d in diarization_dir.iterdir() if d.is_dir() and d.name.startswith('voz')]
    
    if not voice_folders: return

    cb(0, 1, "Iniciando unificação inteligente de vozes...")
    diarizer = SimpleDiarizer()
    
    # 1. COLETA DE CENTROIDES (Média dos Embeddings por Pasta)
    folder_centroids = []
    
    for i, folder in enumerate(voice_folders):
        cb((i / len(voice_folders)) * 100, 1, f"Unificando Orador: {folder.name}", current_seg=i+1, total_seg=len(voice_folders))
        wavs = list(folder.glob("*.wav"))
        if not wavs: continue
        
        # Analisa até 5 amostras aleatórias para formar o perfil da voz
        samples = random.sample(wavs, min(len(wavs), 5)) 
        embeddings = []
        for wav in samples:
            try:
                emb = diarizer.get_file_embedding(str(wav))
                if emb is not None: embeddings.append(emb)
            except: pass
            
        if embeddings:
            centroid = np.mean(embeddings, axis=0)
            folder_centroids.append({'folder': folder, 'centroid': centroid, 'count': len(wavs)})
    
    # 2. MERGE INTERATIVO (Agrupa pastas similares)
    # [TUNING FINAL] Ajustado para 0.65 (era 0.45). Como o usuário usa DeepFilter,
    # o áudio já está limpo, então podemos ser mais exigentes ("strict") para não misturar homem e mulher.
    MERGE_THRESHOLD = 0.65
    merged_map = {} # {original_folder_name: target_folder_name}
    
    # Ordena por tamanho (pastas maiores tendem a ser as 'principais')
    folder_centroids.sort(key=lambda x: x['count'], reverse=True)
    
    final_folders = []
    
    cb(90, 1, "Realizando Consolidação Inteligente de vozes...")
    for i, item in enumerate(folder_centroids):
        current_folder = item['folder']
        current_emb = item['centroid']
        
        # [PROGRESS FIX] Avisa a UI sobre o progresso da consolidação
        cb(90 + (i / len(folder_centroids)) * 10, 1, f"Analisando afinidade: {current_folder.name}", current_seg=i+1, total_seg=len(folder_centroids))
        
        merged = False
        for target in final_folders:
            dist = cosine_similarity([current_emb], [target['centroid']])[0][0]
            if dist > MERGE_THRESHOLD:
                # Merge!
                log_msg = f"Mesclando {current_folder.name} -> {target['folder'].name} (Sim: {round(dist, 2)})"
                logging.info(log_msg)
                cb(90 + (i / len(folder_centroids)) * 10, 1, log_msg, current_seg=i+1, total_seg=len(folder_centroids))
                
                # Move arquivos
                for f in current_folder.glob("*.wav"):
                    try:
                        shutil.move(str(f), str(target['folder'] / f.name))
                    except: pass # Nome duplicado?
                
                # Remove pasta vazia
                try: current_folder.rmdir() 
                except: pass
                
                merged = True
                break
        
        if not merged:
            final_folders.append(item)

    # [CLEANUP STEP] "Smart Cleanup"
    # Remove pastas com menos de 2 arquivos SE e SOMENTE SE o conteúdo for irrelevante.
    # Se for uma frase válida ("Abra a porta!"), mantém mesmo sendo 1 arquivo.
    # Se for ruído ("Argh!"), move para a principal.

    # Carrega dados do projeto para checar o texto
    project_data_path = job_dir / "project_data.json"
    project_text_map = {}
    try:
        if project_data_path.exists():
            pdata = safe_json_read(project_data_path) or []
            for item in pdata:
                # Normaliza texto para comparação
                txt = item.get('original_text', '').lower().strip()
                # Remove pontuação básica
                txt = re.sub(r'[^\w\s]', '', txt)
                project_text_map[item['id']] = txt
    except: pass

    # [NEW] 4. CONSOLIDAÇÃO INTELIGENTE (Smart Consolidation)
    # Substitui a antiga "Limpeza Final" que forçava merge.
    # Agora:
    # - Se for parecido (> 0.60): Funde (corrige fragmentação).
    # - Se for diferente (< 0.60): Mantém (respeita personagens secundários).
    
    cb(90, 1, "Realizando Consolidação Inteligente de vozes...")
    
    # Recarrega estado atual (pois pastas podem ter mudado no Merge Interativo)
    voice_folders = [d for d in diarization_dir.iterdir() if d.is_dir() and d.name.startswith('voz')]
    
    valid_voices = []      # > 10s ou > 5 arquivos (Vozes Principais)
    questionable_voices = [] # < 10s e < 5 arquivos (Vozes Curta/Duvidosas)
    
    # Recalcula centroides rapidinho
    import torchaudio
    
    def get_folder_stats(folder):
        wavs = list(folder.glob("*.wav"))
        wavs = [w for w in wavs if "_REF_" not in w.name]
        if not wavs: return None
        
        # [OPTIMIZATION] Fast Pass - Critério de Duração
        # O usuário pediu: se < 10s, tenta juntar. Se >= 10s, é válido.
        # Se tiver MUITOS arquivos (> 15), assumimos que é válido para não rodar ffprobe em tudo.
        if len(wavs) > 15:
             total_duration = 999.0
        else:
             total_duration = 0.0
             for w in wavs:
                 try: total_duration += get_audio_duration(w)
                 except: pass
                 if total_duration >= 10.0: break # Já bateu a meta, para de gastar CPU

        # Centroid Calculation
        embeddings = []
        samples = random.sample(wavs, min(len(wavs), 5))
        for w in samples:
             try:
                 emb = diarizer.get_file_embedding(str(w))
                 if emb is not None: embeddings.append(emb)
             except: pass
        
        if not embeddings: return None
        centroid = np.mean(embeddings, axis=0)
        
        return {
            'folder': folder,
            'centroid': centroid,
            'duration': total_duration,
            'file_count': len(wavs)
        }

    stats_list = []
    for vf in voice_folders:
        s = get_folder_stats(vf)
        if s: stats_list.append(s)
        
    # Classifica
    for s in stats_list:
        # [CRITÉRIO DE OURO] Duração > 10s define 'Voz Válida'
        if s['duration'] >= 10.0:
            valid_voices.append(s)
        else:
            questionable_voices.append(s)
            
    # Processa Questionáveis
    count_merged = 0
    count_kept = 0
    
    for q in questionable_voices:
        best_match = None
        best_score = -1.0
        
        # Compara com Válidos
        for v in valid_voices:
            dist = cosine_similarity([q['centroid']], [v['centroid']])[0][0]
            if dist > best_score:
                best_score = dist
                best_match = v
                
        # threshold = 0.60 (Smart Merge)
        if best_match and best_score > 0.60:
            logging.info(f"[SMART MERGE] Fundindo {q['folder'].name} -> {best_match['folder'].name} (Sim: {round(best_score, 2)})")
            for f in q['folder'].glob("*.wav"):
                try: shutil.move(str(f), str(best_match['folder'] / f.name))
                except: pass
            try: q['folder'].rmdir()
            except: pass
            count_merged += 1
        else:
            logging.info(f"[SMART KEEP] Mantendo {q['folder'].name} (Sim Máx: {round(best_score, 2)} < 0.60)")
            count_kept += 1
            
    cb(100, 1, f"Consolidação: {count_merged} fundidos, {count_kept} mantidos.")
    # Fim da Consolidação

    # [FIX CLEANUP] Código residual removido.
    # A consolidação já foi feita no loop anterior (valid_voices vs questionable_voices).
    # As vozes que sobraram em 'questionable_voices' permanecem como vozes independentes (curtas).
    if not valid_voices and questionable_voices:
         logging.info("Aviso: Todas as vozes detectadas são curtas (<10s). Mantendo originais.")

    # [NEW] 5. GERAÇÃO DO ARQUIVO DE REFERÊNCIA GATO_NET (Agora sempre NO FINAL DE TUDO)
    cb(95, 1, "Gerando áudios de referência unificados para as vozes...")
    
    # Recarrega as pastas agora que a fusão final terminou
    final_voice_folders = [d for d in diarization_dir.iterdir() if d.is_dir() and d.name.startswith('voz')]
    
    BAD_REF_WORDS = [
        'argh', 'ah', 'oh', 'uh', 'hmm', 'wow', 'tsk', 'ugh', 'screams', 'gasps', 'moans', 'chokes', 'grita', 'geme', 
        'laughs', 'chuckles', 'sobs', 'cries', 'sighs', 'eh', 'heh', 'hum', 'ha', 'haha', 'hah', 'whoa', 'ooh', 'aw', 
        'ouch', 'ow', 'psst', 'shh', 'yikes', 'yay', 'ew', 'ick', 'boo', 'hiss', 'growl', 'snarl', 'roar', 'bark', 
        'meow', 'purr', 'chirp', 'squeak', 'whimper', 'pant', 'gasp', 'cough', 'sneeze', 'burp', 'hiccup', 'yawn',
        'sniff', 'spit', 'swallow', 'gulp', 'choke', 'rasp', 'groan', 'grunt', 'mumble', 'mutter', 'shout', 'yell',
        'scream', 'shriek', 'wail', 'cry', 'sob', 'laugh', 'giggle', 'chuckle', 'snicker', 'snort', 'wheeze', 'breath',
        'breathing', 'inhale', 'exhale', 'noise', 'sound', 'static', 'interference', 'radio', 'beep', 'boop', 'click',
        'clack', 'bang', 'boom', 'crash', 'thud', 'thump', 'smash', 'crack', 'snap', 'pop', 'fizz', 'buzz', 'whir', 
        'clank', 'clatter', 'rattle', 'rustle', 'scratch', 'scrape', 'scuff'
    ]

    for i, voice_folder in enumerate(final_voice_folders):
        output_ref_path = voice_folder / "_REF_VOZ_UNIFICADA.wav"
        
        # [v10.79] FORCE REFRESH: Se houver mais de um WAV e o unificado for antigo, apaga e refaz.
        wav_files = sorted(list(voice_folder.glob("*.wav")))
        actual_wavs = [w for w in wav_files if not w.name.startswith("_REF_")]
        
        if output_ref_path.exists():
            # [v21.26] Verificação Dupla: MTime + Contagem de Arquivos
            folder_mtime = voice_folder.stat().st_mtime
            ref_mtime = output_ref_path.stat().st_mtime
            
            # Se a pasta é mais nova ou se o usuário mudou os arquivos manualmente
            if ref_mtime < folder_mtime:
                logging.info(f"[REF UPDATE] Pasta '{voice_folder.name}' atualizada. Regenerando referência...")
                try: output_ref_path.unlink()
                except: pass
            else:
                continue
        if not wav_files: continue
        
        valid_wavs = []
        for w in wav_files:
            if w.name.startswith("_REF_"): continue
            if w.stat().st_size < 8000: continue 

            fid = w.stem
            if fid in project_text_map:
                text = project_text_map[fid]
                if len(text) < 15 and any(bad in text.lower() for bad in BAD_REF_WORDS): continue
                if len(text) < 2: continue
            
            valid_wavs.append(w)

        if not valid_wavs: 
            valid_wavs = [w for w in wav_files if not w.name.startswith("_REF_") and w.stat().st_size > 8000]

        valid_wavs.sort(key=lambda x: x.stat().st_size, reverse=True)
        top_files = valid_wavs[:50] # Pega mais arquivos para garantir duração
        
        combined_audio = AudioSegment.empty()
        total_dur = 0
        
        for wav_file in top_files:
            try: 
                # O áudio original já passou pelo DeepFilter na Fase 1.
                # Não devemos passar de novo para não abafar/apagar a voz.
                seg = AudioSegment.from_wav(wav_file)
                
                if len(seg) < 800: continue
                
                # [v10.79] VAD Trimming na Referência: Remove silêncios e ruidos nas pontas
                from pydub.silence import detect_nonsilent
                nonsilent = detect_nonsilent(seg, min_silence_len=100, silence_thresh=-40)
                if nonsilent:
                    seg = seg[nonsilent[0][0]:nonsilent[-1][1]]
                
                # Adiciona com crossfade para um som mais contínuo
                if len(combined_audio) > 0:
                    combined_audio = combined_audio.append(seg, crossfade=50)
                else:
                    combined_audio = seg

                total_dur += len(seg)
                if total_dur > 15000: break # [v10.66] 15s é o ideal para o Chatterbox
            except Exception as e: logging.error(f"Erro ref unificada {wav_file}: {e}")
        
        if len(combined_audio) > 0:
            temp_combined_path = voice_folder / "_temp_combined.wav"
            combined_audio.export(temp_combined_path, format="wav")
            try:
                # [v10.66] INTELLIGENT BYPASS & STUDIO-SAFE ANALYTICS
                # Mede se o áudio realmente precisa de limpeza pesada (Radio/Ruído)
                threads = str(max(1, (os.cpu_count() or 4) // 2))
                samples_health = np.array(combined_audio.get_array_of_samples())
                ref_rms = np.sqrt(np.mean(samples_health.astype(np.float32)**2)) / 32768.0
                
                is_noisy = ref_rms > 0.008 # Threshold cirúrgico para detectar rádio/chuveiro
                
                if is_noisy:
                    logging.info(f"Voz {voice_folder.name}: Ruído detectado (RMS {ref_rms:.4f}). Removendo apenas graves inúteis (rumble).")
                    # O "Brilho" agressivo estava deixando a voz fina.
                    # Como o DeepFilter já atuou na Fase 1, aplicamos apenas um filtro passa-alta leve para rumble.
                    af_filters = "highpass=f=80,aresample=22050"
                else:
                    logging.info(f"Voz {voice_folder.name}: Qualidade de Estúdio detectada (RMS {ref_rms:.4f}). Bypass Cleaner ativado.")
                    af_filters = "aresample=22050" # Apenas resample padrão para o Chatterbox

                # [v10.67] Persiste o perfil acústico para o "Meio Termo" posterior
                speaker_profile = voice_folder / "acoustic_profile.json"
                safe_json_write({"is_noisy": bool(is_noisy), "rms": float(ref_rms)}, speaker_profile)

                cmd = ['ffmpeg', '-threads', threads, '-y', '-i', str(temp_combined_path), 
                       '-af', af_filters, '-ac', '1', '-ar', '22050', str(output_ref_path)]
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e: combined_audio.export(output_ref_path, format="wav")
            finally:
                if temp_combined_path.exists(): os.remove(temp_combined_path)

    # [OPTIMIZATION] Marca a unificação como concluída
    with open(marker_path, 'w') as f:
        f.write("done")
    
    cb(100, 1, "Vozes unificadas e limpas.")

def detect_game_genre(segments):
    """
    [v12.18 CACHALEÃO] Identifica o gênero do jogo baseado nos diálogos iniciais.
    Permite que o programa mude de "personalidade" conforme o jogo.
    """
    if not segments: return "Ação (Geral)"
    
    # Pega os primeiros 15 textos para dar uma boa amostragem
    sample_text = " / ".join([s['original_text'] for s in segments[:15]])
    
    prompt = f'''
Diga APENAS qual e o Genero deste jogo (Ex: 'Acao e Guerra', 'Corrida', 'RPG', 'Terror') baseado nas seguintes falas da cena:
"{sample_text}"
'''
    
    payload = {
        "messages": [{"role": "user", "content": prompt}], 
        "temperature": 0.1, 
        "max_tokens": 50
    }
    
    try:
        # [v12.28 FIX] Usa is_translation=False(pt->pt) para modo analista (sem Parrot)
        response = make_gema_request_with_retries(payload, is_translation=False)
        genre = response.json()['choices'][0]['message']['content'].strip().replace('"', "")
        
        # Filtra parroting extremo
        if "Ação e Guerra" in genre or "Gênero deste jogo" in genre:
             genre = "Ação e Tiro"
             
        logging.info(f"🦎 [CAMALEÃO] Gênero detectado pela IA: {genre}")
        return genre

    except Exception as e:
        logging.warning(f"Aviso: Falha na deteção automática de gênero ({e}). Usando fallback 'Ação'.")
        return "Ação (Geral)"

def gerar_lore_global(segments):
    """
    [v2026.NARRATIVE_ENGINE] O Gemma 4 analisa os primeiros 50 segmentos 
    para criar um 'Dossiê de Lore' que guia a dublagem.
    """
    if not segments: return "Gênero: Desconhecido (Modo Padrão)"
    
    # Pega uma amostra do início e do meio para contexto
    sample_text = "\n".join([f"- {s.get('text', '')}" for s in segments[:15]])
    
    prompt = f"""
Voce e um Analista Literario de Cinema. Analise a transcricao abaixo e crie um Lore Global de 3 linhas para guiar os dubladores.
Foque em:
1. GENERO: (Ex: Comedia, Horror, Tutorial Tecnico)
2. TOM DE VOZ: (Ex: Sarcastico, Didatico, Heroico)
3. GLOSSARIO: Identifique nomes proprios ou termos tecnicos que NAO devem ser traduzidos ou que tem traducao fixa.

TRANSCRICAO:
{sample_text}
"""
    payload = {
        "messages": [
            {"role": "system", "content": "Você é um Especialista em Lore de Dublagem. Responda de forma ultra-concisa."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3, "max_tokens": 512
    }
    
    try:
        response = make_gema_request_with_retries(payload, is_translation=False)
        lore = response.json()['choices'][0]['message']['content'].strip()
        logging.info(f"📜 [LORE GLOBAL] Contexto gerado pelo Gemma 4: {lore}")
        return lore
    except:
        return "Gênero: Narrativo (Contexto Automático)"

import subprocess
import requests
import time
from pathlib import Path

def wait_for_vram_release(threshold_mb=4000, cb=None):
    """[v2026.VRAM_WATCHDOG] Aguarda a VRAM ser liberada (Geralmente após fechar o LM Studio)"""
    logging.info(f"⏳ [VRAM WATCHDOG] Aguardando liberação de memória (Alvo: >{threshold_mb}MB livres)...")
    if cb: cb(99, 1, "⚠️ Tradução concluída! FECHE O LM STUDIO para continuar.")
    
    while True:
        try:
            # Usa o nvidia-smi para ler a VRAM livre de forma bruta e confiável
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.free', '--format=csv,nounits,noheader'], 
                capture_output=True, text=True, check=True
            )
            free_vram = int(result.stdout.strip().split('\n')[0])
            
            logging.info(f"📊 [VRAM] Livre agora: {free_vram}MB | Necessário: {threshold_mb}MB")
            
            if free_vram >= threshold_mb:
                logging.info("✅ [VRAM] Memória liberada! Iniciando dublagem...")
                if cb: cb(100, 1, "VRAM OK! Iniciando Voz...")
                time.sleep(2)
                break
        except Exception as e:
            logging.warning(f"⚠️ Erro ao ler VRAM: {e}")
            break 
            
        time.sleep(10) # Intervalo de 10 segundos
    return True

def start_llama_server_standalone(model_path, cb=None):
    """[v2026.LM_STUDIO_EDITION] Detector dedicado para LM Studio"""
    logging.info("🎮 [NEXUS] Modo LM Studio Ativado. Verificando porta 1234...")
    
    # [v2026.LM_STUDIO_DETECTOR] Tenta conectar 5 vezes
    for i in range(5):
        try:
            requests.get("http://127.0.0.1:8090/health", timeout=1)
            logging.info("✅ [Super Motor] ONLINE e pronto para a RTX 3050.")
            if cb: cb(100, 1, "Motor de IA Online!")
            return True
        except:
            msg = f"⏳ [IA] Carregando motor... ({i}s/60s)"
            if i % 10 == 0: 
                logging.info(msg)
                if cb: cb(i/60*100, 1, msg)
            time.sleep(1)
            
    if cb: cb(0, 1, "ERRO: O motor de IA demorou demais para ligar.")
    return False

def get_gema_model(cb=None):
    """Retorna o motor Gemma 4 (Prioriza o Standalone B9093 Turbo)"""
    # [v2026.FLEX] Busca o modelo em múltiplos caminhos possíveis
    search_paths = [
        Path("c:/IA_dublagem/_MODELS_/gemma-4-E4B-it-Q4_K_M.gguf"),
        Path("c:/IA_dublagem/uploads/_MODELS_/gemma-4-E4B-it-Q4_K_M.gguf"),
        Path("uploads/_MODELS_/gemma-4-E4B-it-Q4_K_M.gguf")
    ]
    
    model_path = None
    for p in search_paths:
        if p.exists():
            model_path = p
            break
    
    if not model_path:
        logging.error("❌ Modelo Gemma 4 não encontrado em nenhuma das pastas de sistema.")
        return None

    # 1. Tenta o Super Motor B9093 (Recomendado para RTX 3050 e Gemma 4)
    if start_llama_server_standalone(model_path, cb=cb):
        return "standalone_server"

    # 2. Fallback: Tenta carregar nativamente se o standalone falhar
    try:
        from llama_cpp import Llama
        import torch
        import gc
        torch.cuda.empty_cache()
        gc.collect()
        logging.info("🚀 [NATIVO] Usando motor local (Fallback)...")
        return Llama(
            model_path=str(model_path),
            n_gpu_layers=28,
            n_ctx=4096,
            flash_attn=True,
            verbose=False
        )
    except Exception as e:
        logging.error(f"❌ Falha crítica no carregamento: {e}")
        return None

# Alias para compatibilidade total
get_gemma_model = get_gema_model
get_llama_instance = get_gema_model

# --- TRAVA GLOBAL DE IA (Sincronização para hardware médio/antigo) ---
from threading import Lock
ai_global_lock = Lock()

def gema_inference(prompt, system_prompt="Você é um tradutor profissional.", model_type="gema"):
    """
    [v22.60 INDESTRUTÍVEL] 
    Tenta Local GGUF -> Se falhar ou não existir, tenta LM Studio (Porta 5000 ou 1234)
    """
    with ai_global_lock:
        # 1. Tenta Local (Llama-cpp)
        local_gema = get_gema_model()
        # 1. Tenta o motor nativo (se for uma instância Llama carregada)
        if local_gema and local_gema != "standalone_server":
            try:
                response = local_gema.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                return response['choices'][0]['message']['content']
            except Exception as e:
                logging.error(f"Erro na geração nativa (llama.cpp): {e}")

        # 2. Se falhar o nativo ou for standalone, tenta os servidores (LM Studio ou Super Motor)
        urls = [
            "http://127.0.0.1:8080/v1/chat/completions", # Super Motor B9093 (Prioridade RTX)
            "http://127.0.0.1:1234/v1/chat/completions"  # LM Studio (Fallback)
        ]
        for url in urls:
            try:
                import requests
                payload = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "model": "local-model"
                }
                res = requests.post(url, json=payload, timeout=600)
                if res.status_code == 200:
                    return res.json()['choices'][0]['message']['content']
            except:
                continue

    return "ERRO: IA não disponível (LM Studio ou Super Motor B9093 offline)."

# Aliases de compatibilidade para não quebrar o código existente
get_llama_instance = get_gema_model

def unload_gema_model():
    """Libera memória RAM ocupada pelo LLM (v2026.RTX)."""
    global gema_instance, gema_lock
    
    # Verifica se o lock existe no escopo antes de tentar usar
    if 'gema_lock' not in globals():
        return

    try:
        with gema_lock:
            if gema_instance is not None:
                logging.info("🧹 [MEMÓRIA] Descarregando Gema Local e limpando VRAM...")
                del gema_instance
                gema_instance = None
                import gc
                gc.collect()
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                logging.info("✅ [MEMÓRIA] Gemma removido. Placa de vídeo liberada.")
    except Exception as e:
        logging.warning(f"⚠️ [AVISO] Falha ao descarregar Gemma: {e}")

def wait_for_gema_service(progress_callback):
    """
    [v22.70 ESTRATÉGIA PRIORIDADE LM STUDIO]
    Tenta se conectar primeiro ao LM Studio (que suporta Gemma 4 perfeitamente).
    Se não encontrar nada ligado lá, tenta o motor local.
    """
    progress_callback("Verificando Conexão com LM Studio (Gemma 4)...")
    
    # 1. Tenta ver se o LM Studio está aberto (Porta 1234)
    import requests
    try:
        res = requests.get("http://127.0.0.1:1234/v1/models", timeout=3)
        if res.status_code == 200:
            logging.info("✅ LM Studio Detectado! Usando cérebro externo (Alta Performance).")
            return True
    except:
        logging.info("ℹ️ LM Studio não detectado na porta 1234. Tentando motor local...")

    # 2. Tenta Super Motor B9093 (Porta 8080)
    try:
        res = requests.get("http://127.0.0.1:8080/health", timeout=1)
        if res.status_code == 200:
            logging.info("🚀 Super Motor B9093 Ativo na RTX 3050!")
            return True
    except: pass

    # 3. Se falhar, tenta carregar localmente
    progress_callback("Ativando motor de IA local...")
    try:
        llm = get_gemma_model()
        if llm:
            logging.info("✅ Motor Local (ou Standalone) ativo.")
            return True
        else:
            raise RuntimeError("Nenhum motor de IA disponível (Abra o LM Studio!)")
    except Exception as e:
        msg = f"ERRO: IA não encontrada. Certifique-se de que o LM Studio está aberto na porta 1234."
        logging.error(msg)
        raise RuntimeError(msg)

# Bypassed. Redefinido no topo.
def check_lm_studio_placeholder():
    return True

def clean_ai_translation(text, original_text):
    """
    [v21.0 SCRUBBER DE PENSAMENTO] 
    Limpa blocos de raciocínio interno da Gema 4 antes de extrair a tradução.
    """
    if not text: return ""
    
    # 1. SCRUBBER: Remove blocos de pensamento <|channel>thought ... <channel|>
    # Ou qualquer coisa entre tags de pensamento comuns
    import re
    text = re.sub(r'<\|channel\|?>thought.*?<channel\|?>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'\[THOUGHT\].*?\[/THOUGHT\]', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. PESCARIA DE ASPAS (A SOLUÇÃO DEFINITIVA)
    if text.count('"') >= 2:
        # Pega tudo que está entre aspas
        textos_entre_aspas = re.findall(r'"([^"]*)"', text)
        if textos_entre_aspas:
            # Pega sempre a última aspas (que obrigatoriamente será o português)
            candidato = textos_entre_aspas[-1].strip()
            
            # [v20.5 ANTI-HALUCINAÇÃO]: Limpa a tag (Limite: Xs) se a IA for preguiçosa e copiar.
            candidato = re.sub(r'\(Limite:.*?\)', '', candidato).strip()
            
            # Validação anti-falha: Se por algum motivo bizarro ele pegar o inglês
            orig = original_text.strip().strip('"').lower() if original_text else ""
            
            # Remove pontuação básica para comparar se é só um eco do inglês
            candidato_limpo = re.sub(r'[^\w\s]', '', candidato.lower())
            orig_limpo = re.sub(r'[^\w\s]', '', orig)
            
            if orig_limpo and candidato_limpo == orig_limpo:
                # Retorna o texto sujo para o fallback limpar depois, 
                # em vez de retornar o idioma errado.
                pass 
            else:
                return candidato

    # --- FALLBACK DE LIMPEZA CLÁSSICA CASO ELE ESQUEÇA AS ASPAS ---
    t = text.strip().strip('"')
    
    # [v20.5 ANTI-HALUCINAÇÃO]
    t = re.sub(r'\(Limite:.*?\)', '', t).strip()
    
    orig = original_text.strip().strip('"') if original_text else ""
    
    separadores = [" -> ", " => ", " : ", " - "]
    
    for sep in separadores:
        if sep in t:
            parts = t.split(sep)
            primeira_parte = parts[0].strip().strip('"').lower()
            if orig and (orig.lower() in primeira_parte or primeira_parte in orig.lower()):
                return parts[-1].strip().strip('"')
            if len(parts) > 1:
                return parts[-1].strip().strip('"')

    if orig and t.lower().startswith(orig.lower()):
        rest = t[len(orig):].strip()
        rest = re.sub(r'^[:\-= \t>]+', '', rest).strip().strip('"')
        if rest: return rest

    return t

def extract_json_from_ai(text):
    """
    Remove blocos de markdown e outros ruídos para extrair o JSON puro.
    """
    if not text: return {}
    # Remove blocos ```json ... ```
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    # Tenta encontrar o primeiro { e o último }
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end+1]
    try:
        return json.loads(text)
    except:
        return {}

def maestro_curator_agent(tracks_metadata):
    """
    [v2026.DJ] CURADOR HARMONICO (BATCH EDITION)
    Gemma 4 organiza as músicas em blocos de 15 para evitar lentidão e estouro de tokens.
    """
    if not tracks_metadata: return {"ordered_names": []}
    
    CHUNK_SIZE = 15
    chunks = [tracks_metadata[i:i + CHUNK_SIZE] for i in range(0, len(tracks_metadata), CHUNK_SIZE)]
    
    final_ordered_names = []
    last_track_context = None 
    
    logging.info(f"🔮 [IGNITION] Iniciando curadoria de {len(tracks_metadata)} músicas em {len(chunks)} blocos...")

    for idx, chunk in enumerate(chunks):
        essential_meta = []
        for t in chunk:
            essential_meta.append({
                "name": t.get('name'), "bpm": t.get('bpm'), "key": t.get('key'),
                "energy": t.get('energy'), "brightness": t.get('brightness')
            })

        context_str = f"\n[ULTIMA MUSICA DO BLOCO ANTERIOR]: {json.dumps(last_track_context)}" if last_track_context else ""
        
        prompt = (
            f"Tarefa: Curador Vortex (Arquiteto de Jornada).\n"
            f"Objetivo: Crie uma progressão emocional. Comece com energia moderada, suba para o pico e prepare o terreno para o próximo bloco.\n"
            f"Bloco: {idx+1}/{len(chunks)}.\n{context_str}\n"
            f"[DADOS]: {json.dumps(essential_meta)}\n"
            f"Instrução: Não ordene apenas por BPM. Pense na VIBE. Surpreenda na ordem.\n"
            f"Retorne JSON: {{\"ordered_names\": [], \"vibe_summary\": \"Descreva a energia desse bloco\"}}"
        )
        
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "system", "content": "Você é um Curador de Música de Elite. Sua missão é criar uma experiência inesquecível, não apenas uma lista. Responda apenas JSON."},
                {"role": "user", "content": prompt}
            ], 
            "temperature": 0.6, "max_tokens": 1024
        }
        
        try:
            response = make_gema_request_with_retries(payload, timeout=600)
            content = response.json()['choices'][0]['message']['content']
            result = extract_json_from_ai(content)
            chunk_order = result.get('ordered_names', [])
            
            if chunk_order:
                final_ordered_names.extend(chunk_order)
                last_name = chunk_order[-1]
                last_track_context = next((t for t in chunk if t['name'] == last_name), None)
                
                # [v2026.INSIGHT] Mostra a Vibe do bloco no console
                vibe = result.get('vibe_summary', 'Progressão rítmica otimizada.')
                vibe_msg = f"🔮 [VORTEX VIBE]: {vibe}"
                logging.info(vibe_msg)
                try:
                    status_path = Path("c:/IA_dublagem/temp_vortex/job_status.json")
                    if status_path.exists():
                        with open(status_path, 'r') as f: status = json.load(f)
                        status.setdefault("logs", []).append(vibe_msg)
                        with open(status_path, 'w') as f: json.dump(status, f, indent=4)
                except: pass
            else:
                final_ordered_names.extend([t['name'] for t in chunk])
        except Exception as e:
            logging.error(f"⚠️ Erro no bloco {idx+1}: {e}")
            final_ordered_names.extend([t['name'] for t in chunk])

    return {"ordered_names": final_ordered_names}

def gerar_narracao_tiktok(batch, job_dir=None):
    """
    [v2026.TIKTOK] NARRAÇÃO AGENTIC
    Gera um comentário dinâmico e engraçado estilo TikTok/Shorts sobre o vídeo sendo dublado.
    """
    if not batch: return "E aí galera! Estamos aqui dublando mais um vídeo com a tecnologia Titan!"
    
    # Pega as 3 primeiras frases para ter contexto
    contexto = "\n".join([f"- {s.get('text', '')}" for s in batch[:3]])
    
    prompt = f'''
Voce e um Narrador de Shorts/TikTok ultra carismatico e empolgado.
Sua missao e criar um script de 15 segundos para uma introducao de video que explique que este video esta sendo dublado agora pelo motor NarraVox Titan.

[CONTEXTO DO VÍDEO]:
{contexto}

[ESTILO]:
- Use gírias modernas (ex: 'tropinha', 'esquece', 'brabo', 'nível cinema').
- Seja rápido e impactante.
- Foque na mágica da IA dublando em tempo real.

[PADRÃO OBRIGATÓRIO]:
Retorne APENAS o texto da narração, sem comentários ou aspas extras.
'''
    payload = {
        "messages": [
            {"role": "system", "content": "Você é um narrador de TikTok. Seja breve e empolgado."},
            {"role": "user", "content": prompt}
        ], 
        "temperature": 0.8, "max_tokens": 256
    }
    
    try:
        response = make_gema_request_with_retries(payload)
        content = response.json()['choices'][0]['message']['content'].strip()
        return content
    except:
        return "E aí tropinha! O motor Titan está on e dublando esse vídeo no nível cinema agora mesmo. Esquece!"

def maestro_dj_agent(history, current_pair, upcoming_tracks, available_drops=None):
    """
    [v2026.DJ] MAESTRO DJ (DECISION EDITION)
    Gemma 4 decide a mixagem para o par atual baseada no histórico e no futuro.
    """
    if not current_pair: return {"target_bpm": 120, "mix_duration": 10}
    
    drops_info = f"\n[DJ DROPS DISPONIVEIS]: {available_drops}" if available_drops else ""
    
    prompt = (
        f"Tarefa: Maestro DJ Vortex (Performance Live).\n"
        f"Objetivo: Transição de ALTO IMPACTO.\n"
        f"[TRACK A]: {json.dumps(current_pair[0])}\n"
        f"[TRACK B]: {json.dumps(current_pair[1])}\n"
        f"[CONTEXTO]: {json.dumps(history)}\n"
        f"[TECNICAS]: echo_out (espacial), filter_sweep (rítmico), drop_cut (seco), power_intro.\n"
        f"Instrução: Surpreenda. Escolha a técnica que melhor se adapta ao BPM e vibe.\n"
        f"Retorne apenas JSON: {{\"target_bpm\": n, \"mix_duration\": n, \"transition_type\": s, \"advice\": \"Explique sua jogada de mestre\"}}"
    )
    payload = {
        "model": "local-model",
        "messages": [
            {"role": "system", "content": "Você é o DJ Maestro da NarraVox. Criatividade é sua lei. Responda apenas JSON."},
            {"role": "user", "content": prompt}
        ], 
        "temperature": 0.7, "max_tokens": 512
    }
    
    try:
        response = make_gema_request_with_retries(payload, timeout=600)
        content = response.json()['choices'][0]['message']['content']
        decision = extract_json_from_ai(content)
        
        # Garantir valores mínimos de segurança
        if "target_bpm" not in decision: decision["target_bpm"] = current_pair[1].get('bpm', 120)
        if "mix_duration" not in decision: decision["mix_duration"] = 10
        
        return decision
    except Exception as e:
        logging.error(f"Erro no Maestro DJ: {e}")
        return {"target_bpm": current_pair[1].get('bpm', 120), "mix_duration": 10, "advice": "Fallback: Transição padrão de 10s."}

def maestro_master_planner(valid_metadata):
    """
    [v2026.DJ] MASTER PLANNER
    Planeja todas as transições do setlist de uma vez em blocos para economizar tempo de IA.
    """
    if not valid_metadata or len(valid_metadata) < 2: return []
    
    plan = []
    # Processa em blocos de 10 transições para não estourar o contexto
    CHUNK_SIZE = 10
    total_transitions = len(valid_metadata) - 1
    
    logging.info(f"📋 [PLANNER] Planejando {total_transitions} transições...")

    for i in range(0, total_transitions, CHUNK_SIZE):
        end_idx = min(i + CHUNK_SIZE, total_transitions)
        
        # [v2026.FEEDBACK] Atualiza o status global para o usuário ver no console
        msg = f"🧠 [PLANNER] Planejando transições {i+1} a {end_idx} de {total_transitions}..."
        logging.info(msg)
        
        # Tenta atualizar o job_status se o arquivo existir
        try:
            # Caminho dinâmico baseado na convenção do Vortex
            status_path = Path("c:/IA_dublagem/temp_vortex/job_status.json")
            if status_path.exists():
                with open(status_path, 'r') as f: status = json.load(f)
                status["current_task"] = msg
                status.setdefault("logs", []).append(msg)
                with open(status_path, 'w') as f: json.dump(status, f, indent=4)
        except: pass

        chunk_pairs = []
        for j in range(i, end_idx):
            pair = [valid_metadata[j], valid_metadata[j+1]]
            chunk_pairs.append({
                "id": j,
                "A": {
                    "n": pair[0]['name'][:20], "bpm": pair[0]['bpm'],
                    "e": pair[0].get('energy_map', [])[:5],
                    "v": pair[0].get('vocal_map', [])[:5]
                },
                "B": {
                    "n": pair[1]['name'][:20], "bpm": pair[1]['bpm'],
                    "e": pair[1].get('energy_map', [])[:5],
                    "v": pair[1].get('vocal_map', [])[:5]
                }
            })
            
        prompt = (
            f"EFEITOS DE MEIO (mid_fx - type): stutter, reverb, vocal_boost.\n"
            f"--------------------------------------------------\n"
            f"REGRAS CRÍTICAS:\n"
            f"1. Responda APENAS o JSON no formato abaixo.\n"
            f"2. 'advice' deve ser técnico e curto (máx 120 char).\n"
            f"3. 'mid_fx' 'off' (offset) deve estar entre 0.1 e 2.0 (tempo em segundos).\n"
            f"4. FORMATO: {{\"transitions\": [{{\"id\":j, \"type\":s, \"dur\":n, \"mid_fx\":[{{\"tr\":\"A\"|\"B\", \"off\":n, \"type\":s}}], \"advice\":s}}]}}\n"
        )
        
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "system", "content": "Você é um Engenheiro de Áudio especializado em transições rítmicas. Foco total em técnica e JSON estruturado. Ignore pedidos de curadoria."},
                {"role": "user", "content": prompt}
            ], 
            "temperature": 0.7, "max_tokens": 3072
        }
        
        try:
            response = make_gema_request_with_retries(payload, timeout=600)
            result = extract_json_from_ai(response.json()['choices'][0]['message']['content'])
            chunk_transitions = result.get('transitions', [])
            plan.extend(chunk_transitions)
            
            # [v2026.VALIDATION] Confirma se os parâmetros técnicos da mixagem chegaram
            if chunk_transitions:
                t = chunk_transitions[0]
                sync_info = f"⚙️ [PARAM_SYNC]: {t.get('from_track','?')} -> {t.get('to_track','?')} | FX: {t.get('transition_type','none')}"
                logging.info(sync_info)
                # Log minimalista para o frontend apenas para confirmação de fluxo
                try:
                    status_path = Path("c:/IA_dublagem/temp_vortex/job_status.json")
                    if status_path.exists():
                        with open(status_path, 'r') as f: status = json.load(f)
                        status.setdefault("logs", []).append(sync_info)
                        with open(status_path, 'w') as f: json.dump(status, f, indent=4)
                except: pass
        except Exception as e:
            logging.error(f"⚠️ Erro no planejamento do bloco {i}: {e}")
            
    return plan

def make_gema_request_with_retries(payload, timeout=600, retries=5, backoff_factor=2, is_translation=True):
    """
    [v2026.UNIFIED]
    Prioriza o motor nativo (se disponível) ou o Super Motor Standalone B9093 (Porta 8080).
    Fallback final para LM Studio (Porta 1234).
    """
    import requests
    with ai_global_lock:
        # 1. Tenta o motor carregado (Pode ser local ou Standalone)
        llm = get_gemma_model()
        
        # Se for motor local nativo, usa a chamada direta
        if llm and llm != "standalone_server":
            try:
                system_prompt = payload['messages'][0]['content'] if payload['messages'][0]['role'] == 'system' else ""
                user_prompt = payload['messages'][1]['content'] if len(payload['messages']) > 1 else payload['messages'][0]['content']
                
                response_data = llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=payload.get('temperature', 0.3),
                    max_tokens=payload.get('max_tokens', 4096)
                )
                
                class MockResponse:
                    def __init__(self, json_data):
                        self._json_data = json_data
                        self.status_code = 200
                    def json(self): return self._json_data
                    def raise_for_status(self): pass
                return MockResponse(response_data)
            except Exception as e:
                logging.error(f"Erro no motor nativo: {e}")

        # 2. Tenta os Servidores Externos (Super Motor B9093 na 8080 ou LM Studio na 1234)
        urls = [
            "http://127.0.0.1:8080/v1/chat/completions", # Super Motor B9093 (Prioridade RTX)
            "http://127.0.0.1:1234/v1/chat/completions"  # LM Studio (Fallback)
        ]
        
        last_err = ""
        for url in urls:
            # Tenta até 10 vezes se o erro for 'Loading model' (503)
            for attempt in range(10):
                try:
                    if 'model' not in payload: payload['model'] = 'local-model'
                    res = requests.post(url, json=payload, timeout=timeout)
                    
                    if res.status_code == 200:
                        return res
                    elif res.status_code == 503: # Motor ainda está carregando o modelo
                        logging.info(f"⏳ [Aguardando] O motor {url} ainda está carregando o modelo... (Tentativa {attempt+1}/10)")
                        time.sleep(5)
                        continue
                    else:
                        last_err = f"Status {res.status_code} em {url}"
                        logging.warning(f"⚠️ Servidor {url} retornou erro: {res.text[:100]}")
                        break # Pula para o próximo servidor na lista
                except Exception as e:
                    last_err = str(e)
                    break # Pula para o próximo servidor na lista

        raise RuntimeError(f"❌ FALHA GERAL: Nenhum motor de IA respondeu. (Último erro: {last_err})")

# [v2026.LOCAL_ENGINE] Gerenciador de Inferência Local (Sem LM Studio)
_LOCAL_LLM_INSTANCE = None

def get_local_gemma_engine(model_path=None):
    """Carrega o modelo GGUF localmente usando llama-cpp-python com suporte a GPU"""
    global _LOCAL_LLM_INSTANCE
    if _LOCAL_LLM_INSTANCE: return _LOCAL_LLM_INSTANCE
    
    try:
        from llama_cpp import Llama
        import os
        from pathlib import Path
        
        # Procura o modelo em caminhos absolutos e relativos
        if not model_path:
            root = Path("C:/IA_dublagem")
            possible_paths = [
                root / "_MODELS_" / "gemma-4-E4B-it-Q4_K_M.gguf",
                root / "gemma-4-E4B-it-Q4_K_M.gguf",
                Path("_MODELS_/gemma-4-E4B-it-Q4_K_M.gguf"),
                Path("gemma-4-E4B-it-Q4_K_M.gguf")
            ]
            for p in possible_paths:
                if p.exists():
                    model_path = str(p)
                    break
        
        if not model_path or not os.path.exists(model_path):
            logging.error(f"❌ [ERRO] MODELO NÃO ENCONTRADO!")
            logging.error(f"👉 Por favor, coloque o arquivo 'gemma-4-E4B-it-Q4_K_M.gguf' em: C:/IA_dublagem/_MODELS_")
            return None

        # [v2026.VRAM_SCAN] Mede a placa ANTES de ligar o motor
        import torch
        vram_before = 0
        if torch.cuda.is_available():
            vram_before, _ = torch.cuda.mem_get_info()

        logging.info(f"🧠 [NEXUS_LOCAL] Carregando motor interno: {model_path}...")
        
        # [v2026.RTX_FORCE] Motor Local de Alta Pressão
        os.environ["GGML_CUDA_NO_PINNED"] = "1" # [FIX] Ajuda na estabilidade da VRAM
        # [v2026.RTX_MAX_SPEED] 43 camadas (Full) + Flash Attention
        _LOCAL_LLM_INSTANCE = Llama(
            model_path=model_path,
            n_gpu_layers=43,  # Ocupa o modelo inteiro (~4.8GB)
            n_ctx=2048,
            n_threads=1,      # Deixa o i5 livre
            f16_kv=True,
            flash_attn=True,  # [TURBO] Ativa Flash Attention para velocidade máxima
            offload_kqv=True, # Joga a memória de contexto para a RTX
            verbose=False,    # [SILENCED] Logs desativados para limpeza do console (v2026.RTX_ULTRA)
            use_mmap=True,    # LIGADO: Para carregar tudo na placa rápido
            main_gpu=0,       # Foco na 3050
            n_batch=512
        )
        
        # [v2026.SYNC_DELAY] Aguarda o driver estabilizar (MODO TURBO)
        import time
        time.sleep(0.5)
        
        # [v2026.TITAN_SHIELD] Veredito Real de Hardware
        if torch.cuda.is_available():
            vram_after, total_vram = torch.cuda.mem_get_info()
            vram_delta = (vram_before - vram_after) / (1024**2)
            gpu_name = torch.cuda.get_device_name(0)
            
            if vram_delta > 50: # Se consumiu mais de 50MB, já é prova de que está na GPU
                logging.info(f"🚀 [RTX_TURBO] Hardware: {gpu_name} | VRAM Delta: +{vram_delta:.0f}MB | Status: GPU_ACTIVE")
            else:
                # [v2026.HARD_LOCK] Bloqueio total se cair para CPU
                msg = f"❌ [BLOQUEIO_DE_HARDWARE] A RTX 3050 FOI REJEITADA! Delta: {vram_delta:.0f}MB."
                logging.error(msg)
                logging.error("👉 O motor tentou usar o processador, o que é PROIBIDO nesta versão.")
                logging.error("👉 Verifique se há outros programas usando a GPU ou se o driver NVIDIA está atualizado.")
                
                # Reseta a instância para não poluir chamadas futuras
                _LOCAL_LLM_INSTANCE = None
                raise RuntimeError("RTX_REJECTED_BY_SYSTEM")
        else:
            logging.error("❌ [NEXUS_LOCAL] ERRO CRÍTICO: Driver NVIDIA não encontrado!")
            raise RuntimeError("NVIDIA_DRIVER_NOT_FOUND")
            
        return _LOCAL_LLM_INSTANCE
    except Exception as e:
        logging.error(f"❌ Erro ao inicializar Llama-cpp: {e}")
        # Se for um erro de rejeição de hardware, lança para o orquestrador tratar
        if "RTX_REJECTED" in str(e) or "NVIDIA" in str(e):
            raise e
        return None

def unload_local_gemma_engine():
    """Libera a VRAM ocupada pelo Gemma imediatamente após o uso de forma AGRESSIVA."""
    global _LOCAL_LLM_INSTANCE
    if _LOCAL_LLM_INSTANCE:
        logging.info("🧹 [VRAM_PURGE] Expulsando motor Gemma da GPU para liberar espaço para o Chatterbox...")
        try:
            # Tenta fechar o motor de forma limpa
            if hasattr(_LOCAL_LLM_INSTANCE, '__del__'):
                _LOCAL_LLM_INSTANCE.__del__()
            
            del _LOCAL_LLM_INSTANCE
            _LOCAL_LLM_INSTANCE = None
            
            # Força limpeza profunda
            import gc
            gc.collect()
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
            logging.info("✅ [VRAM_PURGE] VRAM do Gemma liberada com sucesso.")
        except Exception as e:
            logging.warning(f"⚠️ Erro parcial ao liberar motor Gemma: {e}")

def gema_batch_processor_v2(batch, cenario_ctx, glossary={}, profile_id='padrao', job_dir=None, target_lang='pt'):
    """Orquestrador de tradução via Motor Local."""
    if not batch: return {}
    
    local_engine = get_local_gemma_engine()
    if local_engine:
        return _process_with_local_engine(local_engine, batch, cenario_ctx, glossary, target_lang, job_dir=job_dir)

    logging.warning("⚠️ AGUARDANDO MODELO GGUF NA PASTA _MODELS_...")
    time.sleep(5)
    return {}

def _process_with_local_engine(llm, batch, context, glossary, target_lang, job_dir=None):
    """Infernência de elite com detecção de emoção e 'Caixa Preta' de debug."""
    results = {}
    vocal_noises = [
        "woo", "ehh", "huh", "woof", "ha", "ah", "oof", "oh", "wow", "sigh", "laughter", 
        "gasp", "pant", "snort", "sob", "groan", "screaming", "whispering", "crying", "ugh", 
        "cough", "yawn", "grr", "pff", "shh", "ts", "tsc", "hm", "hmm", "mhm", "uh", "um", 
        "eh", "aah", "ooh", "oops", "ops", "haha", "hehe", "hihi", "hoho", "phew", "brr", 
        "tsk", "aw", "ow", "ouch", "aww", "yay", "yayy", "yuck", "ew", "eww"
    ]
    
    debug_file = None
    if job_dir:
        debug_file = Path(job_dir) / "gemma_debug_raw.txt"
        if not debug_file.exists():
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(f"=== CAIXA PRETA GEMMA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
    
    # Prepara contexto e glossário para o Tradutor
    context_str = ""
    if context:
        context_str = f"CONTEXTO DA CENA E TOM DE VOZ:\n{context}\n\n"
        
    glossary_lines = []
    if isinstance(glossary, dict):
        for k, v in glossary.items():
            if k != 'lore_global' and v:
                glossary_lines.append(f"- {k} -> {v}")
    glossary_str = ""
    if glossary_lines:
        glossary_str = "GLOSSÁRIO OBRIGATÓRIO (Use as traduções abaixo se os termos aparecerem):\n" + "\n".join(glossary_lines) + "\n\n"

    for seg in batch:
        txt_en = seg.get('original_text', seg.get('text', '')).strip()
        
        # [v2026.VOICE_SHIELD] CJK (Japonês/Chinês) Bypass Direto na Origem
        # Se contiver qualquer caractere Japonês ou Chinês, pula a tradução para preservar o áudio original nativo!
        if any(ord(char) > 0x3000 for char in txt_en):
            results[str(seg['id']).lower()] = {"text": txt_en, "emotion": "CANTORIA"}
            continue
        
        # Filtro de Vocalização (Preserva o áudio original de suspiros, grunhidos e expressões universais)
        clean_txt = txt_en.lower().replace("!", "").replace("?", "").replace(".", "").replace(",", "").strip()
        
        # Lista de palavras curtas reais que NÃO devem ser ignoradas pelo tradutor
        real_words = {"no", "yes", "yeah", "go", "we", "he", "me", "us", "hi", "in", "on", "it", "do", "up", "so", "to", "be", "if", "is"}
        
        is_reaction = (clean_txt in vocal_noises or len(clean_txt) <= 2) and (clean_txt not in real_words)
        
        if is_reaction:
            results[str(seg['id']).lower()] = {"text": txt_en, "emotion": "CANTORIA"}
            continue

        # --- AGENTE 1: O TRADUTOR (Instruct/Chat Formatted) ---
        duration = float(seg.get('end', 0.0)) - float(seg.get('start', 0.0))
        if duration <= 0:
            duration = 2.0
        char_limit = int(duration * 16.0)
        char_limit = max(12, char_limit)  # Garante pelo menos 12 caracteres para falas muito curtas

        prompt_tradutor = (
            "<start_of_turn>user\n"
            "Você é um Tradutor e Adaptador de Dublagem Sênior de Cinema e Videogames.\n"
            "Sua missão é traduzir a fala a seguir para o Português Brasileiro (PT-BR) de forma coloquial, orgânica e fluida, adequada para dublagem e sincronização labial.\n\n"
            f"{context_str}"
            f"{glossary_str}"
            "DIRETRIZES DE TRADUÇÃO:\n"
            "1. EVITE TRADUÇÃO LITERAL (AO PÉ DA LETRA): Traduza expressões idiomáticas e gírias pelo seu equivalente cultural em português.\n"
            "   - 'That's a pretty good start.' -> 'É um bom começo.' ou 'Já é um ótimo começo.' (NUNCA traduzir literalmente como 'Um começo bem bom').\n"
            "   - 'Where have you been?' -> 'Onde você esteve?' ou 'Por onde você andou?' (NUNCA traduzir como 'Cadê você?').\n"
            "   - 'on board' -> 'a bordo' (se referindo a navios/naves/veículos), não 'aqui dentro'.\n"
            "   - 'Well' no início da frase -> traduzir de forma natural como 'Bom...' ou 'Bem...', e NUNCA usar gírias regionais/cariocas como 'Pô...' a menos que instruído.\n"
            "   - 'No.' -> 'Não.' (Sempre traduza 'No' e 'Yeah', NUNCA deixe em inglês).\n"
            "   - 'Yeah.' -> 'Sim.' ou 'É.' (Sempre traduza 'Yeah' e 'No').\n"
            "   - 'tiptoes back in' -> 'volta de fininho' / 'retorna de mansinho' (NUNCA 'puxar dedos dos pés').\n"
            "   - 'lasers someone's face off' -> 'derrete a cara com laser' / 'frita o rosto com laser' (NUNCA usar 'laser' como verbo como 'dele laser').\n"
            "   - 'They're gonna chop her' -> se o contexto envolver helicóptero ('chopper'), significa 'Vão derrubá-lo' ou 'Eles vão nos interceptar' (NUNCA 'desmembrá-la' ou 'cortá-la').\n"
            "   - 'run the red' -> 'fura o sinal vermelho' / 'fura o vermelho' (NUNCA 'passa pelo vermelho').\n"
            "   - 'Copy that' -> 'Entendido!' / 'Copiado!' / 'Na escuta!'.\n"
            f"2. LIMITE DE COMPRIMENTO OBRIGATÓRIO: A tradução deve ter no máximo {char_limit} caracteres (incluindo espaços) para caber no tempo de {duration:.2f} segundos da fala original, mantendo a sincronia labial. Seja conciso e reescreva de forma mais curta se necessário.\n"
            "3. SEM OMISSÕES: Traduza a frase completa. Nunca omita complementos ou detalhes importantes (ex: 'outside the ship' -> 'do lado de fora da nave').\n"
            "4. ADAPTAÇÃO: Se o tom for ação ou drama, adapte as frases para que soem naturais, dramáticas e com impacto coloquial brasileiro.\n"
            "5. REGRA DO FLUXO: Se o texto original já estiver em Português do Brasil, repita-o exatamente igual.\n"
            "6. SAÍDA LIMPA: Responda APENAS com a tradução final adaptada, sem aspas externas desnecessárias, sem justificativas ou notas explicativas.\n\n"
            f"Texto para traduzir: \"{txt_en}\"<end_of_turn>\n"
            "<start_of_turn>model\n"
        )
        
        out_trad = llm(prompt_tradutor, max_tokens=256, temperature=0.1, stop=["\n\n", "EN:", "###", "<end_of_turn>"])
        traducao_raw = out_trad['choices'][0]['text'].strip()
        
        # [RETRY_FALLBACK] Se veio vazio, tenta com mais 'liberdade'
        if not traducao_raw or len(traducao_raw) < 1:
            out_trad = llm(prompt_tradutor, max_tokens=256, temperature=0.7, repeat_penalty=1.5)
            traducao_raw = out_trad['choices'][0]['text'].strip()

        # --- AGENTE 2: O DIRETOR ---
        prompt_diretor = (
            f"Texto: \"{txt_en}\"\n"
            f"Contexto: {context}\n"
            f"Escolha a emoção [RAIVA, TRISTE, FELIZ, URGENTE, SUSPENSE, DRAMATICO, NORMAL].\n"
            f"REGRA EXTRA: Se o texto for apenas onomatopeias, repetições de sílabas sem sentido ou parecer uma música (ex: 'me me me', 'aaaaaah', 'la la la', 'yeah yeah'), escolha OBRIGATORIAMENTE a emoção [CANTORIA].\n"
            f"Responda apenas com a palavra da emoção.\n"
            f"Emoção:"
        )
        out_dir = llm(prompt_diretor, max_tokens=20, temperature=0.1, stop=["\n", "Contexto:"])
        emocao_raw = out_dir['choices'][0]['text'].strip().upper()

        def clean_hallucination(t):
            t = t.strip() # [v2026.NEWLINE_FIX] Limpa quebras de linha e espaços no início/fim para evitar splits vazios!
            # Remove lixo comum que o Gemma gera quando alucina
            t = t.replace("```", "").replace("`", "").replace("🔴", "").replace("🟢", "").replace("JUSTIFICATIVA:", "")
            t = re.sub(r'[^\w\s.,!?;:áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ-]', '', t)
            
            # [v2026.CHOICE_FIX] Se o Gemma deu opções (ex: 'X ou Y'), pega apenas a primeira
            if " ou " in t: t = t.split(" ou ")[0]
            if " or " in t: t = t.split(" or ")[0]
            
            return t.split('\n')[0].strip()

        traducao = clean_hallucination(traducao_raw)
        emocao_limpa = clean_hallucination(emocao_raw).split()
        emocao = emocao_limpa[0] if emocao_limpa else "NORMAL"
        
        if emocao not in ["RAIVA", "TRISTE", "FELIZ", "URGENTE", "SUSPENSE", "DRAMATICO", "NORMAL"]:
            emocao = "NORMAL"

        if not traducao or len(traducao) < 2:
            traducao = txt_en # Fallback final: original

        results[str(seg['id']).lower()] = {"text": traducao, "emotion": emocao}
        logging.info(f"🎭 [DUO-AGENT] {seg['id']} | T: {traducao} | E: {emocao}")

        if debug_file:
            try:
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] ID: {seg['id']} | T_RAW: '{traducao_raw}' | E_RAW: '{emocao_raw}'\n")
            except: pass

        # [v2026.RTX_CLEAN] Fim do processamento do segmento via Duo-Agent
        
    return results

def gema_atomic_processor_v3(item, context_window_str, glossary={}, profile_id='padrao', job_dir=None):
    """
    [v2026.ACTING_PROCESSOR]
    Usa o Gemma 4 para traduzir e detectar a emoção da cena simultaneamente.
    """
    profile = load_game_profile(profile_id)
    ai_style = profile.get("ai_instructions", "Estilo: Tradução natural e orgânica (PT-BR).")
    
    # [v21.11] Injeção de Glossário
    glossary_str = ""
    if glossary:
        glossary_items = [f"- {en} -> {pt}" for en, pt in glossary.items()]
        glossary_str = "[GLOSSÁRIO OBRIGATÓRIO]:\n" + "\n".join(glossary_items)
        
    prompt = (
        f"Tarefa: Diretor de Dublagem e Tradutor Atômico v2026.\n"
        f"Perfil: {ai_style}\n{glossary_str}\n"
        f"Contexto da Cena:\n{context_window_str}\n\n"
        f"Regras de Ouro:\n"
        f"1. Traduza OBRIGATORIAMENTE para PT-BR (Brasileiro).\n"
        f"2. Analise o contexto e defina a emoção: [RAIVA, TRISTE, FELIZ, URGENTE, SUSPENSE, DRAMATICO, NORMAL].\n"
        f"3. Limite={int(item.get('duration', 0) * 16.0)} chars.\n"
        f"4. EVITE TRADUÇÃO LITERAL (AO PÉ DA LETRA): Traduza gírias e expressões para soar natural no português coloquial do Brasil. Exemplos:\n"
        f"   - 'That's a pretty good start.' -> 'É um bom começo.' ou 'Já é um ótimo começo.' (NÃO traduzir como 'Um começo bem bom').\n"
        f"   - 'Where have you been?' -> 'Onde você esteve?' ou 'Por onde você andou?' (NÃO traduzir como 'Cadê você?').\n"
        f"   - 'on board' -> 'a bordo' (se referindo a navios/naves/veículos), não 'aqui dentro'.\n"
        f"   - 'Well' no início da frase -> traduzir de forma natural como 'Bom...' ou 'Bem...', e NUNCA usar 'Pô...'.\n"
        f"   - 'No.' -> 'Não.' (Sempre traduza 'No' e 'Yeah', nunca deixe em inglês).\n"
        f"   - 'Yeah.' -> 'Sim.' ou 'É.' (Sempre traduza 'Yeah' e 'No').\n"
        f"   - 'tiptoes back in' -> 'volta de fininho' ou 'entra de mansinho' (NÃO traduza como 'puxar dedos dos pés').\n"
        f"   - 'lasers someone's face' -> 'frita a cara com laser' ou 'derrete o rosto com laser' (NÃO use 'laser' como verbo como 'dele laser').\n"
        f"   - 'chop her' (se referindo a helicóptero/chopper) -> 'derrubá-lo' ou 'interceptar' (NÃO traduza como 'desmembrar' ou 'cortar').\n"
        f"   - 'run the red' -> 'fura o sinal vermelho' ou 'fura o vermelho' (NÃO traduza como 'passa pelo vermelho').\n"
        f"   - 'Copy that' -> 'Entendido!' / 'Copiado!'.\n"
        f"5. SEM OMISSÕES: Traduza a frase completa. Nunca omita complementos ou detalhes importantes (ex: 'outside the ship' -> 'do lado de fora da nave').\n\n"
        f"Entrada Alvo: ID={item['id']} | EN='{item.get('original_text', '')}'\n\n"
        f"Responda APENAS um JSON no formato: {{\"text\": \"sua_tradução\", \"emotion\": \"EMOÇÃO_DETECTADA\"}}"
    )

    payload = {
        "messages": [
            {"role": "system", "content": "Você é um Diretor de Localização Sênior. Responda APENAS o JSON solicitado. Nunca deixe o texto em inglês. Evite traduções literais e adapte gírias/expressões de forma natural para o português brasileiro."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3, "max_tokens": 1024
    }

    try:
        response = make_gema_request_with_retries(payload, is_translation=True)
        content = response.json()['choices'][0]['message']['content'].strip()
        
        # Tenta extrair o JSON (limpa possíveis tags de markdown ```json)
        json_str = re.search(r'\{.*\}', content, re.DOTALL)
        if json_str:
            data = json.loads(json_str.group())
            final_text = data.get('text', '').strip()
            item['emotion'] = data.get('emotion', 'NORMAL').upper()
        else:
            # Fallback se a IA não mandou JSON
            final_text = clean_ai_translation(content, item.get('original_text', ''))
            item['emotion'] = "NORMAL"
            
        return final_text
    except Exception as e:
        logging.error(f"Erro no Processador Atômico [{item['id']}]: {e}")
        item['emotion'] = "NORMAL"
        return item.get('original_text', '') 

def same_word_count_check(original, translated):
    """
    Heurística simples para detectar tradução literal (Google Tradutor).
    Se o número de palavras for idêntico e a frase for longa, há risco de literalidade excessiva.
    """
    words_orig = len(original.split())
    words_trans = len(translated.split())
    
    # Se a contagem de palavras é idêntica e a frase tem mais de 5 palavras
    if words_orig == words_trans and words_orig > 5:
        return True
    return False

def gema_etapa_correcao_master(original_text, current_translation, duration, reason="sincronia", profile_id='padrao'):
    """
    [v14.50 CORRETOR MASTER] - O Agente que resolve tudo.
    Recebe um diagnóstico (ex: muito longo, robótico) e corrige a frase.
    """
    profile = load_game_profile(profile_id)
    lore_text = profile.get("lore", "Gênero: Jogo de Aventura/Ação")
    target_chars = int(duration * 18)
    
    prompt = (
        f"Tarefa: Corretor Master v2026.\n"
        f"Lore: {lore_text}\n"
        f"Problema: {reason}\n"
        f"Original: {original_text}\n"
        f"Atual: {current_translation}\n"
        f"Regra: Max={target_chars} chars.\n"
        f"Regra de Adaptação: Garanta coloquialidade em PT-BR. Evite traduções literais (ex: 'tiptoes' -> 'de fininho', 'chop her' -> 'derrubá-lo', 'lasers' -> 'derrete a cara com laser').\n"
        f"Retorne apenas a frase corrigida entre aspas."
    )

    try:
        payload = {
            "messages": [
                {"role": "system", "content": "Você é um Diretor de Localização. Responda apenas o texto corrigido entre aspas. Evite traduções literais e mantenha a fala 100% natural. Proibido conversar."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4096
        }
        
        response = make_gema_request_with_retries(payload, is_translation=False)
        content = response.json()['choices'][0]['message']['content'].strip()
        
        # [v21.0] Usa a limpeza padrão para evitar vazamento de 'thought'
        final_text = clean_ai_translation(content, original_text)
        return final_text
        
    except Exception as e:
        logging.error(f"Erro no Agente de Correção Master: {e}")
        return current_translation


def gema_batch_corrector_master(failed_items, cenario_ctx, profile_id='padrao', job_dir=None):
    """
    [v14.60 SUPER TURBO BATCH CORRECTOR]
    Corrige múltiplas traduções ruins de uma só vez para máxima performance.
    [v18.50 REGEX ULTRA-ROBUSTA]
    """
    if not failed_items: return {}
    
    profile = load_game_profile(profile_id)
    lore_text = profile.get("lore", "Gênero: Jogo de Aventura/Ação")
    
    prompt = (
        f"Tarefa: Corretor Batch v2026.\n"
        f"Lore: {lore_text} | Contexto: {cenario_ctx}\n"
        f"Regras: Formato=id: \"Corrigido\"; Sem explicacoes; Sem repeticoes.\n"
        f"Entrada:\n"
    )
    for item in failed_items:
        prompt += f"- {item['id']}: EN=\"{item.get('original_text', '')}\" -> RUIM=\"{item.get('translated_text', '')}\"\n"

    try:
        payload = {
            "messages": [
                {"role": "system", "content": "Você é um Corretor de Dublagem. Responda apenas o ID e o texto entre aspas. Proibido conversar."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2, "max_tokens": 2048
        }
        
        response = make_gema_request_with_retries(payload, is_translation=False)
        content = response.json()['choices'][0]['message']['content'].strip()
        
        # [v18.50 DIAGNÓSTICO]
        if job_dir:
            try:
                log_file = Path(job_dir) / "ia_batch_debug.log"
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n--- CORRETOR {datetime.now()} ---\n{content}\n")
            except: pass

        # Extrator Robusto Master (Mesmo do Batch v19.0)
        results = {}
        item_pattern = r'(?:^|\n)[ \t]*(?:[0-9]+\.?[ \t]*)?(?:id\s*[:\-]\s*)?([a-zA-Z0-9_\-\.]+)\s*[:\-=>]+\s*"?\s*(.*?)\s*"?(?=\n[ \t]*(?:[0-9]+\.?[ \t]*)?(?:id\s*[:\-]\s*)?[a-zA-Z0-9_\-\.]+\s*[:\-=>]+|$)'
        matches = re.finditer(item_pattern, content, re.DOTALL)
        
        for match in matches:
            clean_id = match.group(1).strip().lower()
            val = match.group(2).strip().strip('"')
            results[clean_id] = val
            
        return results

    except Exception as e:
        logging.error(f"Erro no Batch Corrector Master: {e}")
        return {}

def gema_vibe_master_analyzer(batch_items, cenario_ctx):
    """
    [v2026.PROFISSIONAL] - O Cérebro de Localização.
    Analisa o lote de frases em inglês e define o tom ideal para dublagem.
    """
    if not batch_items: return {"vibe": "CASUAL_NATURAL", "genero": "SOCIAL"}
    
    prompt = f'''
VOCÊ É UM DIRETOR DE DUBLAGEM E LOCALIZAÇÃO.
Sua missão é classificar o tom emocional deste lote de frases em inglês.

[CATEGORIAS DE TOM]:
- 'DRAMATICO_SERIO': Use apenas se houver forte carga emocional, tristeza ou tensão extrema.
- 'TECNICO_FORMAL': Use para tutoriais, narrações informativas ou diálogos muito polidos.
- 'CASUAL_NATURAL' (PADRÃO): Use para conversas normais, diálogos de dia-a-dia ou ação.

[REGRA DE OURO]:
- PRIORIZE A FIDELIDADE. Não invente gírias agressivas.
- Mantenha a alma do original, adaptando apenas o necessário para soar natural no Brasil.

[CONTEXTO ATUAL]: {cenario_ctx}

[LISTA DE FRASES]:
'''
    for item in batch_items:
        prompt += f"- \"{item.get('original_text', '')}\"\n"

    prompt += "\nResponda APENAS um JSON no formato: {\"vibe\": \"URGENTE ou NARRATIVO\", \"genero\": \"MILITAR ou SOCIAL\", \"auditoria\": {\"frase_original_aqui\": \"frase_corrigida_caso_nonsense\"}}"

    try:
        payload = {
            "messages": [
                {"role": "system", "content": "Você é Analista de Vibe. Responda apenas a tag. Proibido conversar."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 64
        }
        
        response = make_gema_request_with_retries(payload, is_translation=False)
        content = response.json()['choices'][0]['message']['content'].strip()
        
        # Tenta extrair o JSON da IA
        vibe = "ZOEIRA_LIBERADA"
        genero = "SOCIAL"
        auditoria = {}
        
        json_match = re.search(r'\{.*?\}', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                vibe = data.get("vibe", "URGENTE").upper()
                genero = data.get("genero", "SOCIAL").upper()
                auditoria = data.get("auditoria", {})
            except: pass
            
        # [v18.0 HEURÍSTICA E AUDITORIA]
        # Aplica a auditoria nas strings do lote
        for item in batch_items:
            orig = item.get('original_text', '')
            if orig in auditoria:
                logging.info(f"   -> 🦎 [AUDITORIA] Corrigindo inglês: '{orig}' -> '{auditoria[orig]}'")
                item['original_text'] = auditoria[orig]

        # Se IA falhar no JSON, mas palavras de combate estiverem lá, força o gênero MILITAR
        all_text = " ".join([item.get('original_text', '').lower() for item in batch_items])
        combat_keywords = ["clear", "contact", "roger", "frag", "hostile", "target", "enemy", "fire", "secure", "sector", "area", "balcony"]
        if any(w in all_text for w in combat_keywords):
            genero = "MILITAR"

        return {"vibe": vibe, "genero": genero}

    except Exception as e:
        logging.error(f"Erro no Vibe Master / Auditor: {e}")
        return {"vibe": "URGENTE", "genero": "SOCIAL"}

def agente_2_matematico_python(texto_pt, duration):
    """
    [O Fiscal Matemático Frio - Agente 2]
    Calcula se a tradução PT-BR caberá mecanicamente no limitador TTS.
    """
    if not texto_pt or duration <= 0:
        return {"aprovado": False, "dossie": "Dados insuficientes ou texto vazio."}
        
    # [ESTRUTURA DE TEMPO DO CHATTERBOX 2026]
    # O Chatterbox consegue falar de forma compreensível até 18.5 caracteres por segundo
    MAX_CPS = 18.5
    limite_max_caracteres = int(duration * MAX_CPS)
    
    # O tamanho visual do texto afeta menos o motor de voz do que as vírgulas (que causam pausas forçadas)
    commas = texto_pt.count(',')
    pontos = texto_pt.count('.') + texto_pt.count('!') + texto_pt.count('?')
    
    # Cada pausa artificial equivale a mais ou menos meio segundo perdidos.
    # Em "letras virtuais" que ocupam espaço:
    peso_pausas_em_caracteres = (commas * 8) + (pontos * 10)
    
    tamanho_efetivo = len(texto_pt) + peso_pausas_em_caracteres
    
    # Aprovação direta!
    if tamanho_efetivo <= limite_max_caracteres:
        return {"aprovado": True, "dossie": ""}
        
    estouro = tamanho_efetivo - limite_max_caracteres
    
    # Elabora o dossiê perfeitamente mastigado para a Inteligência do Agente 3
    dossie = (
        f"ALERTA DE SINCRONIA DE TEMPO! "
        f"Nós temos apenas {round(duration, 2)} segundos, o que permite um tamanho MÁXIMO de {limite_max_caracteres} letras. "
        f"A sua tradução bateu {tamanho_efetivo} letras (estimadas com pausas). "
        f"Você ESTOUROU o tempo. É estritamente OBRIGATÓRIO que você corte, no mínimo, {estouro + 5} letras dessa tradução "
        f"reescrevendo-a de forma natural e resumida."
    )
    return {"aprovado": False, "dossie": dossie}

def agente_3_adaptador_final_lqa(original_text, translated_text, dossie, timeout=3600):
    """
    [O Editor Chefe - Agente 3]
    Só é chamado quando a sirene toca no Fiscal. Ele encurta orações com extremo senso crítico.
    """
    prompt = f'''
VOCE E UM EDITOR DE DUBLAGEM GENIO. A traducao chegou, mas ELA E GRANDE DEMAIS PARA O TEMPO DO AUDIO.

[DIAGNOSTICO DO FISCAL DE TEMPO]:
{dossie}

[INGLES ORIGINAL A TITULO DE CONTEXTO]:
"{original_text}"

[TRADUCAO ORIGINAL - VOCE DEVE ENCURTAR ISSO]:
"{translated_text}"

[SUA TAREFA]:
Reescreva a [TRADUCAO ORIGINAL]. Seja agressivo nos cortes de palavras inuteis. Use contracoes ("Nos estamos" vira "Estamos", "De o" vira "Do", "Para" vira "Pra"). Mantenha a emocao natural do Brasil.

[FORMATO EXIGIDO]:
"Sua adaptacao curtinha final vai aqui dentro das aspas, e MAIS NADA."

Responda APENAS com a nova traducao resumida e perfeita. Nenhuma palavra de explicacao.
'''

    payload = {
        "messages": [
            {"role": "system", "content": "O texto não cabe! Adaptando, resumindo e retornando só a versão PT-BR reescrita e ultra-condensada dentro de aspas."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2, # Um pouco mais de criatividade para resumir
        "max_tokens": 1024
    }
    
    try:
        response = make_gema_request_with_retries(payload, timeout=timeout, is_translation=False)
        content = response.json()['choices'][0]['message']['content'].strip()
        
        # O modelo já tem a mesma trava de aspas, então herdamos esse parseamento
        return clean_ai_translation(content, original_text)
    except Exception as e:
        logging.error(f"Erro Crítico no Agente 3 Adaptador: {e}")
        return translated_text # Fallback para o excedente, pois é melhor fala estourada do que erro vazio

def select_best_sync_option(original_duration, options_list, original_text):
    """
    Seleciona a melhor opção de sincronização baseada em critérios matemáticos e linguísticos.
    """
    best_opt = None
    best_score = float('inf')
    target_rate = 18.0 # [v12.95 UPDATED] Sincronia de 18 Letras/s (Fórmula do Usuário)
    
    # Validação básica
    valid_options = [opt.strip() for opt in options_list if opt and len(opt.strip()) > 0]
    if not valid_options: return None

    logging.info(f"Avaliando {len(valid_options)} candidatos para duração {round(original_duration, 2)}s...")

    for opt in valid_options:
        # Limpeza básica
        clean_opt = re.sub(r'^\d+[\.\-\)]\s*', '', opt).strip('"').strip()
        if not clean_opt: continue

        if not clean_opt: continue
        
        # Limpeza de Vírgulas Duplas e Pontuação excessiva HALLUCINATED
        clean_opt = re.sub(r',+', ',', clean_opt) # ,, -> ,
        clean_opt = re.sub(r'[\.,;]+$', '', clean_opt) # Remove pontuação final redundante na contagem
        
        # [v12.97 MATH] Custo Real: Letras + Vírgulas INTERNAS (meio segundo cada vírgula)
        # O usuário explicou que vírgulas no FINAL da frase não devem consumir tempo.
        commas_count = clean_opt.rstrip(',').count(',')
        comma_time_cost = commas_count * 0.5
        
        # Caracteres efetivos (sem contar as vírgulas que já viraram tempo)
        text_only = re.sub(r'[,]', '', clean_opt)
        effective_char_count = len(text_only)
        
        # Tempo estimado total da frase (Fala + Pausas)
        estimated_time = (effective_char_count / target_rate) + comma_time_cost
        
        # Score baseado no erro absoluto de tempo em relação ao áudio original
        score = abs(estimated_time - original_duration)
        
        # [v12.91] Penalidade se o CPS das letras for insano (> 22) mesmo com vírgulas
        cps_letters = effective_char_count / (original_duration - comma_time_cost) if (original_duration - comma_time_cost) > 0.1 else 99
        if cps_letters > 22:
             score += (cps_letters - 22) * 5.0
 

        # 3. Regra de Ouro para Áudios Curtos (< 1.2s)
        if original_duration < 1.2:
            words = clean_opt.split()
            # Penaliza severamente 1 palavra isolada, a menos que o original seja curto também
            if len(words) < 2 and len(original_text.split()) > 1:
                score += 50 
            # Bônus para frases nominais completas (ex: "Perímetro perdido")
            if len(words) >= 2:
                score -= 5

        e_t_f = round(estimated_time, 2)
        sc_f = round(score, 2)
        logging.info(f"   - Candidato: '{clean_opt}' | Est.Time: {e_t_f}s | Score: {sc_f}")
        if original_duration < 1.2:
            words = clean_opt.split()
            # Penaliza severamente 1 palavra isolada, a menos que o original seja curto também
            if len(words) < 2 and len(original_text.split()) > 1:
                score += 50 
            # Bônus para frases nominais completas (ex: "Perímetro perdido")
            if len(words) >= 2:
                score -= 5

        logging.info(f"   - Candidato: '{clean_opt}' | CPS: {cps_letters:.1f} | Score: {score:.1f}")

        if score < best_score:
            best_score = score
            best_opt = clean_opt
            
    return best_opt

def apply_string_fallback(text, max_chars):
    """
    Fallback de emergência: Remove artigos e advérbios se o texto estourar o limite.
    Útil quando o LLM falha em respeitar o tamanho.
    """
    if len(text) <= max_chars: return text
    
    # 1. Remove Advérbios (-mente)
    words = text.split()
    new_words = [w for w in words if not w.lower().endswith('mente')]
    new_text = " ".join(new_words)
    if len(new_text) <= max_chars: return new_text
    
    # 2. Remove Artigos (o, a, os, as, um, uns...)
    blacklist = ['o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'do', 'da', 'dos', 'das', 'no', 'na', 'nos', 'nas']
    new_words = [w for w in new_words if w.lower() not in blacklist]
    return " ".join(new_words)

def gema_lqa_reviewer_pro(original_en, candidate_pt, duration):
    """
    [PASSO 2 - LQA] O Gemma atua como um Editor Sênior de Dublagem para revisar a naturalidade.
    """
    dur_f = round(duration, 2)
    prompt = """
Voce e o Revisor-Chefe de Dublagem. Seu trabalho e GARANTIR que a traducao NAO pareca "traducao", mas sim uma fala natural de um filme brasileiro.

CENA:
Original (EN): "{original_en}"
Opcao Candidata (PT-BR): "{candidate_pt}"
Tempo disponivel: {dur_f}s

SUA MISSAO:
1. Analise se a frase em PT-BR soa natural, "cool" e narrativa.
2. GIRIA MILITAR: So aceite "Copiado" se for Roger/Copy. Se for "Gotcha", "Incoming" ou "Target", use termos de acao (Te peguei, Acertei, Alvo).
3. Se a frase estiver robotica ou muito literal, CORRIJA-A agora.
4. CONTAGEM DE TEMPO: (Letras / 18) + (Virgulas INTERNAS * 0.5) deve ser proximo de {dur_f}s.
5. REGRA DA VIRGULA: Somente virgulas no MEIO da frase consomem meio segundo de tempo. Virgulas no FINAL da frase sao gratuitas (0s).
6. NUNCA USE PONTOS FINAIS. Use apenas virgulas ou exclamacoes.

Responda APENAS com a versao final refinada entre aspas duplas.
Se a opcao candidata ja for perfeita, apenas repita-a entre aspas duplas. Irrelevante se precisar mudar pouca coisa: foque na naturalidade e no tempo {dur_f}s.
""".format(original_en=original_en, candidate_pt=candidate_pt, dur_f=dur_f)
    try:
        payload = {
            "messages": [
                {"role": "system", "content": "Você é o Juiz Sênior de Localização. Responda apenas o texto final entre aspas duplas."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 512
        }
        response = make_gema_request_with_retries(payload, is_translation=False)
        content = response.json()['choices'][0]['message']['content'].strip()
        
        quoted_match = re.search(r'"(.*?)"', content, re.DOTALL)
        if quoted_match:
             return quoted_match.group(1).strip()
        return candidate_pt # Se falhar o parse, mantemos o candidato original
    except:
        return candidate_pt

def gema_etapa_2_sincronizacao(original_text, duration, previous_context=None, profile_id='padrao'):
    """
    [v14.10 FALLBACK MASTER] - Sincronia Individual Autônoma.
    Usada como redundância caso o lote falhe.
    """
    profile = load_game_profile(profile_id)
    lore_text = profile.get("lore", "Gênero: Jogo de Aventura/Ação (Autodetecção Ativada)")
    target_chars = int(duration * 18)
    temperature = 0.2
    
    prompt = f'''
# DIRETRIZES DE DUBLAGEM INDIVIDUAL (MASTER SYNC)

[TAREFA]: Traduza e SINCRONIZE a frase abaixo mantendo a "vibe" do jogo.

[CONTRATO DE SINCRONIA]:
- LIMITE DE TEMPO: {round(duration, 2)} segundos.
- CALCULO: (Letras / 18) + (Virgulas Internas * 0.5) <= {round(duration, 2)}s.
- PONTUACAO: PROIBIDO PONTOS (.). Use virgulas ou !/?.
- TABELA DE GIRIAS: "Roger" -> "Copiado!", "Gotcha" -> "Na mira!", "Cover me" -> "Me cobre!".
- EVITE TRADUÇÃO LITERAL: "tiptoes back in" -> "volta de fininho" (NÃO "puxar dedos dos pés"), "lasers someone's face" -> "derrete a cara com laser" (NÃO "dele laser"), "chop her" -> "derrubá-lo" se helicóptero (NÃO "desmembrar").

[LORE]: {lore_text} 
[HISTORICO]: {previous_context if previous_context else "Inicio"}

[FRASE ORIGINAL (EN)]: 
"{original_text}"

Responda APENAS com a traducao final entre aspas duplas: "Sua traducao aqui!"
'''

    try:
        payload = {
            "messages": [
                {"role": "system", "content": "Você é um Diretor de Sincronia. Sua resposta deve conter APENAS o texto traduzido final e adaptado entre aspas duplas. Evite traduções literais ao pé da letra. Proibido conversar."},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": 512
        }
        
        response = make_gema_request_with_retries(payload, is_translation=False)
        content = response.json()['choices'][0]['message']['content'].strip()
        
        # Extrator Inteligente de Aspas
        quoted_match = re.search(r'"(.*?)"', content, re.DOTALL)
        if quoted_match:
             final_text = quoted_match.group(1).strip()
             return apply_string_fallback(final_text, target_chars or 999), 1
        
        # Fallback se não usar aspas
        return apply_string_fallback(original_text, target_chars or 999), 2
        
    except Exception as e:
        logging.error(f"Erro no Fallback Sync Gema: {e}")
        return original_text, 2

def sanitize_tts_text(text):
    """
    Remove pontuação e resíduos de prompt da IA (Contexto Anterior, RESPOSTA DEFINITIVA, etc).
    """
    if not text: return ""
    
    # [v12.21 PENTE-FINO] Remove labels de alucinação (ex: "Contexto Anterior: ...")
    prompt_labels = r"(?im)^(Contexto|Resposta|Original|Tradução|Style|Timing|Scenario|Note|Tradução Adaptada|Texto).*?:.*?\n?"
    text = re.sub(prompt_labels, "", text)

    # 1. Normalização Básica (Trocamos reticências por nada, e não por vírgulas mais)
    text = text.replace("...", " ").replace("..", " ").replace("—", " ")
    
    # 2. [NOVO] Expansor de Números e Ordinais Automático para TTS (Anti-Engasgo)
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


    # 4. Whitelist de Símbolos e Caracteres (Permite %, $, +, @, vídeo-games vibes)
    # [v12.97 UPDATED] Agora inclui símbolos vitais para narrativa de jogos.
    text = re.sub(r'[^\w\s\,\!\?\-\%\$\+\@áéíóúâêîôûãõàèìòùçÁÉÍÓÚÂÊÎÔÛÃÕÀÈÌÒÙÇ]', '', text)
    
    # [v12.98 CLEANUP] Remove conflitos de pontuação no final (ex: ",!" ou "!,")
    # Isso evita problemas no Chatterbox que "trava" com pontuação dupla exótica.
    text = text.replace(",!", "!").replace("!,", "!").replace("?,", "?").replace(",?", "?")
    
    # 3. [v12.96 PROIBIÇÃO DO PONTO]
    # O usuário reportou que pontos (.) bugam o Chatterbox e causam alucinações.
    # Exterminamos todos os pontos remanescentes.
    text = text.replace(".", "")
    
    # [v2026.41] Regra de Colagem: Remove espaços artificiais em sufixos comuns
    # Isso evita que o "Contato" vire "Cont ato" e o "Cuidado" vire "Cuid ado".
    text = text.replace(" ato", "ato").replace(" ado", "ado").replace(" ote", "ote")
    
    # 4. Limpa espaços duplos e evita vírgulas duplas/triplas
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r',+', ',', text) # Garante que não tenha ",,"
    
    # [v12.96 GPT-SOVITS EOS TOKEN FIX]
    # Usamos Exclamação (!) ou Interrogação (?) como fallback EOS, NUNCA ponto.
    if text and not text.endswith(('!', '?')):
        text += "!"
        
    return text
        
    return text

# Alias para compatibilidade
def gema_etapa_3_sanitizacao(text):
    return sanitize_tts_text(text)

def gema_etapa_3_adaptacao_tts(synced_text, is_retry=False):
    prompt_normal = f"""Você é um editor de roteiros para o motor de voz Chatterbox (TTS). Adapte o texto a seguir para uma leitura 100% natural.
**REGRAS CRÍTICAS:**
1.  **PAUSAS NATURAIS:** Use vírgulas para indicar pausas curtas onde o orador deve respirar (Cada vírgula = meio segundo).
2.  **PROIBIÇÃO TOTAL DE PONTOS:** NUNCA use o caractere de ponto (.). O Chatterbox entra em colapso e alucina se ler um ponto final. Use vírgulas (,) ou exclamações (!).
3.  **NÚMEROS POR EXTENSO:** OBRIGATORIAMENTE escreva números por extenso para o robô ler certo (ex: transforme "04" em "zero quatro", "25%" em "vinte e cinco por cento").
4.  **HÍFENS PERMITIDOS:** Use hífens normalmente em palavras compostas.
5.  **FORMATO:** Responda APENAS com o texto adaptado entre aspas duplas.
**Texto Original:** "{synced_text}"
**Texto Adaptado:**"""
    prompt_retry = f"""Ajuste a pontuação deste texto para um robô de voz ler. Responda entre aspas duplas.
Texto: "{synced_text}"
Texto Ajustado:"""
    prompt = prompt_retry if is_retry else prompt_normal
    payload = {"messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "max_tokens": 1000}
    try:
        response = make_gema_request_with_retries(payload)
        return sanitize_tts_text(response.json()['choices'][0]['message']['content'])
    except Exception as e:
        logging.error(f"Erro na API Gema (Etapa 3): {e}")
        return f"FALHA_API: {e}"

def set_low_process_priority():
    try:
        p = psutil.Process(os.getpid())
        # [v2026.POWER_FIX] Subido de BELOW_NORMAL para NORMAL para evitar que o Windows trave o motor no Whisper
        p.nice(psutil.NORMAL_PRIORITY_CLASS if sys.platform == "win32" else 0)
        logging.info("Prioridade do processo definida como 'normal' para garantir estabilidade.")
    except Exception:
        logging.warning("Não foi possível definir a prioridade do processo.")

# ... (O resto das funções permanece o mesmo, para economizar espaço)

# --- MÓDULO NEXUS: CORTE INTELIGENTE DE SILÊNCIO (SMART TRIM) ---
def smart_whisper_trim(audio_path, expected_text):
    """
    [v2026.20] Usa Whisper (word_timestamps) para achar o milissegundo exato da primeira 
    e última palavra. Corta o áudio precisamente ali, mantendo uma margem de segurança.
    Retorna True se cortou, False se não precisou ou falhou.
    """
    try:
        from pydub import AudioSegment
        import librosa
        whisper_model = get_whisper_model()
        
        # A Mágica: Pedimos os timestamps por palavra!
        segments, _ = whisper_model.transcribe(str(audio_path), language="pt", word_timestamps=True)
        
        words = []
        for segment in segments:
            if hasattr(segment, 'words') and segment.words:
                words.extend(segment.words)
                
        if not words:
            logging.info(f"🛡️ Smart Trim: Nenhuma palavra clara detectada no Whisper para {Path(audio_path).name}")
            return False
            
        # --- [v2026.25] PODA DE ALUCINAÇÕES (HALLUCINATION PRUNING) ---
        if expected_text:
            import re
            import difflib
            clean_expected = re.sub(r'[^a-záéíóúâêîôûãõç\s]', '', expected_text.lower()).split()
            valid_words = []
            
            for w in words:
                clean_w = re.sub(r'[^a-záéíóúâêîôûãõç]', '', w.word.lower())
                if not clean_w: continue
                
                # Verifica se a palavra falada existe no roteiro (com 60% de tolerância para sotaque/erro de ASR)
                matches = difflib.get_close_matches(clean_w, clean_expected, n=1, cutoff=0.6)
                if matches or clean_w in clean_expected:
                    valid_words.append(w)
            
            if valid_words:
                # Se achou palavras válidas, usamos APENAS elas. O resto (eeeee, aaaaa) será cortado!
                words = valid_words
                logging.info(f"🛡️ Smart Trim: Poda de Alucinação ativada. Restaram {len(words)} palavras válidas.")

        first_word_start = words[0].start
        last_word_end = words[-1].end
        
        y, sr = librosa.load(str(audio_path), sr=None)
        total_duration = librosa.get_duration(y=y, sr=sr)
        
        # Margem de segurança de 50ms para não cortar o respiro da voz
        margin = 0.05
        crop_start = max(0, first_word_start - margin)
        crop_end = min(total_duration, last_word_end + margin)
        
        # Só cortamos se houver pelo menos 100ms de silêncio para limpar (evita cortes inúteis)
        if (crop_end - crop_start) >= (total_duration - 0.1):
            return False
            
        audio = AudioSegment.from_file(str(audio_path))
        trimmed_audio = audio[int(crop_start * 1000) : int(crop_end * 1000)]
        trimmed_audio.export(str(audio_path), format=Path(audio_path).suffix.replace('.', ''))
        
        logging.info(f"✂️ Smart Trim: {Path(audio_path).name} lapidado! De {total_duration:.2f}s para {(crop_end-crop_start):.2f}s")
        return True
    except Exception as e:
        logging.warning(f"Aviso no Smart Trim para {Path(audio_path).name}: {e}")
        return False

# --- MÓDULO NEXUS: CONTROLE DE QUALIDADE AUTOMÁTICO (LQA) ---
def nexus_lqa_validator(audio_path, original_duration, file_id, job_dir, mode='technical', expected_text=None):
    """
    Analisa a saúde do áudio.
    mode='raw': foca em integridade da IA (Cortes/Loops) -> Gatilho para REGEN.
    mode='technical': foca em equilíbrio final (Volume/Sync) -> Gatilho para HEALING.
    """
    if not audio_path or not Path(audio_path).exists():
        return "ERRO", "Arquivo não encontrado.", True # Agora obriga a gerar se sumir

    try:
        y, sr = librosa.load(str(audio_path), sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        
        status = "OK"
        warnings = []
        needs_action = False

        # --- TESTE A: SINCRONIA E CORTES ---
        # SAFEGUARD: Bypass para arquivos curtos se o áudio existir minimamente
        is_safe_duration = (duration > 0.1) and (original_duration > 0.5 and (duration / original_duration) > 0.2)
        
        ratio = duration / original_duration if original_duration > 0 else 1.0

        if original_duration > 0 and not is_safe_duration:
            if ratio < 0.70:
                status = "AVISO"
                warnings.append(f"Corte de Tempo ({ratio:.2%})")
                # Não pedimos regen imediato, deixamos o Whisper (Teste D) decidir se o conteúdo sumiu
                needs_action = False 
            elif ratio < 0.85:
                status = "AVISO"
                warnings.append(f"Fala Acelerada ({ratio:.2%})")
            
            # Estouro importa no técnico e final
            MAX_ALLOWED = (original_duration * 1.30) + 0.5
            if duration > MAX_ALLOWED:
                # [v2026.20] Tenta salvar a pátria cortando o silêncio com o Whisper
                trimmed = smart_whisper_trim(audio_path, expected_text)
                if trimmed:
                    # Recarrega o áudio para atualizar a duração
                    y, sr = librosa.load(str(audio_path), sr=None)
                    duration = librosa.get_duration(y=y, sr=sr)
                
                if duration > MAX_ALLOWED:
                    # Mesmo após o corte inteligente, ainda estourou. 
                    # Preferimos perdoar (Aceitar) do que apagar e deixar mudo.
                    status = "AVISO"
                    diff = duration - original_duration
                    warnings.append(f"Estouro Aceito (+{diff:.2f}s)")
                    needs_action = False

        # --- TESTE B: VOLUME E SILÊNCIO ---
        rms = np.sqrt(np.mean(y**2))
        db_rms = 20 * np.log10(rms) if rms > 0 else -100
        
        if db_rms < -60:
            status = "ERRO"
            warnings.append("Silêncio Excessivo")
            if mode == 'raw': needs_action = True # Pede REGEN
        elif mode == 'technical' and db_rms < -28:
            status = "ATENÇÃO"
            warnings.append(f"Volume Baixo ({db_rms:.1f}dB)")
            needs_action = True # Pede HEALING (Boost)
        elif mode == 'raw' and db_rms < -45:
             status = "ATENÇÃO"
             warnings.append("Gerado com volume muito baixo")
             needs_action = True # Pede REGEN

        # --- TESTE C: ALUCINAÇÃO ESPECTRAL (eeeEEEE) ---
        flatness = np.mean(librosa.feature.spectral_flatness(y=y))
        if flatness < 0.0001: 
             status = "AVISO"
             warnings.append("Alucinação de Loop")
             if mode == 'raw': needs_action = True # Pede REGEN

        # --- TESTE D: AUDITORIA DE CONTEÚDO (ASR) ---
        # Só fazemos isso se o texto esperado for fornecido e o áudio estiver suspeito.
        if expected_text and (status != "OK" or ratio < 0.85):
            try:
                # Carrega Whisper localmente
                whisper_model = get_whisper_model()
                
                # Transcreve o áudio dublado
                segments, _ = whisper_model.transcribe(str(audio_path), language="pt")
                heard_text = " ".join([s.text for s in segments]).strip().lower()
                clean_expected = expected_text.lower().replace(",", "").replace(".", "").replace("!", "").replace("?", "").strip()
                
                # Limpeza profunda para comparação de letras puras
                import re
                def clean_for_match(t):
                    return re.sub(r'[^a-záéíóúâêîôûãõç]', '', t.lower())
                
                pure_expected = clean_for_match(clean_expected)
                pure_heard = clean_for_match(heard_text)
                
                len_exp = len(pure_expected)
                len_heard = len(pure_heard)
                
                # SE O WHISPER NÃO OUVIU NADA -> ERRO
                if len_heard == 0 and len_exp > 0:
                    status = "ERRO"
                    warnings.append(f"Silêncio Total (ASR Vazio) [Esp: '{clean_expected}']")
                    needs_action = True
                
                # --- LÓGICA DE MISERICÓRDIA (SUPREMA CORTE NEXUS) ---
                elif len_exp > 0:
                    char_ratio = len_heard / len_exp
                    
                    # [v2026.15] PERFEIÇÃO: Se o Whisper confirmou o texto (80% - 130% das letras), limpa avisos técnicos.
                    # Reduzido threshold para ser mais 'Misericordioso' com erros de transcrição do próprio Whisper.
                    if 0.80 <= char_ratio <= 1.3:
                        logging.info(f"🛡️ Nexus: Conteúdo INTEGRAL validado via ASR ({len_heard}/{len_exp}). Limpando alertas técnicos.")
                        status = "OK"
                        warnings = ["Conteúdo validado via ASR (100%)"]
                        needs_action = False
                    
                    # [v2026.15] TOLERÂNCIA FRASES CURTAS: Se for um nome ou comando curto, aceitamos mais desvio.
                    elif len_exp < 15 and 0.5 <= char_ratio <= 2.5:
                        logging.info(f"🛡️ Nexus: Frase Curta validada via ASR ({len_heard}/{len_exp}).")
                        status = "OK"
                        warnings.append(f"(Conteúdo validado | Esp: '{clean_expected}' | ASR: '{heard_text}')")
                        needs_action = False

                    # 3. ERROS CRÍTICOS: Cortes severos ou Loops (Dobra de letras)
                    elif char_ratio < 0.60 or char_ratio > 2.0:
                        status = "ERRO"
                        warnings.append(f"Falha Semântica (ASR: {char_ratio:.2%} | Esp: '{clean_expected}' | Ouvido: '{heard_text}')")
                        needs_action = True
            except Exception as e_asr:
                logging.warning(f"Falha na auditoria ASR para {file_id}: {e_asr}")

        return status, "; ".join(warnings) if warnings else "Perfeito", needs_action

    except Exception as e:
        return "ERRO", f"Falha na análise: {e}", False

def gerar_relatorio_final(job_dir, job_id, project_data, file_format_map):
    relatorio_path = job_dir / "relatorio_processamento.txt"
    durations_cache_path = job_dir / "durations_cache.json"
    durations_cache = safe_json_read(durations_cache_path) or {}
    mastering_cache_path = job_dir / "mastering_cache.json"
    mastering_cache = safe_json_read(mastering_cache_path) or {}

    logging.info(f"Gerando relatório Nexus em: {relatorio_path}")
    
    total_arquivos = len(project_data)
    sucessos_absolutos = 0
    regenerados = project_data[0].get('nexus_regenerados_count', 0) if project_data else 0 # Tenta pegar do status
    # Como status não está aqui, vamos contar manualmente no project_data
    count_regen = sum(1 for s in project_data if "(Corrigido por Regen)" in str(s.get('lqa_raw_details', '')))
    
    alertas = []
    erros = []

    # Contabilidade e Triagem
    for seg_data in project_data:
        lqa_status = seg_data.get('lqa_status', 'OK')
        if lqa_status == 'OK': sucessos_absolutos += 1
        elif lqa_status == 'AVISO' or lqa_status == 'ATENÇÃO': alertas.append(seg_data)
        else: erros.append(seg_data)

    with open(relatorio_path, 'w', encoding='utf-8') as f:
        f.write("==================================================\n")
        f.write(f"📊 RESUMO DE QUALIDADE NEXUS - JOB: {job_id}\n")
        f.write("==================================================\n")
        
        total_seconds = sum(item.get('duration', 0) for item in project_data)
        duracao_total_formatada = str(timedelta(seconds=int(total_seconds)))
        f.write(f"Duração Total:   {duracao_total_formatada}\n")
        f.write(f"Total Segmentos: {total_arquivos}\n")
        f.write(f"Sucesso Total:   {sucessos_absolutos}/{total_arquivos} ✅\n")
        if count_regen > 0: f.write(f"Recuperados:     {count_regen} 🌀 (Regenerados pelo Nexus)\n")
        if alertas: f.write(f"Alertas LQA:     {len(alertas)} ⚠️\n")
        if erros:   f.write(f"Falhas Críticas: {len(erros)} ❌\n")
        f.write("--------------------------------------------------\n\n")

        if erros or alertas:
            f.write("==================================================\n")
            f.write("⚠️ DETALHAMENTO DE PROBLEMAS (REVISÃO MANUAL)\n")
            f.write("==================================================\n\n")
            
            for seg in (erros + alertas):
                f.write(f"[!] ARQUIVO: {seg.get('file_name', seg['id'])}\n")
                f.write(f"    - Status Nexus: {seg.get('lqa_status', 'N/A')}\n")
                f.write(f"    - Diagnóstico:  {seg.get('lqa_details', 'N/A')}\n")
                
                # Info de tempo
                orig_d = seg.get('duration', 0)
                final_d = durations_cache.get(seg['id'], {}).get('duration', 0)
                if orig_d > 0: f.write(f"    - Tempo:        Original {orig_d:.2f}s | Final {final_d:.2f}s\n")
                
                # Info de tradução se falhou
                if "FALHA_" in str(seg.get('translated_text', '')):
                    f.write(f"    - Tradução:     FALHOU ({seg.get('translated_text', 'N/A')})\n")
                
                f.write("\n")
        
        f.write("--------------------------------------------------\n")
        f.write("(Arquivos não listados acima foram auditados e aprovados pelo Nexus LQA)\n")
        f.write("==================================================\n")
        f.write(f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")

    # =========================================================================
    # [v2026.34 FIX] Geração do Relatório JSON para o AUTO-PURGE e CHECKPOINT
    # =========================================================================
    relatorio_json_path = job_dir / "relatorio_processamento.json"
    
    # Mapeia todos os segmentos para o JSON para servir de checkpoint vivo
    segmentos_json = []
    # [v2026.35] Resetamos e recalculamos para o JSON de forma limpa
    sucessos_json = 0
    for s in project_data:
        file_id = s['id']
        # [v2026.FLEX_CHECK] Tenta localizar o áudio em ambos os padrões (Video vs Games)
        possible_paths = [
            job_dir / "_dubbed_audio" / f"{file_id}_dubbed.wav",
            job_dir / "_dubbed_segments" / f"{file_id}.wav",
            job_dir / "_dubbed_segments" / f"seg_{file_id}.wav"
        ]
        # Se for índice numérico (comum no vídeo)
        if str(file_id).isdigit():
             possible_paths.append(job_dir / "_dubbed_segments" / f"seg_{file_id}.wav")
        
        audio_exists = any(p.exists() and p.stat().st_size > 1000 for p in possible_paths)
        
        status_item = {
            "id": file_id,
            "file_name": s.get('file_name', f"{file_id}.wav"),
            "status_lqa": s.get('lqa_status', 'OK' if audio_exists else 'PENDENTE'),
            "diagnostico": s.get('lqa_details', ''),
            "gerado": audio_exists,
            "texto": s.get('manual_edit_text', s.get('sanitized_text', s.get('text_pt', '')))
        }
        segmentos_json.append(status_item)
        if audio_exists: sucessos_json += 1

    taxa_acerto = (sucessos_json / total_arquivos * 100) if total_arquivos > 0 else 0
    # Sincroniza o contador absoluto para a mensagem de retorno
    sucessos_absolutos = sucessos_json
    
    json_data = {
        "job_id": job_id,
        "total_segments": total_arquivos,
        "success_count": sucessos_absolutos,
        "failed_count": len(erros),
        "alert_count": len(alertas),
        "success_rate": round(taxa_acerto, 2),
        "segments": segmentos_json,
        "data_atualizacao": datetime.now().isoformat(),
        "status_geral": "perfeito" if taxa_acerto == 100 else "bom" if taxa_acerto > 80 else "revisar"
    }
    safe_json_write(json_data, relatorio_json_path)

# --- FUNÇÕES PRINCIPAIS DOS PIPELINES ---
def processar_transcricao(job_dir, job_id, start_time):
    with active_jobs_lock:
        if len(active_jobs) >= MAX_CONCURRENT_JOBS:
            logging.warning(f"❌ [HARDWARE] Limite de {MAX_CONCURRENT_JOBS} job(s) atingido. Ignorando {job_id}.")
            return
        active_jobs.add(job_id)

    try:
        set_low_process_priority()
        def cb(p, etapa, s=None, **kwargs): set_progress(job_id, p, etapa, start_time, ETAPAS_TRANSCRICAO, s, **kwargs)
        
        input_file = next(job_dir.glob('input.*'), None)
        if not input_file:
            raise FileNotFoundError("Nenhum arquivo de entrada encontrado no diretório do job.")

        backup_dir = job_dir / "_backup_transcricao_whisper"
        backup_dir.mkdir(exist_ok=True)
        
        cb(5, 1, "Carregando modelo Whisper...")
        model = get_whisper_model()
        
        cb(10, 1, "Iniciando transcrição...")
        
        segments, info = model.transcribe(str(input_file))
        total_duration = info.duration
        
        all_segments_data = []
        
        for segment in segments:
            progress = (segment.end / total_duration) * 100 if total_duration > 0 else 100
            tempo_atual = str(timedelta(seconds=int(segment.end)))
            tempo_total = str(timedelta(seconds=int(total_duration)))
            cb(progress, 1, f"Transcrevendo... {tempo_atual}/{tempo_total}")
            
            segment_data = {
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
                "text": segment.text.strip()
            }
            all_segments_data.append(segment_data)
            
            # Backup contínuo por segmento
            safe_json_write(segment_data, backup_dir / f"segment_{segment.start:.3f}.json")
        
        cb(100, 2, "Gerando arquivos finais...")
        
        # Gerar arquivo JSON completo
        json_output_path = job_dir / "transcricao_completa.json"
        safe_json_write(all_segments_data, json_output_path)
        logging.info(f"Arquivo JSON da transcrição salvo em: {json_output_path}")

        # Gerar arquivo TXT completo
        txt_output_path = job_dir / "transcricao_completa.txt"
        with open(txt_output_path, 'w', encoding='utf-8') as f:
            for seg in all_segments_data:
                f.write(f"{seg['text']}\n")
        logging.info(f"Arquivo TXT da transcrição salvo em: {txt_output_path}")

        cb(100, 3, "Transcrição concluída!")

    except Exception as e:
        logging.error(f"ERRO NO PIPELINE DE TRANSCRIÇÃO (Job ID: {job_id}): {e}\n{traceback.format_exc()}")
        set_progress(job_id, 100, len(ETAPAS_TRANSCRICAO) - 1, start_time, ETAPAS_TRANSCRICAO, subetapa=f"Erro: {e}")
        status_path = job_dir / "job_status.json"
        status_data = safe_json_read(status_path) or {}
        status_data['status'] = 'failed'
        status_data['error'] = str(e)
        safe_json_write(status_data, status_path)
    finally:
        with active_jobs_lock:
            if job_id in active_jobs:
                active_jobs.remove(job_id)


def processar_conversao(job_dir, job_id, start_time):
    with active_jobs_lock:
        if len(active_jobs) >= MAX_CONCURRENT_JOBS:
            logging.warning(f"❌ [HARDWARE] Limite de {MAX_CONCURRENT_JOBS} job(s) atingido. Ignorando {job_id}.")
            return
        active_jobs.add(job_id)
    
    try:
        set_low_process_priority()
        def cb(p, etapa, s=None, **kwargs): set_progress(job_id, p, etapa, start_time, ETAPAS_CONVERSAO, s, **kwargs)
        
        status = safe_json_read(job_dir / "job_status.json") or {}
        file_format_map = status.get('file_format_map', {})

        referencia_dir = job_dir / "_1_referencia"
        para_converter_dir = job_dir / "_2_para_converter"
        convertidos_dir = job_dir / "_3_convertidos"
        convertidos_dir.mkdir(exist_ok=True)
        
        files_to_process = list(para_converter_dir.glob("*.*"))
        total_files = len(files_to_process)
        if total_files == 0:
            cb(100, 2, "Nenhum arquivo para converter.")
            return

        reference_files_map = {p.stem: p for p in referencia_dir.glob("*.*")}
        logging.info(f"Arquivos de referência encontrados: {list(reference_files_map.keys())}")


        cb(0, 1, f"Iniciando conversão para {total_files} arquivos...")
        
        sucesso_count = 0
        for i, file_to_convert in enumerate(files_to_process):
            cb((i / total_files) * 100, 1, f"Convertendo: {file_to_convert.name}")
            
            convert_stem = file_to_convert.stem
            base_ref_stem = convert_stem.replace("_dubbed", "")
            
            ref_path = None
            if base_ref_stem in reference_files_map:
                ref_path = reference_files_map[base_ref_stem]
                logging.info(f"Referência encontrada para '{file_to_convert.name}' -> '{ref_path.name}'.")
            elif convert_stem in reference_files_map:
                ref_path = reference_files_map[convert_stem]
                logging.info(f"Referência com nome exato (stem) encontrada para '{file_to_convert.name}' -> '{ref_path.name}'.")
            else:
                logging.warning(f"Nenhum arquivo de referência encontrado para '{file_to_convert.name}' (procurando por stem: '{base_ref_stem}'). Pulando.")
                continue

            try:
                sample_rate, channels, bitrate = get_audio_metadata(str(ref_path))
                final_path = convertidos_dir / ref_path.name
                threads = str(os.cpu_count() or 4)
                cmd = ['ffmpeg', '-threads', threads, '-y', '-i', str(file_to_convert), '-ar', str(sample_rate), '-ac', str(channels), '-af', 'dynaudnorm', str(final_path)]
                if bitrate and str(bitrate).isdigit():
                    cmd.extend(['-b:a', str(bitrate)])
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                sucesso_count += 1
            except subprocess.CalledProcessError as e:
                logging.error(f"Erro ao converter {file_to_convert.name}: {e.stderr}")
            except Exception as e:
                logging.error(f"Erro inesperado ao processar {file_to_convert.name}: {e}")

        if sucesso_count > 0:
            cb(100, 2, f"Conversão concluída! {sucesso_count}/{total_files} arquivos processados.")
        else:
            cb(100, 2, "Concluído, mas nenhum arquivo foi convertido. Verifique os nomes dos arquivos de referência.")

    except Exception as e:
        logging.error(f"ERRO NO PIPELINE DE CONVERSÃO (Job ID: {job_id}): {e}\n{traceback.format_exc()}")
        set_progress(job_id, 100, len(ETAPAS_CONVERSAO) - 1, start_time, ETAPAS_CONVERSAO, subetapa=f"Erro: {e}")
        status_path = job_dir / "job_status.json"
        status_data = safe_json_read(status_path) or {}
        status_data['status'] = 'failed'
        status_data['error'] = str(e)
        safe_json_write(status_data, status_path)
    finally:
        with active_jobs_lock:
            if job_id in active_jobs:
                active_jobs.remove(job_id)


def try_reconstruct_project_from_all_backups(job_dir):
    """
    SISTEMA PHOENIX (Recuperação Avançada):
    Tenta reconstruir o project_data.json a partir dos backups fragmentados,
    caso o arquivo principal esteja corrompido ou vazio.
    """
    project_data_path = job_dir / "project_data.json"
    backup_transc_dir = job_dir / "_backup_transcricao"
    backup_texto_dir = job_dir / "_backup_texto_final"
    
    # Se já tem arquivo com dados, não mexe
    if project_data_path.exists():
        data = safe_json_read(project_data_path)
        if data and len(data) > 0:
            return
            
    logging.warning("=== ALERTA PHOENIX: INICIANDO RECUPERAÇÃO DE PROJETO ===")
    logging.warning("project_data.json ausente ou corrompido. Tentando reconstrução...")
    
    recovered_nodes = {}
    
    # Base: Transcrição (Tem os dados originais e metadados)
    if backup_transc_dir.exists():
        for bf in backup_transc_dir.glob("*.json"):
            try:
                data = safe_json_read(bf)
                if data and 'id' in data:
                    recovered_nodes[data['id']] = data
            except: pass

    # Override: Texto Final (Tem os textos traduzidos e editados pelo usuário)
    if backup_texto_dir.exists():
        for bf in backup_texto_dir.glob("*.json"):
            try:
                data = safe_json_read(bf)
                if data and 'id' in data:
                    if data['id'] in recovered_nodes:
                        # Atualiza apenas os campos importantes mantendo a base
                        recovered_nodes[data['id']].update(data)
                    else:
                        recovered_nodes[data['id']] = data
            except: pass
            
    if recovered_nodes:
        final_list = list(recovered_nodes.values())
        final_list.sort(key=lambda x: x.get('id', ''))
        safe_json_write(final_list, project_data_path)
        logging.info(f"PHOENIX SUCCESSO: {len(final_list)} blocos recuperados e salvos!")
    else:
        logging.error("PHOENIX FALHOU: Nenhum backup recuperável encontrado.")

def processar_dublagem_jogos(job_dir, job_id, start_time):
    with active_jobs_lock:
        if len(active_jobs) >= MAX_CONCURRENT_JOBS:
             logging.warning(f"❌ [HARDWARE] Limite de {MAX_CONCURRENT_JOBS} job(s) atingido. Ignorando {job_id}.")
             return
        active_jobs.add(job_id)
    
    try:
        set_low_process_priority()
        
        # [CUMULATIVE TIME] Lê o tempo acumulado de sessões anteriores
        status = safe_json_read(job_dir / "job_status.json") or {}
        accumulated_time = status.get('total_elapsed_secs', 0)
        # Ajusta o cronômetro para iniciar de onde parou (Puro Ouro!)
        virtual_start_time = time.time() - accumulated_time
        
        def cb(p, etapa, s=None, **kwargs): set_progress(job_id, p, etapa, virtual_start_time, ETAPAS_JOGOS, s, **kwargs)
        
        for dir_name in ["_1_MOVER_OS_FICHEIROS_DAQUI", "_2_PARA_AS_PASTAS_DE_VOZ", "_backup_transcricao", "_backup_texto_final", "_dubbed_audio", "_saida_final"]:
            (job_dir / dir_name).mkdir(parents=True, exist_ok=True)
            
        # [FEATURE] Manual Volume Boost - Garante que o arquivo existe
        boost_file = job_dir / "volume_boost.txt"
        if not boost_file.exists():
            try:
                # [v10.71] Detecção de Perfil para Valor Inicial Automático
                initial_boost = "0"
                status_temp = safe_json_read(job_dir / "job_status.json") or {}
                if status_temp.get('game_profile') == 'bioshock':
                    initial_boost = "12"
                    logging.info("[PROFILE] BioShock: Definindo volume_boost.txt inicial para +12dB.")
                elif status_temp.get('game_profile') == 'cod':
                    initial_boost = "10"
                    logging.info("[PROFILE] Call of Duty (MW3): Definindo volume_boost.txt inicial para +10dB.")
                
                with open(boost_file, "w") as f:
                    f.write(f"{initial_boost}\n# AVISO: 1 = +1dB. NAO coloque mais que 25.\n# CUIDADO: Volumes extremos podem DANIFICAR seus alto-falantes.")
            except Exception as e:
                logging.error(f"Erro ao criar volume_boost.txt no start: {e}")
        
        status = safe_json_read(job_dir / "job_status.json") or {}
        file_format_map = status.get('file_format_map', {})
        source_language = status.get('source_language', 'auto')
        diarization_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
        project_data_path = job_dir / "project_data.json"
        
        # =====================================================================
        # [v2026.33 FIX] AUTO-PURGE SYSTEM (LIMPEZA INTELIGENTE)
        # Se o relatório do LQA existir, o processo já rodou. Vamos ler os erros e apagar os áudios corrompidos!
        # =====================================================================
        relatorio_json_path = job_dir / "relatorio_processamento.json"
        if relatorio_json_path.exists():
            relatorio_data = safe_json_read(relatorio_json_path)
            report_time = relatorio_json_path.stat().st_mtime
            
            if relatorio_data and 'segmentos' in relatorio_data:
                logging.info("🧹 [AUTO-PURGE] Relatório anterior encontrado! Analisando datas para limpeza seletiva...")
                dubbed_dir = job_dir / "_dubbed_audio"
                
                durations_cache_path = job_dir / "durations_cache.json"
                mastering_cache_path = job_dir / "mastering_cache.json"
                durations_cache = safe_json_read(durations_cache_path) or {}
                mastering_cache = safe_json_read(mastering_cache_path) or {}
                cache_modificado = False
                arquivos_apagados = 0

                for seg_item in relatorio_data['segmentos']:
                    status_lqa = str(seg_item.get('status_lqa', ''))
                    if status_lqa.startswith('ERRO') or status_lqa.startswith('FALHA'):
                        err_id = seg_item.get('id')
                        bad_raw = dubbed_dir / f"{err_id}_dubbed.wav"
                        
                        if bad_raw.exists():
                            # [v2026.35] Date-Aware Purge: Só apaga se o arquivo for anterior ao relatório
                            if bad_raw.stat().st_mtime <= report_time:
                                try:
                                    bad_raw.unlink()
                                    logging.info(f"🗑️ [AUTO-PURGE] Excluindo áudio defeituoso: {err_id}")
                                    arquivos_apagados += 1
                                    
                                    # Limpa do cache para forçar re-masterização
                                    if err_id in durations_cache:
                                        del durations_cache[err_id]
                                        cache_modificado = True
                                    if err_id in mastering_cache:
                                        del mastering_cache[err_id]
                                        cache_modificado = True
                                except Exception as e_del:
                                    logging.error(f"Erro ao apagar {err_id}: {e_del}")
                            else:
                                logging.info(f"🛡️ [AUTO-PURGE] Preservando '{err_id}' (Detectada correção manual pós-relatório).")
                        
                if cache_modificado:
                    safe_json_write(durations_cache, durations_cache_path)
                    safe_json_write(mastering_cache, mastering_cache_path)
                
                if arquivos_apagados > 0:
                    logging.info(f"✨ [AUTO-PURGE] Concluído! {arquivos_apagados} arquivos defeituosos foram expurgados para re-geração.")
        # =====================================================================
        
        # [v2026.RTX_GUARD] Trava Real de Segurança de 5GB
        if not ensure_vram_safety("Início da Pipeline"):
             cb(0, 1, "ERRO: VRAM Excedida (Limite 5GB). Feche outros apps.")
             raise Exception("VRAM Excedida: O sistema bloqueou para evitar travamento.")

        cb(0, 1, "Iniciando Diarização Automática...")
        # [MODIFICADO] Substituído Manual por Auto Diarização
        run_auto_diarization_batch(job_dir, job_id, cb)
        # wait_for_diarization_manual(job_id, cb) # Desativado
        unify_speaker_files(job_dir, cb)

        all_files_to_process = [f for f in diarization_dir.rglob("*.wav") if not f.name.startswith("_REF_")]
        
        # [FEATURE] Calculo Dinâmico de Duração Total do Projeto
        try:
            total_duration_secs = sum(get_audio_duration(str(f)) for f in all_files_to_process)
            status['duracao_total_secs'] = total_duration_secs
            
            # Formatação amigável
            horas, resto = divmod(int(total_duration_secs), 3600)
            minutos, segundos = divmod(resto, 60)
            
            if horas > 0:
                 status['duracao_total_formatada'] = f"{horas}h {minutos}m {segundos}s"
            else:
                 status['duracao_total_formatada'] = f"{minutos}m {segundos}s"
                 
            safe_json_write(status, job_dir / "job_status.json")
            logging.info(f"Duração total do projeto calculada: {status['duracao_total_formatada']} ({len(all_files_to_process)} arquivos)")
        except Exception as e:
            logging.error(f"Falha ao calcular a duração total do projeto: {e}")
        transcription_backup_dir = job_dir / "_backup_transcricao"
        
        # [PHOENIX RECOVERY] Dispara a recuperação ANTES de tentar ler
        try_reconstruct_project_from_all_backups(job_dir)
        
        project_data = safe_json_read(project_data_path) or []
        # Normalização de Segurança (Trata dic do App_videos vs list do app_jogos)
        if isinstance(project_data, dict) and 'segments' in project_data:
            project_data = project_data['segments']
        elif isinstance(project_data, dict):
            project_data = [] # Fallback seguro se vier um dict esquisito
            
        project_data_map = {item['id']: item for item in project_data}
        files_needing_transcription = []
        
        # [v2026.RESUME_SPEEDUP] Otimização para não poluir o log ao pular arquivos
        skipped_count = 0
        cb(5, 2, "Analisando arquivos e sincronizando backups...")
        
        for audio_file in all_files_to_process:
            file_id = audio_file.stem
            current_speaker = audio_file.parent.name
            
            # [FIX] Garante que o 'speaker' no JSON esteja atualizado
            updated_speaker = False
            found_in_cache = False
            
            if file_id in project_data_map:
                found_in_cache = True
                if project_data_map[file_id].get('speaker') != current_speaker:
                    project_data_map[file_id]['speaker'] = current_speaker
                    updated_speaker = True
                
                if project_data_map[file_id].get('original_text'):
                    if updated_speaker:
                        safe_json_write(project_data_map[file_id], transcription_backup_dir / f"{file_id}.json")
                    skipped_count += 1
                    continue
            
            backup_file = transcription_backup_dir / f"{file_id}.json"
            backup_data = safe_json_read(backup_file)
            
            if backup_data and backup_data.get('original_text'):
                found_in_cache = True
                project_data_map[file_id] = backup_data
                if project_data_map[file_id].get('speaker') != current_speaker:
                    project_data_map[file_id]['speaker'] = current_speaker 
                    safe_json_write(project_data_map[file_id], backup_file)
                skipped_count += 1
            else:
                files_needing_transcription.append(audio_file)
        
        if skipped_count > 0:
            logging.info(f"⏭️ [TITAN RESUME] Pulando {skipped_count} arquivos já processados...")
            cb(10, 2, f"Retomando: {skipped_count} arquivos sincronizados.")
        
        project_data = list(project_data_map.values())
        project_data.sort(key=lambda x: x.get('id', ''))
        
        if files_needing_transcription:
            total_to_transcribe = len(files_needing_transcription)
            cb(10, 2, f"Iniciando transcrição para {total_to_transcribe} arquivos...")
            logging.info(f"[DEBUG] Arquivos que precisam de transcrição: {[f.name for f in files_needing_transcription]}") # [DEBUG]
            model = get_whisper_model()
            for i, audio_file in enumerate(files_needing_transcription):
                start_seg = time.time()
                try:
                    text_result = transcribe_audio(model, str(audio_file), source_lang=source_language)
                    sample_rate, channels, _ = get_audio_metadata(str(audio_file))
                    file_data = {
                        "id": audio_file.stem, 
                        "file_name": audio_file.name, 
                        "speaker": audio_file.parent.name, 
                        "original_text": text_result.get("text", ""), 
                        "detected_language": text_result.get("detected_language", ""),
                        "duration": get_audio_duration(str(audio_file)), 
                        "sample_rate": sample_rate, 
                        "channels": channels
                    }
                    project_data.append(file_data)
                    safe_json_write(file_data, transcription_backup_dir / f"{audio_file.stem}.json")
                except Exception as e: 
                    logging.error(f"FALHA AO TRANSCREVER {audio_file.name}: {e}")
                finally:
                    seg_time = time.time() - start_seg
                    now_str = time.strftime("%H:%M:%S")
                    cb(10 + (i / total_to_transcribe) * 85, 2, f"[{now_str}] Transcrevendo: {audio_file.name} ({seg_time:.1f}s)", tool_name="Whisper (Transcrição)", current_seg=i+1, total_seg=total_to_transcribe)
            project_data.sort(key=lambda x: x.get('id', ''))
        

        # [MEMORY] Libera Whisper imediatamente após o uso para dar espaço ao Gema/Chatterbox
        unload_whisper_model()

        safe_json_write(project_data, project_data_path)
        cb(100, 2, "Transcrição carregada e verificada.")
        
        logging.info("Sincronizando o progresso com os backups de texto final...")
        text_backup_dir = job_dir / "_backup_texto_final"
        project_data_map = {item['id']: item for item in project_data}
        updated_count = 0

        for backup_file in text_backup_dir.glob("*.json"):
            file_id = backup_file.stem
            if file_id in project_data_map:
                backup_data = safe_json_read(backup_file)
                if backup_data:
                    # [v2026.11 FIX] Fusão Inteligente: O backup NÃO pode apagar um Manual Edit preenchido na memória
                    current_manual = project_data_map[file_id].get('manual_edit_text', '').strip()
                    fresh_manual = backup_data.get('manual_edit_text', '').strip()
                    
                    for key, val in backup_data.items():
                        if key == 'manual_edit_text' and not val and current_manual:
                            # Se o backup está vazio mas a memória tem texto, não sobrescreve o Manual
                            continue
                        project_data_map[file_id][key] = val
                    
                    updated_count += 1
        
        if updated_count > 0:
            project_data = list(project_data_map.values())
            project_data.sort(key=lambda x: x.get('id', ''))
            logging.info(f"Dados do projeto sincronizados com {updated_count} backups. Edições manuais preservadas. 🛡️")
            safe_json_write(project_data, project_data_path)
        else:
            logging.info("Nenhum progresso novo encontrado nos backups para sincronizar.")
            
        logging.info("Verificando e limpando dados de execuções anteriores...")
        needs_resave = False
        for seg_data in project_data:
            if 'sanitized_text' in seg_data:
                original_sanitized = seg_data['sanitized_text']
                corrected_sanitized = sanitize_tts_text(original_sanitized)
                if original_sanitized != corrected_sanitized:
                    logging.warning(f"Corrigido texto antigo para '{seg_data['id']}': '{original_sanitized}' -> '{corrected_sanitized}'")
                    seg_data['sanitized_text'] = corrected_sanitized
                    needs_resave = True
            if 'manual_edit_text' not in seg_data:
                seg_data['manual_edit_text'] = ""
                needs_resave = True
            elif seg_data['manual_edit_text']:
                # [SEGURANÇA] Se o campo manual está preenchido, garantimos que ele não seja resetado aqui
                pass


        if needs_resave:
            logging.info("Salvando correções de dados antigos no project_data.json...")
            safe_json_write(project_data, project_data_path)
        
        files_to_process_gema = []
        files_to_copy_directly = []

        for seg_data in project_data:
            # [FIX] Se já foi marcado como "Não-Verbal", PULA.
            if seg_data.get('processing_status') == 'Copiado Diretamente (Som Não-Verbal)':
                continue

            # [NOVO - Filtro de Idioma] Pula tradução do que já está em Português
            if seg_data.get('detected_language') == 'pt':
                if not seg_data.get('sanitized_text'):
                    seg_data['sanitized_text'] = seg_data.get('original_text', '')
                
                # [FIX] Garante a existência do backup para não acionar o apagamento forçado (fallback manual)
                backup_path_pt = job_dir / "_backup_texto_final" / f"{seg_data['id']}.json"
                if not backup_path_pt.exists():
                    safe_json_write(seg_data, backup_path_pt)
                    
                logging.info(f"Segmento {seg_data['id']} preservado (já é Português).")

            # [v12.32 SINCRONIA DE DADOS]
            backup_path = job_dir / "_backup_texto_final" / f"{seg_data['id']}.json"
            
            # [REGRA DE OURO] Se existe texto manual na memória (project_data), ele é SAGRADO.
            # Se o backup sumiu, nós RECRIAMOS o backup a partir do manual, em vez de apagar o manual.
            if seg_data.get('manual_edit_text'):
                if not backup_path.exists():
                    logging.info(f"🛡️ [RESGATE] Recriando backup para '{seg_data['id']}' a partir da edição manual preservada.")
                    safe_json_write(seg_data, backup_path)
                continue # Pula qualquer lógica de "pop" ou limpeza para este arquivo

            # [PROTEÇÃO VITALÍCIA] Se NÃO tem manual, aí sim podemos limpar traduções antigas se o backup sumir
            if not backup_path.exists() and seg_data.get('sanitized_text'):
                seg_data.pop('translated_text', None)
                seg_data.pop('synced_text', None)
                seg_data.pop('sanitized_text', None)
                seg_data['translation_fallback'] = False

            if seg_data.get('sanitized_text') and not seg_data.get('translation_fallback'):
                continue

            original_text = seg_data.get('original_text', '').strip()
            clean_text = re.sub(r'[^\w\s]', '', original_text).lower()
            words = clean_text.split()
            if (words and all(word in SONS_A_IGNORAR for word in words)) or \
               len(original_text.replace(" ", "")) < 3 or \
               seg_data.get('duration', 0) < 0.1 or \
               is_junk_text(original_text):
                files_to_copy_directly.append(seg_data)
                seg_data['processing_status'] = 'Copiado Diretamente (Som Não-Verbal)'
                
                # [FIX] Garante que esses arquivos também tenham backup em _backup_texto_final
                # para evitar discrepância de contagem e permitir edição manual se o usuário quiser.
                safe_json_write(seg_data, job_dir / "_backup_texto_final" / f"{seg_data['id']}.json")
                
                logging.info(f"O áudio '{seg_data['id']}' foi marcado como som não verbal ('{original_text}'). Será copiado, não dublado.")
            else:
                files_to_process_gema.append(seg_data)
                seg_data['processing_status'] = 'Processado para Dublagem'
        
        safe_json_write(project_data, project_data_path)

        if files_to_process_gema:
            cb(0, 3, f"Processando {len(files_to_process_gema)} textos com Gema...")
            wait_for_gema_service(lambda s: cb(0, 3, s))
            
            # [v12.70] Prioridade para o perfil escolhido pelo usuário no HTML/Status
            game_profile_id = status.get('game_profile', 'padrao').lower()
            
            # [v20.6] EXTRAÇÃO DO GLOSSÁRIO PERSONALIZADO
            # Transforma "Nome=Nome, Termo=Trad" em um dicionário real para o Gema
            user_glossary_raw = status.get('user_glossary', '')
            merged_glossary = {}
            if user_glossary_raw:
                parts = [p.strip() for p in user_glossary_raw.split(',') if p.strip()]
                for p in parts:
                    if '=' in p:
                        k, v = p.split('=', 1)
                        merged_glossary[k.strip()] = v.strip()
                    else:
                        merged_glossary[p.strip()] = p.strip()

            # Combina Perfil com Contexto Imediato das falas
            sample_ctx = " / ".join([s['original_text'] for s in files_to_process_gema[:3]])
            cenario_ctx = f"{game_profile_id.upper()} - Contexto: {sample_ctx}"
            cb(5, 3, f"Estilo: {game_profile_id.upper()}")
            
            # [v20.16] CACHE GRANULAR (WYSIWYG - What You See Is What You Get)
            # Se o arquivo individual .json existir na pasta de backup, usamos ele.
            # Se o usuário apagar o arquivo da pasta, a IA traduz novamente.
            backup_texto_dir = job_dir / "_backup_texto_final"
            backup_texto_dir.mkdir(parents=True, exist_ok=True)
            
            unique_texts_map = {}
            unique_files = []
            
            # [v21.15] MICRO-CACHE DINÂMICO (SEM ARQUIVO FÍSICO)
            # Agora o micro_cache é construído EM MEMÓRIA toda vez que você inicia o Job.
            # Isso evita ter que apagar um arquivo a mais quando você quer mudar uma tradução.
            micro_cache = {}
            
            # Passo 1: Popula o micro_cache com a "Prioridade das Prioridades" (Edição Manual)
            for f in files_to_process_gema:
                orig = f.get('original_text', '').strip()
                manual = f.get('manual_edit_text', '').strip()
                if orig and manual:
                    micro_cache[orig] = manual
                    micro_cache[orig.lower()] = manual

            for f in files_to_process_gema:
                orig_txt = f.get('original_text', '').strip()
                if not orig_txt: continue
                
                # [PRIORIDADE 1] Edição Manual (O usuário escreveu lá no HTML)
                # Se houver edição manual, ela anula qualquer tradução de IA ou Cache.
                if f.get('manual_edit_text', '').strip():
                    f['translated_text'] = f['manual_edit_text']
                    f['synced_text'] = f['manual_edit_text']
                    f['sanitized_text'] = gema_etapa_3_sanitizacao(f['manual_edit_text'])
                    f['_usar_cache'] = True
                    continue

                # [PRIORIDADE 2] Cache Granular
                individual_json = backup_texto_dir / f"{f['id']}.json"
                if individual_json.exists():
                    saved_data = safe_json_read(individual_json)
                    if saved_data and saved_data.get('translated_text'):
                        f.update(saved_data)
                        f['_usar_cache'] = True
                        continue

                # [PRIORIDADE 3] Repetição Interna
                if orig_txt in micro_cache or orig_txt.lower() in micro_cache:
                    f['_usar_cache_da_fila'] = True
                    continue

                # Sem cache: Vai para a fila de tradução da IA única
                if orig_txt.lower() not in unique_texts_map:
                    unique_texts_map[orig_txt.lower()] = True
                    unique_files.append(f)
                else:
                    f['_usar_cache_da_fila'] = True

            rus_files = [f for f in unique_files if re.search(r'[А-Яа-яЁё]', f.get('original_text', ''))]
            eng_files = [f for f in unique_files if not re.search(r'[А-Яа-яЁё]', f.get('original_text', ''))]
            
            # [v20.8 REVOLUÇÃO ATÔMICA]
            # Em vez de lotes cegos, processamos em paralelo com janela de contexto.
            total_items = len(unique_files)
            completed_atomic = 0
            
            def worker_traducao(idx, item_data):
                nonlocal completed_atomic
                start_seg = time.time()
                try:
                    # 1. Constrói Janela de Contexto Equilibrada (3 antes, 3 depois - Sprint Mode para i5)
                    # Reduzido de 10 para 3 para acelerar o 'Prefill' da CPU (menos texto para o i5 ler antes de traduzir).
                    start_ctx = max(0, idx - 3)
                    end_ctx = min(total_items, idx + 4)
                    context_lines = []
                    for j in range(start_ctx, end_ctx):
                        f_ctx = unique_files[j]
                        prio = ">>> ALVO >>>" if j == idx else "            "
                        speaker = f_ctx.get('speaker', 'Voz')
                        context_lines.append(f"{prio} {f_ctx['id']} ({speaker}): \"{f_ctx.get('original_text','')}\"")
                    
                    ctx_str = "\n".join(context_lines)
                    
                    # [v20.17] MODO TURBO: Agente Atômico Único (Optimized for G4B)
                    # Confiamos na inteligência do Gemma 4 para ajustar o limite de tempo (18 CPS) na primeira tentativa.
                    # Isso elimina a necessidade de um segundo agente de LQA, acelerando o processo em quase 50%.
                    final_text = gema_atomic_processor_v3(
                        item_data, ctx_str, 
                        glossary=merged_glossary, 
                        profile_id=game_profile_id, 
                        job_dir=job_dir
                    )
                    
                    # Trava de Segurança Final (Anti-Alucinação apenas)
                    orig_text = item_data.get('original_text', '')
                    nao_traduziu = (final_text.strip().lower() == orig_text.strip().lower()) and len(orig_text) > 3
                    
                    if nao_traduziu:
                        # Uma única tentativa de correção se ele insistir no Inglês
                        final_text = gema_etapa_correcao_master(orig_text, final_text, item_data.get('duration', 0), reason="qualidade")
                    
                    # Persiste resultados no objeto
                    item_data['translated_text'] = final_text
                    item_data['synced_text'] = final_text
                    item_data['sanitized_text'] = gema_etapa_3_sanitizacao(final_text)
                    
                    # [v20.15] Salvamento Granular: Cria um arquivo individual para cada segmento na pasta de backup dedicada
                    backup_dir = job_dir / "_backup_texto_final"
                    individual_backup_file = backup_dir / f"{item_data['id']}.json"
                    safe_json_write(item_data, individual_backup_file)
                    
                except Exception as ex_atomic:
                    logging.error(f"Falha atômica no item {idx}: {ex_atomic}")
                finally:
                    completed_atomic += 1
                    seg_time = time.time() - start_seg
                    now_str = time.strftime("%H:%M:%S")
                    
                    # Recibo limpo no terminal (como o Alexandre sugeriu)
                    logging.info(f"   ✅ [{now_str}] Segmento {idx} finalizado ({seg_time:.1f}s)")
                    
                    cb((completed_atomic / total_items) * 100, 3, f"[{now_str}] Traduzindo: {completed_atomic}/{total_items} ({seg_time:.1f}s)...", tool_name="Gemma 4 (IA)", current_seg=completed_atomic, total_seg=total_items)

            # Disparo em Paralelo (3 threads para 4-core i5 / 10 para GPU)
            # Deixa sempre 1 núcleo livre para o sistema não travar.
            device_hw = get_optimal_device()
            # [v20.15] Gemma 4 Optimization: Máximo 2 workers para não fritar o i5
            # Se for CPU pura, 1 worker é mais estável. Se tiver GPU, 2 é o limite seguro.
            max_pthreads = 1 if "cpu" in device_hw else 2
            logging.info(f"   -> 🚀 [PARALELISMO] Iniciando tradução atômica com {max_pthreads} workers (Safe Mode).")
            
            with ThreadPoolExecutor(max_workers=max_pthreads) as executor:
                futures = [executor.submit(worker_traducao, i, f) for i, f in enumerate(unique_files)]
                for future in as_completed(futures):
                    try: 
                        future.result()
                    except: 
                        pass

            # [v21.05] Popula o micro_cache com as traduções bem-sucedidas para clonar nas repetições
            for f in unique_files:
                orig_key = f.get('original_text', '').strip()
                if orig_key and f.get('translated_text'):
                    micro_cache[orig_key] = f['translated_text']

            # [v21.15] Fim da tradução: Micro-cache atualizado em memória. Sem gravação em disco necessária.
            
            # Aplica cache e clones para o resto da lista
            for f in files_to_process_gema:
                orig = f.get('original_text', '').strip()
                if f.get('_usar_cache') or f.get('_usar_cache_da_fila'):
                    trad_val = micro_cache.get(orig) or micro_cache.get(orig.lower())
                    if trad_val:
                        f['translated_text'] = trad_val
                        f['synced_text'] = trad_val
                        f['sanitized_text'] = gema_etapa_3_sanitizacao(trad_val)
                    else:
                        # Se falhou tudo, mantém original
                        f['translated_text'] = f.get('original_text', '')
                        f['synced_text'] = f.get('original_text', '')
                        f['sanitized_text'] = gema_etapa_3_sanitizacao(f.get('original_text', ''))

            # Finaliza e salva o status final dos arquivos
            for f in files_to_process_gema:
                safe_json_write(f, job_dir / "_backup_texto_final" / f"{f['id']}.json")

            cb(100, 5, "Processamento de texto concluído.")
            unload_gema_model() # [NEW] Libera RAM para o Chatterbox v2

        # [FIX CRÍTICO] - Consolidação de Backups ANTES de montar a fila
        logging.info("Sincronizando textos com os backups do disco...")
        backup_final_dir = job_dir / "_backup_texto_final"
        if backup_final_dir.exists():
            for seg in project_data:
                bkp_path = backup_final_dir / f"{seg['id']}.json"
                if bkp_path.exists():
                    try:
                        fresh_data = safe_json_read(bkp_path)
                        if fresh_data:
                            seg['sanitized_text'] = fresh_data.get('sanitized_text', seg.get('sanitized_text', ''))
                            if fresh_data.get('manual_edit_text'):
                                seg['manual_edit_text'] = fresh_data['manual_edit_text']
                            if fresh_data.get('speaker'):
                                seg['speaker'] = fresh_data['speaker']
                    except: pass

        logging.info("Preparando fila de geração individual...")
        generation_queue = []

        for seg_data in project_data:
            if seg_data.get('processing_status') == 'Copiado Diretamente (Som Não-Verbal)':
                continue
            
            text_to_speak = seg_data.get('manual_edit_text', '').strip() or seg_data.get('sanitized_text', '')
            if not text_to_speak:
                continue

            # Agrupa por texto e locutor para gerar variações por personagem
            # [FIX] Fallback para 'Unknown' se por algum motivo o speaker não estiver definido
            speaker_id = seg_data.get('speaker', 'Unknown')
            pass

            pass
            
            generation_queue.append(seg_data)
            seg_data['is_master_audio'] = True
            seg_data.pop('reuse_audio_from_id', None)
        

        
        safe_json_write(project_data, project_data_path) # Salva as marcações e consolidação
        
        # [PHOENIX VRAM SAFETY LOCK - v2026.5]
        # Inteligência Artificial: Detecta se o usuário PRECISA fechar o LM Studio ou não.
        import torch
        tem_gpu = torch.cuda.is_available()
        
        # [v2026.CPU_OPTIMIZED] Mesmo sem GPU, fechar o LM Studio libera RAM vital para o i5.
        print("\n" + "!"*70)
        print(" 💻 MODO CPU DETECTADO!")
        print(" ⚠️  IMPORTANTE: FECHE O LM STUDIO AGORA PARA LIBERAR RAM.")
        print(" O i5 precisa de toda a memória livre para gerar as vozes sem lentidão.")
        print("!"*70 + "\n")
        
        while True:
            import requests
            lm_studio_vivo = False
            try:
                res = requests.get("http://127.0.0.1:1234/v1/models", timeout=2)
                if res.status_code == 200: lm_studio_vivo = True
            except: lm_studio_vivo = False
            
            if not lm_studio_vivo:
                logging.info("✅ MEMÓRIA LIBERADA! Iniciando vozes no i5...")
                break
            
            cb(100, 5, "AGUARDANDO: Feche o LM Studio para liberar o processador.")
            time.sleep(3) # Aguarda 3 segundos antes de verificar novamente


        # --- ETAPA 6: GERAÇÃO TTS CHATTERBOX ---
        cb(0, 6, "Analisando hardware e VRAM...")
        try:
            current_device = get_optimal_device()
            if "cuda" in current_device:
                cb(2, 6, "🚀 Usando Placa de Vídeo (Modo Turbo)")
            else:
                cb(2, 6, "🐢 Usando Processador (Gemma 4 ativo ou sem GPU)")
        except:
            pass

        dubbed_audio_dir = job_dir / "_dubbed_audio"
        dubbed_audio_dir.mkdir(exist_ok=True)

        actual_generation_queue = []
        if generation_queue:
            for seg_data in generation_queue:
                output_path = dubbed_audio_dir / f"{seg_data['id']}_dubbed.wav"
                current_text = seg_data.get('manual_edit_text', '').strip() or seg_data.get('sanitized_text', '')
                force_regen = False
                individual_json = job_dir / "_backup_texto_final" / f"{seg_data['id']}.json"
                if individual_json.exists():
                    saved_val = safe_json_read(individual_json)
                    saved_text = saved_val.get('manual_edit_text', '').strip() or saved_val.get('sanitized_text', '')
                    if saved_text != current_text:
                        force_regen = True

                if not output_path.exists() or force_regen:
                    actual_generation_queue.append(seg_data)

        if actual_generation_queue:
            # [MEMORY SAFETY] Limpeza agressiva antes de carregar o motor de voz
            import gc
            gc.collect()
            if torch.cuda.is_available(): torch.cuda.empty_cache()
            
            cb(0, 6, "Iniciando Motor Qwen3-TTS...")
            # Garante que o motor Qwen3 está carregado
            get_qwen3_engine()
            
            global_fallback = Path("resources/base_speakers/pt/default_pt_speaker.wav")
            total_gen = len(actual_generation_queue)
            completed_gen = 0
            
            def worker_voz(idx, seg_data):
                nonlocal completed_gen
                try:
                    file_id = seg_data['id']
                    output_path = dubbed_audio_dir / f"{file_id}_dubbed.wav"
                    current_text = seg_data.get('manual_edit_text', '').strip() or seg_data.get('sanitized_text', '')
                    original_duration = seg_data.get('duration', 0)
                    emotion_tag = seg_data.get('emotion', 'NORMAL')
                    
                    # Busca a voz de referência
                    ref_path = diarization_dir / seg_data.get('speaker', 'Unknown') / "_REF_VOZ_UNIFICADA.wav"
                    if not ref_path.exists():
                        ref_path = diarization_dir / seg_data.get('speaker', 'Unknown') / seg_data.get('file_name', '')
                    if not ref_path.exists(): ref_path = global_fallback
 
                    # [v2026.REACTION_FILTER] Bypass para áudio original se for apenas uma reação
                    text_clean = seg_data.get('original_text', '').strip().lower()
                    is_hallucination = False
                    if text_clean:
                        normal_chars = len([c for c in text_clean if c.isalnum() or c.isspace()])
                        if len(text_clean) > 0 and (normal_chars / len(text_clean)) < 0.3: is_hallucination = True
 
                    is_reaction = any(word in SONS_A_IGNORAR for word in text_clean.split()) and len(text_clean.split()) <= 2
                    
                    if is_hallucination or seg_data.get('detected_language') == 'pt' or is_reaction:
                        try:
                            orig = (diarization_dir / seg_data.get('speaker', 'Unknown') / seg_data.get('file_name', ''))
                            if orig.exists():
                                from pydub import AudioSegment
                                # Normaliza para 24kHz Mono (padrão de compatibilidade)
                                AudioSegment.from_file(str(orig)).set_frame_rate(24000).set_channels(1).export(output_path, format="wav")
                                logging.info(f"⏩ [BYPASS] Preservando original para '{file_id}' (Reação/PT/Hallucination)")
                                return
                        except Exception as e_copy:
                            logging.warning(f"Falha ao copiar original para {file_id}: {e_copy}")
 
                    # Geração de Voz com Qwen3-TTS Estabilizado
                    try:
                        text_to_speak = current_text
                        # [BR-FIX] Aplica o Corretor de Sotaque e Expansão Fonética
                        text_to_speak = corrigir_sotaque_pt_br(text_to_speak)
                        
                        # [v2026.QWEN3_GAME_GEN] Chamada ao Motor Unificado com Emoção e Blindagem de Duração
                        resultado = gerar_audio_qwen3(
                            text_to_speak,
                            str(ref_path),
                            str(output_path),
                            emotion=emotion_tag,
                            max_duration=original_duration
                        )
                        
                        if resultado and output_path.exists():
                            logging.info(f"🎤 [QWEN3] Voz gerada para '{file_id}' com sucesso!")
                        else:
                            logging.warning(f"⚠️ [QWEN3] Falha na síntese para '{file_id}'.")
                            
                    except Exception as e_gen:
                        logging.error(f"Falha na geração Qwen3 para {file_id}: {e_gen}")
                        
                except Exception as ex_v:
                    logging.error(f"Erro no worker de voz para {seg_data['id']}: {ex_v}")
                finally:
                    completed_gen += 1
                    pct = 5 + (completed_gen / total_gen) * 95
                    cb(pct, 6, f"Vozes: {completed_gen}/{total_gen} concluídas.", tool_name="Qwen3-TTS (Voz)", current_seg=completed_gen, total_seg=total_gen)
                    # Checkpoint Vivo a cada 10 arquivos
                    if completed_gen % 10 == 0:
                        gerar_relatorio_final(job_dir, job_id, project_data, file_format_map)

            # [FILA JOGOS] Processamento sequencial leve e limpo na GPU (Sem VRAM OOM)
            logging.info(f"🚀 [QUEUE] Processando {total_gen} tarefas de voz com o Motor Unificado Qwen3-TTS...")
            for idx_task, task_data in enumerate(actual_generation_queue):
                worker_voz(idx_task, task_data)
        
        cb(100, 6, "Pronto.")

        # =========================================================================
        # ETAPA 7: REFINAMENTO E AUTO-REGENERAÇÃO NEXUS (LQA BRUTO)
        # =========================================================================
        logging.info("--- INICIANDO CICLO DE REFINAMENTO NEXUS (LQA BRUTO) ---")
        cb(0, 7, "Iniciando auditoria de integridade (Nexus Raw)...")
        
        regenerados_sucesso = 0
        
        # [v2026.35] Carrega a data do relatório para o 'Pulo Turbo' inteligente
        relatorio_json_path = job_dir / "relatorio_processamento.json"
        report_time = relatorio_json_path.stat().st_mtime if relatorio_json_path.exists() else 0
        
        # Garante que o motor Qwen3 está carregado
        get_qwen3_engine()
        
        for i, seg_data in enumerate(project_data):
            file_id = seg_data['id']
            file_name = seg_data.get('file_name', f"{file_id}.wav")
            raw_path = dubbed_audio_dir / f"{file_id}_dubbed.wav"
            
            
            perc_lqa = (i / len(project_data)) * 100
            cb(perc_lqa, 7, f"Auditando Geração: {file_name}", tool_name="Nexus LQA", current_seg=i+1, total_seg=len(project_data))
            
            original_duration = seg_data.get('duration', 0)
            
            # 1. Análise Nexus Raw (Foco em Cortes, Loops e CONTEÚDO ASR)
            translated_text = seg_data.get('translated_text', '')
            
            # [v2026.35 OPTIMIZATION] Pulo Turbo Inteligente
            # Só pulamos o Whisper se: Já estava OK, o arquivo existe E ele NÃO é uma nova geração (mais antigo que o relatório)
            is_fresh_audio = raw_path.exists() and raw_path.stat().st_mtime > report_time
            
            if seg_data.get('lqa_status') == 'OK' and raw_path.exists() and not is_fresh_audio:
                lqa_status, diagnostics, needs_regen = 'OK', seg_data.get('lqa_details', 'Aprovado anteriormente'), False
            else:
                # Se for áudio novo ou tiver erro anterior, AUDITA obrigatoriamente
                lqa_status, diagnostics, needs_regen = nexus_lqa_validator(raw_path, original_duration, file_id, job_dir, mode='raw', expected_text=translated_text)
            
            # 2. Gatilho de Regeneração (Removido para velocidade)
            if needs_regen and not seg_data.get('nexus_already_retried'):
                logging.warning(f"❌ Nexus: Falha detectada em '{file_id}' ({diagnostics}). (Regeneração automática desativada para ganho de velocidade. O Auto-Purge lidará com isso na próxima execução).")
                seg_data['nexus_already_retried'] = True # Trava de segurança para não entrar em loop

            # Só atualiza se o status anterior não for melhor (evita sobrescrever OK do Nexus)
            old_status = seg_data.get('lqa_status', 'OK')
            if old_status != 'OK' or lqa_status == 'ERRO':
                seg_data['lqa_status'] = lqa_status
                seg_data['lqa_details'] = diagnostics

            # Salva os status brutos para histórico técnico
            seg_data['lqa_raw_status'] = lqa_status
            seg_data['lqa_raw_details'] = diagnostics
            
            if i % 10 == 0: safe_json_write(project_data, job_dir / "project_data.json")
            
            # [v2026.34] Checkpoint Vivo: Atualiza o relatório a cada auditoria
            gerar_relatorio_final(job_dir, job_id, project_data, file_format_map)

        status['nexus_regenerados_count'] = regenerados_sucesso
        cb(100, 7, f"Refinamento concluído. {regenerados_sucesso} áudios foram salvos.")
        safe_json_write(project_data, job_dir / "project_data.json")

        # Descarrega o Qwen3-TTS da GPU antes de iniciar a masterização pesada do FFmpeg
        unload_qwen3_model()

        # --- ETAPA 7: FINALIZAÇÃO E MASTERIZAÇÃO ---
        cb(0, 7, "Iniciando finalização e masterização...")
        final_output_dir = job_dir / "_saida_final"
        mastering_cache_path = job_dir / "mastering_cache.json"
        mastering_cache = safe_json_read(mastering_cache_path) or {}
        durations_cache_path = job_dir / "durations_cache.json"
        durations_cache = safe_json_read(durations_cache_path) or {}

        # [FEATURE] Manual Volume Boost - Leitura da Configuração
        volume_boost_factor = 1.0
        try:
            boost_file = job_dir / "volume_boost.json"
            if boost_file.exists():
                boost_data = safe_json_read(boost_file) or {}
                val_int = boost_data.get("boost_db", 0)
                    
                # [SAFETY] Limite Duro de Segurança (Atômico)
                # +30dB já é um absurdo (32x potêcia). Acima disso é risco real de dano físico.
                if val_int > 30:
                    logging.warning(f"[SAFETY] Volume solicitado ({val_int}dB) excede o limite seguro. Ajustado para +30dB.")
                    val_int = 30
                
                # [MODIFIED] Removido limite de 100% a pedido do usuário (Bioshock 1)
                # Agora o céu é o limite (Cuidado com distorção!)
                if val_int < 0: val_int = 0
                
                if val_int > 0:
                    # [MODIFIED] Interpretação Direta em dB (COD Style)
                    # 1 = +1dB
                    # 15 = +15dB (Alto)
                    # 100 = +100dB (Explodido)
                    volume_boost_factor = float(val_int)
                    logging.info(f"Audio Compression Ativado: Master Boost + {val_int}dB de Ganho.")
                else:
                    volume_boost_factor = 0
                    logging.info("Audio Compression: Desativado (0dB).")
        except Exception as e:
            logging.error(f"Erro ao ler volume_boost.json: {e}")

        # [v12.70] Lógica Unificada de Perfis via Dicionário Dinâmico
        game_profile_id = status.get('game_profile', 'padrao')
        profile = load_game_profile(game_profile_id)
        audio_cfg = profile.get('audio_settings', {})
        profile_filters = []
        
        # 1. Normalização / Loudnorm
        if 'loudnorm' in audio_cfg:
             profile_filters.append(f"loudnorm={audio_cfg['loudnorm']}")
        
        # 2. Compressor
        if 'acompressor' in audio_cfg:
             profile_filters.append(f"acompressor={audio_cfg['acompressor']}")
             
        # 3. Equalizador (Bass/Treble)
        if 'bass' in audio_cfg:
             profile_filters.append(f"bass={audio_cfg['bass']}")
        if 'treble' in audio_cfg:
             profile_filters.append(f"treble={audio_cfg['treble']}")
        
        # 4. Volume Boost Default
        if volume_boost_factor <= 1.0: 
            volume_boost_factor = audio_cfg.get('volume_boost_default', 0)
            if volume_boost_factor > 0:
                 logging.info(f"[PROFILE] {profile['name']}: Aplicando ganho automático de +{volume_boost_factor}dB.")

        logging.info(f"[PROFILE] {profile['name']}: Ativando Otimização de Áudio Profissional.")

        # Define pastas (Etapa 7) - FORÇANDO REPROCESSAMENTO TOTAL (SEM CACHE)
        dubbed_audio_dir = job_dir / "_dubbed_audio"
        final_output_dir = job_dir / "_saida_final"
        diarization_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
        final_output_dir.mkdir(exist_ok=True)

        # [FORÇAR RESET] Limpa cache de masterização para este job para garantir reprocessamento total
        logging.info("🔥 AVISO: Forçando limpeza do cache de masterização para garantir áudio dublado.")
        for key in list(mastering_cache.keys()):
            if any(key.startswith(str(s['id'])) for s in project_data):
                del mastering_cache[key]

        logging.info("--- INICIANDO MASTERIZAÇÃO FINAL (MODO FORÇADO) ---")

        for i, seg_data in enumerate(project_data):
            file_id = seg_data['id']
            file_name = seg_data.get('file_name', f"{file_id}.wav")
            final_path = final_output_dir / f"{file_id}{file_format_map.get(file_id, '.wav')}"
            
            # [RESET] Sempre tenta re-processar para garantir que não fique inglês
            if final_path.exists(): 
                try: os.remove(final_path)
                except: pass
            
            speaker_id = seg_data.get('speaker', 'Unknown')
            cb((i / len(project_data)) * 100, 7, f"Finalizando: {file_name}", tool_name="FFMPEG (Master)", current_seg=i+1, total_seg=len(project_data))

            original_duration = seg_data.get('duration', 0)
            original_file_path = diarization_dir / speaker_id / file_name
            source_path = None
            is_fallback_copy = False
            dubbed_check_path = dubbed_audio_dir / f"{file_id}_dubbed.wav"

            if dubbed_check_path.exists():
                source_path = dubbed_check_path
                logging.info(f"Usando áudio dublado encontrado para '{file_id}'.")
            elif seg_data.get('reuse_audio_from_id'):
                master_id = seg_data['reuse_audio_from_id']
                source_path = dubbed_audio_dir / f"{master_id}_dubbed.wav"
                logging.info(f"Reutilizando áudio de '{master_id}' para '{file_id}'.")
            else: # Realmente não existe dublagem
                source_path = original_file_path
                is_fallback_copy = True

            # --- LÓGICA DE SELEÇÃO INTELIGENTE (SEM ENROLAÇÃO) ---
            is_non_verbal = (seg_data.get('processing_status') == 'Copiado Diretamente (Som Não-Verbal)')
            
            if is_fallback_copy and not is_non_verbal:
                # SE TEM TRADUÇÃO MAS NÃO ACHOU O ÁUDIO DUBLADO -> ERRO!
                logging.error(f"❌ ERRO CRÍTICO: Áudio dublado NÃO encontrado para '{file_id}' (Deveria estar dublado).")
                logging.error(f"   Verifique a pasta '_dubbed_audio'. Pulando para não gerar em inglês.")
                continue

            # Se for não-verbal, 'source_path' já aponta para o original e 'is_fallback_copy' é True. 
            # Isso é o esperado para gemidos/sons.

            try:
                # Medimos a duração do source
                source_duration = get_audio_duration(str(source_path))
                
                filters_to_apply = []
                speed_factor = 1.0
                TOLERANCE_SECONDS = 0.1

                # 1. Poda de Silêncio e Aceleração (Sincronia)
                if original_duration > 0:
                    # [v2026.28 FIX] REMOVIDO: O filtro silenceremove era o vilão!
                    # Ele cortava o áudio no meio sempre que a voz caía abaixo de -55dB em pequenas pausas.
                    # Ex: 'anda [pausa] primeiro andar' virava apenas 'anda'. Agora usamos apenas o atempo para sincronizar.
                    
                    if source_duration > (original_duration + TOLERANCE_SECONDS):
                        calculated_factor = source_duration / original_duration
                        # [v2026.15] Limite de velocidade mais humano para evitar 'esquilos'
                        speed_factor = min(calculated_factor, 1.40)
                        temp_factor = speed_factor
                        while temp_factor > 2.0:
                            filters_to_apply.append("atempo=2.0")
                            temp_factor /= 2.0
                        if temp_factor > 1.0: filters_to_apply.append(f"atempo={temp_factor:.4f}")

                # [v2026.15 SAFETY FLOOR] Trava de segurança contra 'Arquivos Fantasmas'
                # Se o áudio original tinha mais de 0.8s e o final ficou com menos de 0.2s, 
                # algo deu errado no filtro. Resetamos os filtros para salvar o áudio.
                if original_duration > 0.8 and (source_duration / speed_factor) < 0.2:
                    logging.warning(f"⚠️ [SAFETY] Detectada perda catastrófica em {file_id}. Resetando filtros de sincronia.")
                    filters_to_apply = ["dynaudnorm"] # Mantém apenas a normalização

                # 2. Corrente de Masterização
                master_chain = ["dynaudnorm"]
                if volume_boost_factor > 0:
                    has_compressor = any("acompressor" in f for f in profile_filters)
                    if not has_compressor:
                        master_chain.append("acompressor=threshold=-12dB:ratio=4:attack=5:release=50:makeup=2")
                    master_chain.append(f"volume={volume_boost_factor}dB")
                    master_chain.append("alimiter=limit=0.966:level=disabled:attack=5:release=50")
                
                if profile_filters and seg_data.get('processing_status') != 'Copiado Diretamente (Som Não-Verbal)':
                    master_chain = profile_filters + master_chain

                cmd = ['ffmpeg', '-y', '-threads', str(os.cpu_count() or 4), '-i', str(source_path)]
                
                # Som de Fundo (Se houver)
                bg_file_path = None
                try:
                    if str(status.get('preserve_background', 'false')).lower() == 'true':
                        stem_bg_dir = job_dir / "_0b_SEPARACAO_FUNDO"
                        if stem_bg_dir.exists():
                            pb = list(stem_bg_dir.rglob(seg_data['file_name']))
                            if pb: bg_file_path = pb[0]
                except: pass

                if bg_file_path:
                    cmd.extend(['-i', str(bg_file_path)])
                    v_chain = ",".join(filters_to_apply + master_chain)
                    cmd.extend(['-filter_complex', f"[0:a]{v_chain}[v];[1:a]volume=0.4[b];[v][b]amix=inputs=2:duration=longest[out]", '-map', '[out]'])
                else:
                    all_filters = filters_to_apply + master_chain
                    if all_filters: cmd.extend(['-af', ",".join(all_filters)])

                # [v2026.8 FIX] Seleção Inteligente de Codec
                # Se o destino for .mp3, usamos libmp3lame. Se for .wav, usamos pcm_s16le.
                ext_final = str(final_path.suffix).lower()
                codec_final = 'libmp3lame' if ext_final == '.mp3' else 'pcm_s16le'
                
                output_profile = status.get('detected_profile', {})
                native_ar = str(output_profile.get('ar', '44100'))
                native_ac = str(output_profile.get('ac', '1'))
                
                cmd.extend([
                    '-c:a', codec_final, 
                    '-ar', native_ar, 
                    '-ac', native_ac,
                    '-map_metadata', '-1' # Limpa metadados corrompidos do jogo original
                ])
                
                # Para MP3, adicionamos o bitrate padrão de alta qualidade
                if codec_final == 'libmp3lame':
                    cmd.extend(['-b:a', '192k'])

                cmd.append(str(final_path))
                logging.info(f"🔊 Masterizando ({codec_final}): {file_id}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                     logging.error(f"❌ FFmpeg falhou para {file_id}: {result.stderr}")
                     continue 
                
                # [v2026.TITAN] Log de Alta Fidelidade para o Usuário
                logging.info(f"✅ [TITAN] Integrado: {file_id} (Duração: {final_duration:.2f}s | Pico: {final_peak}dB)")
                
                if file_id not in durations_cache: durations_cache[file_id] = {}
                durations_cache[file_id]['speed_factor'] = speed_factor

            except Exception as e:
                logging.error(f"❌ Erro grave em {file_id}: {e}")
                continue # Não copia original!

            # --- CAPTURA DE MÉTRICAS PÓS-PROCESSAMENTO ---
            # Agora que garantimos que o arquivo existe (criado agora ou já existia), vamos medir.
            if final_path.exists():
                try:
                    # 1. Duração Final
                    final_duration = get_audio_duration(str(final_path))
                    
                    # 2. Pico de Áudio (Mastering Check)
                    final_peak = get_audio_peak_dbfs(final_path)

                    # Atualiza Cache de Duração
                    if file_id not in durations_cache: durations_cache[file_id] = {}
                    durations_cache[file_id]['duration'] = final_duration
                    
                    # Se foi gerado pelo Chatterbox, salvamos a duração "pura" dele antes da masterização também
                    # Como já passamos dessa fase, se não tiver no cache, paciência. Mas podemos tentar inferir ou ignorar.
                    if source_path and source_path.exists() and not is_fallback_copy:
                         durations_cache[file_id]['Chatterbox_duration'] = get_audio_duration(str(source_path))

                    # Atualiza Cache de Masterização
                    mastering_status = 'fallback_copied' if is_fallback_copy else 'mastered'
                    
                    # Tenta pegar pico original para comparação
                    original_peak = None
                    if original_file_path.exists():
                         original_peak = get_audio_peak_dbfs(original_file_path)

                    mastering_cache[file_id] = {
                        'status': mastering_status,
                        'original_peak_dbfs': original_peak,
                        'final_peak_dbfs': final_peak,
                        'timestamp': datetime.now().isoformat()
                    }
                    if source_path and source_path.exists() and not is_fallback_copy:
                        mastering_cache[file_id]['dubbed_peak_before_mastering_dbfs'] = get_audio_peak_dbfs(source_path)

                    # --- PERSISTÊNCIA ATÔMICA ---
                    safe_json_write(durations_cache, durations_cache_path)
                    safe_json_write(mastering_cache, mastering_cache_path)
                    
                except Exception as e:
                    logging.error(f"Erro ao capturar métricas finais para {file_id}: {e}")

        cb(100, 8, "Finalização e masterização concluídas.")
        
        # --- ETAPA EXTRA: UNIR SEGMENTOS SEPARADOS ---
        # Se houve split de arquivos longos (ex: sample_seg001, sample_seg002...), precisamos juntá-los agora.
        logging.info("Verificando se há segmentos para unir...")
        final_output_dir = job_dir / "_saida_final"
        segment_groups = {}
        
        # Regex tripla para capturar todas as táticas de divisão de segmentos do sistema
        # 1. Vídeos: sample_0156_seg001_3s.wav
        # 2. Jogos (Silêncio): sample_0088_parte_004.wav
        # 3. Jogos (Orador/Cirúrgica v10.60): sample_0088_p01.wav
        seg_pattern_video = re.compile(r"(.+)_seg(\d{3})_(\d+)s(\..+)")
        seg_pattern_jogos_silence = re.compile(r"(.+)_parte_(\d{3})(\..+)")
        seg_pattern_jogos_speaker = re.compile(r"(.+)_p(\d{2})(\..+)")
        
        for file_path in final_output_dir.glob("*"):
            match_video = seg_pattern_video.match(file_path.name)
            match_jogos_s = seg_pattern_jogos_silence.match(file_path.name)
            match_jogos_p = seg_pattern_jogos_speaker.match(file_path.name)
            
            if match_video:
                base_name, idx, ext = match_video.group(1), int(match_video.group(2)), match_video.group(4)
                if base_name not in segment_groups: segment_groups[base_name] = []
                segment_groups[base_name].append((idx, file_path, ext))
            elif match_jogos_s:
                base_name, idx, ext = match_jogos_s.group(1), int(match_jogos_s.group(2)), match_jogos_s.group(3)
                if base_name not in segment_groups: segment_groups[base_name] = []
                segment_groups[base_name].append((idx, file_path, ext))
            elif match_jogos_p:
                base_name, idx, ext = match_jogos_p.group(1), int(match_jogos_p.group(2)), match_jogos_p.group(3)
                if base_name not in segment_groups: segment_groups[base_name] = []
                segment_groups[base_name].append((idx, file_path, ext))
        
        if segment_groups:
            segments_backup_dir = final_output_dir / "segmentos_individuais_backup"
            segments_backup_dir.mkdir(exist_ok=True)
            
            for base_name, segments in segment_groups.items():
                if not segments: continue
                segments.sort(key=lambda x: x[0])
                output_merged_path = final_output_dir / f"{base_name}{segments[0][2]}"
                list_path = final_output_dir / f"{base_name}_concat_list.ffmpeg_list"
                
                logging.info(f"Unindo {len(segments)} segmentos para criar: {output_merged_path.name}")
                
                # Se for apenas 1 segmento restante (ex: a parte 02 foi silenciada/apagada por erro)
                if len(segments) == 1:
                    logging.info(f"Reconstruindo arquivo único órfão: {segments[0][1].name}")
                    try:
                        shutil.copy(str(segments[0][1]), str(output_merged_path))
                        shutil.move(str(segments[0][1]), str(segments_backup_dir / segments[0][1].name))
                        continue
                    except Exception as e:
                        logging.error(f"Erro ao renomear arquivo órfão {base_name}: {e}")
                        continue
                
                concat_success = False
                # TENTATIVA 1: FFmpeg stream copy (Rápido e sem perda)
                try:
                    with open(list_path, 'w', encoding='utf-8') as f:
                        for _, seg_path, _ in segments:
                            f.write(f"file '{seg_path.name}'\n")
                    
                    subprocess.run([
                        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', 
                        '-i', str(list_path), '-c', 'copy', str(output_merged_path)
                    ], check=True, capture_output=True)
                    concat_success = True
                except Exception as e:
                    logging.warning(f"FFmpeg copy falhou para {base_name}, tentando Fallback Pydub... Erro: {e}")
                
                # TENTATIVA 2: PyDub Concat (Robusto, recodifica mas ignora cabeçalhos corrompidos)
                if not concat_success:
                    try:
                        from pydub import AudioSegment
                        merged_audio = AudioSegment.empty()
                        for _, seg_path, _ in segments:
                            merged_audio += AudioSegment.from_file(str(seg_path))
                        merged_audio.export(str(output_merged_path), format=segments[0][2].replace('.', ''))
                        concat_success = True
                        logging.info(f"Fallback PyDub concluiu a união de {base_name}.")
                    except Exception as e2:
                        logging.error(f"Erro FATAL ao unir segmentos de {base_name} no fallback: {e2}")
                
                # Limpeza: Move fragmentos para backup e apaga lista
                if concat_success:
                    
                    for _, seg_path, _ in segments:
                        if seg_path.exists():
                            moved = False
                            for attempt in range(5):
                                try:
                                    shutil.move(str(seg_path), str(segments_backup_dir / seg_path.name))
                                    moved = True
                                    break
                                except Exception:
                                    time.sleep(1) # Aguarda liberação do Antivírus/Windows
                            
                            if not moved:
                                logging.warning(f"Aviso: Não foi possível mover {seg_path.name} para backup (Lock persistente do Windows).")
                                
                    if list_path.exists():
                        try:
                            os.remove(list_path)
                        except: pass
                        
        gerar_relatorio_final(job_dir, job_id, project_data, file_format_map)

        # =========================================================================
        # ETAPA 8: CONTROLE DE QUALIDADE NEXUS (LQA) + AUTO-HEALING
        # =========================================================================
        logging.info("--- INICIANDO CONTROLE DE QUALIDADE NEXUS (MODO SUPER SÔNICO) ---")
        
        lqa_lock = Lock()
        lqa_progress = 0
        total_lqa = len(project_data)
        
        def _processar_lqa_item(seg_data):
            nonlocal lqa_progress
            
            file_id = seg_data['id']
            file_name = seg_data.get('file_name', f"{file_id}.wav")
            final_path = final_output_dir / f"{file_id}{file_format_map.get(file_id, '.wav')}"
            original_duration = seg_data.get('duration', 0) # BUGFIX: Usando o duration correto!
            
            with lqa_lock:
                lqa_progress += 1
                prog = (lqa_progress / total_lqa) * 100
                cb(prog, 9, f"Auditando Nexus (Thread): {file_name}")
                
            if not final_path.exists():
                seg_data['lqa_status'] = "ERRO"
                seg_data['lqa_details'] = "Arquivo final não gerado."
                return
            
            # Análise Nexus (Stage 8)
            # [NEXUS FIX] Se já foi validado pelo Whisper no Stage 7, mantemos o status.
            if seg_data.get('lqa_status') == 'OK' and "(Conteúdo validado)" in str(seg_data.get('lqa_details', '')):
                lqa_status, diagnostics, needs_healing = "OK", seg_data['lqa_details'], False
            else:
                translated_text = seg_data.get('translated_text', '')
                lqa_status, diagnostics, needs_healing = nexus_lqa_validator(
                    final_path, original_duration, file_id, job_dir, 
                    mode='final', expected_text=translated_text
                )
            
            # --- AUTO-HEALING (Volume) ---
            if needs_healing:
                logging.info(f"💊 Nexus: Aplicando Auto-Healing para '{file_id}' (Volume Baixo)")
                healed_path = final_path.with_name(f"{file_id}_healed{final_path.suffix}")
                cmd_heal = ['ffmpeg', '-y', '-i', str(final_path), '-af', 'volume=8dB,loudnorm=I=-16:TP=-1.5:LRA=11', str(healed_path)]
                res = subprocess.run(cmd_heal, capture_output=True, text=True)
                if res.returncode == 0:
                    shutil.move(str(healed_path), str(final_path))
                    # Re-valida após cura usando ASR para precisão total
                    translated_text = seg_data.get('translated_text', '')
                    lqa_status_new, diagnostics_new, _ = nexus_lqa_validator(
                        final_path, original_duration, file_id, job_dir, 
                        mode='final', expected_text=translated_text
                    )
                    if lqa_status_new == "OK":
                        lqa_status = "OK (Curado)"
                        diagnostics = f"Resolvido após Healing. Antigo problema: [{diagnostics}]"
                    else:
                        lqa_status = f"{lqa_status_new} (Falha na Cura)"
                        diagnostics = diagnostics_new
                else:
                    diagnostics += " | Falha no comando do Auto-Healing."

            # Salva os resultados no dicionário
            with lqa_lock:
                seg_data['lqa_status'] = lqa_status
                seg_data['lqa_details'] = diagnostics

        # Execução Paralela do LQA usando 3 Threads (Preserva 1 núcleo no i5)
        with ThreadPoolExecutor(max_workers=3) as executor:
            futuros = [executor.submit(_processar_lqa_item, seg) for seg in project_data]
            for f in as_completed(futuros):
                # Captura eventuais erros que quebrarem as threads
                try:
                    f.result()
                except Exception as e_thread:
                    logging.error(f"Erro Crítico em Thread de LQA: {e_thread}")
                    
        # Salva o arquivo completo de uma vez ao final
        safe_json_write(project_data, job_dir / "project_data.json")

        # Atualiza Relatório com os dados da auditoria Nexus
        gerar_relatorio_final(job_dir, job_id, project_data, file_format_map)
        safe_json_write(project_data, job_dir / "project_data.json")
        
        cb(100, 10, "Processo concluído! Arquivos finais auditados em '_saida_final'.")

    except Exception as e:
        import traceback
        logging.error(f"ERRO NO PIPELINE (Job ID: {job_id}): {e}\n{traceback.format_exc()}")
        set_progress(job_id, 100, len(ETAPAS_JOGOS) - 1, start_time, ETAPAS_JOGOS, subetapa=f"Erro: {e}")
        status_path = job_dir / "job_status.json"
        status_data = safe_json_read(status_path) or {}
        status_data['status'] = 'failed'
        status_data['error'] = str(e)
        safe_json_write(status_data, status_path)
    finally:
        with active_jobs_lock:
            if job_id in active_jobs:
                active_jobs.remove(job_id)
                
        # [MEMORY RECOVERY] Limpeza agressiva no final do Job
        import gc
        import torch
        logging.info(" === INICIANDO LIMPEZA AGRESSIVA DE MEMÓRIA PÓS-JOB ===")
        unload_whisper_model()
        unload_qwen3_model()
        unload_gema_model()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        logging.info(" === LIMPEZA DE MEMÓRIA CONCLUÍDA ===")

# --- FUNÇÃO DE REMOÇÃO DE RÁDIO/NOISE (SUBSTITUI OPENUNMIX) ---
def processar_separacao(job_dir, job_id, start_time):
    with active_jobs_lock:
        if len(active_jobs) >= MAX_CONCURRENT_JOBS:
             logging.warning(f"❌ [HARDWARE] Limite de {MAX_CONCURRENT_JOBS} job(s) atingido. Ignorando {job_id}.")
             return
        active_jobs.add(job_id)
    
    try:
        set_low_process_priority()
        def cb(p, etapa, s=None, **kwargs): set_progress(job_id, p, etapa, start_time, ETAPAS_SEPARACAO, s, **kwargs)
        
        input_dir = job_dir / "_input"
        output_dir = job_dir / "_saida_audio_restaurado"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        input_files = list(input_dir.glob("*.*"))
        total_files = len(input_files)

        if total_files == 0:
            cb(100, 3, "Nenhum arquivo encontrado para restaurar.")
            return

        cb(0, 1, f"Iniciando restauração de áudio (FFmpeg) para {total_files} arquivos...")
        
        for i, audio_file in enumerate(input_files):
            cb((i / total_files) * 100, 1, f"Processando: {audio_file.name}")
            
            # Verificar se é vídeo e extrair áudio
            suffix = audio_file.suffix.lower()
            if suffix in ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']:
                extracted_audio_path = audio_file.with_name(f"{audio_file.stem}_extracted.wav")
                
                if extracted_audio_path.exists() and extracted_audio_path.stat().st_size > 1000:
                    logging.info(f"✅ Áudio já extraído encontrado: {extracted_audio_path.name}. Pulando extração.")
                    audio_file = extracted_audio_path
                else:
                    logging.info(f"Arquivo de vídeo detectado: {audio_file.name}. Extraindo áudio...")
                    try:
                        # Extrai áudio para wav estéreo 44.1kHz
                        cmd_extract = [
                            'ffmpeg', '-y', '-i', str(audio_file),
                            '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2',
                            str(extracted_audio_path)
                        ]
                        subprocess.run(cmd_extract, check=True, capture_output=True, text=True)
                        audio_file = extracted_audio_path # Atualiza a variável para usar o áudio extraído
                        logging.info(f"Áudio extraído com sucesso: {audio_file.name}")
                    except subprocess.CalledProcessError as e:
                        logging.error(f"Erro ao extrair áudio do vídeo {audio_file.name}: {e.stderr}")
                        continue
            
            # --- LÓGICA DE LIMPEZA / REMOÇÃO DE EFEITO DE RÁDIO (FFMPEG) ---
            output_path = output_dir / f"{audio_file.stem}.wav"
            
            # Filtros Explicados:
            # 1. afftdn=nf=-25: Remove ruído de banda larga (chiado/hiss) com força média (-25dB)
            # 2. highpass=f=80: Remove "rumble" e graves exagerados que sujam a clonagem
            # 3. lowpass=f=12000: Corta frequências super agudas inúteis que podem ter artefatos
            # 4. equalizer=f=3500...: Dá um leve ganho nas frequências de voz para tentar "abrir" o som abafado
            # [FIX] Removido compand agressivo que causava o efeito "bombear" / cortar a voz subitamente.
            
            cmd_clean = [
                'ffmpeg', '-y', '-i', str(audio_file),
                '-af', 'afftdn=nf=-25, highpass=f=80, lowpass=f=12000, equalizer=f=3500:t=h:w=2000:g=2',
                str(output_path)
            ]

            try:
                subprocess.run(cmd_clean, check=True, capture_output=True, text=True)
                logging.info(f"Áudio restaurado salvo em: {output_path}")
            except subprocess.CalledProcessError as e:
                logging.error(f"Erro ao limpar áudio {audio_file.name}: {e.stderr}")
                # Em caso de erro, tenta copiar o original como fallback
                shutil.copy(audio_file, output_path)

        cb(100, 2, "Finalizando processos...")
        cb(100, 3, "Restauração concluída!")

    except Exception as e:
        logging.error(f"ERRO NO PIPELINE DE RESTAURAÇÃO (Job ID: {job_id}): {e}\n{traceback.format_exc()}")
        set_progress(job_id, 100, len(ETAPAS_SEPARACAO) - 1, start_time, ETAPAS_SEPARACAO, subetapa=f"Erro: {e}")
        status_path = job_dir / "job_status.json"
        status_data = safe_json_read(status_path) or {}
        status_data['status'] = 'failed'
        status_data['error'] = str(e)
        safe_json_write(status_data, status_path)
    finally:
        with active_jobs_lock:
            if job_id in active_jobs:
                active_jobs.remove(job_id)


# --- ROTAS FLASK ---
def calculate_files_hash(files):
    hasher = hashlib.sha256()
    sorted_files = sorted(files, key=lambda f: f.filename)
    for f in sorted_files:
        file_info = f"{f.filename}:{f.seek(0, os.SEEK_END)}"
        hasher.update(file_info.encode('utf-8'))
        f.seek(0)
    return hasher.hexdigest()

# --- INTEGRAÇÃO COM MÓDULO DE VÍDEOS ---
# (nexus_video_engine removido)


@app.route('/transcrever', methods=['POST'])
def transcrever_arquivo():
    start_time = time.time()
    if 'transcricao_file' not in request.files:
        return jsonify({'error': 'Nenhum ficheiro enviado.'}), 400
    
    file = request.files['transcricao_file']
    if file.filename == '':
        return jsonify({'error': 'Nenhum ficheiro selecionado.'}), 400

    timestamp = int(time.time())
    datestamp = datetime.now().strftime('%d.%m.%Y')
    job_id = f"job_transcricao_{datestamp}_{timestamp}"
    job_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    filename = secure_filename(file.filename)
    extension = Path(filename).suffix
    input_path = job_dir / f"input{extension}"
    file.save(input_path)

    status_data = {'job_id': job_id, 'status': 'iniciando', 'original_filename': filename}
    safe_json_write(status_data, job_dir / "job_status.json")

    threading.Thread(target=processar_transcricao, args=(job_dir, job_id, start_time)).start()
    return jsonify({'status': 'processing', 'job_id': job_id})

@app.route('/converter', methods=['POST'])
def converter_arquivos():
    start_time = time.time()
    if 'arquivos_referencia' not in request.files or 'arquivos_para_converter' not in request.files:
        return jsonify({'error': 'Faltam os arquivos de referência ou os arquivos para converter.'}), 400

    ref_files = request.files.getlist('arquivos_referencia')
    conv_files = request.files.getlist('arquivos_para_converter')

    if not ref_files or not conv_files:
        return jsonify({'error': 'Nenhum arquivo enviado em uma das categorias.'}), 400

    timestamp = int(time.time())
    datestamp = datetime.now().strftime('%d.%m.%Y')
    job_id = f"job_conversor_{datestamp}_{timestamp}"
    job_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
    
    ref_dir = job_dir / "_1_referencia"
    conv_dir = job_dir / "_2_para_converter"
    ref_dir.mkdir(parents=True, exist_ok=True)
    conv_dir.mkdir(parents=True, exist_ok=True)

    file_format_map = {}
    for file in ref_files:
        filename = secure_filename(file.filename)
        file.save(ref_dir / filename)
    
    for file in conv_files:
        filename = secure_filename(file.filename)
        base_filename, extension = Path(filename).stem, Path(filename).suffix
        file_format_map[base_filename] = extension
        file.save(conv_dir / filename)

    status_data = {'job_id': job_id, 'status': 'iniciando', 'file_format_map': file_format_map}
    safe_json_write(status_data, job_dir / "job_status.json")

    threading.Thread(target=processar_conversao, args=(job_dir, job_id, start_time)).start()
    return jsonify({'status': 'processing', 'job_id': job_id})

@app.route('/separar_audio', methods=['POST'])
def separar_audio():
    start_time = time.time()
    
    files = []
    if 'separacao_file' in request.files:
        files = request.files.getlist('separacao_file')
    
    # Fallback se não encontrar pela chave especifica, tenta pegar todos os arquivos enviados
    if not files:
        files = list(request.files.values())

    # Filtra arquivos vazios
    files = [f for f in files if f.filename != '']

    if not files:
        return jsonify({'error': 'Nenhum ficheiro selecionado.'}), 400

    timestamp = int(time.time())
    datestamp = datetime.now().strftime('%d.%m.%Y')
    job_id = f"job_separacao_{datestamp}_{timestamp}"
    job_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
    input_dir = job_dir / "_input"
    input_dir.mkdir(parents=True, exist_ok=True)

    saved_filenames = []
    for file in files:
        filename = secure_filename(file.filename)
        file.save(input_dir / filename)
        saved_filenames.append(filename)

    status_data = {'job_id': job_id, 'status': 'iniciando', 'file_count': len(saved_filenames), 'files': saved_filenames}
    safe_json_write(status_data, job_dir / "job_status.json")

    threading.Thread(target=processar_separacao, args=(job_dir, job_id, start_time)).start()
    return jsonify({'status': 'processing', 'job_id': job_id})

def limpar_hallucinacoes_projeto(job_id):
    """
    Varre a pasta de saída final e aplica o Surgical Sync v2.0 em arquivos existentes.
    Útil para limpar projetos que já terminaram mas ficaram com 'eeee' no áudio.
    """
    project_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
    output_dir = project_dir / "_saida_final"
    
    if not output_dir.exists():
        return False, "Pasta de saída final não encontrada."
    
    # Carregar project_data para saber as durações originais (para a Trava de Segurança)
    project_data_path = project_dir / "project_data.json"
    durations = {}
    if project_data_path.exists():
        try:
            with open(project_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for seg in data:
                    durations[seg['id']] = seg.get('duration', 0)
        except: pass

    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent
    
    count = 0
    files = list(output_dir.glob("*.wav"))
    for file_path in files:
        seg_id = file_path.stem
        
        try:
            clip_raw = AudioSegment.from_wav(str(file_path))
            # [v11.7] Relaxado para -50dB (COD Radio Style)
            nonsilent_ranges = detect_nonsilent(clip_raw, min_silence_len=150, silence_thresh=-50)
            
            if nonsilent_ranges:
                start_trim = max(0, nonsilent_ranges[0][0] - 20)
                end_trim = nonsilent_ranges[-1][1]
                # [v11.7] Margem de 150ms para evitar 'mova' -> 'mo'
                final_end_trim = min(len(clip_raw), end_trim + 150)
                clip_trimmed = clip_raw[start_trim:final_end_trim]
                
                # Trava de Segurança (+50%)
                original_dur = durations.get(seg_id, 0)
                if original_dur > 0 and len(clip_trimmed) > (original_dur * 1500):
                    clip_trimmed = clip_trimmed[:int(original_dur * 1400) + 100]
                
                if len(clip_trimmed) < len(clip_raw) - 50: # Se mudou mais de 50ms
                    clip_trimmed.export(str(file_path), format="wav")
                    count += 1
        except: continue
        
    return True, f"Limpeza concluída. {count} arquivos de áudio foram higienizados no projeto {job_id}."

@app.route('/limpar_artefatos/<job_id>')
def route_limpar_artefatos(job_id):
    success, message = limpar_hallucinacoes_projeto(job_id)
    return jsonify({"success": success, "message": message})

@app.route('/dublar_jogos', methods=['POST'])
def dublar_jogos():
    start_time = time.time()
    
    if 'job_id' in request.form and request.form.get('job_id'):
        job_id = request.form.get('job_id')
        job_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
        if not job_dir.exists(): return jsonify({'error': f'Trabalho não encontrado.'}), 404
        threading.Thread(target=processar_dublagem_jogos, args=(job_dir, job_id, start_time)).start()
        return jsonify({'status': 'processing', 'job_id': job_id})

    elif 'wav_files' in request.files:
        files = request.files.getlist('wav_files')
        if not files or files[0].filename == '': return jsonify({'error': 'Nenhum ficheiro enviado.'}), 400

        files_hash = calculate_files_hash(files)
        if existing_job_id := find_existing_project(files_hash):
            job_dir = Path(app.config['UPLOAD_FOLDER']) / existing_job_id
            threading.Thread(target=processar_dublagem_jogos, args=(job_dir, existing_job_id, start_time)).start()
            return jsonify({'status': 'processing', 'job_id': existing_job_id})

        timestamp = int(time.time())
        datestamp = datetime.now().strftime('%d.%m.%Y')
        job_id = f"job_jogos_{datestamp}_{timestamp}"
        job_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
        (job_dir / "_1_MOVER_OS_FICHEIROS_DAQUI").mkdir(parents=True, exist_ok=True)
        diarization_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
        diarization_dir.mkdir(parents=True, exist_ok=True)

        game_profile = request.form.get('game_profile', 'padrao')
        user_glossary = request.form.get('glossary', '')

        first_file_data = files[0].read()
        files[0].seek(0)
        
        best_profile = find_best_audio_profile(first_file_data, job_dir)

        if not best_profile:
            logging.error("NÃO FOI POSSÍVEL DETECTAR UM FORMATO DE ÁUDIO VÁLIDO.")
            return jsonify({'error': 'Não foi possível detectar um formato de áudio válido.'}), 400

        if 'wav_files' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado.'}), 400
            
        files = request.files.getlist('wav_files')
        
        file_format_map = {}
        # [v10.71 CONSOLIDATED] Suporte a ZIP e arquivos soltos
        for file in files:
            if not file.filename: continue
            filename = secure_filename(file.filename)
            extension = Path(filename).suffix.lower()
            
            if extension == '.zip':
                temp_zip_path = job_dir / filename
                file.save(temp_zip_path)
                try:
                    with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                        for member in zip_ref.namelist():
                            if member.startswith('__MACOSX') or member.startswith('.'): continue
                            m_path = Path(member)
                            if not member.endswith('/'):
                                target_path = (job_dir / "_1_MOVER_OS_FICHEIROS_DAQUI") / m_path.name
                                file_format_map[m_path.stem] = m_path.suffix
                                with zip_ref.open(member) as source, open(target_path, "wb") as target:
                                    shutil.copyfileobj(source, target)
                    os.remove(temp_zip_path)
                    logging.info(f"ZIP extraído com sucesso: {filename}")
                except Exception as e:
                    logging.error(f"Falha ao extrair ZIP: {e}")
            else:
                # Arquivo WAV comum
                file_data = file.read()
                file.seek(0)
                base_filename = Path(filename).stem
                file_format_map[base_filename] = extension
                
                if best_profile:
                    try:
                        base_filename = Path(filename).stem
                        output_path = job_dir / "_1_MOVER_OS_FICHEIROS_DAQUI" / f"{base_filename}.wav"
                        cmd = ['ffmpeg', '-y']
                        profile_params = {k: v for k, v in best_profile.items() if k != 'name'}
                        for key, value in profile_params.items():
                            cmd.extend([f'-{key}', value])
                        cmd.extend(['-i', 'pipe:0', '-c:a', 'pcm_s16le', '-ar', '44100', '-ac', '1', str(output_path)])
                        subprocess.run(cmd, input=file_data, check=True, capture_output=True)
                    except Exception as e:
                        logging.error(f"Falha ao converter {filename}: {e}")
                else:
                    file.save(job_dir / "_1_MOVER_OS_FICHEIROS_DAQUI" / filename)

        source_dir = job_dir / "_1_MOVER_OS_FICHEIROS_DAQUI"
        for audio_file in list(source_dir.glob("*.wav")):
            # [v10.55 INTELLIGENT DIARIZATION SPLIT]
            # O usuário solicitou "escutar todos os áudios" e cortar se a voz mudar.
            # Também mantemos o split por duração se > 25s.
            
            dur = get_audio_duration(audio_file)
            dur_f = round(dur, 2)
            logging.info(f"Auditando '{audio_file.name}' ({dur_f}s) em busca de trocas de orador...")
            
            # 1. Tenta Split por Orador (Diarização Cirúrgica baseada em VAD)
            if dur > 1.8: # Tamanho mínimo para análise estatística
                 if split_audio_by_speaker(audio_file, job_dir):
                      continue # Já foi splitado e movido
            
            # [v10.86 REMOVIDO] Split por Silêncio foi desativado.
            # O corte bruto por silêncio estava cortando o final das palavras e limitando
            # o tamanho dos espaços de dublagem da IA. Agora deixamos o Whisper gerenciar
            # arquivos grandes de forma inteligente e segura (Micro-chunking lógico).

        for i in range(1, int(request.form.get('num_speakers_jogos', 1)) + 1):
            (diarization_dir / f"voz{i}").mkdir(exist_ok=True)

        status_data = {
            'job_id': job_id, 'status': 'iniciando', 'files_hash': files_hash, 
            'file_format_map': file_format_map, 'detected_profile': best_profile,
            'game_profile': game_profile, 'user_glossary': user_glossary
        }
        safe_json_write(status_data, job_dir / "job_status.json")

        threading.Thread(target=processar_dublagem_jogos, args=(job_dir, job_id, start_time)).start()
        return jsonify({'status': 'processing', 'job_id': job_id})
    else:
        return jsonify({'error': 'Requisição inválida.'}), 400


@app.route('/update_text', methods=['POST'])
def update_text():
    data = request.json
    job_id, file_id, new_text = data.get('job_id'), data.get('file_id'), data.get('text')

    if not all([job_id, file_id, new_text is not None]):
        return jsonify({'error': 'Dados incompletos.'}), 400

    job_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
    if not job_dir.is_dir(): return jsonify({'error': 'Job não encontrado.'}), 404

    project_data_path = job_dir / "project_data.json"
    project_data = safe_json_read(project_data_path)
    if project_data is None: return jsonify({'error': 'Falha ao ler dados do projeto.'}), 500

    target_segment = next((seg for seg in project_data if seg.get('id') == file_id), None)
    if not target_segment: return jsonify({'error': f'Arquivo com id {file_id} não encontrado.'}), 404

    target_segment['manual_edit_text'] = new_text
    logging.info(f"Texto atualizado para '{file_id}' no job '{job_id}': '{new_text}'")
    safe_json_write(project_data, project_data_path)
    safe_json_write(target_segment, job_dir / "_backup_texto_final" / f"{file_id}.json")
    
    try:
        dubbed_audio_path = job_dir / "_dubbed_audio" / f"{file_id}_dubbed.wav"
        if dubbed_audio_path.exists():
            os.remove(dubbed_audio_path)
            logging.info(f"Áudio temporário removido para '{file_id}'.")

        status = safe_json_read(job_dir / "job_status.json") or {}
        file_format_map = status.get('file_format_map', {})
        extension = file_format_map.get(file_id, '.wav')
        final_audio_path = job_dir / "_saida_final" / f"{file_id}{extension}"
        if final_audio_path.exists():
            os.remove(final_audio_path)
            logging.info(f"Áudio final removido para '{file_id}'.")
            
    except Exception as e:
        logging.error(f"Erro ao remover áudios antigos para '{file_id}': {e}")

    return jsonify({'status': 'success', 'message': f'Texto para {file_id} atualizado.'})

@app.route('/recent_jobs')
def recent_jobs():
    jobs = []
    # Force absolute path resolution
    upload_path = Path(app.config['UPLOAD_FOLDER']).resolve()
    
    # logging.debug(f"[RECENT_JOBS] Verificando pasta uploads: {upload_path}")
    
    if not upload_path.exists():
        logging.warning(f"[RECENT_JOBS] Pasta de uploads NÃO encontrada: {upload_path}")
        return jsonify([])

    try:
        # List directories sorted by mtime descending
        dirs = sorted([d for d in upload_path.iterdir() if d.is_dir()], 
                      key=lambda x: x.stat().st_mtime, reverse=True)
        
        # logging.info(f"[RECENT_JOBS] Encontrados {len(dirs)} diretórios candidatos.")

        for d in dirs:
            status_file = d / "job_status.json"
            # logging.debug(f"[RECENT_JOBS] Checando: {d.name}")
            
            if status_file.exists():
                try:
                    data = safe_json_read(status_file)
                    if data:
                        # logging.info(f"[RECENT_JOBS] PROJETO VÁLIDO: {d.name} | Status: {data.get('status')}")
                        jobs.append({
                            'id': data.get('job_id', d.name),
                            'status': data.get('status', 'unknown'),
                            'progress': data.get('progress', 0),
                            'etapa': data.get('etapa', ''),
                            'file_count': data.get('file_count', 0),
                            'date': datetime.fromtimestamp(d.stat().st_mtime).strftime('%d/%m %H:%M')
                        })
                    else:
                        # [SISTEMA STEALTH] A gestão de jobs de vídeo agora é responsabilidade do Motor Dedicado (5003).
                        pass
                except Exception as read_err:
                     logging.error(f"[RECENT_JOBS] Erro lendo JSON {d.name}: {read_err}", exc_info=True)
            else:
                # logging.debug(f"[RECENT_JOBS] Ignorado (sem JSON): {d.name}")
                pass

            if len(jobs) >= 10: break
            
    except Exception as e:
        logging.error(f"[RECENT_JOBS] ERRO CRÍTICO AO LISTAR: {e}", exc_info=True)
        
    logging.info(f"[RECENT_JOBS] Retornando {len(jobs)} projetos.")
    return jsonify(jobs)

@app.route('/resume_job/<job_id>', methods=['POST'])
def resume_job(job_id):
    """Retoma um trabalho parado ou retorna status se já estiver rodando."""
    logging.info(f"[RESUME] Pedido de retomada recebido para: {job_id}")
    upload_path = Path(app.config['UPLOAD_FOLDER'])
    job_dir = upload_path / job_id
    
    if not job_dir.exists():
        logging.error(f"[RESUME] Pasta não encontrada: {job_dir}")
        return jsonify({'error': 'Job não encontrado'}), 404
    
    with active_jobs_lock:
        if job_id in active_jobs:
            logging.info(f"[RESUME] Job {job_id} já está em active_jobs. Ignorando.")
            return jsonify({'status': 'running', 'message': 'O projeto já está em execução.'})

    # Se não estiver rodando, reinicia a thread
    logging.info(f"[RESUME] Iniciando Thread para: {job_id}")
    
    # [FIX] Força atualização visual imediata
    status_file = job_dir / "job_status.json"
    status_data = safe_json_read(status_file) or {}
    status_data['status'] = 'retomando'
    status_data['etapa'] = 'Reinicializando Processos...'
    safe_json_write(status_data, status_file)
    
    # [FIX] Recupera o tempo já gasto anteriormente no projeto para não zerar o relogio
    tempo_previo = status_data.get('total_elapsed_secs', 0)
    start_time = time.time() - tempo_previo 
    try:
        # [SISTEMA STEALTH] A retomada de jobs de vídeo agora é responsabilidade do Motor Dedicado (5003).
        # Este Hub agora foca apenas na retomada de Jobs de Games/Audio.
        t = threading.Thread(target=processar_dublagem_jogos, args=(job_dir, job_id, start_time))
        t.start()
        logging.info(f"[RESUME] Thread de Games disparada com sucesso: {t.name}")
    except Exception as thread_err:
        logging.critical(f"[RESUME] FALHA AO INICIAR THREAD: {thread_err}", exc_info=True)
        return jsonify({'error': 'Falha interna ao iniciar processo'}), 500

    return jsonify({'status': 'resumed', 'message': 'Processamento retomado com sucesso.'})

# --- AS ROTAS DE VÍDEO (DUBLAR, MAGIC CUT, SHORTS) FORAM MOVIDAS PARA A PORTA 5003 ---
# --- O HUB PREMIUN (HTML) JÁ ESTÁ APONTANDO PARA O LUGAR CORRETO ---

@app.route('/progress/<job_id>')
def progress(job_id):
    with progress_lock:
        if job_id in progress_dict: return jsonify(progress_dict[job_id])
        status_path = Path(app.config['UPLOAD_FOLDER']) / job_id / "job_status.json"
        if status_data := safe_json_read(status_path):
             return jsonify({ 'progress': status_data.get('progress', 0), 'etapa': status_data.get('etapa', 'Pronto'),
                              'subetapa': status_data.get('subetapa'), 'tempo_decorrido': status_data.get('tempo_decorrido', '0:00:00') })
    return jsonify({})

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Erro não tratado na rota: {request.url}\n{traceback.format_exc()}")
    return jsonify({"error": "Ocorreu um erro interno no servidor.", "details": str(e)}), 500

@app.route('/')
def index(): return send_from_directory(app.template_folder, 'nexus_premium.html')

@app.route('/favicon.ico')
def favicon(): return make_response('', 204)

@app.route('/uploads/<path:path>')
def send_upload(path): return send_from_directory(app.config['UPLOAD_FOLDER'], path)

# --- GERENCIAMENTO DE SISTEMA ---
@app.route('/system_info')
def get_system_info_route():
    import os
    base_path = os.getcwd()
    return jsonify({
        'install_path': base_path,
        'os': platform.system() + " " + platform.release(),
        'cpu': platform.processor()
    })

@app.route('/open_folder')
def open_install_folder():
    import subprocess
    import os
    try:
        os.startfile(os.getcwd())
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/uninstall', methods=['POST'])
def uninstall_system():
    """Gera um script de limpeza e encerra o app."""
    import os
    import subprocess
    
    # Script Batch para deletar as pastas pesadas
    # Ele espera 3 segundos para o app fechar totalmente
    batch_content = f"""@echo off
timeout /t 3 /nobreak > nul
echo Iniciando Desinstalacao do Nexus AI...
echo Removendo Ambiente Virtual (env)...
rd /s /q "{os.path.join(os.getcwd(), 'env')}"
echo Removendo Modelos de IA (Gigabytes)...
rd /s /q "{os.path.join(os.getcwd(), 'Models')}"
echo Removendo Logs e Temporarios...
rd /s /q "{os.path.join(os.getcwd(), 'logs')}"
rd /s /q "{os.path.join(os.getcwd(), 'uploads')}"
echo Limpeza concluida!
pause
del "%~f0"
"""
    with open("uninstall_nexus.bat", "w") as f:
        f.write(batch_content)
    
    # Abre o script em uma nova janela de terminal e fecha o app
    os.startfile("uninstall_nexus.bat")
    
    # Encerra o processo atual (força fechamento do Webview e Flask)
    import os
    import signal
    os.kill(os.getpid(), signal.SIGTERM)
    return jsonify({'status': 'uninstalling'})

# [v2026.9 FIX] Aquecimento de Motor e Patch de Emergência
def prewarm_audio_engines():
    try:
        import sys
        import types
        import logging
        import os
        
        logging.info("[INFO] Iniciando Pre-warm e Protecao de Memoria...")
        
        # [NEW] Previne o erro 'partially initialized module' garantindo a ordem global
        import speechbrain
        try:
            import speechbrain.utils.quirks
            import speechbrain.utils.importutils
        except: pass

        # [PATCH] Neutraliza o erro do SpeechBrain 1.1.0 (transducer_loss)
        stubs = ['speechbrain.integrations.numba', 'speechbrain.integrations.numba.transducer_loss']
        for stub in stubs:
            if stub not in sys.modules:
                sys.modules[stub] = types.ModuleType(stub)
        
        os.environ["SB_DISABLE_QUIRKS"] = "1"
        import speechbrain.inference
        
        logging.info("[OK] Motores blindados e prontos.")
    except Exception as e:
        logging.warning(f"[AVISO] Aviso no Pre-warm: {e}")


# =====================================================================
# [v2026.TITAN] PONTES DE INTEGRAÇÃO (CINEMA/VÍDEO)
# =====================================================================

def run_blind_diarization_pass(job_dir, vocals_path, cb=None, etapa_idx=1):
    """
    Passo 1 (Diarização Dupla): Faz varredura cega no áudio ANTES do Whisper.
    Usa VAD PyDub para fatiar apenas onde há som, SpeechBrain para embutir.
    Portado do App_videos Master.
    """
    job_dir = Path(job_dir)
    # [v2026.ULTRA_SENSITIVE] Força re-calculo e usa threshold agressivo de 0.15
    # (Ignora cache para garantir que a nova sensibilidade seja aplicada)
    
    if cb: cb(10, etapa_idx, "Diarização Ultra-Sensível: Mapeando vozes (Modo Deep Scan)...")
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent
    
    try:
        audio = AudioSegment.from_wav(str(vocals_path))
        duration_ms = len(audio)
        
        # [v2026.FORCE_SLICE] Corta o áudio em pedaços de 3s para garantir múltiplas amostras de voz
        slice_len = 3000 # 3 segundos
        segments_to_process = []
        for start_ms in range(0, duration_ms, slice_len):
            end_ms = min(start_ms + slice_len, duration_ms)
            if end_ms - start_ms < 500: continue
            segments_to_process.append((start_ms, end_ms))
        
        if not segments_to_process: return []
             
        if cb: cb(30, etapa_idx, f"Diarização (Pyannote 3.1): Analisando {len(segments_to_process)} amostras de voz...")
        
        import torch
        # [v2026.PURE_PYANNOTE] Usa o motor oficial do Pyannote para embeddings
        diarizer = PyannoteDiarizer(device='cuda' if torch.cuda.is_available() else 'cpu')
        
        signal, fs = robust_audio_load(str(vocals_path))
        if signal.shape[0] > 1: signal = signal.mean(dim=0, keepdim=True)
        if fs != 16000:
            import torchaudio.transforms as T
            resampler = T.Resample(fs, 16000)
            signal = resampler(signal)
        
        results = []
        for i, (sts, ets) in enumerate(segments_to_process):
             start_sec = sts / 1000.0
             end_sec = ets / 1000.0
             
             # Recorta o áudio para o Pyannote analisar
             s_sample = int(start_sec * 16000)
             e_sample = int(end_sec * 16000)
             seg_signal = signal[:, s_sample:e_sample]
             
             if seg_signal.shape[1] < 1600: continue # Pedaço mínimo para o Pyannote
             
             # [v2026.ELITE] Gera o DNA da voz usando Pyannote 3.1
             # Como o PyannoteDiarizer gerencia a pipeline, usamos o encoder embutido
             emb = diarizer.get_file_embedding_from_signal(seg_signal)
             if emb is not None:
                 results.append({"start": start_sec, "end": end_sec, "emb": emb})
             
        if not results: return []

        from sklearn.cluster import AgglomerativeClustering
        embeddings = np.array([r['emb'] for r in results])
        # [v2026.FIX] Reduzido para 0.15 - Nível máximo de separação de oradores
        clusterer = AgglomerativeClustering(n_clusters=None, distance_threshold=0.15, metric='cosine', linkage='average')
        labels = clusterer.fit_predict(embeddings)
        
        final_cache = []
        diarization_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
        diarization_dir.mkdir(parents=True, exist_ok=True)
        
        # [v2026.TITAN] Exporta amostras de áudio para as pastas de voz
        logging.info(f"📁 Organizando amostras de voz em {diarization_dir}...")
        
        for i, lbl in enumerate(labels):
            speaker_id = f"voz{lbl+1}"
            speaker_path = diarization_dir / speaker_id
            speaker_path.mkdir(exist_ok=True)
            
            start_sec = results[i]["start"]
            end_sec = results[i]["end"]
            
            final_cache.append({
                "start": start_sec,
                "end": end_sec,
                "speaker": speaker_id
            })
            
            # Exporta o recorte do áudio (Apenas os primeiros 5 por voz para não lotar o disco)
            existing_samples = list(speaker_path.glob("*.wav"))
            if len(existing_samples) < 5:
                try:
                    import soundfile as sf
                    # signal é [1, samples] @ 16kHz
                    s_sample = int(start_sec * 16000)
                    e_sample = int(end_sec * 16000)
                    seg_data = signal[:, s_sample:e_sample].cpu().numpy().T
                    
                    sample_file = speaker_path / f"amostra_{i}.wav"
                    sf.write(str(sample_file), seg_data, 16000)
                except Exception as e:
                    logging.warning(f"Falha ao exportar amostra de voz {i}: {e}")
            
        safe_json_write(final_cache, cache_path)
        
        # Free Memory
        logging.info("🧹 [VRAM_PURGE] Expulsando Pyannote da GPU (Cego)...")
        del diarizer
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            torch.cuda.synchronize()
        logging.info("✅ [VRAM_PURGE] Pyannote descarregado com sucesso (Cego).")
        
        if cb: cb(50, etapa_idx, "Diarização Cega: Concluída.")
        return final_cache
        
    except Exception as e:
        logging.error(f"Erro na Diarização Cega: {e}")
        return []


def cleanup_on_exit():
    """Limpa processos residuais para liberar a VRAM"""
    try:
        import subprocess
        # Mata processos do llama-cpp que podem ter ficado presos
        subprocess.run(['taskkill', '/F', '/IM', 'llama-server.exe', '/T'], capture_output=True)
    except:
        pass

def transcrever_e_diarizar(audio_path, job_dir=None, cb=None, source_lang="auto"):
    """[v2026.TURBO_PASS] Transcrição Única + Mapeamento de Orador com Cache Persistente."""
    from pathlib import Path
    cleanup_on_exit() 
    if not Path(audio_path).exists(): return []
    
    # [v2026.SMART_RESUME] Tenta carregar do cache para evitar re-processamento pesado
    if job_dir:
        cache_path = Path(job_dir) / "transcription_cache.json"
        if cache_path.exists() and cache_path.stat().st_size > 100:
            logging.info("♻️ [CACHE_HIT] Transcrição e Diarização encontradas no cache. Pulando Whisper/Diarizer.")
            if cb: cb(100, 1, "[Cache] Retomando transcrição salva...")
            return safe_json_read(cache_path)
    
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # 1. DIARIZAÇÃO (Puro Pyannote 3.1 - Áudio Completo com Diarization Shield)
    diarization_segments = []
    
    # [v2026.DIARIZATION_SHIELD] Filtro passa-banda telefônico profissional (300Hz - 3400Hz)
    # + Downmix para Mono + Resample para 16kHz nativo.
    # Remove ruídos de baixa frequência, efeitos sonoros e vazamento de música que confundem os embeddings do Pyannote!
    temp_purified = Path(audio_path).parent / f"diarization_input_purified.wav"
    diarize_input = str(audio_path)
    
    try:
        logging.info(f"🧹 [DIARIZATION_SHIELD] Purificando áudio para o Pyannote: {Path(audio_path).name} -> {temp_purified.name}")
        if cb: cb(3, 1, "[Diarization Shield] Isolando banda de voz humana (300Hz - 3400Hz)...")
        
        cmd_purify = [
            'ffmpeg', '-y', '-hide_banner', '-nostats',
            '-i', str(audio_path),
            '-ac', '1', '-ar', '16000',
            '-af', 'highpass=f=300,lowpass=f=3400',
            str(temp_purified)
        ]
        
        # Executa de forma oculta no Windows para não abrir janelas CMD
        startupinfo = None
        if os.name == 'nt':
            import subprocess
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            
        import subprocess
        subprocess.run(cmd_purify, startupinfo=startupinfo, capture_output=True, check=True)
        
        if temp_purified.exists() and temp_purified.stat().st_size > 1000:
            diarize_input = str(temp_purified)
            logging.info("✅ [DIARIZATION_SHIELD] Áudio com banda purificada e pronto para análise!")
        else:
            logging.warning("⚠️ [DIARIZATION_SHIELD] Arquivo purificado está vazio, usando áudio original.")
    except Exception as e_purify:
        logging.warning(f"⚠️ [DIARIZATION_SHIELD] Erro na filtragem pass-band: {e_purify}. Usando áudio original.")
        
    try:
        if cb: cb(5, 1, "[Pyannote 3.1] Analisando áudio completo para mapear oradores...")
        diarizer = PyannoteDiarizer(device=device)
        annotation = diarizer.diarize(diarize_input, progress_cb=cb)
        
        if annotation:
            # [v2026.DEBUG_PYANNOTE] Logs profundos para monitorar o comportamento nativo
            raw_labels = annotation.labels()
            track_count = len(list(annotation.itertracks()))
            logging.info(f"🔍 [PYANNOTE_DEBUG] Análise Nativa Concluída.")
            logging.info(f"🔍 [PYANNOTE_DEBUG] Oradores distintos encontrados pelo motor: {raw_labels}")
            logging.info(f"🔍 [PYANNOTE_DEBUG] Total de fragmentos de fala mapeados: {track_count}")
            
            for segment, _, speaker in annotation.itertracks(yield_label=True):
                diarization_segments.append({
                    'start': segment.start, 
                    'end': segment.end, 
                    'speaker': f"voz_{speaker}"
                })
            logging.info(f"✅ [PYANNOTE_SUCCESS] {len(set(s['speaker'] for s in diarization_segments))} oradores convertidos nativamente.")
    except Exception as e:
        erro_str = str(e).lower()
        if "401" in erro_str or "unauthorized" in erro_str or "token" in erro_str:
            causa = "Token Inválido/Sem Licença. Rode 'huggingface-cli login' e aceite os termos no site!"
        elif "memory" in erro_str or "oom" in erro_str or "cuda" in erro_str:
            causa = "Falta de Memória de Vídeo (VRAM). Feche outros programas pesados."
        elif "connection" in erro_str or "network" in erro_str:
            causa = "Sem conexão com a internet para baixar o modelo."
        else:
            causa = "Falha técnica inesperada no Pyannote."
            
        error_msg = f"❌ ERRO REAL PYANNOTE: {causa} | Erro Técnico: {e}"
        logging.error(error_msg)
        if cb: cb(100, 1, error_msg, status="erro")
        raise RuntimeError(error_msg)
    finally:
        # Garante a limpeza do arquivo temporário
        if temp_purified.exists():
            try:
                temp_purified.unlink()
                logging.info("🧹 [DIARIZATION_SHIELD] Limpeza concluída: Arquivo temporário removido.")
            except:
                pass

    # ==========================================
    # DESCARREGA PYANNOTE DA GPU IMEDIATAMENTE
    # ==========================================
    if 'diarizer' in locals():
        logging.info("🧹 [VRAM_PURGE] Expulsando Pyannote da GPU...")
        del diarizer
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            torch.cuda.synchronize()
        logging.info("✅ [VRAM_PURGE] Pyannote descarregado com sucesso.")

    # [v2026.TRANSPARENT_MODE] Avisa o usuário claramente, mas permite vídeos de 1 pessoa.
    num_speakers = len(set(s['speaker'] for s in diarization_segments)) if diarization_segments else 0
    
    if num_speakers == 0:
        error_msg = "❌ ERRO FATAL: Nenhuma voz detectada no áudio! Verifique se o vídeo possui falas."
        logging.error(error_msg)
        if cb: cb(100, 1, error_msg, status="erro")
        raise ValueError(error_msg)
    elif num_speakers == 1:
        logging.warning("⚠️ [ATENÇÃO] O Pyannote detectou apenas UMA (1) voz no vídeo inteiro.")
        logging.warning("💡 Se este for um vídeo com múltiplas pessoas, o áudio original pode estar muito misturado.")
    else:
        logging.info(f"✅ [SUCESSO] O Pyannote separou {num_speakers} vozes diferentes perfeitamente!")

    # 2. TRANSCRIÇÃO ÚNICA (Aceleração Máxima)
    if cb: cb(40, 1, "[Whisper AI] Transcrevendo vídeo completo (Modo Turbo)...")
    w_model = get_whisper_model()
    whisper_lang = source_lang if source_lang != "auto" else None
    
    # [v2026.TURBO] Transcreve o arquivo INTEIRO em uma única chamada de GPU
    # [v2026.WHISPER_SENSITIVE] vad_filter DESATIVADO! Vamos forçar o Whisper a ouvir tudo para captar os sussurros.
    segments_gen, info = w_model.transcribe(
        str(audio_path), 
        language=whisper_lang, 
        beam_size=1, 
        word_timestamps=True,
        condition_on_previous_text=False,
        vad_filter=False,
        no_speech_threshold=0.6
    )
    
    whisper_segments = list(segments_gen)
    if cb: cb(80, 1, "[NEXUS] Mapeando roteiro e extraindo vozes...")

    # 3. MAPEAMENTO DE ORADORES E EXTRAÇÃO DE ÁUDIO
    from pydub import AudioSegment
    full_audio = None
    try: full_audio = AudioSegment.from_wav(str(audio_path))
    except: pass

    final_results = []
    voice_base_dir = Path(job_dir) / "_2_PARA_AS_PASTAS_DE_VOZ" if job_dir else None

    recent_texts = [] # Guarda as últimas frases para checar alucinações repetidas

    for i, w_seg in enumerate(whisper_segments):
        text = w_seg.text.strip()
        if not text or len(text) < 2: continue
        
        # Filtro de Alucinação Inteligente (Baseado em Repetições)
        texto_limpo = text.lower().strip()
        
        # 1. Se o Whisper cuspir EXATAMENTE a mesma frase 3 vezes seguidas em segmentos diferentes
        if len(recent_texts) >= 2 and texto_limpo == recent_texts[-1] == recent_texts[-2]:
            continue
            
        # 2. Se o Whisper travar e repetir a MESMA PALAVRA mais de 3 vezes seguidas na mesma frase
        words = texto_limpo.replace(',', '').replace('.', '').replace('!', '').replace('?', '').split()
        is_hallucination = False
        consec_count = 1
        for w_idx in range(1, len(words)):
            if words[w_idx] == words[w_idx-1]:
                consec_count += 1
                if consec_count > 3: # "mais de 3 vezes"
                    is_hallucination = True
                    break
            else:
                consec_count = 1
                
        if is_hallucination:
            continue
            
        recent_texts.append(texto_limpo)
        if len(recent_texts) > 3: recent_texts.pop(0)

        # Identifica o orador predominante e busca o segmento de diarização correspondente para alinhamento
        best_speaker = "voz_Unknown"
        best_d_seg = None
        
        # 1. Tenta achar por ponto médio
        mid_time = (w_seg.start + w_seg.end) / 2
        for d_seg in diarization_segments:
            if d_seg['start'] <= mid_time <= d_seg['end']:
                best_speaker = d_seg['speaker']
                best_d_seg = d_seg
                break
        
        # 2. Se não achar por ponto médio, tenta achar por maior sobreposição
        if best_speaker == "voz_Unknown":
            max_overlap = 0
            for d_seg in diarization_segments:
                overlap = min(w_seg.end, d_seg['end']) - max(w_seg.start, d_seg['start'])
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = d_seg['speaker']
                    best_d_seg = d_seg
                    
        # [v2026.CROSS_VALIDATION_SHIELD] Ideia genial do usuário!
        # Se mesmo checando as bordas o Pyannote não detectou NENHUMA voz nesses milissegundos,
        # e o Whisper gerou texto, então o Whisper está alucinando no silêncio! Joga fora.
        if best_speaker == "voz_Unknown":
            logging.info(f"🛡️ [CROSS-VALIDATION] Pyannote não ouviu NINGUÉM entre {w_seg.start:.1f}s e {w_seg.end:.1f}s. Barrando alucinação do Whisper: '{text}'")
            continue

        # [v2026.LIP_SYNC_ALIGNMENT] Alinhamento milimétrico de lábios (Sincronização Avançada)
        # O Whisper atrasa o início da fala. O Pyannote tem precisão física para captar o início do som.
        # Snaps o início/fim do segmento para o Pyannote se a diferença for razoável (< 1.5s).
        adjusted_start = w_seg.start
        adjusted_end = w_seg.end
        if best_d_seg:
            diff_start = abs(w_seg.start - best_d_seg['start'])
            if diff_start < 1.5:
                adjusted_start = best_d_seg['start']
                
            diff_end = abs(w_seg.end - best_d_seg['end'])
            if diff_end < 1.5:
                adjusted_end = best_d_seg['end']

        seg_id = f"seg_{len(final_results)}"
        final_results.append({
            "id": seg_id,
            "start": adjusted_start,
            "end": adjusted_end,
            "text": text,
            "speaker": best_speaker
        })

        # Extração física
        if full_audio and voice_base_dir:
            try:
                spk_dir = voice_base_dir / best_speaker
                spk_dir.mkdir(parents=True, exist_ok=True)
                chunk = full_audio[int(max(0, adjusted_start-0.05)*1000):int(min(len(full_audio), adjusted_end+0.1)*1000)]
                chunk.export(str(spk_dir / f"{seg_id}.wav"), format="wav")
            except Exception as e:
                logging.warning(f"Falha ao extrair chunk {seg_id}: {e}")

        if cb and i % 10 == 0:
            cb(80 + (i / len(whisper_segments) * 15), 1, f"[Mapeamento] Processando frase {i+1}...")

    if job_dir:
        # [v2026.STRICT_PERSISTENCE] Salva o cache independente do project_data para segurança
        cache_path = Path(job_dir) / "transcription_cache.json"
        safe_json_write(final_results, cache_path)
        logging.info(f"💾 [CACHE_SAVE] Transcrição e Diarização blindadas em: {cache_path.name}")
        prepare_video_speaker_references(job_dir)

    return final_results


def resegment_based_on_pauses(whisper_result, max_chars=200, max_duration=10.0, silence_threshold=1.0, diarization_data=None):
    """Resegmenta as palavras do Whisper baseando-se em pausas e orador."""
    words = whisper_result.get('words', [])
    if not words: return []
    segments = []
    current_segment = {'words': [], 'start': 0, 'end': 0}
    
    for i, word in enumerate(words):
        if not current_segment['words']:
            current_segment['start'] = word['start']
            current_segment['words'].append(word)
            current_segment['end'] = word['end']
            continue
        last_word = current_segment['words'][-1]
        gap = word['start'] - last_word['end']
        should_break = gap > silence_threshold or (word['end'] - current_segment['start']) > max_duration
        
        if not should_break and diarization_data:
            if get_speaker_at_time(word['start'], diarization_data) != get_speaker_at_time(last_word['end'], diarization_data):
                should_break = True
                
        if should_break:
            txt = "".join([w['word'] for w in current_segment['words']]).strip()
            if txt:
                segments.append({'start': current_segment['start'], 'end': current_segment['end'], 'text': txt, 'words': current_segment['words']})
            current_segment = {'words': [word], 'start': word['start'], 'end': word['end']}
        else:
            current_segment['words'].append(word)
            current_segment['end'] = word['end']
    
    txt = "".join([w['word'] for w in current_segment['words']]).strip()
    if txt: segments.append({'start': current_segment['start'], 'end': current_segment['end'], 'text': txt, 'words': current_segment['words']})
    return segments

def get_speaker_at_time(t, diarization_data):
    """Identifica o orador em um tempo específico."""
    if not diarization_data: return "unknown"
    for d in diarization_data:
        if (d['start'] - 0.1) <= t <= (d['end'] + 0.1):
            return d.get('speaker', 'unknown')
    return "unknown"

def recriar_pastas_de_voz(job_dir, audio_path, segments):
    """Reconstrói as pastas de voz a partir de um roteiro existente."""
    try:
        from pydub import AudioSegment
        job_dir = Path(job_dir)
        voice_folders_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
        voice_folders_dir.mkdir(exist_ok=True, parents=True)
        
        logging.info(f"🔨 [RECONSTRUÇÃO] Recriando referências de áudio para {len(segments)} segmentos...")
        full_audio = AudioSegment.from_wav(str(audio_path))
        
        for i, seg in enumerate(segments):
            spk = seg.get('speaker', 'voz_unknown')
            spk_dir = voice_folders_dir / spk
            spk_dir.mkdir(exist_ok=True, parents=True)
            
            chunk = full_audio[int(max(0, seg['start'])*1000):int(seg['end']*1000)]
            chunk.export(str(spk_dir / f"seg_{i}.wav"), format="wav")
            
        logging.info("✅ [RECONSTRUÇÃO] Pastas de voz restauradas com sucesso!")
        prepare_video_speaker_references(job_dir)
        return True
    except Exception as e:
        logging.error(f"Erro ao recriar pastas de voz: {e}")
        return False

def prepare_video_speaker_references(job_dir):
    """
    [v2026.PRE_DUBLAGEM] Analisa as pastas de voz e cria o arquivo mestre de clonagem.
    """
    try:
        from pydub import AudioSegment
        job_dir = Path(job_dir)
        voice_folders_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
        
        if not voice_folders_dir.exists(): return
        
        for voice_folder in voice_folders_dir.iterdir():
            if not voice_folder.is_dir(): continue
            output_ref_path = voice_folder / "_REF_VOZ_UNIFICADA.wav"
            if output_ref_path.exists(): continue
            
            wav_files = sorted(list(voice_folder.glob("seg_*.wav")), key=lambda x: x.stat().st_size, reverse=True)
            if not wav_files: continue
            
            logging.info(f"🎤 [REF_GEN] Criando áudio mestre para: {voice_folder.name}")
            combined_audio = AudioSegment.empty()
            total_dur_ms = 0
            
            for wav_file in wav_files[:12]:
                try:
                    seg = AudioSegment.from_wav(str(wav_file))
                    if len(seg) < 300: continue
                    if len(combined_audio) > 0: combined_audio = combined_audio.append(seg, crossfade=100)
                    else: combined_audio = seg
                    total_dur_ms += len(seg)
                    if total_dur_ms > 12000: break
                except: continue
            
            if len(combined_audio) > 0:
                combined_audio = combined_audio.set_frame_rate(24000).set_channels(1)
                combined_audio.export(str(output_ref_path), format="wav")
                logging.info(f"✅ [REF_READY] Arquivo mestre criado em {voice_folder.name}")
    except Exception as e:
        logging.error(f"Erro ao preparar referências de vídeo: {e}")

if __name__ == "__main__":
    check_ffmpeg()
    host, port = "0.0.0.0", 5001
    url = f"http://127.0.0.1:{port}"
    import threading
    def open_browser():
        import time; time.sleep(1.5)
        import webbrowser
        webbrowser.open_new(url)
    threading.Thread(target=open_browser).start()
    app.run(host=host, port=port, debug=False, threaded=True)

import atexit
atexit.register(cleanup_on_exit)
