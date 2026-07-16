# -*- coding: utf-8 -*-
# Vortex Music Generator Module - [v2026.RTX_ULTRA]
# Temporally decoupled pipeline for VRAM optimization (6GB target)
# Includes automatic 13kHz Low-Pass Filter before AudioSR.

import os
import sys
import subprocess
import json
import logging
import time
import re
import shutil
import random
from pathlib import Path
import torch
import requests
import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter
from nexus.core.model_loader import unload_local_gemma_engine, unload_whisper_model

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
UPLOAD_FOLDER = BASE_DIR / "uploads"
ENV_DIR = BASE_DIR / "env"

def apply_lowpass_filter(input_path, output_path, cutoff_hz=13000):
    """Applies a Butterworth low-pass filter to clean high-frequency metallic artifacts."""
    logging.info(f"[*] [Low-Pass] Aplicando filtro passa-baixa em {cutoff_hz} Hz...")
    try:
        data, sr = sf.read(str(input_path))
        nyquist = 0.5 * sr
        if cutoff_hz >= nyquist:
            shutil.copy(str(input_path), str(output_path))
            return True
            
        normal_cutoff = cutoff_hz / nyquist
        # 6th-order Butterworth low-pass filter
        b, a = butter(6, normal_cutoff, btype='low', analog=False)
        
        if len(data.shape) > 1:
            filtered_channels = []
            for ch in range(data.shape[1]):
                filtered_channels.append(lfilter(b, a, data[:, ch]))
            filtered_data = np.stack(filtered_channels, axis=-1)
        else:
            filtered_data = lfilter(b, a, data)
            
        sf.write(str(output_path), filtered_data, sr)
        logging.info("[*] [Low-Pass] Filtro passa-baixa aplicado com sucesso.")
        return True
    except Exception as e:
        logging.error(f"[ERR] [Low-Pass] Erro ao filtrar áudio: {e}")
        try:
            shutil.copy(str(input_path), str(output_path))
            return True
        except:
            return False

def start_ace_server_helper(dj, acestep_tools_dir, models_dir, update_status):
    """Launches ace-server.exe and waits for it to become ready on port 8085."""
    update_status("🚀 Iniciando motor de áudio local...", "Carregando servidor do motor de música...")
    env = os.environ.copy()
    try:
        import torch
        torch_lib = Path(torch.__file__).parent / "lib"
        if torch_lib.exists():
            env["PATH"] = str(acestep_tools_dir) + os.pathsep + str(torch_lib) + os.pathsep + env.get("PATH", "")
        else:
            env["PATH"] = str(acestep_tools_dir) + os.pathsep + env.get("PATH", "")
    except:
        env["PATH"] = str(acestep_tools_dir) + os.pathsep + env.get("PATH", "")
        
    if torch.cuda.is_available():
        env["GGML_BACKEND"] = "CUDA0"
        env["GGML_CUDA_F16"] = "1"
        env["GGML_CUDA_DMMV_X"] = "64"
        env["CUDA_LAUNCH_BLOCKING"] = "0"
        env["GGML_CUDA_FORCE_MMQ"] = "0"
        
    cmd = [
        str(acestep_tools_dir / "ace-server.exe"),
        "--host", "127.0.0.1",
        "--port", "8085",
        "--models", str(models_dir),
        "--max-batch", "1",
        "--vae-chunk", "512",
        "--vae-overlap", "32"
    ]
    
    log_file_path = UPLOAD_FOLDER / "ace_server.log"
    dj.ace_server_log_file = open(log_file_path, "w", encoding="utf-8")
    dj.ace_server_process = subprocess.Popen(
        cmd, env=env, stdout=dj.ace_server_log_file, stderr=subprocess.STDOUT
    )
    
    try:
        import ctypes
        PROCESS_ALL_ACCESS = 0x1F0FFF
        IDLE_PRIORITY_CLASS = 0x00000040
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, dj.ace_server_process.pid)
        if handle:
            ctypes.windll.kernel32.SetPriorityClass(handle, IDLE_PRIORITY_CLASS)
            ctypes.windll.kernel32.CloseHandle(handle)
    except: pass
    
    server_ready = False
    for _ in range(15):
        if dj.ace_server_process.poll() is not None:
            dj.ace_server_log_file.close()
            with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f_err:
                log_content = f_err.read()
            raise Exception(f"ace-server falhou ao iniciar. Logs:\n{log_content}")
        try:
            r = requests.get("http://127.0.0.1:8085/props", timeout=1)
            if r.status_code == 200:
                server_ready = True
                break
        except: pass
        time.sleep(0.5)
        
    if not server_ready:
        raise Exception("Timeout ao iniciar ace-server.exe local na porta 8085.")

def run_music_generation_flow_logic(dj, title, style, lyrics, mode='text2music', source_audio='', cover_strength=0.6, extend_duration=30, enable_mastering=True, steps=30, cfg_scale=4.0, duration=60, batch_count=1, upscale_steps=25):
    """Orchestrates the temporally decoupled music generation flow."""
    def update_status(task_msg, log_msg=None):
        msg = log_msg or task_msg
        dj.live_current_task = task_msg
        dj.live_logs.append(msg)
        logging.info(task_msg)
        dj.project_state["current_task"] = task_msg
        if log_msg:
            dj.project_state.setdefault("logs", []).append(log_msg)
        dj.save_status()

    def get_audio_duration(file_path):
        try:
            import soundfile as sf
            info = sf.info(str(file_path))
            return info.duration
        except: pass
        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, startupinfo=startupinfo)
            data = json.loads(res.stdout)
            return float(data["format"]["duration"])
        except: pass
        return 0.0

    try:
        dj.generating_music = True
        update_status("🔍 [5%] Verificando ferramentas de música...", "[1/7] Verificando binários e modelos...")
        
        acestep_tools_dir = ENV_DIR / "tools_acestep"
        acestep_tools_dir.mkdir(parents=True, exist_ok=True)
        
        binaries = [
            "ace-server.exe", "ggml.dll", "ggml-cuda.dll", "ggml-cpu-x64.dll",
            "mp3-codec.exe", "neural-codec.exe", "ggml-cpu-haswell.dll",
            "ggml-cpu-skylakex.dll", "ggml-cpu-sse42.dll", "ggml-base.dll"
        ]
        base_url = "https://www.serveurperso.com/temp/acestep.cpp-win64/build/Release/"
        
        for f_name in binaries:
            dest = acestep_tools_dir / f_name
            if not dest.exists():
                update_status(f"⬇️ Baixando {f_name}...", f"Baixando binário {f_name}...")
                dj.download_file_with_progress(base_url + f_name, dest, f_name, update_status)
                
        if os.name == "nt":
            try:
                # Setup CUDA DLLs configuration
                def _find_and_copy_cuda_dlls(dest_dir):
                    candidates = []
                    try:
                        import torch
                        torch_lib = Path(torch.__file__).parent / "lib"
                        if torch_lib.exists(): candidates.append(torch_lib)
                    except: pass
                    import sys
                    for p in sys.path:
                        if "site-packages" in p:
                            sp_path = Path(p)
                            if sp_path.exists():
                                nvidia_dir = sp_path / "nvidia"
                                if nvidia_dir.exists():
                                    for sub in nvidia_dir.glob("**/lib"): candidates.append(sub)
                                    for sub in nvidia_dir.glob("**/bin"): candidates.append(sub)
                    cuda_path = os.environ.get("CUDA_PATH")
                    if cuda_path:
                        cuda_bin = Path(cuda_path) / "bin"
                        if cuda_bin.exists(): candidates.append(cuda_bin)
                    cuda_toolkit_root = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA")
                    if cuda_toolkit_root.exists():
                        for version_dir in cuda_toolkit_root.glob("v*"):
                            cuda_bin = version_dir / "bin"
                            if cuda_bin.exists(): candidates.append(cuda_bin)
                    for p_str in os.environ.get("PATH", "").split(os.pathsep):
                        if p_str:
                            p_path = Path(p_str)
                            if p_path.exists(): candidates.append(p_path)
                    required_prefixes = ["cublas64_", "cublasLt64_", "cudart64_"]
                    found_dlls = {prefix: [] for prefix in required_prefixes}
                    for candidate in candidates:
                        try:
                            for f in candidate.glob("*.dll"):
                                name = f.name.lower()
                                for prefix in required_prefixes:
                                    if name.startswith(prefix): found_dlls[prefix].append(f)
                        except: pass
                    import re
                    version_pattern = re.compile(r"\d+")
                    versioned_files = {}
                    for prefix, paths in found_dlls.items():
                        for path in paths:
                            match = version_pattern.search(path.name)
                            if match:
                                version = int(match.group())
                                versioned_files.setdefault(version, {})[prefix] = path
                    if not versioned_files: return
                    chosen_version = None
                    if 12 in versioned_files and len(versioned_files[12]) == 3: chosen_version = 12
                    elif 11 in versioned_files and len(versioned_files[11]) == 3: chosen_version = 11
                    else:
                        sorted_versions = sorted(versioned_files.keys(), key=lambda v: (len(versioned_files[v]), v), reverse=True)
                        if sorted_versions: chosen_version = sorted_versions[0]
                    if chosen_version is None: return
                    dlls_to_copy = versioned_files[chosen_version]
                    mappings = {}
                    for prefix, src_path in dlls_to_copy.items():
                        mappings[src_path] = src_path.name
                        if prefix == "cublas64_": mappings[src_path] = "cublas64_13.dll"
                        elif prefix == "cublasLt64_": mappings[src_path] = "cublasLt64_13.dll"
                    for src_path, dst_name in mappings.items():
                        dst_path = dest_dir / dst_name
                        if src_path.exists() and not dst_path.exists():
                            shutil.copy(src_path, dst_path)
                _find_and_copy_cuda_dlls(acestep_tools_dir)
                
                hybrid_dll = acestep_tools_dir / "nvcudart_hybrid64.dll"
                if not hybrid_dll.exists():
                    found = False
                    driver_store = Path(r"C:\Windows\System32\DriverStore\FileRepository")
                    if driver_store.exists():
                        for nv_dir in driver_store.glob("nv*"):
                            target_file = nv_dir / "nvcudart_hybrid64.dll"
                            if target_file.exists():
                                shutil.copy(target_file, hybrid_dll)
                                found = True
                                break
                    if not found:
                        for root, dirs, files in os.walk(r"C:\Windows\System32\DriverStore"):
                            if "nvcudart_hybrid64.dll" in [f.lower() for f in files]:
                                shutil.copy(Path(root) / "nvcudart_hybrid64.dll", hybrid_dll)
                                break
            except Exception as ex:
                logging.warning(f"⚠️ Erro ao configurar DLLs CUDA: {ex}")
                
        models_dir = BASE_DIR / "_MODELS_"
        models_dir.mkdir(parents=True, exist_ok=True)
        models_urls = {
            "vae-BF16.gguf": "https://www.serveurperso.com/temp/acestep.cpp-win64/models/vae-BF16.gguf",
            "Qwen3-Embedding-0.6B-Q8_0.gguf": "https://www.serveurperso.com/temp/acestep.cpp-win64/models/Qwen3-Embedding-0.6B-Q8_0.gguf",
            "acestep-5Hz-lm-0.6B-Q8_0.gguf": "https://www.serveurperso.com/temp/acestep.cpp-win64/models/acestep-5Hz-lm-0.6B-Q8_0.gguf"
        }
        for m_name, url in models_urls.items():
            dest = models_dir / m_name
            if not dest.exists():
                update_status(f"⬇️ [15%] Baixando modelo: {m_name}...", f"Baixando modelo {m_name}...")
                dj.download_file_with_progress(url, dest, m_name, update_status)
                
        dit_model = None
        for p in models_dir.glob("*acestep*.gguf"):
            if "lm" not in p.name.lower() and "vae" not in p.name.lower():
                dit_model = p
                break
        if not dit_model:
            m_name = "acestep-v15-turbo-Q4_K_M.gguf"
            dest = models_dir / m_name
            if not dest.exists():
                update_status("⬇️ [15%] Baixando modelo principal...", f"Baixando modelo {m_name}...")
                dj.download_file_with_progress(f"https://www.serveurperso.com/temp/acestep.cpp-win64/models/{m_name}", dest, m_name, update_status)
            dit_model = dest

        update_status("🧹 [25%] Liberando memória da GPU...", "Limpando VRAM antes do Compositor...")
        try: unload_local_gemma_engine()
        except: pass
        try: unload_whisper_model()
        except: pass
        import gc
        gc.collect()
        if torch.cuda.is_available(): torch.cuda.empty_cache()

        caption = style.strip()
        def normalize_lyrics(raw_lyrics):
            if not raw_lyrics: return raw_lyrics
            import re
            normalized = raw_lyrics
            normalized = re.sub(r'\[Verse\s*\d*\]', '[verse]', normalized, flags=re.IGNORECASE)
            normalized = re.sub(r'\[Pre-?Chorus\s*\d*\]', '[pre-chorus]', normalized, flags=re.IGNORECASE)
            normalized = re.sub(r'\[Chorus\s*\d*\]', '[chorus]', normalized, flags=re.IGNORECASE)
            normalized = re.sub(r'\[Bridge\s*\d*\]', '[bridge]', normalized, flags=re.IGNORECASE)
            normalized = re.sub(r'\[Intro\s*\d*\]', '[intro]', normalized, flags=re.IGNORECASE)
            normalized = re.sub(r'\[Outro\s*\d*\]', '[outro]', normalized, flags=re.IGNORECASE)
            normalized = re.sub(r'\[Hook\s*\d*\]', '[hook]', normalized, flags=re.IGNORECASE)
            normalized = re.sub(r'\[Break\s*\d*\]', '[break]', normalized, flags=re.IGNORECASE)
            return normalized
        lyrics_normalized = normalize_lyrics(lyrics)

        # ----------------------------------------------------
        # FASE 1: EXTRAÇÃO DE CONDICIONAMENTO (LANGUAGE MODEL)
        # ----------------------------------------------------
        update_status("🧠 [35%] Iniciando Fase 1: Composição e Letras...", "Carregando servidor em modo Compositor (LM)...")
        start_ace_server_helper(dj, acestep_tools_dir, models_dir, update_status)
        
        lm_data_list = []
        for idx in range(batch_count):
            log_prefix = f"[{idx+1}/{batch_count}] " if batch_count > 1 else ""
            lm_data = None
            
            if (mode == 'cover' or mode == 'extend') and source_audio:
                update_status(f"🔊 {log_prefix}[45%] Analisando música base...", f"{log_prefix}Extraindo tokens da música base...")
                source_path = dj.generated_music_dir / source_audio
                if not source_path.exists(): source_path = UPLOAD_FOLDER / source_audio
                if not source_path.exists(): raise Exception(f"Música de origem não encontrada: {source_audio}")
                
                with open(source_path, "rb") as f_audio:
                    files = {"audio": (source_path.name, f_audio, "audio/mpeg")}
                    res_understand = requests.post("http://127.0.0.1:8085/understand", files=files, timeout=300)
                if res_understand.status_code != 200: raise Exception(f"Erro no understand: {res_understand.text}")
                und_job_id = res_understand.json().get("id")
                
                und_done = False
                for _ in range(120):
                    time.sleep(1)
                    try:
                        res_poll = requests.get(f"http://127.0.0.1:8085/job?id={und_job_id}", timeout=5)
                        if res_poll.status_code == 200:
                            status = res_poll.json().get("status")
                            if status in ["success", "done"]:
                                und_done = True
                                break
                            elif status == "failed": raise Exception(f"Understand falhou: {res_poll.json().get('error')}")
                    except Exception as ex:
                        if "Understand falhou" in str(ex): raise ex
                        
                if not und_done: raise Exception("Timeout no understand.")
                
                res_result = requests.get(f"http://127.0.0.1:8085/job?id={und_job_id}&result=1", timeout=60)
                if res_result.status_code != 200: raise Exception("Erro ao recuperar resultado do understand.")
                
                content_type = res_result.headers.get("Content-Type", "")
                if "multipart/" in content_type:
                    import email
                    msg = email.message_from_bytes(b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + res_result.content)
                    for part in msg.walk():
                        if part.get_content_type() == "application/json":
                            lm_data = json.loads(part.get_payload(decode=True).decode('utf-8'))
                            break
                else: lm_data = res_result.json()
                
                if isinstance(lm_data, list) and len(lm_data) > 0: lm_data = lm_data[0]
                
                if mode == 'extend':
                    codes = lm_data.get("audio_codes", [])
                    precise_duration = len(codes) / 5.0 if isinstance(codes, list) else len(codes.strip().split()) / 5.0
                    source_duration = precise_duration if precise_duration > 0 else get_audio_duration(source_path)
                    if source_duration <= 0: source_duration = lm_data.get("duration", 60.0)
                    repaint_start = max(0.0, source_duration - 1.5)
                    total_duration = repaint_start + extend_duration
                    lm_data["task_type"] = "repaint"
                    lm_data["repainting_start"] = repaint_start
                    lm_data["repainting_end"] = -1.0
                    lm_data["duration"] = total_duration
                    if lyrics_normalized: lm_data["lyrics"] = lyrics_normalized
                else:
                    if caption and caption.strip(): lm_data["caption"] = caption
                    lm_data["audio_cover_strength"] = cover_strength
                    if lyrics_normalized: lm_data["lyrics"] = lyrics_normalized
            elif mode == 'extend':
                raise Exception("Selecione uma música base para estender.")
            else:
                # Text-to-Music normal flow
                update_status(f"🎵 {log_prefix}[50%] Compondo melodia e harmonia...", f"{log_prefix}Processando prompt e estrutura musical...")
                lm_seed = random.randint(1, 2**31 - 1)
                payload_lm = {"caption": caption, "lyrics": lyrics_normalized, "duration": duration, "seed": lm_seed}
                res_lm = requests.post("http://127.0.0.1:8085/lm", json=payload_lm, timeout=300)
                if res_lm.status_code != 200: raise Exception(f"Erro no /lm: {res_lm.text}")
                lm_job_id = res_lm.json().get("id")
                
                lm_done = False
                for _ in range(480):
                    time.sleep(0.25)
                    try:
                        res_poll = requests.get(f"http://127.0.0.1:8085/job?id={lm_job_id}", timeout=5)
                        if res_poll.status_code == 200:
                            status = res_poll.json().get("status")
                            if status in ["success", "done"]:
                                lm_done = True
                                break
                            elif status == "failed": raise Exception(f"LM falhou: {res_poll.json().get('error')}")
                    except Exception as ex:
                        if "LM falhou" in str(ex): raise ex
                        
                if not lm_done: raise Exception("Timeout no Compositor (LM).")
                
                res_result = requests.get(f"http://127.0.0.1:8085/job?id={lm_job_id}&result=1", timeout=60)
                if res_result.status_code != 200: raise Exception("Erro ao recuperar resultado do LM.")
                
                content_type = res_result.headers.get("Content-Type", "")
                if "multipart/" in content_type:
                    import email
                    msg = email.message_from_bytes(b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + res_result.content)
                    for part in msg.walk():
                        if part.get_content_type() == "application/json":
                            lm_data = json.loads(part.get_payload(decode=True).decode('utf-8'))
                            break
                else: lm_data = res_result.json()
                
                if isinstance(lm_data, list) and len(lm_data) > 0: lm_data = lm_data[0]
                if "caption" not in lm_data: lm_data["caption"] = caption

            lm_data_list.append(lm_data)

        # Encerra o servidor Compositor e limpa 100% de VRAM
        update_status("🧹 [60%] Descarregando Compositor e liberando VRAM...", "Encerrando processo do Compositor e limpando GPU...")
        dj.stop_ace_server()
        gc.collect()
        if torch.cuda.is_available(): torch.cuda.empty_cache()
        time.sleep(1) # Intervalo para a GPU estabilizar

        # ----------------------------------------------------
        # FASE 2: SÍNTESE E DIFUSÃO DEDICADA (AUDIO GENERATION)
        # ----------------------------------------------------
        update_status("🚀 [65%] Iniciando Fase 2: Geração do áudio...", "Carregando servidor em modo Síntese (DiT)...")
        start_ace_server_helper(dj, acestep_tools_dir, models_dir, update_status)
        
        generated_files = []
        for idx, lm_data in enumerate(lm_data_list):
            current_title = f"{title}_{idx+1}" if batch_count > 1 else title
            log_prefix = f"[{idx+1}/{batch_count}] " if batch_count > 1 else ""
            
            lm_data["steps"] = steps
            lm_data["cfg_scale"] = cfg_scale
            lm_data["duration"] = duration
            
            update_status(f"🎛️ {log_prefix}[70%] Sintetizando ondas sonoras (Difusora)...", f"{log_prefix}Renderizando áudio do lote...")
            
            if mode == 'extend' and source_audio:
                source_path = dj.generated_music_dir / source_audio
                if not source_path.exists(): source_path = UPLOAD_FOLDER / source_audio
                with open(source_path, "rb") as f_audio:
                    files = {"audio": (source_path.name, f_audio, "audio/mpeg")}
                    data = {"request": json.dumps(lm_data)}
                    res_synth = requests.post("http://127.0.0.1:8085/synth", files=files, data=data, timeout=300)
            else:
                res_synth = requests.post("http://127.0.0.1:8085/synth", json=lm_data, timeout=300)
                
            if res_synth.status_code != 200: raise Exception(f"Erro no /synth: {res_synth.text}")
            synth_job_id = res_synth.json().get("id")
            
            synth_done = False
            for _ in range(720):
                time.sleep(0.25)
                try:
                    res_poll = requests.get(f"http://127.0.0.1:8085/job?id={synth_job_id}", timeout=5)
                    if res_poll.status_code == 200:
                        data = res_poll.json()
                        status = data.get("status")
                        progress = data.get("progress")
                        
                        if progress is not None:
                            pct = int(float(progress))
                            total_pct = 70 + int(pct * 0.25)
                            update_status(f"🎛️ {log_prefix}[{total_pct}%] Gerando áudio: {pct}%...", f"{log_prefix}Difusão: {pct}%")
                            
                        if status in ["success", "done"]:
                            synth_done = True
                            break
                        elif status == "failed": raise Exception(f"Síntese falhou: {data.get('error')}")
                except Exception as ex:
                    if "Síntese falhou" in str(ex): raise ex
                    
            if not synth_done: raise Exception("Timeout na síntese de áudio.")
            
            res_audio = requests.get(f"http://127.0.0.1:8085/job?id={synth_job_id}&result=1", timeout=120)
            if res_audio.status_code != 200: raise Exception("Erro ao baixar áudio sintetizado.")
            
            audio_bytes = None
            if "multipart/" in res_audio.headers.get("Content-Type", ""):
                import email
                msg = email.message_from_bytes(b"Content-Type: " + res_audio.headers["Content-Type"].encode() + b"\r\n\r\n" + res_audio.content)
                for part in msg.walk():
                    if part.get_content_type().startswith("audio/"):
                        audio_bytes = part.get_payload(decode=True)
                        break
            else: audio_bytes = res_audio.content
            
            if not audio_bytes: raise Exception("Áudio vazio recebido do servidor.")
            
            raw_temp_path = dj.generated_music_dir / f"temp_{idx}_{int(time.time())}.wav"
            with open(raw_temp_path, "wb") as f:
                f.write(audio_bytes)
            generated_files.append((raw_temp_path, current_title))

        # Encerra o servidor e libera 100% de VRAM
        update_status("🧹 [96%] Descarregando motor de áudio e limpando GPU...", "Encerrando processo de síntese...")
        dj.stop_ace_server()
        gc.collect()
        if torch.cuda.is_available(): torch.cuda.empty_cache()
        time.sleep(1)

        # ----------------------------------------------------
        # FASE 3: PROCESSAMENTO, FILTRAGEM & UPSCALE (PÓS)
        # ----------------------------------------------------
        for idx, (raw_temp_path, current_title) in enumerate(generated_files):
            log_prefix = f"[{idx+1}/{batch_count}] " if batch_count > 1 else ""
            clean_title = re.sub(r'[\\/:*?"<>|]', '_', current_title).strip()
            short_ts = str(int(time.time()))[-6:]
            final_filename = f"{clean_title}_{short_ts}.mp3"
            final_output_path = dj.generated_music_dir / final_filename
            
            if enable_mastering:
                # 1. Cirurgia: Filtro passa-baixa em 13kHz para cortar ruídos metálicos
                update_status(f"✂️ {log_prefix}[97%] Removendo ruídos metálicos (Cirurgia)...", f"{log_prefix}Filtro Passa-Baixa (13kHz)...")
                filtered_temp_path = dj.generated_music_dir / f"filtered_{idx}_{int(time.time())}.wav"
                apply_lowpass_filter(raw_temp_path, filtered_temp_path, cutoff_hz=13000)
                
                # 2. Upscale: AudioSR reconstrói as altas frequências a 48kHz de forma cristalina
                temp_upscaled_path = dj.generated_music_dir / f"upscaled_{idx}_{int(time.time())}.wav"
                
                def upscale_progress(block_idx, total_blocks):
                    pct = 97 + int((block_idx / total_blocks) * 2)
                    update_status(
                        f"✨ {log_prefix}[{pct}%] Reconstruindo agudos Hi-Fi com AudioSR (Bloco {block_idx}/{total_blocks})...",
                        f"{log_prefix}AudioSR: Bloco {block_idx} de {total_blocks}..."
                    )
                
                dj.process_upscale(filtered_temp_path, temp_upscaled_path, ddim_steps=upscale_steps, progress_callback=upscale_progress)
                
                # Converter para MP3 final via FFmpeg
                update_status(f"✨ {log_prefix}[99%] Exportando áudio masterizado...", f"Exportando MP3: {final_filename}...")
                ffmpeg_cmd = ["ffmpeg", "-y", "-i", str(temp_upscaled_path), "-c:a", "libmp3lame", "-q:a", "2", str(final_output_path)]
                subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Limpa temporários da cirurgia e upscale
                if filtered_temp_path.exists(): os.remove(filtered_temp_path)
                if temp_upscaled_path.exists(): os.remove(temp_upscaled_path)
            else:
                # Exportar sem masterização
                update_status(f"💿 {log_prefix}[98%] Exportando áudio bruto...", f"Exportando MP3 bruto: {final_filename}...")
                ffmpeg_cmd = ["ffmpeg", "-y", "-i", str(raw_temp_path), "-c:a", "libmp3lame", "-q:a", "2", str(final_output_path)]
                subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
            if raw_temp_path.exists(): os.remove(raw_temp_path)
            
            # Cadastra histórico
            history_file = dj.generated_music_dir / "history.json"
            history = []
            if history_file.exists():
                try:
                    with open(history_file, "r", encoding="utf-8") as f: history = json.load(f)
                except: pass
            history.insert(0, {
                "filename": final_filename,
                "title": current_title if enable_mastering else f"{current_title} (Sem Master)",
                "style": style,
                "mastered": enable_mastering,
                "date": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            with open(history_file, "w", encoding="utf-8") as f: json.dump(history, f, indent=4)
            dj.project_state["last_generated_song"] = final_filename
            
        update_status("✅ [100%] Lote de músicas processado com sucesso!", f"Pronto! Geração concluída com {batch_count} faixas.")

    except Exception as e:
        err_msg = f"❌ ERRO GERAÇÃO: {str(e)}"
        logging.error(err_msg)
        dj.project_state.setdefault("logs", []).append(err_msg)
        dj.project_state["current_task"] = err_msg
        dj.save_status()
        dj.stop_ace_server()
    finally:
        dj.generating_music = False
        dj.worker_busy = False
        dj.save_status()
