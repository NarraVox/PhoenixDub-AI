# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

# 1. IMPORTAÇÃO DO PATCH DE SEGURANÇA E MONKEYPATCH DO FLASK (SEMPRE EM PRIMEIRO LUGAR)
import nexus.core.security

# 2. IMPORTAÇÃO DOS MÓDULOS REFATORADOS (FACADE)
from nexus.core.utils_sys import *
from nexus.core.utils_audio import *

import os
import sys
import time
import json
import logging
import hashlib
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from pathlib import Path
from flask import Flask, jsonify, request

# Re-export de instâncias globais
gema_lock = threading.RLock()
chatterbox_lock = threading.Lock()
gema_instance = None
gema_tokenizer = None
gema_model = None

whisper_model = None
chatterbox_model = None
model_lock = Lock()
progress_dict, progress_lock = {}, Lock()
active_jobs_lock = Lock()
active_jobs = set()

Chatterbox_executor = ThreadPoolExecutor(max_workers=1)
General_executor = ThreadPoolExecutor(max_workers=2)
MAX_CONCURRENT_JOBS = 1

# Inicialização do Flask protegida (SecuredFlask herdado via monkeypatch)
try:
    from flask_cors import CORS
    HAS_CORS = True
except ImportError:
    HAS_CORS = False

app = Flask(__name__, template_folder='client', static_folder='client')
if HAS_CORS:
    CORS(app)
else:
    print("[AVISO] Rodando sem CORS. Instale com: pip install flask-cors")

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024
app.config['MAX_FORM_PARTS'] = 10000
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- FUNCTIONS ---

def safe_json_write(data, path, indent=4, ensure_ascii=False, retries=5, delay=0.2):
    path = Path(path)
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
                time.sleep(delay)
            else:
                logging.error(f"ERRO CRÍTICO na tentativa final de escrever em {path}: {e}")
        except Exception as e:
            logging.error(f"ERRO CRÍTICO inesperado ao substituir {path} com {temp_path}: {e}")
            break

def safe_json_read(path, retries=5, delay=0.1):
    path = Path(path)
    for attempt in range(retries):
        try:
            if not path.exists(): return None
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
                    except: pass
                return None
        except Exception:
            return None
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

def calculate_files_hash(files):
    hasher = hashlib.sha256()
    sorted_files = sorted(files, key=lambda f: f.filename)
    for f in sorted_files:
        file_info = f"{f.filename}:{f.seek(0, os.SEEK_END)}"
        hasher.update(file_info.encode('utf-8'))
        f.seek(0)
    return hasher.hexdigest()

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

def gerar_relatorio_final(job_dir, job_id, project_data, file_format_map):
    relatorio_path = job_dir / "relatorio_processamento.txt"
    durations_cache_path = job_dir / "durations_cache.json"
    durations_cache = safe_json_read(durations_cache_path) or {}
    
    logging.info(f"Gerando relatório Nexus em: {relatorio_path}")
    
    total_arquivos = len(project_data)
    sucessos_absolutos = 0
    count_regen = sum(1 for s in project_data if "(Corrigido por Regen)" in str(s.get('lqa_raw_details', '')))
    
    alertas = []
    erros = []

    for seg_data in project_data:
        lqa_status = seg_data.get('lqa_status', 'OK')
        if lqa_status == 'OK': sucessos_absolutos += 1
        elif lqa_status in ['AVISO', 'ATENÇÃO']: alertas.append(seg_data)
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
                orig_d = seg.get('duration', 0)
                final_d = durations_cache.get(seg['id'], {}).get('duration', 0)
                if orig_d > 0: f.write(f"    - Tempo:        Original {orig_d:.2f}s | Final {final_d:.2f}s\n")
                if "FALHA_" in str(seg.get('translated_text', '')):
                    f.write(f"    - Tradução:     FALHOU ({seg.get('translated_text', 'N/A')})\n")
                f.write("\n")
        
        f.write("--------------------------------------------------\n")
        f.write("(Arquivos não listados acima foram auditados e aprovados pelo Nexus LQA)\n")
        f.write("==================================================\n")
        f.write(f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")

    relatorio_json_path = job_dir / "relatorio_processamento.json"
    segmentos_json = []
    sucessos_json = 0
    for s in project_data:
        file_id = s['id']
        possible_paths = [
            job_dir / "_dubbed_audio" / f"{file_id}_dubbed.wav",
            job_dir / "_dubbed_segments" / f"{file_id}.wav",
            job_dir / "_dubbed_segments" / f"seg_{file_id}.wav"
        ]
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
    json_data = {
        "job_id": job_id,
        "total_segments": total_arquivos,
        "success_count": sucessos_json,
        "failed_count": len(erros),
        "alert_count": len(alertas),
        "success_rate": round(taxa_acerto, 2),
        "segments": segmentos_json,
        "data_atualizacao": datetime.now().isoformat(),
        "status_geral": "perfeito" if taxa_acerto == 100 else "bom" if taxa_acerto > 80 else "revisar"
    }
    safe_json_write(json_data, relatorio_json_path)

def _print_progress_to_cmd(job_id, progress, etapa, subetapa, tempo_decorrido, current_seg=None, total_seg=None):
    bar_length = 40
    filled_len = int(bar_length * progress / 100)
    bar = '█' * filled_len + '░' * (bar_length - filled_len)
    job_id_display = (job_id[:30] + '..') if len(job_id) > 32 else job_id
    etapa_display = (etapa[:35] + '..') if len(etapa) > 37 else etapa
    subetapa_display = (subetapa[:40] + '..') if subetapa and len(subetapa) > 42 else (subetapa or "")
    seg_display = f"[{current_seg:03d}/{total_seg:03d}]" if current_seg and total_seg else ""
    progress_line = f" Job: {job_id_display} | {bar} {progress:.1f}% {seg_display} | {etapa_display} | {subetapa_display} | Tempo: {tempo_decorrido}"
    
    try:
        sys.stdout.write(f"\r{progress_line.ljust(150)}")
        sys.stdout.flush()
    except UnicodeEncodeError:
        safe_line = progress_line.encode('ascii', 'replace').decode('ascii')
        sys.stdout.write(f"\r{safe_line.ljust(150)}")
        sys.stdout.flush()

_last_progress_info = {}

def set_progress(job_id, progress, etapa_idx, start_time, etapas_list, subetapa=None, tool_name=None, current_seg=None, total_seg=None, **kwargs):
    if current_seg and total_seg:
        os.system(f"title NEXUS AI - {progress:.1f}% [{current_seg}/{total_seg}] - {subetapa or ''}")
    now = time.time()
    last_info = _last_progress_info.get(job_id, {})
    last_time = last_info.get('time', 0)
    last_subetapa = last_info.get('subetapa', "")
    
    force_update = (subetapa != last_subetapa) or (progress >= 100)
    etapa_atual = etapas_list[etapa_idx] if etapa_idx < len(etapas_list) else "Desconhecida"
    elapsed_time = now - start_time
    tempo_str = str(timedelta(seconds=int(elapsed_time)))

    if progress < 100 and (now - last_time < 2) and not force_update:
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
                sdata['tempo_decorrido'] = str(timedelta(seconds=int(elapsed_time)))
                sdata['tool_name'] = tool_name
                
                if 'metrics' not in sdata:
                    sdata['metrics'] = {
                        'stages_duration_secs': {}, 'vram_peak_mb': {}, 'cache_hit_rate': {}, 'stages_start_times': {}
                    }
                elif 'stages_start_times' not in sdata['metrics']:
                    sdata['metrics']['stages_start_times'] = {}
                
                now_ts = time.time()
                old_etapa = sdata.get('etapa')
                
                if etapa_atual not in sdata['metrics']['stages_start_times']:
                    sdata['metrics']['stages_start_times'][etapa_atual] = now_ts
                    if old_etapa and old_etapa != etapa_atual:
                        try:
                            if torch.cuda.is_available():
                                torch.cuda.reset_peak_memory_stats(0)
                        except: pass
                
                start_t = sdata['metrics']['stages_start_times'][etapa_atual]
                sdata['metrics']['stages_duration_secs'][etapa_atual] = round(now_ts - start_t, 2)
                
                if old_etapa and old_etapa != etapa_atual and old_etapa in sdata['metrics']['stages_start_times']:
                    old_start = sdata['metrics']['stages_start_times'][old_etapa]
                    sdata['metrics']['stages_duration_secs'][old_etapa] = round(now_ts - old_start, 2)
                
                try:
                    if torch.cuda.is_available():
                        peak_bytes = torch.cuda.max_memory_allocated(0)
                        peak_mb = int(peak_bytes / (1024 * 1024))
                        sdata['metrics']['vram_peak_mb'][etapa_atual] = peak_mb
                except: pass
                
                if 'translation_cache_hit' in kwargs:
                    sdata['metrics'].setdefault('cache_hit_rate', {})['traducao'] = round(kwargs['translation_cache_hit'], 2)
                if 'audio_cache_hit' in kwargs:
                    sdata['metrics'].setdefault('cache_hit_rate', {})['dublagem_tts'] = round(kwargs['audio_cache_hit'], 2)
                
                safe_json_write(sdata, status_path)
            except: pass
        
        if progress < 100:
            current_time = time.time()
            last_p = getattr(set_progress, "last_p", -1)
            last_t = getattr(set_progress, "last_t", 0)
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
