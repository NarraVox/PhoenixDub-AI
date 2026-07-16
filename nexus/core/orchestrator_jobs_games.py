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


def trim_silence_logic(audio, threshold=-35, padding_ms_start=20, padding_ms_end=50):
    """Remove o silêncio nas pontas de um AudioSegment com margem de padding."""
    duration = len(audio)
    if duration < 100: return audio 
    start_trim = 0
    for i in range(0, duration, 10):
        if audio[i:i+10].dBFS > threshold:
            start_trim = max(0, i - padding_ms_start)
            break
    end_trim = duration
    for i in range(duration, 0, -10):
        if audio[i-10:i].dBFS > threshold:
            end_trim = min(duration, i + padding_ms_end)
            break
    if start_trim >= end_trim: return audio
    return audio[start_trim:end_trim]

def processar_dublagem_jogos(job_dir, job_id, start_time):
    with active_jobs_lock:
        if len(active_jobs) >= MAX_CONCURRENT_JOBS:
             logging.warning(f"❌ [HARDWARE] Limite de {MAX_CONCURRENT_JOBS} job(s) atingido. Ignorando {job_id}.")
             return
        active_jobs.add(job_id)
    
    try:
        set_low_process_priority()

        # [v2026.PRE_FLIGHT_PURGE] Faxina preventiva de VRAM no início
        logging.info("🧹 [SISTEMA] Realizando faxina preventiva de VRAM (PRE-FLIGHT)...")
        unload_whisper_model()
        unload_qwen3_model()
        unload_gema_model()
        unload_local_gemma_engine()
        import gc, torch
        gc.collect()
        if torch.cuda.is_available(): torch.cuda.empty_cache()
        
        # [CUMULATIVE TIME] Lê o tempo acumulado de sessões anteriores
        status = safe_json_read(job_dir / "job_status.json") or {}
        accumulated_time = status.get('total_elapsed_secs', 0)
        # Ajusta o cronômetro para iniciar de onde parou (Puro Ouro!)
        virtual_start_time = time.time() - accumulated_time
        
        def cb(p, etapa, s=None, **kwargs): set_progress(job_id, p, etapa, virtual_start_time, ETAPAS_JOGOS, s, **kwargs)
        
        for dir_name in ["_1_MOVER_OS_FICHEIROS_DAQUI", "_2_PARA_AS_PASTAS_DE_VOZ", "_backup_transcricao", "_backup_texto_final", "_dubbed_audio", "_saida_final"]:
            (job_dir / dir_name).mkdir(parents=True, exist_ok=True)
            
        # [v2026.PRE_CALCULATE_DURATION] Pré-calcula a duração total do áudio no início (com Cache-Skip)
        try:
            status_temp = safe_json_read(job_dir / "job_status.json") or {}
            source_dir = job_dir / "_1_MOVER_OS_FICHEIROS_DAQUI"
            wav_files = list(source_dir.rglob("*.wav"))
            if wav_files:
                if 'duracao_total_secs' in status_temp and status_temp.get('duracao_total_secs', 0) > 0:
                    logging.info(f"⏱️ [TITAN PRE-CALC] Duração total carregada do cache: {status_temp.get('duracao_total_formatada')} ({len(wav_files)} arquivos)")
                else:
                    total_duration_secs = sum(get_audio_duration(str(f)) for f in wav_files)
                    horas, resto = divmod(int(total_duration_secs), 3600)
                    minutos, segundos = divmod(resto, 60)
                    
                    status_temp['duracao_total_secs'] = total_duration_secs
                    if horas > 0:
                        status_temp['duracao_total_formatada'] = f"{horas}h {minutos}m {segundos}s"
                    else:
                        status_temp['duracao_total_formatada'] = f"{minutos}m {segundos}s"
                    safe_json_write(status_temp, job_dir / "job_status.json")
                    logging.info(f"⏱️ [TITAN PRE-CALC] Duração total calculada e salva: {status_temp['duracao_total_formatada']} ({len(wav_files)} arquivos)")
        except Exception as e_dur:
            logging.warning(f"Falha ao pré-calcular a duração no início: {e_dur}")
            
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
        skip_lqa_enabled = str(status.get('skip_lqa', 'false')).lower() == 'true'
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
            status = safe_json_read(job_dir / "job_status.json") or {}
            if 'duracao_total_secs' in status and status.get('duracao_total_secs', 0) > 0:
                logging.info(f"Duração total do projeto carregada do cache: {status.get('duracao_total_formatada')} ({len(all_files_to_process)} arquivos)")
            else:
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
                
                cached_text = project_data_map[file_id].get('original_text')
                cached_status = project_data_map[file_id].get('processing_status', '')
                cached_dur = project_data_map[file_id].get('duration', 0)
                # [v2026.FIX_EMPTY_CACHE] Só pula se tiver texto real OU for não-verbal curto (< 0.5s)
                # Texto vazio com duração > 0.5s = falha do Whisper/VAD → precisa re-transcrever!
                ja_transcrito = bool(cached_text and cached_text.strip()) or \
                                 ('Não-Verbal' in cached_status and cached_dur < 0.5)
                if ja_transcrito:
                    if updated_speaker:
                        safe_json_write(project_data_map[file_id], transcription_backup_dir / f"{file_id}.json")
                    skipped_count += 1
                    continue
            
            backup_file = transcription_backup_dir / f"{file_id}.json"
            backup_data = safe_json_read(backup_file)
            
            if backup_data:
                bkp_text = backup_data.get('original_text')
                bkp_status = backup_data.get('processing_status', '')
                bkp_dur = backup_data.get('duration', 0)
                # [v2026.FIX_EMPTY_CACHE] Mesmo critério: só aproveita o backup se tiver texto real
                # ou for explicitamente não-verbal e curto
                bkp_valido = bool(bkp_text and bkp_text.strip()) or \
                             ('Não-Verbal' in bkp_status and bkp_dur < 0.5)
                if bkp_valido:
                    found_in_cache = True
                    project_data_map[file_id] = backup_data
                    if project_data_map[file_id].get('speaker') != current_speaker:
                        project_data_map[file_id]['speaker'] = current_speaker 
                        safe_json_write(project_data_map[file_id], backup_file)
                    skipped_count += 1
                else:
                    # Backup existe mas com texto vazio e duração longa = falha anterior, re-transcreve
                    logging.warning(f"⚠️ [CACHE_RETRY] '{file_id}' tem backup com texto vazio (dur={bkp_dur:.2f}s). Forçando re-transcrição.")
                    files_needing_transcription.append(audio_file)
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

            from nexus.dub import is_reaction_or_noise
            original_text = seg_data.get('original_text', '').strip()
            clean_text = re.sub(r'[^\w\s]', '', original_text).lower()
            words = clean_text.split()
            duracao = seg_data.get('duration', 0)
            # [v2026.FIX_WHISPER_MISS] Texto vazio curto (<3 chars) só é não-verbal se duração < 0.5s
            # Áudios mais longos com texto vazio = Whisper falhou em transcrever fala real!
            texto_vazio_curto = len(original_text.replace(' ', '')) < 3 and duracao < 0.5
            if (words and all(word in SONS_A_IGNORAR for word in words)) or \
               texto_vazio_curto or \
               duracao < 0.1 or \
               is_junk_text(original_text) or \
               is_reaction_or_noise(seg_data):
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

            # [LORE GLOBAL] Dossiê de Lore Global do Jogo
            lore_file = job_dir / "lore_global.json"
            lore_global = ""
            if lore_file.exists():
                lore_data = safe_json_read(lore_file) or {}
                lore_global = lore_data.get("lore", "")
            else:
                cb(2, 3, "[Gemma 4] Analisando Lore Global do Jogo...")
                lore_global = gerar_lore_global(project_data)
                safe_json_write({"lore": lore_global}, lore_file)
                logging.info(f"📜 [TITAN GAMES] Lore Global Gerada: {lore_global[:100]}...")

            if lore_global:
                merged_glossary['lore_global'] = lore_global

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
                    
                    # [v20.17] MODO TURBO: Tradução Direta (Sem Chat Completions lento)
                    # Usamos o gema_batch_processor_v2 para rodar no modo de completions direto com stop tokens,
                    # acelerando o processo para ~3 arquivos por segundo igual no do vídeo.
                    # Executa a tradução de forma thread-safe usando o Lock global do gema
                    from nexus.core.model_loader import gema_lock
                    with gema_lock:
                        results_map = gema_batch_processor_v2(
                            batch=[item_data],
                            cenario_ctx=ctx_str,
                            glossary=merged_glossary,
                            profile_id=game_profile_id,
                            job_dir=job_dir,
                            target_lang=status.get('target_language', 'pt')
                        )
                    
                    res = results_map.get(str(item_data['id']).lower())
                    if res:
                        final_text = res['text']
                        item_data['emotion'] = res.get('emotion', 'NORMAL').upper()
                    else:
                        final_text = item_data.get('original_text', '')
                        item_data['emotion'] = 'NORMAL'
                    
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
                    # Se já tem translated_text preenchido e válido (como do cache individual ou manual),
                    # NÃO devemos sobrescrever!
                    if f.get('translated_text') and f.get('translated_text') != f.get('original_text'):
                        continue
                        
                    trad_val = micro_cache.get(orig) or micro_cache.get(orig.lower())
                    if trad_val:
                        f['translated_text'] = trad_val
                        f['synced_text'] = trad_val
                        f['sanitized_text'] = gema_etapa_3_sanitizacao(trad_val)
                    else:
                        # Se falhou tudo e não tínhamos nada, mantém original
                        if not f.get('translated_text'):
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
        # Inteligência Artificial: Avisa se o LM Studio estiver aberto mas não bloqueia a execução
        import torch
        tem_gpu = torch.cuda.is_available()
        
        if not tem_gpu:
            print("\n" + "!"*70)
            print(" 💻 MODO CPU DETECTADO!")
            print(" ⚠️  AVISO: Se notar lentidão no processamento do TTS, feche o LM Studio para liberar RAM.")
            print("!"*70 + "\n")
            
            import requests
            try:
                res = requests.get("http://127.0.0.1:1234/v1/models", timeout=1)
                if res.status_code == 200:
                    logging.warning("⚠️ LM Studio ativo na porta 1234. Recomendado fechar para liberar recursos de RAM em modo CPU.")
            except:
                pass


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
 
                    # [v2026.REACTION_FILTER] Bypass para áudio original se for apenas uma reação, canto ou barulho
                    from nexus.dub import is_reaction_or_noise
                    text_clean = seg_data.get('original_text', '').strip().lower()
                    is_hallucination = False
                    if text_clean:
                        normal_chars = len([c for c in text_clean if c.isalnum() or c.isspace()])
                        if len(text_clean) > 0 and (normal_chars / len(text_clean)) < 0.3: is_hallucination = True
 
                    is_reaction = any(word in SONS_A_IGNORAR for word in text_clean.split()) and len(text_clean.split()) <= 2
                    
                    if is_hallucination or seg_data.get('detected_language') == 'pt' or is_reaction or is_reaction_or_noise(seg_data):
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
            
            # LQA Desativado Uncondicionalmente
            lqa_status, diagnostics, needs_regen = 'OK', 'Ignorado (LQA Desativado)', False
            
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

            final_duration = 0.0
            final_peak = -99.0
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
                # [v2026.FALLBACK_ORIGINAL] Se falhar a geração ou sumir, usa o original em inglês como salvaguarda
                logging.warning(f"⚠️ [FALLBACK] Áudio dublado NÃO encontrado para '{file_id}' (Deveria estar dublado). Usando áudio original em inglês para evitar silêncio.")

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
                
                # --- CAPTURA DE MÉTRICAS PÓS-PROCESSAMENTO ---
                final_duration = get_audio_duration(str(final_path))
                final_peak = get_audio_peak_dbfs(final_path)
                
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
            # LQA Desativado Uncondicionalmente
            lqa_status, diagnostics, needs_healing = "OK", "Ignorado (LQA Desativado)", False
            
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

        # --- [FALLBACK AUTOMÁTICO PÓS-LQA] ---
        # Se um segmento ficou com AVISO (alucinação, loop, áudio vazio),
        # copia o áudio original diretamente para _saida_final em vez de
        # deixar um arquivo corrompido ou silencioso.
        fallback_dir = job_dir / "_saida_final"
        fallback_diar_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
        fallback_count = 0
        for seg in project_data:
            lqa_status = seg.get('lqa_status', 'OK')
            file_id = seg.get('id', '')
            file_name = seg.get('file_name', f"{file_id}.wav")
            speaker_id = seg.get('speaker', 'Unknown')

            if 'AVISO' not in str(lqa_status) and 'Falha' not in str(lqa_status):
                continue

            # Verifica se o arquivo na saída está com problema (tamanho zero ou muito pequeno)
            final_out = fallback_dir / file_name
            final_size = final_out.stat().st_size if final_out.exists() else 0

            # Original na pasta de diarização (por speaker)
            orig_path = fallback_diar_dir / speaker_id / file_name
            if not orig_path.exists():
                # Tenta encontrar diretamente na raiz do job (áudios limpos)
                orig_path = job_dir / "_1c_AUDIO_SEGMENTADO" / file_name

            if orig_path.exists():
                shutil.copy2(str(orig_path), str(final_out))
                fallback_count += 1
                logging.warning(
                    f"🔄 [FALLBACK_ORIG] '{file_name}' tinha LQA='{lqa_status}' "
                    f"(saída: {final_size}b). Restaurado com áudio original."
                )
                seg['lqa_status'] = f"FALLBACK_ORIGINAL ({lqa_status})"
            else:
                logging.error(
                    f"❌ [FALLBACK_ORIG] Não encontrou original para '{file_name}' "
                    f"em '{orig_path}'. Arquivo problemático permanece na saída."
                )

        if fallback_count > 0:
            logging.info(f"✅ [FALLBACK_ORIG] {fallback_count} arquivo(s) restaurado(s) com o áudio original.")
            safe_json_write(project_data, job_dir / "project_data.json")
        # --- [FIM FALLBACK AUTOMÁTICO] ---

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
