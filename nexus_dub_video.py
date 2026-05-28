# -*- coding: utf-8 -*-
# NEXUS DUB VIDEO (v2026.TITAN-CINEMA)
# Motor de Dublagem de Vídeo com Arquitetura de Agentes.

import os
import sys
import time
import subprocess
import logging
import json
import re
import threading
import hashlib
import gc
import shutil
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pydub import AudioSegment, effects

# --- IMPORTAÇÃO DO CÉREBRO (NEXUS CORE) ---
try:
    import nexus_core as core
except ImportError:
    print("[ERRO CRÍTICO] nexus_core.py não encontrado!")
    sys.exit(1)

# --- CONFIGURAÇÕES DE DIRETÓRIO DINÂMICAS (v2026.PORTABLE_REAL) ---
from pathlib import Path
BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_FOLDER = str(BASE_DIR / "uploads")

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/api/health')
def health_check():
    return jsonify({"status": "online", "engine": "Titan Video"})

# --- CONFIGURAÇÕES DE SINCRONIA ---
CPS_TARGET = 16.0      # Caracteres por Segundo (Padrão Confortável e Natural)
MAX_SPEEDUP = 1.20      # Limite de aceleração (20%) para manter a máxima naturalidade
MIN_GAP = 0.1          # Gap mínimo entre frases em segundos

def speedup_audio(audio_segment, speed_factor):
    """Acelera o áudio sem alterar o pitch usando o filtro profissional atempo do FFmpeg (sem cortes)."""
    if speed_factor <= 1.0: return audio_segment
    
    import subprocess
    import tempfile
    import os
    
    try:
        # Cria arquivos temporários seguros na pasta NEXUS_TEMP
        temp_dir = "C:/IA_dublagem/uploads/_NEXUS_TEMP_"
        os.makedirs(temp_dir, exist_ok=True)
        
        fd_in, path_in = tempfile.mkstemp(suffix=".wav", dir=temp_dir)
        fd_out, path_out = tempfile.mkstemp(suffix=".wav", dir=temp_dir)
        os.close(fd_in)
        os.close(fd_out)
        
        # Exporta o áudio original
        audio_segment.export(path_in, format="wav")
        
        # Filtro atempo do FFmpeg (altíssima qualidade, sem perdas de pedaços)
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
        # Fallback seguro caso o FFmpeg falhe
        return effects.speedup(audio_segment, playback_speed=speed_factor, chunk_size=120, crossfade=20)
    except Exception as err:
        logging.error(f"❌ Falha crítica no fallback de aceleração: {err}")
        return audio_segment

def is_reaction_or_noise(seg):
    """
    [v2026.VOICE_SHIELD] Identifica se um segmento é grito, ruído, música ou recusa do LLM.
    Esses áudios devem manter o som original do vídeo e ser ignorados pelo motor de voz.
    """
    texto_bruto = str(seg.get('manual_edit_text') or seg.get('text_pt') or seg.get('original_text', seg.get('text', '')))
    
    # 1. Caracteres CJK (Japonês/Chinês/Coreano) no texto de tradução em português
    if any(ord(char) > 0x3000 for char in texto_bruto):
        return True
        
    # 2. Respostas de recusa ou alucinação/análise explicativa do LLM
    meta_patterns = [
        "texto fornecido", "não é em", "som de", "grito", "gemido", "traduzido", "traduzida", 
        "tradução", "legenda", "o texto", "cannot translate", "not in english", "análise:", "analise:",
        "não pode ser", "não é possível", "erro de digitação", "de digitação", "não é uma frase", 
        "mistura complexa", "caracteres japoneses", "caracteres asiáticos", "reconhecível", "de origem"
    ]
    texto_limpo = texto_bruto.lower()
    if any(pat in texto_limpo for pat in meta_patterns):
        return True
        
    # 3. Grito ou repetição pura de vogal (ex: aaaaaaa, ooooooo, hhhhh)
    only_letters = re.sub(r'[^a-zA-Z]', '', texto_bruto).lower()
    if len(only_letters) > 3 and (
        len(set(only_letters)) <= 2 or 
        "aaa" in only_letters or "ooo" in only_letters or "uuu" in only_letters or "eee" in only_letters or "iii" in only_letters
    ):
        return True
        
    # 4. Palavras de reação normais
    REACTION_WORDS = {
        "yeah", "yes", "ah", "oh", "uh", "hmm", "hm", "wow", "haha", "ha ha", "huh", "hã", "é", "ok", "ops", "oops", "ah!", "oh!", "yeah!",
        "mmm", "mmm.", "mmm...", "mm-hmm", "mm-mm", "uhu", "uh-huh", "uh-oh", "shh", "ts", "tsc"
    }
    palavras = re.sub(r'[^a-zA-Z0-9 ]', '', texto_limpo).strip().split()
    if not palavras or (len(palavras) > 0 and all(p in REACTION_WORDS for p in palavras)):
        return True
        
    # 5. Cantoria / Música
    if seg.get('emotion') == 'CANTORIA':
        return True
        
    return False

def get_best_encoder():
    """Detecta NVIDIA NVENC (RTX) ou Intel QuickSync (i5) para aceleração master."""
    try:
        # 1. Prioridade Máxima: NVIDIA NVENC (Poder total da RTX!)
        cmd_nv = ['ffmpeg', '-f', 'lavfi', '-i', 'color=c=black:s=64x64', '-frames:v', '1', '-c:v', 'h264_nvenc', '-f', 'null', '-']
        if subprocess.run(cmd_nv, capture_output=True, timeout=2).returncode == 0:
            logging.info("🚀 [HARDWARE] NVIDIA NVENC Ativo! Renderização via RTX 3050.")
            return 'h264_nvenc'
        
        # 2. Fallback: Intel QuickSync
        cmd_qsv = ['ffmpeg', '-f', 'lavfi', '-i', 'color=c=black:s=64x64', '-frames:v', '1', '-c:v', 'h264_qsv', '-f', 'null', '-']
        if subprocess.run(cmd_qsv, capture_output=True, timeout=2).returncode == 0:
            return 'h264_qsv'
    except:
        pass
    return 'libx264'

def pipeline_video_master(video_path, job_id, game_profile='padrao', source_lang='auto', target_lang='pt', narrative_mode=False):
    """
    PIPELINE MASTER DE CINEMA (v2026.TITAN-i5_OPTIMIZED)
    Otimizado para i5-6400 (4 Cores) | 16GB RAM | Intel HD 530.
    """
    job_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    start_time = time.time()
    start_clock = datetime.now().strftime("%H:%M:%S")
    
    status_path = job_dir / "job_status.json"
    etapas = ["Extraindo Áudio", "Transcrição/Diarização", "Tradução Agente (Gemma)", "Sincronização", "Geração de Voz (Titan Qwen3)", "Merge Final"]

    def cb(p, etapa_idx, s=None, **kwargs): 
        core.set_progress(job_id, p, etapa_idx, start_time, etapas, s, **kwargs)
        loc_status = core.safe_json_read(status_path) or {
            "job_id": job_id, "video_path": str(video_path), "start_time": start_time, 
            "status": "iniciado", "progress": 0, "message": "Iniciando..."
        }
        loc_status.update({"progress": p, "message": s, "status": etapas[etapa_idx], "start_time": start_time})
        loc_status.update(kwargs)
        core.safe_json_write(loc_status, status_path)

    # [v2026.PRE_FLIGHT_PURGE] Faxina de emergência para garantir RTX limpa no início
    logging.info("🧹 [SISTEMA] Realizando faxina preventiva de VRAM (PRE-FLIGHT)...")
    cb(5, 0, "Limpando VRAM para o novo motor...")
    core.unload_whisper_model()
    core.unload_qwen3_model()
    core.unload_local_gemma_engine()
    import gc, torch
    gc.collect()
    if torch.cuda.is_available(): torch.cuda.empty_cache()

    # [v2026.VRAM_EFFICIENCY] Removido o carregamento precoce do motor de voz.
    # O motor só será carregado sob demanda na etapa de dublagem.
    cb(2, 0, "Preparando motores Titan (Otimizado para i5-6400)...")
    
    
    # [v2026.CPU_ADAPTIVE] Detecta e usa o poder total do processador automaticamente
    import os
    THREADS = str(os.cpu_count() or 4) 
    
    if isinstance(job_dir, dict):
        job_dir = Path(job_dir.get('path', str(UPLOAD_FOLDER / job_id)))
    else:
        job_dir = Path(job_dir)

    status_path = job_dir / "job_status.json"
    existing_status = core.safe_json_read(status_path)
    
    if existing_status and "total_elapsed_secs" in existing_status:
        # [v2026.TELEMETRY_RESUME] Recupera o tempo transcorrido e simula o start_time para acumular perfeitamente
        total_elapsed = float(existing_status["total_elapsed_secs"])
        start_time = time.time() - total_elapsed
        logging.info(f"⏱️ [RESUME] Cronômetro recuperado: Acumulando {int(total_elapsed)} segundos anteriores.")

    # [v2026.PERSISTENCE] Inicializa o arquivo de status na pasta do projeto
    status_initial = {
        "job_id": job_id,
        "video_path": str(video_path),
        "start_time": start_time,
        "status": "iniciado",
        "progress": 0,
        "message": "Preparando motores Titan (Otimizado para i5-6400)..."
    }
    
    core.safe_json_write(status_initial, status_path)

    try:
        profile_data = core.load_game_profile(game_profile)
        audio_cfg = profile_data.get('audio_settings', {})
        ln_filter = audio_cfg.get('loudnorm', 'I=-14:TP=-1.5:LRA=11')

        # 1. PREPARAÇÃO DE ATIVOS
        cb(2, 0, "[SISTEMA] Espelhando vídeo original...")
        ext = os.path.splitext(str(video_path))[1] or ".mp4"
        # [v2026.SAFE_PATH] Garante que o nome do espelho não seja gigante
        video_mirror_name = Path(video_path).name
        if len(video_mirror_name) > 100:
             video_mirror_name = video_mirror_name[:90] + "_" + hashlib.md5(video_mirror_name.encode()).hexdigest()[:4] + Path(video_path).suffix
             
        video_mirror = job_dir / video_mirror_name
        if not video_mirror.exists():
            cb(2, 0, "[SISTEMA] Espelhando vídeo original...")
            shutil.copy2(str(video_path), str(video_mirror))

        # 2. EXTRAÇÃO E SEPARAÇÃO DE ÁUDIO
        vocals_path = job_dir / "vocals.wav"
        instrumental_path = job_dir / "instrumental.wav"
        
        logging.info(f"🔍 [CHECK] Verificando cache em: {vocals_path}")
        
        if vocals_path.exists() and vocals_path.stat().st_size > 10000:
            cb(10, 0, "[Cache] Áudio (Vocais) detectado. Pulando extração.")
            logging.info("✅ [CACHE] Vocais encontrados. Ignorando separação de áudio.")
        else:
            temp_raw_audio = job_dir / "_raw_audio.wav"
            
            # [v2026.SMART_RESUME] Só extrai se o arquivo bruto não existir ou for inválido
            if temp_raw_audio.exists() and temp_raw_audio.stat().st_size > 10000:
                logging.info(f"✅ [CACHE] Áudio bruto encontrado: {temp_raw_audio.name}. Pulando extração FFmpeg.")
                cb(5, 0, "[Cache] Áudio bruto detectado. Pulando extração...")
            else:
                cb(5, 0, f"[FFmpeg] Extraindo áudio (Modo Turbo)...")
                # [v2026.RTX_ULTRA_FAST] 
                # Removemos o 'loudnorm' desta etapa pois ele é extremamente lento.
                # Usamos -map 0:a:0 para ignorar o vídeo e ir direto no áudio.
                # -threads 0 deixa o FFmpeg gerenciar o poder total do processador.
                cmd = [
                    'ffmpeg', '-y', '-hide_banner', '-nostats',
                    '-i', str(video_mirror), 
                    '-vn', '-sn', '-dn', '-map', '0:a:0',
                    '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', 
                    '-f', 'wav', '-threads', '0',
                    str(temp_raw_audio)
                ]
                subprocess.run(cmd, capture_output=True, check=True)
                logging.info("✅ Extração de áudio concluída com sucesso (Modo Turbo).")
            
            cb(0, 0, "[OpenUnmix] Separando Vocais/Fundo...")
            core.separar_vocal_instrumental(temp_raw_audio, job_dir, cb)
            gc.collect()

        # 3. TRANSCRIÇÃO E DIARIZAÇÃO
        project_data_path = job_dir / "project_data.json"
        voice_folders_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ"
        backup_texto_dir = job_dir / "_backup_texto_final"
        backup_texto_dir.mkdir(exist_ok=True)
        
        # [v2026.PRE_FLIGHT_CHECK] Auditoria de Integridade e Preparação RTX
        existing_data = core.safe_json_read(project_data_path)
        voices_missing = True # Assume que falta por segurança até provar o contrário
        
        # [v2026.RTX_SAFETY] Garante que as pastas e referências existam ANTES de abrir o Whisper
        if existing_data and "segments" in existing_data and len(existing_data["segments"]) > 0:
            cb(5, 1, "[Check-up] Verificando integridade dos arquivos...")
            
            # 1. Verifica se as pastas de voz existem e têm conteúdo
            has_voice_dir = voice_folders_dir.exists() and any(voice_folders_dir.iterdir())
            
            if not has_voice_dir:
                logging.info("🔧 [INTEGRIDADE] Pastas de voz não encontradas. Iniciando reparo preventivo...")
                cb(10, 1, "[Reparo] Reconstruindo pastas de voz...")
                core.recriar_pastas_de_voz(job_dir, vocals_path, existing_data["segments"])
            
            # 2. Garante que todas as vozes tenham o arquivo de referência unificada
            cb(15, 1, "[Check-up] Preparando amostras de clonagem...")
            core.prepare_video_speaker_references(job_dir)
            
            # 3. Verifica se os segmentos principais estão íntegros
            try:
                first_spk = existing_data["segments"][0]["speaker"]
                sample_seg = voice_folders_dir / first_spk / "seg_0.wav"
                if not sample_seg.exists():
                    logging.warning(f"⚠️ [INTEGRIDADE] Segmento {sample_seg.name} ausente. Forçando reconstrução...")
                    core.recriar_pastas_de_voz(job_dir, vocals_path, existing_data["segments"])
            except: pass
                
            cb(20, 1, "[Check-up] Sistema íntegro. Pulando Diarização.")
            segments = existing_data["segments"]
            voices_missing = False # SUCESSO: Não precisa de nova diarização
        else:
            logging.info("📝 [NEXUS] Nenhum dado prévio encontrado. Iniciando pipeline do zero.")
            voices_missing = True

        # SÓ entra aqui se REALMENTE não tiver os dados ou os arquivos
        if voices_missing:
            cb(0, 1, "[Diarização/Whisper] Mapeando vozes e roteiro...")
            segments = core.transcrever_e_diarizar(vocals_path, job_dir=job_dir, cb=cb, source_lang=source_lang) 
            core.unload_whisper_model()
            gc.collect()

            # [STRICT CHECK] 
            if not segments:
                raise Exception("❌ ERRO CRÍTICO: A Transcrição falhou!")

            project_data = {"job_id": job_id, "segments": segments, "status": "transcribed"}
            core.safe_json_write(project_data, project_data_path)
            existing_data = project_data

        # 4. TRADUÇÃO AGENTE (GEMMA 4)
        
        # [v2026.SMART_DETECT] Detetive de Tradução: Identifica o que realmente falta
        def get_cache_name(sid):
            # Garante que o ID não tenha o prefixo duplicado
            clean_id = str(sid).replace("seg_seg_", "seg_")
            return f"{clean_id}.json" if clean_id.startswith("seg_") else f"seg_{clean_id}.json"

        pending_segments = [s for s in segments if not (backup_texto_dir / get_cache_name(s['id'])).exists()]
        
        translated_batch = []
        total_planned_tr = len(segments)
        cached_count_tr = total_planned_tr - len(pending_segments)
        translation_cache_hit = (cached_count_tr / total_planned_tr) * 100 if total_planned_tr > 0 else 0

        if not pending_segments:
            # [CACHE_HIT] Tudo completo!
            cb(100, 2, "✅ [Cache] Tradução completa detectada. Pulando motor IA...", translation_cache_hit=100.0)
            logging.info(f"♻️ [SMART_RESUME] Recuperando {len(segments)} traduções do cache...")
            for s in segments:
                cached_seg = core.safe_json_read(backup_texto_dir / get_cache_name(s['id']))
                translated_batch.append(cached_seg or s)
        else:
            # [v2026.FIX] Recupera o que já foi traduzido ANTES de começar o novo lote
            # Isso evita que o arquivo final fique incompleto
            logging.info(f"♻️ [SMART_RESUME] Recuperando {len(segments) - len(pending_segments)} traduções já prontas do cache...")
            for s in segments:
                if s['id'] not in [p['id'] for p in pending_segments]:
                    cached_seg = core.safe_json_read(backup_texto_dir / get_cache_name(s['id']))
                    if cached_seg:
                        translated_batch.append(cached_seg)
            
            # [CACHE_MISS] Faltam traduções! Ativar sensor do LM Studio.
            logging.info(f"📝 [NEXUS] Faltam {len(pending_segments)} traduções. Ativando GEMA_GUARD...")
            cb(0, 2, "[Gemma 4] Preparando tradução...")
            
            import requests
            # [v2026.HARDWARE_OR_FILE_CHECK]
            while True:
                try:
                    if core.get_local_gemma_engine():
                        logging.info("🧠 [NEXUS] Motor Interno Gemma detectado e na Placa! Prosseguindo...")
                        break
                    else:
                        msg_alerta = "⚠️ ERRO: MODELO GGUF NÃO ENCONTRADO EM _MODELS_!"
                        logging.warning(f"🛑 [SISTEMA] {msg_alerta}")
                        cb(40, 2, msg_alerta)
                        time.sleep(4)
                except Exception as e:
                    if "RTX_REJECTED" in str(e) or "NVIDIA" in str(e):
                        msg_erro = "❌ ERRO DE HARDWARE: A RTX 3050 FOI REJEITADA PELO MOTOR!"
                        logging.error(f"🛑 [SISTEMA] {msg_erro}")
                        cb(40, 2, msg_erro)
                    else:
                        logging.error(f"❌ Erro ao despertar motor: {e}")
                    time.sleep(5)

            # [v2026.LORE_CACHE] Persistência da Lore Global em arquivo JSON
            lore_file = job_dir / "lore_global.json"
            if lore_file.exists():
                lore_data = core.safe_json_read(lore_file)
                lore_global = lore_data.get("lore", "")
                logging.info(f"♻️ [V2026.LORE] Lore carregada do cache: {lore_global[:100]}...")
            else:
                # [v2026.PRE_FLIGHT_LORE] Garante que o modelo está carregado antes de gerar a Lore
                import requests
                # [v2026.LOCAL_LORE_CHECK]
                while not core.get_local_gemma_engine():
                    msg_alerta = "⚠️ COLOQUE O MODELO GEMMA GGUF NA PASTA _MODELS_ PARA GERAR A LORE!"
                    logging.warning(f"🛑 [SISTEMA] {msg_alerta}")
                    cb(40, 2, msg_alerta)
                    time.sleep(4)

                cb(40, 2, "[Gemma 4] Analisando Lore Global do Vídeo...")
                lore_global = core.gerar_lore_global(segments)
                core.safe_json_write({"lore": lore_global}, lore_file)
                logging.info(f"📜 [V2026.LORE] Lore Global Gerada: {lore_global[:100]}...")
            
            core.unload_whisper_model()
            core.unload_qwen3_model()
            gc.collect()
            
        # [v2026.ULTRA_BATCH] Processamento em Lote
        batch_size = 1
        consecutive_failures = 0
        
        # [v2026.MOAN_GUARD] Lista de reações que NÃO devem ser traduzidas
        REACTION_WORDS = {
            "mm", "mm.", "mmm", "ah", "ah.", "oh", "oh.", "hum", "hum.", "hm", "hm.", 
            "uh", "uh.", "uhhuh", "mmhmm", "mhm", "mhm.", "hmm", "wow", "haha", "ha ha", "huh", 
            "hã", "é", "ok", "ops", "oops", "ui", "ai", "ai!", "ui!", "ah!", "oh!", 
            "yeah", "yeah!", "ooh", "aah", "woah"
        }

        for b_idx in range(0, len(pending_segments), batch_size):
            logging.info("💓 [ESTOU VIVO] Processando lote de tradução...")
            batch = pending_segments[b_idx : b_idx + batch_size]
            
            # [v2026.MOAN_BYPASS] Se for apenas um gemido/reação, pula a IA
            first_seg = batch[0]
            clean_text = re.sub(r'[^\w\s]', '', first_seg.get('original_text', first_seg.get('text', '')).lower()).strip()
            
            if clean_text in REACTION_WORDS or len(clean_text) <= 1:
                logging.info(f"🍃 [MOAN_BYPASS] Segmento {first_seg['id']} ('{clean_text}') identificado como reação. Preservando original.")
                first_seg['text_pt'] = first_seg.get('original_text', first_seg.get('text', ''))
                first_seg['emotion'] = "NORMAL"
                translated_batch.append(first_seg)
                core.safe_json_write(first_seg, backup_texto_dir / get_cache_name(first_seg['id']))
                continue

            # Contexto baseado no primeiro item do lote
            first_seg = batch[0]
            i_orig = segments.index(first_seg)
            start_ctx = max(0, i_orig - 2)
            end_ctx = min(len(segments), i_orig + 3)
            
            # [v2026.CONTEXT_WITH_MEMORY] Inclui traduções já feitas no contexto para manter o fluxo
            ctx_lines = []
            for s in segments[start_ctx:end_ctx]:
                prefix = '[LOTE] ->' if s['id'] in [b['id'] for b in batch] else '  '
                line = f"{prefix} {s['id']}: \"{s.get('original_text', s.get('text', ''))}\""
                
                # Se já temos a tradução desse vizinho, mostramos para o Gemma seguir o fluxo
                cached_file = backup_texto_dir / f"seg_{s['id']}.json"
                if cached_file.exists() and s['id'] not in [b['id'] for b in batch]:
                    cached_data = core.safe_json_read(cached_file)
                    if cached_data and 'text_pt' in cached_data:
                        line += f" (TRADUZIDO: \"{cached_data['text_pt']}\")"
                
                ctx_lines.append(line)
            
            # [v2026.SMART_CONTEXT] Suprime contexto para frases ultra-curtas para evitar alucinações
            orig_text = batch[0].get('original_text', batch[0].get('text', ''))
            word_count = len(orig_text.split())
            
            if word_count <= 3:
                ctx_str = "[FRASE CURTA - TRADUÇÃO DIRETA OBRIGATÓRIA]"
            else:
                ctx_str = "\n".join(ctx_lines)

            # Progresso visual
            current_count = b_idx + len(batch)
            total_total = len(pending_segments)
            stage_p = (current_count / total_total * 100)
            p_msg = f"[Gemma 4] Frase {current_count}/{total_total}"
            cb(stage_p, 2, p_msg, current_seg=current_count, total_seg=total_total, translation_cache_hit=translation_cache_hit)
            logging.info(f"➔ [{stage_p:.1f}%] {p_msg}")

            # [v2026.PRE_FLIGHT_BATCH] Garante que o modelo continua ativo durante a tradução longa
            import requests
            # [v2026.PRE_FLIGHT_BATCH] Motor local não descarrega sozinho, então apenas segue
            if not core.get_local_gemma_engine():
                 cb(stage_p, 2, "⚠️ MOTOR IA DESCARREGADO! VERIFIQUE O ARQUIVO GGUF.")
                 time.sleep(5)

            try:
                results_map = core.gema_batch_processor_v2(batch, ctx_str, glossary={'lore_global': lore_global}, profile_id=game_profile, job_dir=job_dir, target_lang=target_lang)
                
                batch_failed = True
                for seg in batch:
                    s_id_str = str(seg['id']).lower()
                    res = results_map.get(s_id_str)
                    
                    if res:
                        # Se temos um resultado (mesmo que igual ao original via Vocal Shield), é sucesso!
                        seg['text_pt'] = res['text']
                        seg['emotion'] = res.get('emotion', 'NORMAL')
                        
                        if res['text'] == seg.get('original_text', seg.get('text', '')):
                            logging.info(f"🎭 [SHIELD] Segmento {seg['id']} preservado como original.")

                        batch_failed = False
                        consecutive_failures = 0
                    else:
                        # Fallback se não houver resposta do mapa
                        seg['text_pt'] = seg.get('original_text', seg.get('text', ''))
                        seg['emotion'] = "NORMAL"

                    translated_batch.append(seg)
                    core.safe_json_write(seg, backup_texto_dir / get_cache_name(seg['id']))

                if batch_failed:
                    consecutive_failures += 1
                    logging.warning(f"⚠️ [ALERTA] Lote inteiro falhou ({consecutive_failures}/3)")
                
                if consecutive_failures >= 3:
                    raise Exception("❌ ERRO CRÍTICO: 3 lotes seguidos falharam. Verifique a janela do motor IA.")

            except Exception as e:
                logging.error(f"Erro no processamento do lote: {e}")
                raise e

        core.unload_local_gemma_engine()
        gc.collect()

        # [v2026.SYNC_MASTER] Salva os dados traduzidos no arquivo mestre
        project_data = {"job_id": job_id, "segments": translated_batch, "status": "translated"}
        core.safe_json_write(project_data, job_dir / "project_data.json")
        logging.info(f"✅ [V2026.SYNC] Project Data atualizado com {len(translated_batch)} traduções.")

        # 5. GERAÇÃO DE ÁUDIOS (CHATTERBOX)
        dub_dir = job_dir / "_dubbed_segments"
        dub_dir.mkdir(exist_ok=True)
        
        # [v2026.SMART_VOICE_RESUME] Detetive de Áudio: Verifica se o trabalho pesado já foi feito
        all_voiced = True
        missing_segments = []
        for seg in translated_batch:
            wav_path = dub_dir / f"{seg['id']}.wav"
            texto_bruto = seg.get('manual_edit_text') or seg.get('text_pt') or ""
            
            # Se não tem texto nenhum, não precisa de áudio!
            if not texto_bruto.strip():
                continue

            if not wav_path.exists() or wav_path.stat().st_size < 1000:
                all_voiced = False
                missing_segments.append(seg['id'])
        
        total_voiced_tr = len([s for s in translated_batch if (s.get('manual_edit_text') or s.get('text_pt') or "").strip()])
        missing_count_tr = len(missing_segments)
        voiced_cached_tr = total_voiced_tr - missing_count_tr
        audio_cache_hit = (voiced_cached_tr / total_voiced_tr) * 100 if total_voiced_tr > 0 else 0

        if all_voiced:
            logging.info("♻️ [SMART_RESUME] Todos os áudios dublados encontrados no cache. Pulando Chatterbox!")
            cb(100, 4, "✅ [Cache] Vozes detectadas. Indo para Mixagem Final...", audio_cache_hit=100.0)
        else:
            logging.info(f"🎙️ [NEXUS] Faltam {len(missing_segments)} áudios: {missing_segments}. Iniciando motor de voz...")
            cb(0, 4, "[Chatterbox TTS] Preparando Vozes...", audio_cache_hit=audio_cache_hit)
            
            # [v2026.VRAM_HANDOFF] Só espera liberação de memória se realmente for carregar a IA
            logging.info("🧹 [NEXUS] Limpando VRAM para o Qwen3-TTS...")
            core.unload_local_gemma_engine()
            core.unload_whisper_model()
            core.unload_qwen3_model()
            import gc, torch
            gc.collect()
            if torch.cuda.is_available(): torch.cuda.empty_cache()
            
            core.wait_for_vram_release(threshold_mb=4000, cb=cb)
            
            # [v2026.SUPER_REFERENCE_BUILDER] Engenharia de Som Automática
            speaker_refs = {}
            for seg in translated_batch:
                spk = seg.get('speaker', 'voz1')
                if spk not in speaker_refs:
                    spk_dir = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ" / spk
                    ref_path = spk_dir / "_ref_titan_22k.wav"
                    txt_path = ref_path.with_suffix('.txt')
                    
                    # [v2026.QUALITY_CHECK] Se a ref já existe mas é curta demais, reconstrói
                    is_bad_ref = False
                    if ref_path.exists():
                        try:
                            dur = core.get_audio_duration(str(ref_path))
                            if dur < 5.0 or not txt_path.exists(): is_bad_ref = True
                        except: is_bad_ref = True

                    if not ref_path.exists() or is_bad_ref:
                        logging.info(f"🎙️ [SUPER_REF] Construindo identidade vocal robusta para {spk}...")
                        samples = list(spk_dir.glob("*.wav"))
                        # Ignora a própria ref se ela for a culpada
                        samples = [s for s in samples if "_ref_" not in s.name]
                        
                        if not samples:
                            logging.warning(f"⚠️ Sem amostras para {spk}. Usando fallback do projeto...")
                            continue
                        
                        # [v2026.ICL_SUPPORT] Mapeia os textos originais usando o JSON
                        seg_texts = {str(s['id']): (s.get('original_text') or s.get('text') or "") for s in translated_batch}
                        
                        master_audio = AudioSegment.empty()
                        master_text = ""
                        for smp in samples:
                            try:
                                audio = AudioSegment.from_wav(str(smp))
                                if len(audio) > 500: # Ignora ruídos menores que 0.5s
                                    # Adiciona a frase + 300ms de silêncio para não embolar
                                    master_audio += audio + AudioSegment.silent(duration=300)
                                    
                                    # [v2026.ICL_SUPPORT] Concatena o texto do segmento correspondente
                                    smp_text = seg_texts.get(smp.stem, "").strip()
                                    if smp_text:
                                        master_text += smp_text + " "
                                        
                                    if len(master_audio) >= 12000: break # Alvo: 12-15 segundos
                            except: pass
                        
                        if len(master_audio) > 1000:
                            # [v2026.STUDIO_QUALITY] 22050Hz Mono + Normalização
                            master_audio = master_audio.set_frame_rate(22050).set_channels(1).normalize()
                            master_audio = master_audio[:15000] # Garante limite de 15s para estabilidade VRAM
                            master_audio.export(str(ref_path), format="wav")
                            
                            # [v2026.ICL_SUPPORT] Salva a "Cola" para o Qwen3 ler
                            if master_text.strip():
                                txt_path.write_text(master_text.strip(), encoding='utf-8')
                        else:
                            logging.error(f"❌ Falha ao criar super-ref para {spk}. Amostras insuficientes.")
                    
                    speaker_refs[spk] = str(ref_path)

            # Inicia o Qwen3 apenas se necessário
            # [v2026.REACTION_FILTER] Sons humanos que soam melhor com o áudio original do que com dublagem IA (Gemidos, suspiros, reações)
            REACTION_WORDS = {
                "yeah", "yes", "ah", "oh", "uh", "hmm", "hm", "wow", "haha", "ha ha", "huh", "hã", "é", "ok", "ops", "oops", "ah!", "oh!", "yeah!",
                "mmm", "mmm.", "mmm...", "mm-hmm", "mm-mm", "uhu", "uh-huh", "uh-oh", "shh", "ts", "tsc"
            }
            
            # [v2026.DUAL_IGNITION] Sistema de Dublagem Paralela de 2 Canais
            # Maximiza o uso da RTX 3050 ao processar 2 frases simultaneamente via Titan Engine.
            from concurrent.futures import ThreadPoolExecutor
            import threading
            
            progress_lock = threading.Lock()
            current_done_count = [0] # Usamos lista para ser mutável dentro da função
            total_tasks = len(translated_batch)

            # [v2026.RTX_LIGHTNING_ENGINE] Dublagem de Alta Performance (Modo Relâmpago)
            # Processa uma frase por vez para garantir sincronia, mas usa CUDA Graphs + DNA Cache.
            logging.info(f"🚀 [RTX] Iniciando Dublagem Relâmpago para {total_tasks} segmentos.")
            # [v2026.HALLUCINATION_BREAKER] Detecta se o Whisper alucinou a mesma palavra consecutivamente
            consecutive_texts = []
            for i, s in enumerate(translated_batch):
                t_bruto = s.get('manual_edit_text') or s.get('text_pt') or s.get('original_text', '')
                t_limpo = re.sub(r'[^a-zA-Z0-9 ]', '', t_bruto.lower()).strip()
                
                if len(consecutive_texts) > 0 and t_limpo == consecutive_texts[-1]['text']:
                    consecutive_texts.append({'idx': i, 'text': t_limpo})
                else:
                    consecutive_texts = [{'idx': i, 'text': t_limpo}]
                
                # Se repetiu 4 vezes ou mais, marca TODAS como CANTORIA para não dublar a música de fundo
                if len(consecutive_texts) >= 4:
                    for item in consecutive_texts:
                        translated_batch[item['idx']]['emotion'] = 'CANTORIA'
            
            def worker_dublagem(task_data):
                idx, seg = task_data
                out_path = dub_dir / f"{seg['id']}.wav"
                
                # Se já existe e é válido, pula (Cache Inteligente v2026)
                if out_path.exists() and out_path.stat().st_size > 1000:
                    with progress_lock: current_done_count[0] += 1
                    return

                # [v2026.VOICE_SHIELD] Filtro unificado contra reações, ruídos, cantoria e alucinações do LLM
                if is_reaction_or_noise(seg):
                    with progress_lock: current_done_count[0] += 1
                    return

                texto_bruto = seg.get('manual_edit_text') or seg.get('text_pt') or seg.get('original_text', '')
                texto_final = re.sub(r'[^a-zA-Z0-9 áéíóúâêîôûãõàèìòùçÁÉÍÓÚÂÊÎÔÛÃÕÀÈÌÒÙÇ.,!?]', '', texto_bruto).strip()
                
                # [v2026.DYNAMIC_ZERO_SHOT] Híbrido: Emoção Específica vs Identidade Segura
                speaker_id = seg.get('speaker', 'voz1')
                dur_original = seg['end'] - seg['start']
                
                # Base Segura: Super Ref do projeto
                ref_wav = speaker_refs.get(speaker_id)
                
                # Se a frase tem 4s ou mais, usamos o áudio ORIGINAL da cena para capturar a emoção pura!
                if dur_original >= 4.0:
                    specific_wav = job_dir / "_2_PARA_AS_PASTAS_DE_VOZ" / speaker_id / f"{seg['id']}.wav"
                    if specific_wav.exists() and specific_wav.stat().st_size > 1000:
                        ref_wav = str(specific_wav)

                if not ref_wav: 
                    with progress_lock: current_done_count[0] += 1
                    return
                
                emotion_tag = seg.get('emotion', 'NORMAL')

                try:
                    # [v2026.RTX_IGNITION] Chama o motor Faster com Emoção Injetada e Blindagem de Duração
                    resultado = core.gerar_audio_qwen3(texto_final, ref_wav, str(out_path), emotion=emotion_tag, max_duration=dur_original)
                    
                    if resultado and out_path.exists():
                        audio_gerado = AudioSegment.from_wav(str(out_path))
                        dur_original = seg['end'] - seg['start']
                        dur_gerado = len(audio_gerado) / 1000.0
                        
                        if dur_gerado > dur_original and dur_original > 0:
                            pass # O speedup agora é feito SOMENTE na fase de mixagem para evitar perda de sincronia.
                        
                        audio_gerado.export(str(out_path), format="wav")
                except Exception as err:
                    import traceback
                    logging.error(f"❌ Erro crítico no worker_dublagem para o segmento {seg['id']}: {err}\n{traceback.format_exc()}")

                # Atualiza telemetria
                with progress_lock:
                    current_done_count[0] += 1
                    prog = (current_done_count[0] / total_tasks * 100)
                    cb(prog, 4, f"[Modo Relâmpago] Dublando {current_done_count[0]}/{total_tasks}...", current_seg=current_done_count[0], total_seg=total_tasks, audio_cache_hit=audio_cache_hit)
                    
                    # [v2026.VRAM_SWEEPER] Previne o Spillover da GPU para a RAM limpando o lixo do PyTorch
                    if current_done_count[0] % 10 == 0:
                        import torch, gc
                        
                        # Captura telemetria antes de limpar
                        try:
                            import psutil
                            ram_gb = psutil.Process().memory_info().rss / (1024**3)
                            if torch.cuda.is_available():
                                f_m, t_m = torch.cuda.mem_get_info()
                                vram_gb = (t_m - f_m) / (1024**3)
                                total_vram = t_m / (1024**3)
                                logging.info(f"📊 [TELEMETRIA] GPU VRAM: {vram_gb:.1f}GB / {total_vram:.1f}GB | System RAM: {ram_gb:.1f}GB")
                        except: pass
                        
                        gc.collect()
                        if torch.cuda.is_available(): torch.cuda.empty_cache()

            # Executa com ThreadPool de 1 para evitar conflitos de VRAM, mas o motor interno é veloz!
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.map(worker_dublagem, enumerate(translated_batch))

            # Gera o mapa de arquivos para o relatório
            file_format_map = {s['id']: ".wav" for s in translated_batch}
            
            core.unload_qwen3_model()
            gc.collect()
            
            # Atualiza relatório após geração de vozes
            core.gerar_relatorio_final(job_dir, job_id, translated_batch, file_format_map)

            # [v2026.SAFETY_GATE] Bloqueia a masterização se houver falhas críticas (Min 90% de sucesso)
            # Isso impede que o vídeo seja finalizado com partes mudas ou incompletas.
            # O cálculo agora considera Dublagens + Reações Originais como SUCESSO.
            dubbed_files_count = len(list((job_dir / "_dubbed_segments").glob("*.wav")))
            
            reaction_count = 0
            for s in translated_batch:
                # [v2026.VOICE_SHIELD] Usa a mesma lógica unificada para validar reações/skips
                if is_reaction_or_noise(s):
                    reaction_count += 1
            
            total_success = dubbed_files_count + reaction_count
            total_planned = len(translated_batch)
            success_rate = (total_success / total_planned) * 100 if total_planned > 0 else 0
            
            if success_rate < 90:
                logging.error(f"🛑 [SAFETY GATE] Masterização ABORTADA! Sucesso: {success_rate:.1f}%.")
                logging.error(f"👉 DICA: Gerados: {dubbed_files_count} | Reações: {reaction_count} | Total: {total_planned}")
                cb(95, 4, f"❌ ERRO DE INTEGRIDADE: {success_rate:.1f}% de sucesso. Masterização bloqueada.")
                raise Exception(f"Qualidade Insuficiente ({success_rate:.1f}%). A masterização final foi bloqueada.")

        # 6. MERGE FINAL (TITAN DUCKING ENGINE v2026)
        full_dur = core.get_audio_duration(str(vocals_path))
        cb(95, 5, "[Titan Ducking] Mixagem Cinematográfica...")
        
        # [v2026.DEBUG_MODE] Pasta para áudios limpos
        clean_dub_dir = job_dir / "dubbed_audio_clean"
        clean_dub_dir.mkdir(exist_ok=True)
        
        # Carrega trilhas base
        orig_vocals = AudioSegment.from_wav(str(job_dir / "vocals.wav"))
        
        # Função interna de limpeza
        # [v2026.SNAPPY_SYNC] Função de Trim de Silêncio de Alta Precisão (Sincronismo Ultra-Rápido)
        def trim_silence_logic(audio, threshold=-50, padding_ms_start=25, padding_ms_end=50):
            duration = len(audio)
            if duration < 100: return audio 
            
            start_trim = 0
            # Busca o início exato da fala (Ataque Rápido)
            for i in range(0, duration, 10):
                if audio[i:i+10].dBFS > threshold:
                    start_trim = max(0, i - padding_ms_start)
                    break
            
            end_trim = duration
            # Busca o final da fala (Respiro Suave)
            for i in range(duration, 0, -10):
                if audio[i-10:i].dBFS > threshold:
                    end_trim = min(duration, i + padding_ms_end)
                    break
                    
            if start_trim >= end_trim: return audio
            return audio[start_trim:end_trim]

        if instrumental_path.exists():
            orig_instrum = AudioSegment.from_wav(str(instrumental_path))
        else:
            orig_instrum = AudioSegment.silent(duration=len(orig_vocals))

        # Cria a trilha de vozes dubladas (PT-BR)
        pt_vocals = AudioSegment.silent(duration=len(orig_vocals))
        
        dub_windows = []
        segments_found = 0
        
        # --- MIXAGEM DE PRECISÃO (v2026.STRICT_ALIGNMENT) ---
        # Garante a ordem cronológica para evitar conflitos de sobreposição
        translated_batch = sorted(translated_batch, key=lambda x: x['start'])
        
        # Rastreia o fim da última fala de cada orador individualmente
        speaker_last_end_ms = {}
        for i, seg in enumerate(translated_batch):
            seg_id = seg['id']
            raw_wav = dub_dir / f"{seg_id}.wav"
            clean_wav = clean_dub_dir / f"{seg_id}.wav"
            
            if not raw_wav.exists() or raw_wav.stat().st_size < 1000:
                logging.warning(f"⚠️ Segmento {seg_id} ignorado na mixagem (Áudio não encontrado). Recuperando original...")
                try:
                    start_ms = int(seg['start'] * 1000)
                    end_ms = int(seg['end'] * 1000)
                    start_ms = max(0, start_ms)
                    end_ms = min(len(orig_vocals), end_ms)
                    if end_ms > start_ms:
                        orig_chunk = orig_vocals[start_ms:end_ms]
                        fade_ms = min(100, len(orig_chunk) // 2)
                        if fade_ms > 0:
                            orig_chunk = orig_chunk.fade_in(fade_ms).fade_out(fade_ms)
                        pt_vocals = pt_vocals.overlay(orig_chunk, position=start_ms)
                        dub_windows.append((start_ms, end_ms))
                except Exception as rec_err:
                    logging.warning(f"⚠️ Erro ao recuperar áudio original para o segmento {seg_id}: {rec_err}")
                continue
            
            try:
                # Se não existe a versão limpa, gera agora
                if not clean_wav.exists():
                    raw_seg = AudioSegment.from_wav(str(raw_wav))
                    clean_seg = trim_silence_logic(raw_seg)
                    # [v2026.AUDIO_NORM] Normaliza o segmento individual para garantir volumes uniformes
                    clean_seg = effects.normalize(clean_seg)
                    clean_seg.export(str(clean_wav), format="wav")
                
                dub_seg = AudioSegment.from_wav(str(clean_wav))
                # [v2026.AUDIO_NORM] Garante normalização mesmo se o arquivo foi carregado do cache
                dub_seg = effects.normalize(dub_seg)
                
                # 1. Cálculo de "Vaga" (Espaço disponível até o próximo áudio)
                start_ms = int(seg['start'] * 1000)
                
                # Proteção contra sobreposição do mesmo orador (evita gagueira da mesma voz)
                spk = seg.get('speaker', 'default_speaker')
                spk_last_end = speaker_last_end_ms.get(spk, 0)
                if start_ms < spk_last_end:
                    start_ms = spk_last_end
                
                # Busca limites e calcula espaço disponível
                next_same_spk_start_ms = len(orig_vocals)
                for next_seg in translated_batch[i+1:]:
                    if next_seg.get('speaker') == spk:
                        next_same_spk_start_ms = int(next_seg['start'] * 1000)
                        break
                        
                next_any_start_ms = len(orig_vocals)
                if i + 1 < len(translated_batch):
                    next_any_start_ms = int(translated_batch[i+1]['start'] * 1000)
                
                available_space_ms = next_same_spk_start_ms - start_ms
                
                # --- DIRETOR DE DIÁLOGO INTELIGENTE (v2026.DIALOGUE_DIRECTOR) ---
                # Decide dinamicamente entre sobreposição (overlap) ou corte abrupto
                overlap_allowance_ms = 150  # Margem padrão de segurança
                next_seg_exists = (i + 1 < len(translated_batch))
                
                if next_seg_exists and spk != translated_batch[i+1].get('speaker'):
                    emo_current = seg.get('emotion', 'NORMAL')
                    emo_next = translated_batch[i+1].get('emotion', 'NORMAL')
                    orig_gap_ms = int((translated_batch[i+1]['start'] - seg['end']) * 1000)
                    
                    is_tense = any(e in ['RAIVA', 'URGENTE', 'DRAMATICO'] for e in [emo_current, emo_next])
                    
                    if is_tense:
                        if orig_gap_ms < 0:
                            # Sobreposição original em discussão: mantém a conversa atropelada
                            overlap_allowance_ms = 600
                        elif orig_gap_ms < 150:
                            # Resposta imediata em discussão: permite overlap moderado
                            overlap_allowance_ms = 400
                        else:
                            # B corta A abruptamente na cena: corta a cauda de A
                            overlap_allowance_ms = 50
                    else:
                        # Diálogo calmo: overlap sutil de respiro
                        if orig_gap_ms < 0:
                            overlap_allowance_ms = 300
                        else:
                            overlap_allowance_ms = 150
                    # Garante que, se eles já sobrepunham no original (detectado via Pyannote), permitimos pelo menos essa quantidade de sobreposição
                    if orig_gap_ms < 0:
                        overlap_allowance_ms = max(overlap_allowance_ms, -orig_gap_ms)
                            
                    max_space = (next_any_start_ms - start_ms) + overlap_allowance_ms
                    available_space_ms = min(available_space_ms, max_space)
                else:
                    available_space_ms = min(available_space_ms, next_any_start_ms - start_ms)
                
                # 2. Sincronia Inteligente (Com aproveitamento dinâmico de silêncios)
                orig_dur_ms = (seg['end'] - seg['start']) * 1000
                
                # [v2026.GAP_HARVESTING] Aproveita até 500ms do silêncio entre frases antes de acelerar!
                # Isso impede que falas sejam desnecessariamente aceleradas ou cortadas quando há espaço livre.
                target_dur_ms = min(orig_dur_ms + 500, available_space_ms)
                
                # Só acelera se o áudio for mais longo que o nosso alvo expandido
                diff_ms = len(dub_seg) - target_dur_ms
                if diff_ms > 50:
                    speed_factor = len(dub_seg) / (target_dur_ms or 1)
                    dub_seg = speedup_audio(dub_seg, min(MAX_SPEEDUP, speed_factor))
                
                # 3. Corte de Segurança Final (Anti-Atropelamento Estrito)
                if len(dub_seg) > available_space_ms:
                    # Aplica fade out de 50ms e corta para não invadir o próximo áudio
                    f_out = min(50, len(dub_seg))
                    dub_seg = dub_seg[:available_space_ms]
                    if f_out > 0 and len(dub_seg) > 0:
                        dub_seg = dub_seg.fade_out(f_out)
                
                segments_found += 1
                
                # [v2026.FADE] Apenas Fade Out suave. Fade In estava engolindo a primeira sóaba e causando sensação de atraso!
                f_time_out = min(100, len(dub_seg) // 4)
                if f_time_out > 0:
                    dub_seg = dub_seg.fade_out(f_time_out)
                
                # [v2026.TELEMETRY] Progresso na Mixagem
                prog_mix = 95 + (segments_found / len(translated_batch) * 4)
                cb(prog_mix, 5, f"[Mixer] Integrando {seg_id}...", current_seg=segments_found, total_seg=len(translated_batch))
                
                pt_vocals = pt_vocals.overlay(dub_seg, position=start_ms)
                speaker_last_end_ms[spk] = start_ms + len(dub_seg)
                dub_windows.append((start_ms, start_ms + len(dub_seg)))
                
                logging.info(f"✅ [MIX] Integrado: {seg_id} ({len(dub_seg)}ms) em {start_ms}ms | Limite: {available_space_ms}ms")
            except Exception as mix_err:
                logging.error(f"❌ Erro ao mixar segmento {seg_id}: {mix_err}")

        # --- PROCESSAMENTO TITAN DUCKING ---
        dub_windows.sort()
        
        # [v2026.SMART_RECOVERY] Aplica o Ducking e recupera voz original em gaps > 1s
        FADE_MS = 1000 # 1 Segundo de transição
        
        for start_ms, end_ms in dub_windows:
            # Abaixa o volume do original na janela da dublagem (com fade)
            # Volume -20dB no original e -12dB no instrumental durante a fala
            duck_orig = AudioSegment.silent(duration=(end_ms - start_ms) + (FADE_MS * 2))
            
            # Corta o original onde tem a dublagem (com margem de segurança)
            # O pydub não tem envelope complexo fácil, então usamos overlay de silêncio ou redução
            pass

        # Simplificação robusta para i5: 
        # Criamos uma trilha de 'Original Vocals' que só existe onde NÃO tem dublagem
        vocal_mask = AudioSegment.silent(duration=len(orig_vocals))
        
        last_end = 0
        for start_ms, end_ms in dub_windows:
            # Se o gap for > 500ms (Regra dos 500ms do usuário), recuperamos a voz original
            if start_ms - last_end > 500:
                # Pega o pedaço original e aplica fade in/out
                gap_start = last_end + 100 # Margem reduzida para maior fidelidade
                gap_end = start_ms - 100
                fade_len = min(200, (gap_end - gap_start) // 2)
                if gap_end > gap_start and fade_len > 0:
                    chunk = orig_vocals[gap_start:gap_end].fade_in(fade_len).fade_out(fade_len)
                    vocal_mask = vocal_mask.overlay(chunk, position=gap_start)
            last_end = end_ms

        # Recupera no final do vídeo também
        if len(orig_vocals) - last_end > 500:
            gap_start = last_end + 100
            gap_end = len(orig_vocals) - 100
            fade_len = min(200, (gap_end - gap_start) // 2)
            if gap_end > gap_start and fade_len > 0:
                chunk = orig_vocals[gap_start:gap_end].fade_in(fade_len).fade_out(fade_len)
                vocal_mask = vocal_mask.overlay(chunk, position=gap_start)

        # [v2026.REACTION_FILTER] Lista de reações que soam melhor no original
        REACTION_WORDS = {"yeah", "yes", "ah", "oh", "uh", "hmm", "wow", "haha", "huh", "hã", "é", "ok", "ops", "oops"}
        
        # --- PROCESSAMENTO TITAN DUCKING ---
        final_vocals_path = job_dir / "dubbed_vocals_master.wav"
        
        # [v2026.HIGH_FIDELITY] O áudio original recuperado agora fica em volume total (0dB)
        # Isso garante que reações não dubladas soem perfeitas e naturais.
        final_dub_mix = pt_vocals.overlay(vocal_mask) 
        # [v2026.AUDIO_NORM] Normalização final de picos para nivelar dublagem e vozes originais perfeitamente
        final_dub_mix = effects.normalize(final_dub_mix)
        final_dub_mix.export(str(final_vocals_path), format="wav")
        
        logging.info(f"📊 [MIX] Master: {segments_found} segmentos PT-BR integrados.")
        logging.info(f"📊 [MIX] Recuperação Original: Volume 100% (High-Fidelity Mode)")

        # Mixagem Instrumental com Ducking Simples (Abaixa o fundo 7dB onde tem voz)
        output_video = job_dir / "video_dublado.mp4"
        encoder = get_best_encoder()
        
        if instrumental_path.exists():
            # [v2026.FIXED_MIX_RTX] Mixagem Híbrida: Vídeo na RTX + Áudio na CPU (Estável)
            # - highpass=f=80 remove o ruído/hum de fundo da voz de baixa frequência.
            # - volume=1.4 amplifica a voz dublada (+3dB) para que fique bem à frente do fundo.
            # - sidechaincompress ajustado com threshold sensível (0.02), ataque rápido (15ms) e release suave (500ms).
            filter_str = "[1:a]aresample=44100,highpass=f=80,volume=1.4,asplit=2[v_pt1][v_pt2]; [2:a]aresample=44100[v_bg]; "
            filter_str += "[v_bg][v_pt1]sidechaincompress=threshold=0.02:ratio=5:attack=15:release=500[v_ducked]; "
            filter_str += "[v_ducked][v_pt2]amix=inputs=2:duration=longest[v_mixed]"
            
            # Removemos -hwaccel_output_format cuda para compatibilidade com amix/sidechain
            # [v2026.NVDEC_DECODE] Usa NVDEC (via flag 'cuda') para decodificar o vídeo na RTX
            cmd = ['ffmpeg', '-y', '-hwaccel', 'cuda', '-i', str(video_mirror), '-i', str(final_vocals_path), '-i', str(instrumental_path)]
            cmd.extend(['-filter_complex', filter_str, '-map', '0:v', '-map', '[v_mixed]'])
        else:
            logging.warning("⚠️ [MIX] Instrumental não encontrado. Usando apenas vozes.")
            cmd = ['ffmpeg', '-y', '-hwaccel', 'cuda', '-i', str(video_mirror), '-i', str(final_vocals_path)]
            cmd.extend(['-map', '0:v', '-map', '1:a'])
        
        # Tenta QSV, se der erro o fallback cuidará
        # [v2026.RTX_DUB_MASTER_V3] Qualidade Premium Full HD + Leveza
        v_codec = encoder
        
        # Como não estamos modificando o vídeo (apenas o áudio), podemos simplesmente copiar o stream de vídeo,
        # o que faz a masterização ser concluída em segundos em vez de minutos.
        cmd.extend(['-c:v', 'copy'])

        cmd.extend(['-avoid_negative_ts', 'make_zero', '-map_metadata', '-1', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '128k', str(output_video), '-progress', 'pipe:1'])
        
        logging.info(f"🚀 [FFmpeg] Executando: {' '.join(cmd)}")
        
        try:
            # Tenta a primeira vez (geralmente com QSV)
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding='utf-8', errors='replace')
            last_lines = []
            for line in process.stdout:
                last_lines.append(line.strip())
                if len(last_lines) > 20: last_lines.pop(0) # Mantém apenas o histórico recente
                
                if "out_time_ms=" in line:
                    try:
                        time_us = int(line.split('=')[1])
                        time_sec = time_us / 1000000.0
                        pct_stage = min(100, (time_sec / (full_dur or 1)) * 100)
                        label_enc = "NVIDIA RTX" if v_codec == 'h264_nvenc' else "Intel CPU"
                        cb(pct_stage, 5, f"[{label_enc}] Masterizando Vídeo... {int(pct_stage)}%")
                    except: pass
                elif "Error" in line or "warning" in line.lower():
                    logging.warning(f"⚠️ [FFmpeg] {line.strip()}")

            process.wait()
            if process.returncode != 0:
                error_msg = "\n".join(last_lines)
                raise Exception(f"Erro FFmpeg (QSV): {process.returncode}\nSaída:\n{error_msg}")
                
        except Exception as e:
            logging.warning(f"⚠️ [FALLBACK] Erro no QuickSync ou comando inicial. Tentando CPU...\nDetalhes: {e}")
            # Remove o QSV e tenta libx264
            cmd_safe = [c if c != v_codec else 'libx264' for c in cmd]
            if 'balanced' in cmd_safe: cmd_safe[cmd_safe.index('balanced')] = 'ultrafast'
            if 'veryfast' in cmd_safe: cmd_safe[cmd_safe.index('veryfast')] = 'ultrafast'
            
            logging.info(f"🚀 [FFmpeg-CPU] Executando Fallback: {' '.join(cmd_safe)}")
            process = subprocess.Popen(cmd_safe, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding='utf-8', errors='replace')
            last_lines_cpu = []
            for line in process.stdout:
                last_lines_cpu.append(line.strip())
                if len(last_lines_cpu) > 20: last_lines_cpu.pop(0)

                if "out_time_ms=" in line:
                    try:
                        time_us = int(line.split('=')[1])
                        time_sec = time_us / 1000000.0
                        pct_stage = min(100, (time_sec / (full_dur or 1)) * 100)
                        cb(pct_stage, 5, f"[CPU_FALLBACK] Masterizando Vídeo... {int(pct_stage)}%")
                    except: pass
            process.wait()
            if process.returncode != 0:
                error_msg_cpu = "\n".join(last_lines_cpu)
                raise Exception(f"Erro FFmpeg (CPU): {process.returncode}\nSaída:\n{error_msg_cpu}")
        
        # --- RELATÓRIO DE QUALIDADE NEXUS (v2026.QUALITY) ---
        file_format_map = {s['id']: ".wav" for s in translated_batch}
        core.gerar_relatorio_final(job_dir, job_id, translated_batch, file_format_map)
        
        # Recupera dados do JSON recém gerado para o log final
        quality_rpt = core.safe_json_read(job_dir / "relatorio_processamento.json")
        if quality_rpt:
            taxa_acerto = quality_rpt.get("success_rate", 0)
            acertos = quality_rpt.get("success_count", 0)
            total_segs = quality_rpt.get("total_segments", 0)
            
            logging.info("\n" + "="*50)
            logging.info("📊 RELATÓRIO DE INTEGRIDADE (v2026.QUALITY)")
            logging.info(f"🔹 Total Planejado: {total_segs} segmentos")
            logging.info(f"✅ Sucesso Real: {acertos} segmentos")
            logging.info(f"📈 Taxa Final: {taxa_acerto:.1f}% de acerto")
            logging.info("="*50 + "\n")

            cb(100, 5, f"Concluído! {acertos}/{total_segs} dublados ({taxa_acerto:.1f}%)")
        
        return str(output_video)

    except Exception as e:
        logging.error(f"Erro na pipeline: {e}")
        traceback.print_exc()
        return None

@app.route('/api/dublar_video', methods=['POST'])
def api_dublar_video():
    data = request.get_json()
    video_path = data.get('path')
    # [v2026.STABLE_ID] Gera ID baseado no nome do arquivo para aproveitar o cache
    # [v2026.SAFE_PATH] Limpa e trunca o nome para evitar WinError 3 (MAX_PATH)
    video_name = Path(video_path).stem
    video_name_clean = "".join([c if c.isalnum() or c in "._-" else "_" for c in video_name])
    if len(video_name_clean) > 40:
        import hashlib
        short_hash = hashlib.md5(video_name.encode()).hexdigest()[:6]
        video_name_clean = video_name_clean[:35] + "_" + short_hash
    
    job_id = f"video_{video_name_clean}"
    
    # [v2026.CONCURRENCY_SHIELD] Evita lançar a mesma pipeline de dublagem em paralelo
    if job_id in _active_video_jobs:
        logging.warning(f"⚠️ [CONCORRÊNCIA] Job {job_id} já está rodando. Ignorando requisição duplicada.")
        return jsonify({"success": True, "job_id": job_id, "message": "Já em processamento."})
        
    _active_video_jobs.add(job_id)
    
    def thread_wrapper():
        try:
            pipeline_video_master(video_path, job_id, data.get('profile', 'padrao'), data.get('source_lang', 'auto'), data.get('target_lang', 'pt'), data.get('narrative_mode', False))
        finally:
            _active_video_jobs.discard(job_id)
            
    threading.Thread(target=thread_wrapper).start()
    return jsonify({"success": True, "job_id": job_id})

@app.route('/api/status/<job_id>')
def api_status(job_id):
    status = core.safe_json_read(Path(app.config['UPLOAD_FOLDER']) / job_id / "job_status.json")
    return jsonify(status if status else {"status": "searching"})

_active_video_jobs = set()

@app.route('/api/resume_video', methods=['POST'])
def api_resume_video():
    data = request.get_json()
    job_id = data.get('job_id')
    job_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
    
    status = core.safe_json_read(job_dir / "job_status.json")
    video_path = status.get('video_path') if status else None
    
    # Reseta o status para iniciar direto na etapa de tradução/sincronia
    new_status = {
        "job_id": job_id,
        "video_path": video_path,
        "start_time": time.time(),
        "status": "retomado",
        "progress": 20, 
        "message": "Retomando projeto (pós-transcrição)..."
    }
    core.safe_json_write(new_status, job_dir / "job_status.json")

    if job_id in _active_video_jobs:
        return jsonify({"success": True, "message": "Já em processamento."})
    
    _active_video_jobs.add(job_id)

    def thread_wrapper():
        try:
            # [v2026.FIX] Corrigida a ordem dos argumentos no Resume (auto -> pt)
            pipeline_video_master(video_path, job_id, 'padrao', 'auto', 'pt', False)
        finally:
            _active_video_jobs.discard(job_id)

    threading.Thread(target=thread_wrapper).start()
    return jsonify({"success": True, "job_id": job_id})

@app.route('/api/project/<job_id>/segments', methods=['GET'])
def api_get_segments(job_id):
    job_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
    project_data_path = job_dir / "project_data.json"
    
    if not project_data_path.exists():
        return jsonify({"success": False, "message": "Projeto não possui transcrição gerada ainda."}), 404
        
    data = core.safe_json_read(project_data_path)
    if not data or "segments" not in data:
        return jsonify({"success": False, "message": "Dados do projeto corrompidos."}), 400
        
    # Extrai oradores únicos
    speakers = sorted(list(set(seg.get('speaker', 'voz_Unknown') for seg in data["segments"])))
    
    return jsonify({
        "success": True,
        "segments": data["segments"],
        "speakers": speakers
    })

@app.route('/api/project/<job_id>/segments', methods=['POST'])
def api_save_segments(job_id):
    job_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
    project_data_path = job_dir / "project_data.json"
    vocals_path = job_dir / "vocals.wav"
    
    if not project_data_path.exists():
        return jsonify({"success": False, "message": "Projeto não possui transcrição."}), 404
        
    req_data = request.get_json()
    new_segments = req_data.get('segments')
    
    if not new_segments:
        return jsonify({"success": False, "message": "Nenhum segmento enviado."}), 400
        
    # Lê os dados atuais
    data = core.safe_json_read(project_data_path) or {"job_id": job_id}
    data["segments"] = new_segments
    data["status"] = "transcribed"
    
    # Salva os novos dados
    core.safe_json_write(data, project_data_path)
    
    # Também atualiza o cache de transcrição redundante para garantia estrita
    cache_path = job_dir / "transcription_cache.json"
    core.safe_json_write(new_segments, cache_path)
    
    # Reconstrói fisicamente as pastas de voz
    if vocals_path.exists():
        logging.info(f"🔄 [ROTEIRO_UPDATE] Reconstruindo pastas de voz devido a alteração manual do usuário...")
        core.recriar_pastas_de_voz(job_dir, vocals_path, new_segments)
    
    return jsonify({"success": True, "message": "Roteiro e vozes salvos e atualizados com sucesso!"})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5004, debug=False, use_reloader=False)
