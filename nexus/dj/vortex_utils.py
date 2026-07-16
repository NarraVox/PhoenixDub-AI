# -*- coding: utf-8 -*-
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

import os
import sys
import subprocess
import json
import logging
import time
import re
import shutil
import random
import threading
from pathlib import Path
import torch
import gc
import soundfile as sf
import numpy as np
import nexus.core as core

try:
    import mixingbear
    MIXINGBEAR_AVAILABLE = True
except ImportError:
    MIXINGBEAR_AVAILABLE = False

try:
    from audiosr import build_model, super_resolution
    AUDIOSR_AVAILABLE = True
except ImportError:
    AUDIOSR_AVAILABLE = False

def process_upscale_logic(input_path, output_path, ddim_steps=25, guidance_scale=3.5, progress_callback=None, upload_folder=None):
    if not AUDIOSR_AVAILABLE:
        logging.error("[ERR] [AudioSR] Biblioteca AudioSR não instalada.")
        raise ImportError("AudioSR não está instalado.")

    logging.info(f"[*] [AudioSR] Iniciando super-resolução de áudio fatiada: {input_path}")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # 1. Carrega o áudio de entrada
    try:
        audio_data, sr = sf.read(str(input_path))
    except Exception as e:
        logging.error(f"[ERR] [AudioSR] Falha ao ler áudio de entrada: {e}")
        raise e
        
    if len(audio_data.shape) > 1:
        audio_data = audio_data[:, 0]  # usa o canal mono se for estéreo
        
    total_samples = len(audio_data)
    duration_s = total_samples / sr
    logging.info(f"[INFO] [AudioSR] Áudio carregado: {duration_s:.2f}s | Sample Rate: {sr}Hz | Amostras: {total_samples}")
    
    # 2. Carrega o modelo AudioSR
    model = build_model(model_name="basic", device=device)
    
    if device == "cuda" and torch.cuda.is_bf16_supported():
        logging.info("[AudioSR] GPU suporta BFloat16. Convertendo U-Net (model.model) para BFloat16...")
        model.model = model.model.bfloat16()
        
        # Monkeypatch para forçar o Vocoder a processar e retornar Float32 antes de converter para numpy
        import types
        def safe_mel_to_wave(self_model, mel, savepath=".", bs=None, name="outwav", save=True):
            if len(mel.size()) == 4:
                mel = mel.squeeze(1)
            mel = mel.permute(0, 2, 1)
            waveform = self_model.first_stage_model.vocoder(mel)
            waveform = waveform.float()  # Garante conversão de BF16 para Float32 para evitar erros no NumPy
            waveform = waveform.cpu().detach().numpy()
            if save:
                self_model.save_waveform(waveform, savepath, name)
            return waveform
            
        model.mel_spectrogram_to_waveform = types.MethodType(safe_mel_to_wave, model)
        logging.info("[AudioSR] Monkeypatch seguro de BFloat16 aplicado com sucesso.")
    
    # 3. Configura parâmetros de chunking
    chunk_len_s = 10.0
    overlap_len_s = 1.0
    
    chunk_samples = int(chunk_len_s * sr)
    overlap_samples = int(overlap_len_s * sr)
    stride_samples = chunk_samples - overlap_samples
    
    sr_out = 48000
    chunk_samples_out = int(chunk_len_s * sr_out)
    overlap_samples_out = int(overlap_len_s * sr_out)
    stride_samples_out = chunk_samples_out - overlap_samples_out
    
    # Prepara vetor de saída estimado
    total_duration_out_samples = int(duration_s * sr_out) + 48000  # margem de segurança
    output_audio = np.zeros(total_duration_out_samples, dtype=np.float32)
    output_samples_written = 0
    
    # Cria um arquivo temporário exclusivo
    temp_chunk_in = Path(os.environ.get("NEXUS_TEMP", upload_folder or ".")) / f"temp_chunk_upscale_{int(time.time())}.wav"
    
    # Calcula a quantidade total de blocos para exibição de progresso
    total_blocks = 0
    temp_start = 0
    while temp_start < total_samples:
        temp_end = temp_start + chunk_samples
        if temp_end > total_samples:
            temp_end = total_samples
        actual_len = temp_end - temp_start
        if actual_len < sr * 1.0 and total_blocks > 0:
            break
        total_blocks += 1
        temp_start += stride_samples
        
    i = 0
    start_sample = 0
    
    try:
        with torch.no_grad():
            while start_sample < total_samples:
                end_sample = start_sample + chunk_samples
                if end_sample > total_samples:
                    end_sample = total_samples
                    
                chunk_data = audio_data[start_sample:end_sample]
                actual_chunk_len = len(chunk_data)
                if actual_chunk_len < sr * 1.0 and i > 0:
                    break
                    
                # Se for o último bloco e for menor que chunk_samples, fazemos padding com silêncio
                # para garantir que o AudioSR sempre processe blocos de tamanho idêntico de 10s.
                padded = False
                if actual_chunk_len < chunk_samples:
                    padded_chunk = np.zeros(chunk_samples, dtype=chunk_data.dtype)
                    padded_chunk[0:actual_chunk_len] = chunk_data
                    chunk_data = padded_chunk
                    padded = True
                    
                logging.info(f"[~] [AudioSR] Processando bloco {i}: {start_sample/sr:.1f}s até {end_sample/sr:.1f}s... (Total: {total_blocks})")
                if progress_callback:
                    progress_callback(i + 1, total_blocks)
                
                # Grava chunk temporário de entrada
                sf.write(str(temp_chunk_in), chunk_data, sr)
                
                # Roda super_resolution com AMP (BFloat16 se suportado, senão FP16)
                use_bf16 = (device == "cuda" and torch.cuda.is_bf16_supported())
                autocast_dtype = torch.bfloat16 if use_bf16 else torch.float16
                with torch.amp.autocast(device_type=device, dtype=autocast_dtype, enabled=(device == "cuda")):
                    waveform = super_resolution(
                        model, 
                        str(temp_chunk_in), 
                        seed=42, 
                        ddim_steps=ddim_steps, 
                        guidance_scale=guidance_scale
                    )
                
                chunk_out = waveform[0, 0] # mono
                
                # Converte float16 do AMP para float32 para compatibilidade com numpy e soundfile
                if chunk_out.dtype == np.float16 or str(chunk_out.dtype) == 'float16':
                    chunk_out = chunk_out.astype(np.float32)
                
                # Se foi feito padding, cortamos o excesso correspondente de silêncio do resultado
                if padded:
                    actual_chunk_len_out = int((actual_chunk_len / sr) * sr_out)
                    chunk_out = chunk_out[0:actual_chunk_len_out]
                    
                chunk_out_len = len(chunk_out)
                
                # Mescla no vetor final
                if i == 0:
                    output_audio[0:chunk_out_len] = chunk_out
                    output_samples_written = chunk_out_len
                else:
                    overlap_start = i * stride_samples_out
                    overlap_end = overlap_start + overlap_samples_out
                    
                    # Crossfade linear na zona de overlap
                    for t in range(overlap_samples_out):
                        if overlap_start + t < len(output_audio) and t < chunk_out_len:
                            weight = t / overlap_samples_out
                            output_audio[overlap_start + t] = (1.0 - weight) * output_audio[overlap_start + t] + weight * chunk_out[t]
                            
                    # Copia o resto do chunk
                    remaining_samples = chunk_out_len - overlap_samples_out
                    if remaining_samples > 0:
                        start_dest = overlap_end
                        end_dest = start_dest + remaining_samples
                        output_audio[start_dest:end_dest] = chunk_out[overlap_samples_out:chunk_out_len]
                        output_samples_written = end_dest
                        
                start_sample += stride_samples
                i += 1
                
                # Liberação de VRAM intra-loop
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    
        # Trunca o áudio de saída
        output_audio_final = output_audio[0:output_samples_written]
        
        # Converte para estéreo
        audio_stereo = np.stack([output_audio_final, output_audio_final], axis=-1)
        
        # Salva o arquivo final WAV
        sf.write(str(output_path), audio_stereo, sr_out)
        logging.info(f"[SUCCESS] [AudioSR] Super-resolução chunked concluída! Salvo em: {output_path}")
        
    except Exception as e:
        logging.error(f"[ERR] [AudioSR] Erro no processamento do chunked upscale: {e}")
        raise e
    finally:
        if temp_chunk_in.exists():
            try: os.remove(temp_chunk_in)
            except: pass
        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def separate_stems_logic(self, track_path):
    """Separação Neural via OpenUnmix."""
    track_path = Path(track_path)
    vocal_mp3 = self.stems_dir / f"{track_path.stem}_vocals.mp3"
    instr_mp3 = self.stems_dir / f"{track_path.stem}_instrumental.mp3"
    
    # [v2026.CACHE] Retorna se os MP3s já estiverem prontos no disco
    if vocal_mp3.exists() and instr_mp3.exists():
        return self.stems_dir / track_path.stem
    
    # [v2026.PRE_FLIGHT_PURGE] Limpeza preventiva de VRAM
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # Detecta se CUDA está disponível para o OpenUnmix
    device = "cuda" if torch.cuda.is_available() else "cpu"

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
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return self.stems_dir / track_path.stem

def mix_tracks_professional_logic(self, track_a_data, track_b_data, output_name, custom_output=None):
    """Motor de Mixagem Super Mix 2.0 (4-Channel Remix Engine)."""
    upload_folder = Path("C:/IA_dublagem/uploads")
    output_path = custom_output if custom_output else upload_folder / output_name
    
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
