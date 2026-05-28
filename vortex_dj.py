import os
import subprocess
import json
import logging
import time
import re
import shutil
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import nexus_core as core

try:
    import mixingbear
    MIXINGBEAR_AVAILABLE = True
except ImportError:
    logging.warning("⚠️ mixingbear não está instalado no ambiente. Fallback para FFmpeg ativado.")
    MIXINGBEAR_AVAILABLE = False

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURAÇÃO DE PASTAS ABSOLUTAS (v2026.CENTRAL) ---
BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

app = Flask(__name__)
CORS(app)

@app.route('/api/health')
def health_check():
    return jsonify({"status": "online", "engine": "Vortex DJ"})

print("\\n" + "="*50)
print("🌪️  VORTEX DJ ENGINE - [v2026.STABLE.4] - ATIVO")
print("="*50 + "\\n")

class VortexDJ:
    def __init__(self):
        # Pasta de projetos agora CENTRALIZADA dentro de uploads
        self.projects_root = UPLOAD_FOLDER / "dj_projects"
        self.projects_root.mkdir(parents=True, exist_ok=True)
        self.current_project_dir = None
        self.status_file = None
        self.project_state = {"tracks": {}, "completed_mixes": []}
        self.worker_busy = False
        self.current_worker_process = None 
        self.active_process = None # [v2026.FIX] Rastreia o processo FFmpeg ativo

    def init_project(self, name=None):
        if not name:
            name = f"job_vortex_{time.strftime('%Y%m%d_%H%M%S')}"
        
        self.current_project_dir = self.projects_root / name
        self.source_dir = self.current_project_dir / "source"
        self.stems_dir = self.current_project_dir / "stems"
        self.output_dir = self.current_project_dir / "output"
        self.status_file = self.current_project_dir / "job_status.json"

        for p in [self.source_dir, self.stems_dir, self.output_dir]:
            p.mkdir(parents=True, exist_ok=True)
            
        self.project_state = self.load_status()
        
        # [v2026.CLEAN] Se o motor não está rodando, limpa mensagens de tarefas antigas
        if not self.worker_busy:
            self.project_state["current_task"] = ""
            
        self.save_status() # Garante a existência física do JSON
        logging.info(f"📁 [PROJETO] Nucleo ativo em: {name}")
        return name

    def load_status(self):
        if self.status_file and self.status_file.exists():
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Garante chaves básicas
                    if "tracks" not in data: data["tracks"] = {}
                    if "completed_mixes" not in data: data["completed_mixes"] = []
                    # [v2026.STABLE] Mantém o status independente do estado do worker_busy
                    return data
            except: return {"tracks": {}, "completed_mixes": []}
        return {"tracks": {}, "completed_mixes": []}

    def save_status(self):
        """Salva o estado com MERGE para não apagar dados do Worker."""
        if self.status_file:
            # 1. Carrega o que está no disco agora (pode ter sido atualizado pelo Worker)
            disk_state = self.load_status()
            
            # 2. Mescla os dados: Prioridade para o que está no disco (análises) 
            # e para o que está na memória (decisões da IA)
            if "tracks" in self.project_state:
                disk_state["tracks"].update(self.project_state["tracks"])
            
            # Copia chaves importantes, mas RESPEITA o que o Worker escreveu no disco para a tarefa atual
            for k in ["ordered_names", "master_plan", "transition_history", "completed_mixes"]:
                if k in self.project_state:
                    disk_state[k] = self.project_state[k]
            
            # Só atualiza current_task se o Worker NÃO estiver ocupado ou se a memória tiver algo NOVO
            if "current_task" in self.project_state:
                if not getattr(self, 'worker_busy', False) or "Mixando" in self.project_state["current_task"]:
                    disk_state["current_task"] = self.project_state["current_task"]

            # 3. Backup de segurança
            bak_file = self.status_file.with_suffix('.json.bak')
            if self.status_file.exists():
                shutil.copy(self.status_file, bak_file)

            # 4. Escrita Atômica
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(disk_state, f, indent=4)
            
            # Atualiza a memória local com o resultado final
            self.project_state = disk_state

    def separate_stems(self, track_path):
        """Separação Neural via OpenUnmix."""
        track_path = Path(track_path)
        vocal_mp3 = self.stems_dir / f"{track_path.stem}_vocals.mp3"
        instr_mp3 = self.stems_dir / f"{track_path.stem}_instrumental.mp3"
        
        # [v2026.CACHE] Retorna se os MP3s já estiverem prontos no disco
        if vocal_mp3.exists() and instr_mp3.exists():
            return self.stems_dir / track_path.stem
        
        # [v2026.PRE_FLIGHT_PURGE] Limpeza preventiva de VRAM
        import gc
        try:
            import torch
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

        # Detecta se CUDA está disponível para o OpenUnmix
        device = "cpu"
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
        except ImportError:
            pass

        logging.info(f"🧠 [UNMIX] Separando stems na GPU ({device}): {track_path.name}")
        cmd = f"python -m openunmix.cli \"{track_path}\" --output \"{self.stems_dir}\" --model umxhq --device {device}"
        subprocess.run(cmd, shell=True)

        # [v2026.STEM_CONVERSION] Converte os WAVs do OpenUnmix para os MP3s esperados pelo Vortex DJ
        unmix_folder = self.stems_dir / track_path.stem
        vocals_wav = unmix_folder / "vocals.wav"
        
        if unmix_folder.exists() and vocals_wav.exists():
            logging.info(f"💾 [CONVERT] Convertendo stems de WAV para MP3 para economizar espaço...")
            # 1. Converte vocal para MP3
            subprocess.run([
                'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                '-i', str(vocals_wav),
                '-c:a', 'libmp3lame', '-q:a', '2',
                str(vocal_mp3)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 2. Junta os outros stems (drums, bass, other) para formar o instrumental
            drums_wav = unmix_folder / "drums.wav"
            bass_wav = unmix_folder / "bass.wav"
            other_wav = unmix_folder / "other.wav"
            
            inputs = []
            for name in ["drums.wav", "bass.wav", "other.wav"]:
                p = unmix_folder / name
                if p.exists():
                    inputs.append(str(p))
            
            if inputs:
                mix_cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error']
                for inp in inputs:
                    mix_cmd.extend(['-i', inp])
                if len(inputs) > 1:
                    mix_cmd.extend(['-filter_complex', f'amix=inputs={len(inputs)}:weights={" ".join(["1"] * len(inputs))}:normalize=0'])
                mix_cmd.extend(['-c:a', 'libmp3lame', '-q:a', '2', str(instr_mp3)])
                subprocess.run(mix_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # [v2026.PURGE_TEMP] Apaga a pasta WAV temporária do OpenUnmix
            try:
                shutil.rmtree(str(unmix_folder))
                logging.info("🧹 [CLEAN] Pasta WAV temporária removida do disco.")
            except Exception as e:
                logging.warning(f"⚠️ Não foi possível limpar a pasta temporária de stems: {e}")

        # [v2026.VRAM_SWEEPER] Faxina pós-execução
        try:
            import torch
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

        return self.stems_dir / track_path.stem

    def transcribe_lot(self, track_paths):
        """Fase 0: OUVINTE (ASSÍNCRONO)."""
        import sys, threading
        temp_list_path = self.current_project_dir / "temp_transcribe_list.json"
        with open(temp_list_path, 'w') as f:
            json.dump([str(p) for p in track_paths], f)
            
        logging.info("🔒 [GUARD] BLOQUEANDO CPU PARA TRABALHO PESADO (WHISPER)...")
        self.worker_busy = True
        def run():
            logging.info("🚀 [SYSTEM] Disparando WHISPER WORKER UNIFICADO...")
            cmd = [sys.executable, "c:/IA_dublagem/vortex_dj.py", "--worker-whisper", str(temp_list_path), str(self.status_file)]
            self.current_worker_process = subprocess.Popen(cmd)
            self.current_worker_process.wait() # Espera o processo terminar
            self.project_state = self.load_status()
            self.worker_busy = False
            self.current_worker_process = None
            logging.info("🔓 [GUARD] CPU LIBERADA PELO WHISPER.")

        threading.Thread(target=run).start()

    def analyze_lot(self, track_paths):
        """Fase 1: CIENTISTA (ASSÍNCRONO)."""
        import sys, threading
        temp_list_path = self.current_project_dir / "temp_analyze_list.json"
        with open(temp_list_path, 'w') as f:
            json.dump([str(p) for p in track_paths], f)
            
        logging.info("🔒 [GUARD] BLOQUEANDO CPU PARA TRABALHO PESADO (ANALYSIS)...")
        self.worker_busy = True
        def run():
            logging.info("🚀 [SYSTEM] Disparando ANALYSIS WORKER UNIFICADO...")
            cmd = [sys.executable, "c:/IA_dublagem/vortex_dj.py", "--worker-analysis", str(temp_list_path), str(self.status_file)]
            self.current_worker_process = subprocess.Popen(cmd)
            self.current_worker_process.wait()
            self.project_state = self.load_status()
            self.worker_busy = False
            self.current_worker_process = None
            logging.info("🔓 [GUARD] CPU LIBERADA PELA ANÁLISE.")

        threading.Thread(target=run).start()

    def stop_current_worker(self):
        """Mata o processo atual (FFmpeg, Whisper ou Mixagem)."""
        if self.current_worker_process:
            logging.warning("🛑 [STOP] Encerrando processo worker forçadamente...")
            self.current_worker_process.terminate()
            try:
                self.current_worker_process.wait(timeout=5)
            except:
                self.current_worker_process.kill()
            self.current_worker_process = None
            self.worker_busy = False
            self.project_state["current_task"] = "🛑 Processo interrompido pelo usuário."
            self.save_status()
            return True
        
        # Se for a thread de mixagem (que não é um subprocesso direto)
        if self.worker_busy and "Mixando" in self.project_state.get("current_task", ""):
            logging.warning("🛑 [STOP] Interrupção de mixagem solicitada. O worker parará no próximo ciclo.")
            self.worker_busy = False # Isso fará o loop do worker parar ou falhar graciosamente
            self.project_state["current_task"] = "🛑 Mixagem interrompida."
            self.save_status()
            return True
            
    def _auto_schedule_fx(self, track_name, track_data):
        """Analisa o espectro e agenda efeitos estratégicos (Build-ups, Drops, Scratches)."""
        fx_list = []
        energy_map = track_data.get('energy_map', [])
        duration = track_data.get('duration', 200)
        if not energy_map: return []

        # 1. BUILD-UP: Detecta subida brusca para Sweep/Flanger
        for i in range(1, len(energy_map)):
            if energy_map[i] > energy_map[i-1] * 1.4:
                time_at = (i / len(energy_map)) * duration
                fx_list.append({"type": "filter_sweep", "time_offset": max(0, time_at - 4), "track": "B"})
                break

        # 2. DROP & SCRATCH: Localiza o pico máximo e aplica o "DJ Hero Scratch"
        max_idx = energy_map.index(max(energy_map))
        drop_time = (max_idx / len(energy_map)) * duration
        
        # Scratch agressivo 1 segundo antes do drop
        fx_list.append({"type": "scratch", "time_offset": max(0, drop_time - 1), "track": "A"})
        # Stutter rítmico no impacto do drop
        fx_list.append({"type": "stutter", "time_offset": drop_time, "track": "B"})
                
        # 3. AMBIENT MODS (DJ Hero Vibe): Efeitos aleatórios rítmicos ao longo da música
        for i in range(2, len(energy_map) - 2):
            if i % 3 == 0: # Adiciona um "tempero" a cada ~10-15s
                time_at = (i / len(energy_map)) * duration
                fx_type = "bitcrush" if i % 2 == 0 else "pulsar"
                fx_list.append({"type": fx_type, "time_offset": time_at, "track": "A"})

        # 4. VOCAL INTELLIGENCE (Whisper Reaction): Reage a palavras fortes ou fim de frases
        transcription = track_data.get('transcription', "")
        if transcription:
            strong_words = ["dale", "vai", "agora", "now", "go", "fire", "beat", "drop"]
            words = transcription.lower().split()
            if any(sw in words for sw in strong_words):
                fx_list.append({"type": "echo_out", "time_offset": duration / 2, "track": "A"})
                
        return fx_list

    def curate_set_fast(self):
        """Versão Turbo: Curadoria instantânea e mapeamento de Auto-FX."""
        logging.info("🚀 [VORTEX MASTER] Planejando setlist e efeitos via análise de espectro...")
        tracks = self.project_state.get("tracks", {})
        if not tracks: return []
        
        sorted_tracks = sorted(tracks.items(), key=lambda x: x[1].get('bpm', 120))
        sequence = []
        for i in range(len(sorted_tracks) - 1):
            name_a, data_a = sorted_tracks[i]
            name_b, data_b = sorted_tracks[i+1]
            
            # Agenda efeitos matemáticos
            fx_a = self._auto_schedule_fx(name_a, data_a)
            fx_b = self._auto_schedule_fx(name_b, data_b)
            
            # [v2026.PERSONALITY] Escolhe o humor do set baseado na energia média
            avg_energy = (data_a.get('energy', 0) + data_b.get('energy', 0)) / 2
            if avg_energy > 0.08: personality = "festival"
            elif avg_energy > 0.05: personality = "agressivo"
            else: personality = "suave"
            
            if personality == "festival":
                t_type, dur = "filter_sweep", 40 # Extended Mix de Festival (20-40s)
                advice = "🎪 MODO FESTIVAL: Extended Mashup & Silêncio Épico"
                is_super = True
                # Adiciona o silêncio estratégico pré-drop no final da música A
                fx_a.append({"type": "silence_pre_drop", "time_offset": dur - 0.5, "track": "A"})
                # Adiciona o eco na saída
                fx_a.append({"type": "echo_out", "time_offset": dur - 3, "track": "A"})
            elif personality == "agressivo":
                t_type, dur = "drop_cut", 6
                advice = "💥 MODO AGRESSIVO: Cortes Rápidos & Scratches"
                is_super = False
            else:
                t_type, dur = "acrossfade", 12
                advice = "🍃 MODO SUAVE: Transições Orgânicas"
                is_super = False
            
            sequence.append({
                "track_a": name_a, "track_b": name_b,
                "transition": {
                    "type": t_type, "duration": dur, "target_bpm": data_b.get('bpm', 120),
                    "fx_a": fx_a, "fx_b": fx_b, "advice": advice, "is_super": is_super,
                    "personality": personality
                }
            })
        return sequence

    def _check_vocal_conflict(self, data_a, data_b):
        """Verifica se há conflito de vozes na transição (v2026.STEM_LOGIC)."""
        v_a = data_a.get('vocal_map', [])
        v_b = data_b.get('vocal_map', [])
        if not v_a or not v_b: return False
        
        # Olha os últimos 20% da A e os primeiros 20% da B
        if v_a[-1] > 2000 and v_b[0] > 2000:
            logging.warning(f"🎙️ [VOCAL CONFLICT] Detectado! Ativando lógica de Stems...")
            return True
        return False

    def ignite_mix_lot(self, valid_metadata):
        """Fase 2: MAESTRO (ASSÍNCRONO)."""
        import threading
        
        logging.info("🔒 [GUARD] BLOQUEANDO CPU PARA TRABALHO PESADO (MIXING)...")
        self.worker_busy = True
        total_steps = len(valid_metadata) - 1
        
        def run():
            try:
                # [v2026.CLEAN] Limpa estados de erro anteriores para recomeçar
                self.project_state["current_task"] = "🚀 Inicializando motor Vortex..."
                if "error" in self.project_state: del self.project_state["error"]
                self.save_status()

                # 1. Planejamento Técnico (DETERMINÍSTICO - Sem IA)
                self.project_state["current_task"] = "🔬 Analisando espectro e agendando efeitos..."
                
                # Usa a curadoria instantânea interna para gerar o master_plan
                curation = self.curate_set_fast()
                master_plan = []
                for i, step in enumerate(curation):
                    trans = step['transition']
                    if trans.get('is_super'):
                        logging.info(f"🔥 [SUPER MIX] AGENDADA: {step['track_a']} ➔ {step['track_b']}")
                        self.project_state.setdefault("logs", []).append(f"🔥 [SUPER MIX] AGENDADA: {step['track_a']} ➔ {step['track_b']}")
                    
                    master_plan.append({
                        "id": i,
                        "track_a": step['track_a'],
                        "track_b": step['track_b'],
                        "type": trans['type'],
                        "dur": trans['duration'],
                        "target_bpm": trans['target_bpm'],
                        "mid_fx": trans.get('fx_a', []) + trans.get('fx_b', []),
                        "advice": trans.get('advice', "Auto-Mix")
                    })

                self.project_state["master_plan"] = master_plan
                self.save_status()

                # 2. Execução de Mixagem
                current_track_data = valid_metadata[0]
                
                for i in range(len(valid_metadata) - 1):
                    track_a = valid_metadata[i]
                    track_b = valid_metadata[i+1]
                    
                    # [v2026.SUPER_MIX] Lógica de detecção de momento épico
                    is_super = False
                    bpm_diff = abs(track_a.get('bpm', 120) - track_b.get('bpm', 120))
                    if bpm_diff < 4 and track_a.get('energy', 0) > 0.05:
                        is_super = True
                        logging.info(f"🔥 [SUPER MIX] DETECTADA: {track_a['name']} ➔ {track_b['name']} será épica!")
                        self.project_state.setdefault("logs", []).append(f"🔥 [SUPER MIX] ATIVADA: {track_a['name']} ➔ {track_b['name']}")
                    
                    # [v2026.SAFETY] Verifica se o usuário solicitou parada
                    if not self.worker_busy:
                        logging.warning("🛑 [VORTEX] Interrupção detectada no worker de mixagem.")
                        break

                    current_pair = [track_a, track_b]
                    
                    # [v2026.SMART_STEMS] Decide se precisa de OpenUnmix por conflito vocal
                    use_instrumental = self._check_vocal_conflict(current_pair[0], current_pair[1])
                    
                    track_a_name = current_pair[0]['name'].split('.')[0]
                    track_b_name = current_pair[1]['name'].split('.')[0]
                    
                    if is_super:
                        self.project_state["current_task"] = f"🎙️ [SUPER MIX] Isolando Stems de A e B..."
                        self.save_status()
                        for track in [current_pair[0], current_pair[1]]:
                            t_name = track['name'].split('.')[0]
                            vocal_p = self.stems_dir / f"{t_name}_vocals.mp3"
                            instr_p = self.stems_dir / f"{t_name}_instrumental.mp3"
                            if not vocal_p.exists() or not instr_p.exists():
                                self.separate_stems(track['path'])
                            # [v2026.STEM_INJECT] Passa os caminhos dos stems para o motor
                            track['vocal_path'] = str(vocal_p) if vocal_p.exists() else track['path']
                            track['instr_path'] = str(instr_p) if instr_p.exists() else track['path']
                    
                    if use_instrumental and not is_super: # Lógica padrão se não for super mix
                        self.project_state["current_task"] = f"🎙️ Isolando Instrumental: {track_b_name}..."
                        self.save_status()
                        instr_path = self.stems_dir / f"{track_b_name}_instrumental.mp3"
                        if not instr_path.exists():
                            self.separate_stems(current_pair[1]['path'])
                        if instr_path.exists():
                            current_pair[1]['path'] = str(instr_path)
                    
                    self.project_state["current_task"] = f"🎧 Mixando: {track_a_name} ➔ {track_b_name} ({i+1}/{total_steps}) | ⏳ 0%"
                    self.save_status()
                    
                    # [v2026.RESTORE] Verifica se o mix já existe e se o arquivo físico está no disco
                    mix_id = f"mix_{i}_{track_a_name}_to_{track_b_name}"
                    final_track_a_name = f"{i+1:02d} - {track_a_name}.mp3"
                    next_temp_base = f"base_for_next_{i}.mp3"
                    
                    file_exists = (self.output_dir / next_temp_base).exists()
                    if mix_id in self.project_state.get("completed_mixes", []) and file_exists:
                        logging.info(f"♻️ [RESTORE] Pulando Mix {i+1} (Já existe no disco)")
                        current_track_data = {"path": str(self.output_dir / next_temp_base), "name": next_temp_base, "bpm": current_pair[1]['bpm']}
                        continue

                    # Executa a mixagem profissional
                    decision = next((p for p in master_plan if p.get('id') == i), None)
                    if not decision: decision = {"target_bpm": current_pair[1].get('bpm', 120), "dur": 10, "type": "crossfade", "advice": "Standard."}
                    
                    advice = decision.get('advice', "Transição fluída.")
                    self.project_state["current_task"] = f"🧠 Estratégia: {advice} ({i+1}/{total_steps})"
                    self.save_status()

                    t_type = decision.get('type', decision.get('transition_type', 'crossfade'))
                    mix_dur = decision.get('dur', decision.get('mix_duration', 10))
                    
                    raw_mid_fx = decision.get('mid_fx', decision.get('mid_track_fx', []))
                    normalized_fx = []
                    for fx in raw_mid_fx:
                        fx_type = fx.get('type', 'stutter').lower()
                        if fx_type == 'aecho': fx_type = 'reverb'
                        normalized_fx.append({
                            "track": fx.get('tr', fx.get('track', 'B')),
                            "time_offset": fx.get('off', fx.get('time_offset', 0)),
                            "type": fx_type
                        })

                    next_track_data = {**current_pair[1], "transition_type": t_type, "mix_duration": mix_dur, "mid_track_fx": normalized_fx}
                    temp_mix_name = f"temp_mix_{i}.mp3"
                    temp_mix_path = self.output_dir / temp_mix_name
                    
                    self.mix_tracks_professional(current_track_data, next_track_data, temp_mix_name, custom_output=temp_mix_path)
                    
                    # Fatiamento Progressivo (Cria a base para a PRÓXIMA mixagem)
                    self.project_state["current_task"] = f"🔪 Finalizando Mix {i+1}..."
                    self.save_status()
                    
                    # [v2026.FIX] O ponto de corte deve ser baseado na duração da trilha A (entrada)
                    # [v2026.PITCH_FIX] Calcula o split_point com base na velocidade aplicada
                    bpm_a = current_track_data.get('bpm', 120)
                    target_bpm = decision.get('target_bpm', bpm_a)
                    speed_a = target_bpm / bpm_a if bpm_a > 0 else 1.0
                    
                    dur_in_raw = core.get_audio_duration(current_track_data['path'])
                    dur_in_adjusted = dur_in_raw / speed_a
                    
                    mix_dur_final = decision.get('dur', decision.get('mix_duration', 10))
                    split_point = max(0.1, dur_in_adjusted - (mix_dur_final / 2))
                    
                    logging.info(f"✂️ [SLICE] Speed A: {speed_a:.3f} | Adjusted Dur: {dur_in_adjusted:.2f}s | Split: {split_point:.2f}s")
                    
                    # Gera o arquivo final da música atual e a base para a próxima
                    # [v2026.SAFETY] Verificação de duração real antes do corte
                    mix_actual_dur = core.get_audio_duration(temp_mix_path)
                    safe_split = min(split_point, mix_actual_dur - 0.1)
                    
                    logging.info(f"✂️ [SLICE] Real Dur: {mix_actual_dur}s | Target Split: {safe_split}s")

                    # [v2026.TRANSPARENT_MASTER] Som fiel ao original: Apenas limitador de segurança
                    mastering = "alimiter=limit=0.9"
                    
                    clean_name = track_a_name.replace("_", " ")
                    # Exportação Final com Masterização
                    subprocess.run(['ffmpeg', '-y', '-i', str(temp_mix_path), '-t', str(safe_split), '-af', mastering, '-map_metadata', '-1', '-metadata', f'title={clean_name}', '-c:a', 'libmp3lame', '-q:a', '2', str(self.output_dir / final_track_a_name)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    # Base para a próxima SEM Masterização (para não acumular)
                    subprocess.run(['ffmpeg', '-y', '-i', str(temp_mix_path), '-ss', str(safe_split), '-map_metadata', '-1', '-c:a', 'libmp3lame', '-q:a', '2', str(self.output_dir / next_temp_base)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    if not (self.output_dir / next_temp_base).exists():
                        logging.error(f"❌ Erro: Falha ao gerar base para a próxima música ({next_temp_base})")
                        raise Exception(f"Erro no fatiamento da trilha {i+1}")

                    self.project_state.setdefault("transition_history", []).append({
                        "pair": f"{track_a_name} -> {track_b_name}",
                        "type": t_type, "duration": mix_dur, "advice": decision.get('advice', "")
                    })
                    self.project_state.setdefault("completed_mixes", []).append(mix_id)
                    self.save_status()
                    
                    current_track_data = {"path": str(self.output_dir / next_temp_base), "name": next_temp_base, "bpm": decision.get('target_bpm', current_pair[1].get('bpm', 120))}

                # [v2026.FINAL_EXPORT] Salva a última música que sobrou no loop
                final_song_idx = len(valid_metadata)
                final_song_name = f"{final_song_idx:02d} - {valid_metadata[-1]['name']}"
                if (self.output_dir / next_temp_base).exists():
                    logging.info(f"💾 [FINAL] Salvando trilha de encerramento: {final_song_name}")
                    shutil.copy(self.output_dir / next_temp_base, self.output_dir / final_song_name)

                self.project_state["current_task"] = "✅ Mixagem concluída com sucesso!"
                self.save_status()

            except Exception as e:
                err_msg = f"❌ ERRO CRÍTICO: {str(e)}"
                logging.error(err_msg)
                self.project_state["current_task"] = err_msg
                # Injeta o erro no log para aparecer no console do site
                self.project_state.setdefault("logs", []).append(err_msg)
                self.save_status()
            finally:
                self.worker_busy = False
        logging.info("🔓 [GUARD] CPU LIBERADA PELA MIXAGEM.")

        threading.Thread(target=run).start()

    def mix_tracks_professional(self, track_a_data, track_b_data, output_name, custom_output=None):
        """Motor de Mixagem Super Mix 2.0 (4-Channel Remix Engine)."""
        output_path = custom_output if custom_output else UPLOAD_FOLDER / output_name
        
        path_a = track_a_data['path']
        path_b = track_b_data['path']
        is_super = track_b_data.get('is_super', False)
        
        # [DJ_AUTO_MIX] Integração do MixingBear para transições normais
        t_type = track_b_data.get('transition_type', 'crossfade')
        if MIXINGBEAR_AVAILABLE and not is_super and t_type in ['crossfade', 'acrossfade']:
            try:
                logging.info(f"🐻 [MIXINGBEAR] Iniciando mixagem automatizada: {track_a_data.get('name')} ➔ {track_b_data.get('name')}")
                mixingbear.mix(str(path_a), str(path_b), str(output_path), mix_mode='first')
                logging.info(f"🐻 [MIXINGBEAR] Mixagem concluída com sucesso! Salvo em: {output_path}")
                return output_path
            except Exception as e:
                logging.error(f"⚠️ [MIXINGBEAR] Erro na mixagem rápida (usando fallback do FFmpeg): {e}")

        # [v2026.SUPER_MIX_2_0] Injeção de 4 canais se for Super Mix
        if is_super:
            path_a_v = track_a_data.get('vocal_path', path_a)
            path_a_i = track_a_data.get('instr_path', path_a)
            path_b_v = track_b_data.get('vocal_path', path_b)
            path_b_i = track_b_data.get('instr_path', path_b)
            input_args = f"-i \"{path_a_i}\" -i \"{path_a_v}\" -i \"{path_b_i}\" -i \"{path_b_v}\""
        else:
            input_args = f"-i \"{path_a}\" -i \"{path_b}\""
            
        bpm_a, bpm_b = track_a_data.get('bpm', 120), track_b_data.get('bpm', 120)
        target_bpm = track_b_data.get('target_bpm', bpm_b)
        dur_mix = track_b_data.get('mix_duration', 10)
        t_type = track_b_data.get('transition_type', 'crossfade')
        mid_fx = track_b_data.get('mid_track_fx', [])
        
        speed_a = target_bpm / bpm_a if bpm_a > 0 else 1.0
        speed_b = target_bpm / bpm_b if bpm_b > 0 else 1.0
        
        # [v2026.PITCH_SAFETY] Limita o atempo entre 0.5 e 2.0 (limite técnico do FFmpeg)
        speed_a = max(0.5, min(2.0, speed_a))
        speed_b = max(0.5, min(2.0, speed_b))
        
        # [v2026.VALIDATION] Log de engenharia para confirmar os ajustes reais
        eng_log = f"🎧 [AUDIO_ENGINE] {track_a_data.get('name')} (Speed: {speed_a:.3f}) ➔ {track_b_data.get('name')} (Speed: {speed_b:.3f}) | Target: {target_bpm} BPM"
        logging.info(eng_log)
        
        try:
            with open(self.status_file, 'r') as f: status = json.load(f)
            status.setdefault("logs", []).append(eng_log)
            with open(self.status_file, 'w') as f: json.dump(status, f, indent=4)
        except: pass
        
        # --- LÓGICA DE SINCRONIA DE FASE (PERFECT BEAT-MATCH) ---
        dur_a = core.get_audio_duration(path_a)
        ideal_transition_start = dur_a - dur_mix
        
        # Procura o beat mais próximo na música A para começar a transição
        beats_a = track_a_data.get('beats', [])
        sync_start_a = ideal_transition_start
        if beats_a:
            # Encontra o beat mais próximo do ponto ideal de transição
            sync_start_a = min(beats_a, key=lambda x: abs(x - ideal_transition_start))
            
            # [v2026.SAFETY] Se o beat encontrado for muito longe do fim (> 60s), 
            # ignoramos a sincronia para evitar crossfades gigantes que o FFmpeg não suporta.
            if (dur_a - sync_start_a) > 60:
                logging.warning(f"⚠️ [VORTEX] Sincronia de batida ignorada (muito longe do fim: {round(dur_a - sync_start_a, 2)}s)")
                sync_start_a = ideal_transition_start
            else:
                # Ajusta a duração da mixagem para compensar o deslocamento
                dur_mix = dur_a - sync_start_a

        # [v2026.SAFETY] Hard cap de 30s para dur_mix (FFmpeg limite é 60, mas 30 é o padrão DJ seguro)
        dur_mix = max(0.5, min(dur_mix, 30))
            
        # [v2026.STABLE_PITCH] Só aplica atempo se houver mudança real (> 0.1%) para evitar artefatos
        f_base_a = f"[0:a]atrim=start={track_a_data.get('start_offset', 0)},asetpts=PTS-STARTPTS"
        if abs(speed_a - 1.0) > 0.001: f_base_a += f",atempo={speed_a}"
        f_base_a += ",aresample=44100"

        f_base_b = f"[1:a]atrim=start={track_b_data.get('first_beat', 0)},asetpts=PTS-STARTPTS"
        if abs(speed_b - 1.0) > 0.001: f_base_b += f",atempo={speed_b}"
        f_base_b += ",aresample=44100"

        # --- APLICAÇÃO DE MID-TRACK FX (Efeitos agendados pela IA) ---
        fx_chain_a, fx_chain_b = "", ""
        for fx in mid_fx:
            target = fx.get('track', 'B')
            t_offset = fx.get('time_offset', 0)
            t_end = t_offset + 2
            
            chain = ""
            # [v2026.CREATIVE_MASHUP] Lógica de Troca de Drop e Foco Vocal Dinâmica
            if is_super:
                mid_point = dur_mix / 2
                # 1. Silencia o Instrumental de A na metade da transição para entrar o Drop de B
                fx_chain_a += f",volume='if(gt(t,{mid_point}),0.3,1)':eval=frame" 
                # 2. Dá brilho na voz de A para se destacar no Mashup (Clean Mix Boost)
                fx_chain_a += f",equalizer=f=3000:width_type=h:width=1500:g=6:enable='between(t,{mid_point},{dur_mix})'"
                # 3. Scratch Vocal na transição de saída (últimos 2 segundos)
                fx_chain_a += f",vibrato=f=16:d=0.8:enable='between(t,{dur_mix-2},{dur_mix})'"
                
                # [v2026.CLEAN_MIX_SIDECHAIN] Abre espaço na Track B para a voz da Track A
                fx_chain_b += f",equalizer=f=3000:width_type=h:width=2000:g=-8:enable='between(t,0,{dur_mix})'"
                fx_chain_b += f",volume=0.8:enable='between(t,0,{dur_mix})'" # Ducking suave
                
            if fx['type'] == 'silence_pre_drop':
                # [v2026.FESTIVAL_DROP] Vácuo absoluto de 0.5s para explodir o drop
                chain = f",volume=0:enable='between(t,{t_offset},{t_offset+0.5})'"
            elif fx['type'] == 'echo_out':
                # [v2026.SMOOTH_ECHO] Rampa de volume no eco para entrada suave
                chain = f",aecho=0.8:0.9:1000:0.3,volume='if(lt(t-{t_offset},1),(t-{t_offset})/1,1)':eval=frame:enable='between(t,{t_offset},{t_offset+3})'"
            elif fx['type'] == 'scratch':
                # [v2026.PREMIUM_SCRATCH] Com Humanização (Micro-variações)
                import random
                style = random.choice(['baby', 'burst', 'transform', 'tear'])
                jitter_f = random.uniform(0.9, 1.1)
                jitter_d = random.uniform(0.8, 1.2)
                
                if style == 'baby':
                    # Movimento clássico com rampa de profundidade
                    f_val = 8 * jitter_f
                    d_val = 0.5 * jitter_d
                    chain = f",vibrato=f={f_val}:d={d_val},equalizer=f=1000:width_type=h:width=400:g=8:enable='between(t,{t_offset},{t_offset+0.8})'"
                elif style == 'burst':
                    # 3 cortes rápidos (Triplo)
                    chain = f",volume='if(lt(mod(t,0.15),0.05),0,1)':eval=frame:enable='between(t,{t_offset},{t_offset+0.45})'"
                elif style == 'transform':
                    # Corte rítmico estilo DJ Hero
                    chain = f",volume='if(lt(mod(t,0.1),0.05),0,1)':eval=frame:enable='between(t,{t_offset},{t_offset+1})'"
                else: # tear
                    # Irregular e "arrastado"
                    chain = f",vibrato=f=4:d=0.9,lowpass=f=2000:enable='between(t,{t_offset},{t_offset+1.2})'"
            elif fx['type'] == 'bitcrush':
                # [v2026.GLITCH_HERO] Som digital esmagado
                chain = f",acrusher=level_in=1:level_out=1:bits=8:mode=log:aa=1:enable='between(t,{t_offset},{t_offset+1})'"
            elif fx['type'] == 'pulsar':
                # [v2026.GLITCH_HERO] Modulação de volume rítmica
                chain = f",tremolo=f=8:d=0.8:enable='between(t,{t_offset},{t_offset+2})'"
            elif fx['type'] == 'stutter':
                # [v2026.HI_FI_STUTTER] Sincronizado com o BPM (1/16 de nota) para soar musical
                bpm = track_a_data.get('bpm', 128) if target == 'A' else track_b_data.get('bpm', 128)
                cycle = 60 / bpm / 4 # 1/16 note cycle
                # Usa senoide para um "pumping" suave em vez de corte seco (evita estalos)
                chain = f",volume='0.5+0.5*sin(2*pi*t/{cycle})':eval=frame:enable='between(t,{t_offset},{t_end})'"
            elif fx['type'] == 'flanger':
                # [v2026.HI_FI_FLANGER] Efeito clássico de DJ
                chain = f",flanger=delay=2:depth=0.5:regen=20:width=100:speed=0.5:enable='between(t,{t_offset},{t_end})'"
            elif fx['type'] == 'reverb':
                # [v2026.HI_FI_SPACE] Lowpass mais aberto (3kHz) para não abafar os hats
                chain = f",lowpass=f=3000:enable='between(t,{t_offset},{t_end})'"
            elif fx['type'] == 'vocal_boost':
                # [v2026.HI_FI_PRESENCE] EQ de presença
                chain = f",equalizer=f=3000:width_type=h:width=500:g=4:enable='between(t,{t_offset},{t_end})'"
            
            if target == 'A': fx_chain_a += chain
            else: fx_chain_b += chain

        # --- CADEIA DE TRANSIÇÃO (ESTÁVEL) ---
        if is_super:
            # [v2026.SUPER_MIX_2_0] Lógica de Coreografia de Camadas (Mashup Épico)
            # [0:a] Instr A | [1:a] Vocal A | [2:a] Instr B | [3:a] Vocal B
            mid = dur_mix / 2
            # 1. Instr A fade out na metade | Instr B fade in na metade
            f_instr_a = f"[0:a]volume='if(lt(t,{mid}),1,0)':eval=frame[ia]"
            f_instr_b = f"[2:a]volume='if(gt(t,{mid}),1,0)':eval=frame[ib]"
            # 2. Vocal A e B se alternam rítmicamente (Call & Response)
            f_vocal_a = f"[1:a]volume='if(lt(mod(t,4),2),1,0)':eval=frame[va]" 
            f_vocal_b = f"[3:a]volume='if(gt(mod(t,4),2),1,0)':eval=frame[vb]" 
            
            master_chain = f"{f_instr_a};{f_instr_b};{f_vocal_a};{f_vocal_b};[ia][va][ib][vb]amix=inputs=4:weights=1 1 1 1"
        elif t_type == 'echo_out':
            # No Echo Out, aplicamos o aecho SEM o enable (pois é no segmento todo)
            fx_a = f"{f_base_a}{fx_chain_a},aecho=0.8:0.8:1000:0.5[a1]"
            fx_b = f"{f_base_b}{fx_chain_b}[a2]"
            mix_logic = f"[a1][a2]acrossfade=d={dur_mix}:c1=exp:c2=tri"
        elif t_type == 'filter_sweep':
            # [v2026.SMOOTH_SWEEP] LPF abre (de 500Hz para 20kHz) | HPF sobe (de 20Hz para 2000Hz)
            # Adicionado: Sidechain EQ na B para abrir espaço para o vocal da A
            fx_a = f"{f_base_a}{fx_chain_a},highpass=f='20+(1980*t/{dur_mix})':enable='between(t,0,{dur_mix})'[a1]" 
            fx_b = f"{f_base_b}{fx_chain_b},lowpass=f='500+(19500*t/{dur_mix})',equalizer=f=3000:width_type=h:width=2000:g=-5:enable='between(t,0,{dur_mix})'[a2]"
            mix_logic = f"[a1][a2]acrossfade=d={dur_mix}:c1=qsin:c2=qsin"
        elif t_type == 'drop_cut':
            fx_a = f"{f_base_a}{fx_chain_a}[a1]"
            fx_b = f"{f_base_b}{fx_chain_b}[a2]"
            mix_logic = f"[a1][a2]acrossfade=d=0.3:c1=exp:c2=tri"
        else:
            fx_a = f"{f_base_a}{fx_chain_a}[a1]"
            fx_b = f"{f_base_b}{fx_chain_b}[a2]"
            mix_logic = f"[a1][a2]acrossfade=d={dur_mix}:c1=qsin:c2=qsin"

        # [v2026.CLEAN_MIX] Mixagem limpa para evitar processamento acumulado
        master_chain = f"{fx_a};{fx_b};{mix_logic}"
        
        logging.info(f"🎧 [VORTEX FX] Tipo: {t_type.upper()} | Mixando: {output_name}")
        
        # [v2026.PROGRESS] Estima a duração total para cálculo de %
        total_expected_duration = dur_a + dur_mix # Aproximação segura
        
        # [v2026.METADATA_FIX] Remove metadados globais na mixagem base
        cmd = ['ffmpeg', '-y', '-threads', '0', '-progress', '-']
        if is_super:
            cmd.extend([
                '-i', str(path_a_i),
                '-i', str(path_a_v),
                '-i', str(path_b_i),
                '-i', str(path_b_v)
            ])
        else:
            cmd.extend([
                '-i', str(path_a),
                '-i', str(path_b)
            ])
        cmd.extend([
            '-filter_complex', master_chain,
            '-map_metadata', '-1',
            str(output_path)
        ])
        
        # [v2026.DEBUG] Captura stderr para diagnóstico em caso de falha
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.active_process = process # Registra para o stop_job
        
        ffmpeg_error_log = []
        try:
            last_pct = -1
            # Thread para ler stderr simultaneamente para não travar o buffer
            import threading
            def capture_stderr():
                for line in process.stderr:
                    ffmpeg_error_log.append(line.strip())
                    if "Error" in line or "error" in line:
                        logging.error(f"FFMPEG: {line.strip()}")
            
            err_thread = threading.Thread(target=capture_stderr)
            err_thread.start()

            for line in process.stdout:
                if "out_time_ms=" in line:
                    try:
                        ms = int(line.split('=')[1].strip())
                        current_sec = ms / 1000000.0
                        pct = min(99, int((current_sec / total_expected_duration) * 100))
                        
                        if pct > last_pct and pct % 5 == 0: 
                            last_pct = pct
                            msg = f"⏳ Renderizando Mix: {pct}%"
                            self.project_state["current_task"] = msg
                            self.save_status()
                    except: pass
            
            process.wait()
            err_thread.join()
        except Exception as e:
            process.kill()
            raise e
        
        if process.returncode != 0:
            full_err = "\n".join(ffmpeg_error_log[-10:]) # Pega as últimas 10 linhas de erro
            logging.error(f"❌ Erro Crítico no FFmpeg: {full_err}")
            raise Exception(f"Falha na renderização: {full_err}")
        return output_path

dj_engine = VortexDJ()

# --- ENDPOINTS ---

@app.route('/api/init_session', methods=['POST'])
def init_session():
    data = request.json
    files = data.get('files', []) # [{name, path}, ...]
    project_id = data.get('project_id') # Opcional para retomar
    
    if not files and not project_id: 
        return jsonify({"error": "Nenhum dado para iniciar ou retomar"}), 400
    
    # Se project_id existir, retomamos. Senão, criamos novo.
    project_name = dj_engine.init_project(project_id)
    
    # [v2026.PRE-POPULATE] Garante que as músicas apareçam no status antes mesmo da análise
    copied_count = 0
    if not project_id:
        for file_info in files:
            if isinstance(file_info, str):
                f_name = file_info
                src = UPLOAD_FOLDER / f_name
            else:
                f_name = file_info.get('name')
                src = Path(file_info.get('path'))
                
            dst = dj_engine.source_dir / f_name
            if src.exists():
                logging.info(f"🚚 [COPY] Movendo {f_name} para projeto...")
                shutil.copy(src, dst)
                # Adiciona entrada vazia no status para a UI contar
                if f_name not in dj_engine.project_state["tracks"]:
                    dj_engine.project_state["tracks"][f_name] = {}
                copied_count += 1
        dj_engine.save_status() # Salva o dicionário populado
    else:
        # Se retomou, conta quantos arquivos já existem na pasta source
        copied_count = len(list(dj_engine.source_dir.glob("*")))
            
    return jsonify({
        "success": True, 
        "project": project_name, 
        "copied": copied_count,
        "resumed": project_id is not None
    })

@app.route('/api/list_uploads', methods=['GET'])
def list_uploads():
    """Lista arquivos de áudio na pasta uploads para novos projetos."""
    files = [f.name for f in UPLOAD_FOLDER.glob("*") if f.suffix.lower() in ['.mp3', '.wav']]
    return jsonify({"success": True, "files": files})

@app.route('/api/get_job_status', methods=['GET'])
def get_job_status():
    """Retorna o estado atual do projeto (Lendo diretamente do disco para evitar lag)."""
    status = dj_engine.load_status()
    
    # [v2026.STABLE] Apenas confia no estado real do worker_busy do motor
    status["worker_busy"] = dj_engine.worker_busy
    return jsonify(status)

@app.route('/api/transcribe_tracks', methods=['GET'])
def transcribe_tracks():
    if not dj_engine.source_dir: return jsonify({"error": "Projeto não iniciado"}), 400
    
    # [v2026.RELOAD] Força leitura do disco para não repetir o que já foi feito
    dj_engine.project_state = dj_engine.load_status()

    # [v2026.CPU_GUARD] Impede múltiplos workers de transcrição
    if dj_engine.worker_busy:
        logging.warning("⚠️ [GUARD] BLOQUEIO ATIVO: Transcrição negada para evitar sobrecarga.")
        return jsonify({"success": True, "msg": "Worker já está ocupado.", "count": 0})
    
    files = list(dj_engine.source_dir.glob("*"))
    audio_files = [f for f in files if f.suffix.lower() in ['.mp3', '.wav']]
    
    # [v2026.SMART] Só transcreve o que ainda não tem texto (Lyrics ou Transcription)
    to_transcribe = []
    for f in audio_files:
        track_data = dj_engine.project_state.get("tracks", {}).get(f.name, {})
        # [v2026.FIX] Verifica a flag whisper_done em vez de apenas o conteúdo da letra
        if not track_data.get("whisper_done") and not track_data.get("transcription") and not track_data.get("lyrics"):
            to_transcribe.append(f)
    
    if to_transcribe:
        dj_engine.transcribe_lot(to_transcribe)
    return jsonify({"success": True, "count": len(to_transcribe)})

    def curate_set_fast(self):
        """Versão instantânea com Auto-FX baseado em espectro."""
        logging.info("🚀 [AUTO-FX] Mapeando estrutura musical e agendando efeitos...")
        tracks = self.project_state.get("tracks", {})
        if not tracks: return []
        sorted_tracks = sorted(tracks.items(), key=lambda x: x[1].get('bpm', 120))
        sequence = []
        for i in range(len(sorted_tracks) - 1):
            name_a, data_a = sorted_tracks[i]
            name_b, data_b = sorted_tracks[i+1]
            fx_a = self._auto_schedule_fx(name_a, data_a)
            fx_b = self._auto_schedule_fx(name_b, data_b)
            bpm_diff = abs(data_a.get('bpm', 120) - data_b.get('bpm', 120))
            if bpm_diff < 3: t_type, dur = "acrossfade", 12
            elif bpm_diff < 7: t_type, dur = "filter_sweep", 8
            else: t_type, dur = "drop_cut", 4
            sequence.append({
                "track_a": name_a, "track_b": name_b,
                "transition": {
                    "type": t_type, "duration": dur, "target_bpm": data_b.get('bpm', 120),
                    "fx_a": fx_a, "fx_b": fx_b, "advice": "Auto-FX via Espectro"
                }
            })
        return sequence

@app.route('/api/scan_tracks', methods=['GET'])
def scan_tracks():
    if not dj_engine.source_dir: return jsonify({"error": "Projeto não iniciado"}), 400
    
    # [v2026.CPU_GUARD] Impede múltiplos workers de análise
    if dj_engine.worker_busy:
        logging.info("⏳ [GUARD] Fila ativa: Aguardando conclusão da tarefa anterior para evitar sobrecarga na CPU.")
        return jsonify({"success": True, "msg": "CPU Ocupada. A tarefa entrará na fila.", "count": 0})

    # [v2026.RELOAD] Força leitura do disco
    dj_engine.project_state = dj_engine.load_status()
    
    files = list(dj_engine.source_dir.glob("*"))
    audio_files = [f for f in files if f.suffix.lower() in ['.mp3', '.wav']]
    
    # [v2026.SMART] Verificação de upgrade v2026 robusta
    to_analyze = []
    for f in audio_files:
        track_data = dj_engine.project_state.get("tracks", {}).get(f.name, {})
        # Verifica se as chaves essenciais existem (mesmo que vazias)
        has_essential = all(k in track_data for k in ["bpm", "beats", "energy_map"])
        if not has_essential:
            to_analyze.append(f)
    
    if to_analyze:
        dj_engine.analyze_lot(to_analyze)
    
    metadata_batch = []
    for f_path in audio_files:
        meta = dj_engine.project_state["tracks"].get(f_path.name, {})
        metadata_batch.append({"name": f_path.name, **meta})
    return jsonify({"success": True, "metadata": metadata_batch, "count": len(to_analyze)})

@app.route('/api/curate_set', methods=['POST'])
def curate_set():
    # Agora usamos a curadoria instantânea por padrão (v2026.TURBO)
    setlist = dj_engine.curate_set_fast()
    dj_engine.project_state["setlist"] = setlist
    dj_engine.save_status()
    return jsonify({"success": True, "setlist": setlist})

@app.route('/api/ignite_mix', methods=['POST'])
def ignite_mix():
    data = request.json
    ordered_metadata = data.get('ordered_metadata', [])
    
    # [v2026.RESILIENCE] Se a lista veio vazia, tenta reconstruir do estado atual salvo no disco
    if not ordered_metadata:
        logging.warning("⚠️ ordered_metadata vazio. Tentando carregar do estado salvo...")
        current_state = dj_engine.load_status()
        saved_order = current_state.get("ordered_names", [])
        tracks = current_state.get("tracks", {})
        
        if saved_order:
            # Reconstroi o metadata baseado na ordem salva
            ordered_metadata = []
            for name in saved_order:
                if name in tracks:
                    ordered_metadata.append({"name": name, **tracks[name]})
        
        if not ordered_metadata and tracks:
            # Fallback se não tiver ordem salva: usa BPM
            ordered_metadata = [{"name": name, **meta} for name, meta in tracks.items()]
            ordered_metadata.sort(key=lambda x: x.get('bpm', 120))
        
        if not ordered_metadata:
            return jsonify({"error": "Sem músicas analisadas para mixar. Faça o Scan Técnico primeiro."}), 400

    # [v2026.CPU_GUARD] Bloqueia se o Worker está fisicamente ocupado
    if dj_engine.worker_busy:
        return jsonify({
            "error": "CPU Ocupada.", 
            "details": "Aguarde o Scan Técnico terminar para liberar a CPU para a Gemma."
        }), 429

    # [v2026.CPU_GUARD] Verifica se todas as análises terminaram antes de chamar a IA
    # [v2026.FIX] Agora aceita músicas com whisper_done mesmo sem lyrics
    pending_analysis = []
    for m in ordered_metadata:
        has_energy = m.get('energy_map')
        has_text = m.get('transcription') or m.get('lyrics') or m.get('whisper_done')
        if not has_energy or not has_text:
            pending_analysis.append(m['name'])
            
    if pending_analysis:
        logging.warning(f"⏳ [GUARD] Aguardando análise de {len(pending_analysis)} trilhas: {pending_analysis}")
        return jsonify({
            "error": "Aguarde o Scan Técnico terminar.", 
            "details": f"Ainda analisando: {', '.join(pending_analysis[:3])}..."
        }), 429

    full_setlist = []
    # [v2026.GUARD] Filtra entradas nulas ou corrompidas e garante caminhos como Strings
    valid_metadata = [m for m in ordered_metadata if m and isinstance(m, dict) and 'name' in m]
    
    for m in valid_metadata:
        # Converte para string explicitamente para evitar erro de WindowsPath no JSON
        m['path'] = str(dj_engine.source_dir / m['name'])

    if not valid_metadata:
        return jsonify({"error": "Nenhuma trilha válida para mixagem."}), 400

    # [v2026.MASTER_PLAN] Planeja as transições em LOTES para evitar estouro de tokens (Gemma 4k limit)
    master_plan = dj_engine.project_state.get("master_plan", [])
    if not master_plan:
        logging.info(f"🧠 [VORTEX] Criando Plano de Mixagem para {len(valid_metadata)} trilhas em lotes...")
        
        # [v2026.BATCH] Processa de 5 em 5 músicas para garantir segurança de tokens
        batch_size = 5
        for i in range(0, len(valid_metadata) - 1, batch_size - 1):
            batch = valid_metadata[i : i + batch_size]
            if len(batch) < 2: break
            
            logging.info(f"   > Planejando lote: {i} até {i + len(batch) - 1}")
            try:
                # Chama a IA para este lote específico
                batch_plan = core.maestro_master_planner(batch)
                
                # Ajusta os IDs do plano do lote para a escala global
                for item in batch_plan:
                    if 'id' in item:
                        item['id'] += i
                
                master_plan.extend(batch_plan)
            except Exception as e:
                logging.error(f"⚠️ Erro ao planejar lote {i}: {e}")
        
        # Remove duplicatas de ID (caso o slide window repita o último)
        seen_ids = set()
        final_plan = []
        for p in master_plan:
            if p['id'] not in seen_ids:
                final_plan.append(p)
                seen_ids.add(p['id'])
        
        master_plan = final_plan
        dj_engine.project_state["master_plan"] = master_plan
        dj_engine.save_status()
    
    # [v2026.ASYNC] Dispara a mixagem em segundo plano e libera a UI imediatamente
    dj_engine.ignite_mix_lot(valid_metadata)
    
    return jsonify({
        "success": True, 
        "msg": "Mixagem iniciada em segundo plano.",
        "project": str(dj_engine.current_project_dir)
    })

@app.route('/api/stop_job', methods=['POST'])
def stop_job():
    dj_engine.project_state["current_task"] = ""
    dj_engine.project_state["worker_busy"] = False
    
    if dj_engine.active_process:
        try:
            dj_engine.active_process.kill()
            logging.warning("🛑 PROCESSO FFMPEG INTERROMPIDO PELO USUÁRIO.")
        except: pass
        dj_engine.active_process = None
        
    dj_engine.stop_current_worker()
    
    # Limpa resíduos do disco imediatamente
    status = dj_engine.load_status()
    status["current_task"] = None
    status.setdefault("logs", []).append("🛑 OPERAÇÃO ABORTADA PELO USUÁRIO (STATUS LIMPO).")
    dj_engine.project_state = status
    dj_engine.save_status()
    dj_engine.worker_busy = False

    return jsonify({"success": True, "msg": "Processos interrompidos e status resetado."})

# =========================================================================
# VORTEX WORKERS CONSOLIDADOS (Isolamento de Processo Sem Arquivos Soltos)
# =========================================================================

def run_transcription(files_json_path, project_status_path):
    """Worker de Transcrição Whisper integrado."""
    from faster_whisper import WhisperModel
    import json
    import sys
    from pathlib import Path
    import logging
    import time
    from datetime import datetime
    
    logging.basicConfig(level=logging.INFO)
    
    with open(files_json_path, 'r') as f:
        files = json.load(f)
    
    if not files:
        logging.info("ℹ️ [WORKER] Lista vazia. Nada para transcrever.")
        return
    
    if not Path(project_status_path).exists():
        logging.warning(f"⚠️ [WORKER] Arquivo {project_status_path} não encontrado. Criando novo...")
        status = {"tracks": {}, "completed_mixes": []}
    else:
        with open(project_status_path, 'r') as f:
            status = json.load(f)

    logging.info(f"⚡ [FASTER-WHISPER] Ignorando CPU e ativando núcleos CUDA (RTX 3050)...")
    import os
    num_threads = os.cpu_count() or 4
    model = WhisperModel("base", device="cuda", compute_type="float16", cpu_threads=num_threads, num_workers=2)
    
    total_files = len(files)
    logging.info(f"🚀 [WHISPER] Iniciando processamento ultra-rápido de {total_files} segmentos...")

    for i, f_path in enumerate(files, 1):
        path = Path(f_path)
        name = path.name
        
        lyrics = ""
        try:
            segments, info = model.transcribe(str(path), beam_size=1, vad_filter=True)
            lyrics = " ".join([s.text for s in segments])
        except Exception as e:
            logging.error(f"Erro no Whisper para {name}: {e}")

        if name not in status["tracks"]: status["tracks"][name] = {}
        status["tracks"][name]["lyrics"] = lyrics
        status["tracks"][name]["whisper_done"] = True
        
        if i % 10 == 0 or i == total_files:
            time_str = datetime.now().strftime("%H:%M:%S")
            msg = f"[{time_str}] 🎙️ [{i}/{total_files}] Dublando... (Último: {name})"
            status["current_task"] = msg
            status.setdefault("logs", []).append(msg)
            
            if Path(project_status_path).exists():
                try:
                    with open(project_status_path, 'r') as f_check:
                        live_status = json.load(f_check)
                        status["completed_mixes"] = live_status.get("completed_mixes", [])
                except: pass

            with open(project_status_path, 'w') as f:
                json.dump(status, f, indent=4)
            logging.info(msg)

    if Path(project_status_path).exists():
        with open(project_status_path, 'r') as f: status = json.load(f)
        status["current_task"] = None
        status.setdefault("logs", []).append("✅ [WHISPER] Transcrição concluída.")
        with open(project_status_path, 'w') as f: json.dump(status, f, indent=4)

    logging.info("✅ [FASTER-WHISPER] Transcrição concluída. Liberando RAM.")
    # [v2026.VRAM_SWEEPER] Força a limpeza e devolução imediata da VRAM da RTX
    try:
        import torch
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except:
        pass


def run_analysis(files_json_path, project_status_path):
    """Worker de Análise Librosa integrado."""
    import librosa
    import numpy as np
    import json
    import sys
    from pathlib import Path
    import logging
    import time
    from datetime import datetime
    
    logging.basicConfig(level=logging.INFO)
    
    with open(files_json_path, 'r') as f:
        files = json.load(f)
        
    if not files:
        logging.info("ℹ️ [WORKER] Lista vazia. Nada para analisar.")
        return
    
    if not Path(project_status_path).exists():
        logging.warning(f"⚠️ [WORKER] Arquivo {project_status_path} não encontrado. Criando novo...")
        status = {"tracks": {}, "completed_mixes": [], "logs": []}
    else:
        with open(project_status_path, 'r') as f:
            status = json.load(f)
        if "logs" not in status: status["logs"] = []

    total_files = len(files)
    for i, f_path in enumerate(files, 1):
        name = Path(f_path).name
        start_t = time.time()
        time_str = datetime.now().strftime("%H:%M:%S")
        
        existing = status.get("tracks", {}).get(name, {})
        if all(k in existing for k in ["bpm", "key", "energy", "energy_map", "beats"]):
            logging.info(f"⏩ [SKIP] {name} já analisado.")
            continue

        msg_start = f"[{time_str}] 🔬 [{i}/{total_files}] Analisando técnica: {name} (Librosa)"
        status["current_task"] = msg_start
        status.setdefault("logs", []).append(f"> {msg_start}")
        with open(project_status_path, 'w') as f:
            json.dump(status, f, indent=4)
        
        try:
            logging.info(f"🔬 [ANALYSIS] Escaneando: {name}")
            y, sr = librosa.load(f_path, sr=44100)
            
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            bpm = float(tempo[0]) if isinstance(tempo, np.ndarray) else float(tempo)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
            
            rms = librosa.feature.rms(y=y)[0]
            chunks = np.array_split(rms, 10)
            energy_map = [round(float(np.mean(c)), 4) for c in chunks]
            
            S = np.abs(librosa.stft(y))
            vocal_presence = [round(float(np.mean(librosa.feature.spectral_centroid(S=S[:, j:j+100], sr=sr))), 2) for j in range(0, S.shape[1], 100)]
            
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            key_idx = np.argmax(np.mean(chroma, axis=1))
            keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            key_name = keys[key_idx]
            
            spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
            brightness = np.mean(spec_centroid)

            if name not in status["tracks"]: status["tracks"][name] = {}
            status["tracks"][name].update({
                "bpm": round(bpm, 2),
                "key": key_name,
                "energy": round(float(np.mean(rms)), 4),
                "energy_map": energy_map,
                "vocal_map": vocal_presence[:10],
                "brightness": round(float(brightness), 2),
                "duration": float(librosa.get_duration(y=y, sr=sr)),
                "beats": beat_times[:40],
                "first_beat": beat_times[0] if beat_times else 0
            })
            
            elapsed = round(time.time() - start_t, 1)
            msg_end = f"✅ [{i}/{total_files}] {name} analisado em {elapsed}s."
            status.setdefault("logs", []).append(msg_end)
            logging.info(msg_end)
            
        except Exception as e:
            logging.error(f"❌ Erro ao analisar {name}: {e}")
            status.setdefault("logs", []).append(f"ERRO: {name} ({str(e)})")
        
        with open(project_status_path, 'w') as f:
            json.dump(status, f, indent=4)

    if Path(project_status_path).exists():
        with open(project_status_path, 'r') as f: status = json.load(f)
        status["current_task"] = None
        status.setdefault("logs", []).append("🏁 [ANALYSIS] Scan técnico concluído.")
        with open(project_status_path, 'w') as f: json.dump(status, f, indent=4)

    logging.info("✅ [ANALYSIS WORKER] Tarefa concluída. Encerrando processo.")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "--worker-whisper":
            run_transcription(sys.argv[2], sys.argv[3])
            sys.exit(0)
        elif sys.argv[1] == "--worker-analysis":
            run_analysis(sys.argv[2], sys.argv[3])
            sys.exit(0)

    # [v2026.STABLE] Desativado reloader para evitar crash do SpeechBrain (k2)
    app.run(host="127.0.0.1", port=5005, debug=False, use_reloader=False)
