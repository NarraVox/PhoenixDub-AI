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
        
    # print(f"🛡️ [NEXUS_ISOLATION] Ambiente blindado e seletivo. Local: {local_site.name}")

except Exception as e:
    print(f"⚠️ [FALHA_ISOLAMENTO] Erro ao limpar caminhos: {e}")

# [v2026.DLL_PANIC_FIX] Força bruta para encontrar a RTX 3050 (OPTIMIZED & SILENT)
try:
    import sys
    import ctypes
    from pathlib import Path
    
    base_env = Path(sys.executable).parent.parent
    site_packages = base_env / "Lib" / "site-packages"
    
    dll_paths = [
        site_packages / "llama_cpp" / "lib",
        site_packages / "nvidia" / "cublas" / "bin",
        site_packages / "nvidia" / "cuda_runtime" / "bin",
        site_packages / "nvidia" / "cuda_nvrtc" / "bin"
    ]
    
    for p in dll_paths:
        if p.exists():
            os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                try: os.add_dll_directory(str(p))
                except: pass
            try: ctypes.windll.kernel32.SetDllDirectoryW(str(p))
            except: pass

    os.environ["LLAMA_CUDA"] = "1"
    os.environ["GGML_CUDA_NO_PINNED"] = "1"

except Exception:
    pass

# --- PATCH DE COMPATIBILIDADE MASTER: WINDOWS SYMLINK BYPASS (v2026.90) ---
# Resolve o WinError 1314 interceptando o Path.symlink_to globalmente.
# Se falhar ao criar link, ele faz uma cópia física.
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import torch
import gc


# --- CÓDIGO EXTRAÍDO ---


# --- CÓDIGO EXTRAÍDO ---

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
