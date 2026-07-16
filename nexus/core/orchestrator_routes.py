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


from nexus.core.utils import app

@app.route('/separar_audio', methods=['POST'])
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
