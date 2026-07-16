# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import re
import logging
import json
from pathlib import Path
import numpy as np
import librosa

# Runtime globals injected by __init__.py namespace patching:
# load_game_profile, make_gema_request_with_retries, clean_ai_translation
# get_whisper_model, sanitize_tts_text, smart_whisper_trim

def select_best_sync_option(original_duration, options_list, original_text):
    best_opt = None
    best_score = float('inf')
    target_rate = 16.0
    
    valid_options = [opt.strip() for opt in options_list if opt and len(opt.strip()) > 0]
    if not valid_options: return None

    logging.info(f"Avaliando {len(valid_options)} candidatos para duração {round(original_duration, 2)}s...")

    for opt in valid_options:
        clean_opt = re.sub(r'^\d+[\.\-\)]\s*', '', opt).strip('"').strip()
        if not clean_opt: continue
        clean_opt = re.sub(r',+', ',', clean_opt)
        clean_opt = re.sub(r'[\.,;]+$', '', clean_opt)
        
        commas_count = clean_opt.rstrip(',').count(',')
        comma_time_cost = commas_count * 0.5
        text_only = re.sub(r'[,]', '', clean_opt)
        effective_char_count = len(text_only)
        
        estimated_time = (effective_char_count / target_rate) + comma_time_cost
        score = abs(estimated_time - original_duration)
        
        cps_letters = effective_char_count / (original_duration - comma_time_cost) if (original_duration - comma_time_cost) > 0.1 else 99
        if cps_letters > 22:
             score += (cps_letters - 22) * 5.0

        if original_duration < 1.2:
            words = clean_opt.split()
            if len(words) < 2 and len(original_text.split()) > 1:
                score += 50 
            if len(words) >= 2:
                score -= 5

        e_t_f = round(estimated_time, 2)
        sc_f = round(score, 2)
        logging.info(f"   - Candidato: '{clean_opt}' | Est.Time: {e_t_f}s | Score: {sc_f}")

        if score < best_score:
            best_score = score
            best_opt = clean_opt
            
    return best_opt


def trim_repetitions_to_fit(text, max_chars):
    if len(text) <= max_chars:
        return text
        
    words = text.split()
    
    for pat_len in range(1, 6):
        i = 0
        while i < len(words) - 2 * pat_len:
            pattern = words[i:i+pat_len]
            repeat_count = 1
            j = i + pat_len
            while j <= len(words) - pat_len:
                next_pattern = words[j:j+pat_len]
                pat_clean = [re.sub(r'[^\w]', '', w).lower() for w in pattern]
                next_clean = [re.sub(r'[^\w]', '', w).lower() for w in next_pattern]
                if pat_clean == next_clean:
                    repeat_count += 1
                    j += pat_len
                else:
                    break
            
            if repeat_count > 1:
                best_k = 1
                for k in range(1, repeat_count + 1):
                    candidate = " ".join(words[:i] + pattern * k + words[j:])
                    if len(candidate) <= max_chars:
                        best_k = k
                    else:
                        break
                
                words = words[:i] + pattern * best_k + words[j:]
                i += pat_len * best_k
            else:
                i += 1
            
    return " ".join(words)


def apply_string_fallback(text, max_chars):
    text = trim_repetitions_to_fit(text, max_chars)
    if len(text) <= max_chars: return text
    
    words = text.split()
    new_words = [w for w in words if not w.lower().endswith('mente')]
    new_text = " ".join(new_words)
    if len(new_text) <= max_chars: return new_text
    
    blacklist = ['o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'do', 'da', 'dos', 'das', 'no', 'na', 'nos', 'nas']
    new_words = [w for w in new_words if w.lower() not in blacklist]
    return " ".join(new_words)


def gema_etapa_2_sincronizacao(original_text, duration, previous_context=None, profile_id='padrao'):
    profile = load_game_profile(profile_id)
    lore_text = profile.get("lore", "Gênero: Jogo de Aventura/Ação (Autodetecção Ativada)")
    target_chars = int(duration * 16)
    temperature = 0.2
    
    prompt = f'''
# DIRETRIZES DE DUBLAGEM INDIVIDUAL (MASTER SYNC)
 
[TAREFA]: Traduza e SINCRONIZE a frase abaixo mantendo a "vibe" do jogo.
 
[CONTRATO DE SINCRONIA]:
- LIMITE DE TEMPO: {round(duration, 2)} segundos.
- CALCULO: (Letras / 16) + (Virgulas Internas * 0.5) <= {round(duration, 2)}s.
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
        
        quoted_match = re.search(r'"(.*?)"', content, re.DOTALL)
        if quoted_match:
             final_text = quoted_match.group(1).strip()
             return apply_string_fallback(final_text, target_chars or 999), 1
        
        return apply_string_fallback(original_text, target_chars or 999), 2
    except Exception as e:
        logging.error(f"Erro no Fallback Sync Gema: {e}")
        return original_text, 2


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


def gema_lqa_reviewer_pro(original_en, candidate_pt, duration):
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
Se a opcao candidata ja for perfeita, apenas repita-a entre aspas duplas.
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
        return candidate_pt
    except:
        return candidate_pt


def nexus_lqa_validator(audio_path, original_duration, file_id, job_dir, mode='technical', expected_text=None):
    if not audio_path or not Path(audio_path).exists():
        return "ERRO", "Arquivo não encontrado.", True

    try:
        y, sr = librosa.load(str(audio_path), sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        
        status = "OK"
        warnings = []
        needs_action = False

        is_safe_duration = (duration > 0.1) and (original_duration > 0.5 and (duration / original_duration) > 0.2)
        ratio = duration / original_duration if original_duration > 0 else 1.0

        if original_duration > 0 and not is_safe_duration:
            if ratio < 0.70:
                status = "AVISO"
                warnings.append(f"Corte de Tempo ({ratio:.2%})")
                needs_action = False 
            elif ratio < 0.85:
                status = "AVISO"
                warnings.append(f"Fala Acelerada ({ratio:.2%})")
            
            MAX_ALLOWED = (original_duration * 1.30) + 0.5
            if duration > MAX_ALLOWED:
                trimmed = smart_whisper_trim(audio_path, expected_text)
                if trimmed:
                    y, sr = librosa.load(str(audio_path), sr=None)
                    duration = librosa.get_duration(y=y, sr=sr)
                
                if duration > MAX_ALLOWED:
                    status = "AVISO"
                    diff = duration - original_duration
                    warnings.append(f"Estouro Aceito (+{diff:.2f}s)")
                    needs_action = False

        rms = np.sqrt(np.mean(y**2))
        db_rms = 20 * np.log10(rms) if rms > 0 else -100
        
        if db_rms < -60:
            status = "ERRO"
            warnings.append("Silêncio Excessivo")
            if mode == 'raw': needs_action = True
        elif mode == 'technical' and db_rms < -28:
            status = "ATENÇÃO"
            warnings.append(f"Volume Baixo ({db_rms:.1f}dB)")
            needs_action = True
        elif mode == 'raw' and db_rms < -45:
             status = "ATENÇÃO"
             warnings.append("Gerado com volume muito baixo")
             needs_action = True

        flatness = np.mean(librosa.feature.spectral_flatness(y=y))
        if flatness < 0.0001: 
             status = "AVISO"
             warnings.append("Alucinação de Loop")
             if mode == 'raw': needs_action = True

        if expected_text and (status != "OK" or ratio < 0.85):
            try:
                whisper_model = get_whisper_model()
                segments, _ = whisper_model.transcribe(str(audio_path), language="pt")
                heard_text = " ".join([s.text for s in segments]).strip().lower()
                clean_expected = expected_text.lower().replace(",", "").replace(".", "").replace("!", "").replace("?", "").strip()
                
                def clean_for_match(t):
                    return re.sub(r'[^a-záéíóúâêîôûãõç]', '', t.lower())
                
                pure_expected = clean_for_match(clean_expected)
                pure_heard = clean_for_match(heard_text)
                len_exp = len(pure_expected)
                len_heard = len(pure_heard)
                
                if len_heard == 0 and len_exp > 0:
                    status = "ERRO"
                    warnings.append(f"Silêncio Total (ASR Vazio) [Esp: '{clean_expected}']")
                    needs_action = True
                elif len_exp > 0:
                    char_ratio = len_heard / len_exp
                    if 0.80 <= char_ratio <= 1.3:
                        logging.info(f"🛡️ Nexus: Conteúdo INTEGRAL validado via ASR ({len_heard}/{len_exp}). Limpando alertas técnicos.")
                        status = "OK"
                        warnings = ["Conteúdo validado via ASR (100%)"]
                        needs_action = False
                    elif len_exp < 15 and 0.5 <= char_ratio <= 2.5:
                        logging.info(f"🛡️ Nexus: Frase Curta validada via ASR ({len_heard}/{len_exp}).")
                        status = "OK"
                        warnings.append(f"(Conteúdo validado | Esp: '{clean_expected}' | ASR: '{heard_text}')")
                        needs_action = False
                    elif char_ratio < 0.60 or char_ratio > 2.0:
                        status = "ERRO"
                        warnings.append(f"Falha Semântica (ASR: {char_ratio:.2%} | Esp: '{clean_expected}' | Ouvido: '{heard_text}')")
                        needs_action = True
            except Exception as e_asr:
                logging.warning(f"Falha na auditoria ASR para {file_id}: {e_asr}")

        return status, "; ".join(warnings) if warnings else "Perfeito", needs_action
    except Exception as e:
        return "ERRO", f"Falha na análise: {e}", False
