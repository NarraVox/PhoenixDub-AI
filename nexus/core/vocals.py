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
from enum import Enum
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

def separar_vocal_instrumental(input_audio, job_dir, cb=None):
    """
    Separação Profissional por Chunks (60s) para máxima performance em GPU.
    Restaurado do App_videos.py para máxima estabilidade.
    """
    job_dir = Path(job_dir)
    temp_chunks_dir = job_dir / "_temp_umx_chunks"
    # [v2026.CLEAN_INTERRUPTED] Limpa a pasta temporária de blocos para não misturar tamanhos (ex: 120s antigos com 60s novos)
    if temp_chunks_dir.exists():
        try:
            shutil.rmtree(temp_chunks_dir)
        except:
            pass
    temp_chunks_dir.mkdir(parents=True, exist_ok=True)
    
    vocals_final_path = job_dir / "vocals.wav"
    instrumental_final_path = job_dir / "instrumental.wav"

    try:
        # 1. Segmentar áudio original em chunks de 60s para otimizar o processamento e reduzir pausas na GPU
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
        
        # [v2026.CPU_GUARD] Limita threads do PyTorch a 2 para evitar sobrecarga da CPU (que atinge 97%)
        try:
            torch.set_num_threads(2)
        except:
            pass
            
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
    "6. Gerando Áudios (Qwen3-TTS)", # 6
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
    'and', 'but', 'so', 'then', 'or', 'a', 'the', 'is', 'it', 'rpg', 'rbg', 'roger'
]

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

