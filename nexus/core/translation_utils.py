# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import re
import logging
import json
import requests
from pathlib import Path

# Runtime globals injected by __init__.py namespace patching:
# ai_global_lock, get_gemma_model, get_local_gemma_engine, find_gemma_model_path, get_whisper_model

# Import standard vocal noises
vocal_noises = [
    "woo", "ehh", "huh", "woof", "ha", "ah", "oof", "oh", "wow", "sigh", "laughter", 
    "gasp", "pant", "snort", "sob", "groan", "screaming", "whispering", "crying", "ugh", 
    "cough", "yawn", "grr", "pff", "shh", "ts", "tsc", "hm", "hmm", "mhm", "uh", "um", 
    "eh", "aah", "ooh", "oops", "ops", "haha", "hehe", "hihi", "hoho", "phew", "brr", 
    "tsk", "aw", "ow", "ouch", "aww", "yay", "yayy", "yuck", "ew", "eww"
]

def detect_game_genre(segments):
    """
    [v12.18 CACHALEÃO] Identifica o gênero do jogo baseado nos diálogos iniciais.
    """
    if not segments: return "Ação (Geral)"
    sample_text = " / ".join([s['original_text'] for s in segments[:15]])
    
    prompt = f'''
Diga APENAS qual e o Genero deste jogo (Ex: 'Acao e Guerra', 'Corrida', 'RPG', 'Terror') baseado nas seguintes falas da cena:
"{sample_text}"
'''
    payload = {
        "messages": [{"role": "user", "content": prompt}], 
        "temperature": 0.1, 
        "max_tokens": 50
    }
    
    try:
        response = make_gema_request_with_retries(payload, is_translation=False)
        genre = response.json()['choices'][0]['message']['content'].strip().replace('"', "")
        if "Ação e Guerra" in genre or "Gênero deste jogo" in genre:
             genre = "Ação e Tiro"
        logging.info(f"🦎 [CAMALEÃO] Gênero detectado pela IA: {genre}")
        return genre
    except Exception as e:
        logging.warning(f"Aviso: Falha na deteção automática de gênero ({e}). Usando fallback 'Ação'.")
        return "Ação (Geral)"


def gerar_lore_global(segments, video_title=None):
    """
    [v2026.NARRATIVE_ENGINE] Analisa dinamicamente os primeiros segmentos (20% do vídeo, entre 20 e 50 segmentos)
    para criar um 'Dossiê de Lore' que guia a dublagem.
    """
    if not segments: return "Gênero: Desconhecido (Modo Padrão)"
    
    num_samples = max(20, min(50, int(len(segments) * 0.20)))
    sample_text = "\n".join([f"- [{s.get('speaker', 'desconhecido')}]: {s.get('text') or s.get('original_text', '')}" for s in segments[:num_samples]])
    
    video_title_header = ""
    if video_title:
        clean_title = video_title
        for ext in ['.mp4', '.avi', '.mkv', '.wav', '.mp3']:
            clean_title = clean_title.replace(ext, '')
        if clean_title.startswith('video_') and '__' in clean_title:
            parts = clean_title.split('__')
            clean_title = parts[0].replace('video_', '')
        clean_title = clean_title.replace('_', ' ').strip()
        video_title_header = f"TÍTULO DO ARQUIVO/PROJETO: {clean_title}\n\n"
        
    prompt = f"""
Você é um Especialista em Localização, Tradução de Mídia e Análise de Conteúdo.
Analise a transcrição da amostra do vídeo abaixo e crie um dossiê de Lore Global ultra-simplificado para guiar a dublagem de forma concisa e rápida.
Este vídeo pode ser de qualquer assunto (ex: jogos, filmes, tutoriais de programação, gameplays, vlogs, resenhas, etc.).

{video_title_header}REGRAS DE CONCISÃO E ESTABILIDADE (LEIA COM ATENÇÃO):
- NÃO invente ou assuma obras famosas, a menos que haja nomes próprios de personagens marcantes e exclusivos na transcrição.
- NÃO entre em loops de repetição de palavras ou frases.
- Seja extremamente objetivo, curto, direto e conciso. Resuma todo o dossiê em menos de 100 palavras no total.

Foque em detalhar exatamente estes 2 tópicos:

1. TOM DE VOZ E CATEGORIA GERAL:
(Descreva de forma muito breve o tom das falas e a categoria do vídeo. Ex: Diálogos casuais e irônicos de ficção científica; Tutorial de TI didático e calmo; Gameplay energético e espontâneo).

2. GÊNERO GRAMATICAL DE CADA LOCUTOR:
(Determine o gênero gramatical para concordância de adjetivos de cada voz que aparece na amostra. Ex: 'voz_9 -> Masculino', 'voz_6 -> Feminino', 'voz_2 -> Masculino').

TRANSCRIÇÃO DE AMOSTRA DO VÍDEO:
{sample_text}
"""
    payload = {
        "messages": [
            {
                "role": "system", 
                "content": "Você é um Diretor de Localização profissional. Crie um dossiê descritivo, prático e útil para a tradução e dublagem de vídeos. IMPORTANTE: Não use a tag <think> e responda diretamente sem raciocinar em voz alta (no-thinking)."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3, "max_tokens": 2048
    }
    
    try:
        response = make_gema_request_with_retries(payload, is_translation=False)
        lore = response.json()['choices'][0]['message']['content'].strip()
        lore = re.sub(r'<think>.*?</think>', '', lore, flags=re.DOTALL | re.IGNORECASE)
        for tag in ['<think>', '<thought>', '[thought]', '<|im_start|>thought']:
            if tag in lore.lower():
                idx = lore.lower().find(tag)
                lore = lore[:idx]
        lore = lore.strip()
        
        lines = lore.split('\n')
        clean_lines = []
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                clean_lines.append("")
                continue
            words = line_strip.split()
            if len(words) > 10:
                unique_words = set(w.lower().strip(',.?!()":;-') for w in words)
                if len(unique_words) / len(words) < 0.30:
                    logging.warning(f"⚠️ [LORE-SHIELD] Linha repetitiva detectada e removida da Lore Global.")
                    continue
            clean_lines.append(line)
        lore = "\n".join(clean_lines).strip()
        
        if not lore:
            lore = "Gênero: Narrativo (Contexto Geral)"
            
        logging.info(f"📜 [LORE GLOBAL] Contexto gerado pelo Gemma 4:\n{lore}")
        return lore
    except Exception as e:
        logging.error(f"Erro ao gerar a Lore Global: {e}")
        return "Gênero: Narrativo (Contexto Automático)"


def gema_inference(prompt, system_prompt="Você é um tradutor profissional.", model_type="gema"):
    """
    Tenta Local GGUF -> Se falhar ou não existir, tenta LM Studio.
    """
    with ai_global_lock:
        local_gema = get_gemma_model()
        if local_gema and local_gema != "standalone_server":
            try:
                full_prompt = f"<start_of_turn>user\n{system_prompt}\n\n{prompt}<end_of_turn>\n<start_of_turn>model\n"
                response = local_gema(
                    full_prompt,
                    max_tokens=256,
                    temperature=0.3,
                    stop=["<end_of_turn>"]
                )
                return response['choices'][0]['text']
            except Exception as e:
                logging.error(f"Erro na geração nativa (llama.cpp): {e}")

        urls = [
            "http://127.0.0.1:8080/v1/completions",
            "http://127.0.0.1:1234/v1/completions"
        ]
        full_prompt = f"<start_of_turn>user\n{system_prompt}\n\n{prompt}<end_of_turn>\n<start_of_turn>model\n"
        for url in urls:
            try:
                payload = {
                    "prompt": full_prompt,
                    "temperature": 0.3,
                    "max_tokens": 512,
                    "model": "local-model",
                    "stop": ["<end_of_turn>"]
                }
                res = requests.post(url, json=payload, timeout=600)
                if res.status_code == 200:
                    return res.json()['choices'][0]['text']
            except:
                continue

    return "ERRO: IA não disponível (LM Studio ou Super Motor offline)."


def should_strip_prefix(prefix_str, original_text, segment_id=None):
    """
    Decide if a matched prefix (like '12:', 'seg_11:', '1.') is a hallucinated index
    that should be stripped, or if it represents a valid part of the translation (like call signs '1-2', '01').
    """
    if not prefix_str:
        return False
    prefix_nums = re.findall(r'\d+', prefix_str)
    if not prefix_nums:
        return True
        
    orig_lower = original_text.lower() if original_text else ""
    num_words = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
    has_orig_num = any(char.isdigit() for char in original_text) if original_text else False
    if not has_orig_num and original_text:
        has_orig_num = any(w in orig_lower for w in num_words)
    
    if not has_orig_num:
        return True
        
    seg_num = None
    if segment_id:
        seg_num_match = re.search(r'\d+', str(segment_id))
        if seg_num_match:
            seg_num = int(seg_num_match.group())
            
    for num_str in prefix_nums:
        num_val = int(num_str)
        if seg_num is not None:
            if num_val in (seg_num, seg_num + 1, seg_num - 1):
                return True
                
        num_word_map = {
            0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
            6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"
        }
        word = num_word_map.get(num_val, "")
        digit = str(num_val)
        
        if (digit not in original_text) and (not word or word not in orig_lower):
            return True
            
    return False


def is_hallucinated_number_translation(translated_text, original_text):
    """
    Returns True if the translation is a hallucinated number/duration (like "15", "14.65 segundos")
    but the original English text has no numbers or digits.
    """
    if not translated_text:
        return False
    t_clean = translated_text.strip().lower()
    if not t_clean:
        return False
        
    orig_lower = original_text.lower() if original_text else ""
    has_orig_num = any(char.isdigit() for char in original_text) if original_text else False
    if not has_orig_num and original_text:
        num_keywords = [
            "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
            "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
            "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand",
            "second", "seconds", "sec", "minute", "minutes", "min", "hour", "hours", "time",
            "char", "character", "characters", "letter", "letters", "limit", "phrase", "word", "words"
        ]
        has_orig_num = any(w in orig_lower for w in num_keywords)
        

    if not has_orig_num:
        if re.search(r'\b\d{2}:\d{2}\b', t_clean) or '--' in t_clean or '-->' in t_clean:
            return True
        meta_indicators = ["segundo", "segundos", "caractere", "caracteres", "chars", "char", "limite", "frase", "letras", "letra"]
        has_meta_word = any(w in t_clean for w in meta_indicators)
        if has_meta_word and any(char.isdigit() for char in t_clean):
            return True

    if has_orig_num:
        return False
        
    t_stripped = re.sub(r'(?:segundos|segundo|caracteres|caractere|chars|char|letras|letra|seg)\b', '', t_clean)
    t_stripped = re.sub(r'[^\w\s]', '', t_stripped).strip()
    
    if not t_stripped:
        return True
    if t_stripped.isdigit():
        return True
        
    return False


def is_loop_hallucination(translated_text, original_text):
    """
    [v2026.LOOP_SHIELD] Detecta alucinações em loop ou repetição infinita de palavras/frases
    que não existiam no texto original em inglês.
    """
    if not translated_text or not original_text:
        return False
        
    words_trans = translated_text.split()
    words_orig = original_text.split()
    
    len_trans = len(words_trans)
    len_orig = len(words_orig)
    
    if len_orig >= 3 and len_trans > 25 and len_trans > 2.5 * len_orig:
        return True
    if len_orig >= 10 and len_trans > 50 and len_trans > 2.0 * len_orig:
        return True

    def get_max_repeat_count(text):
        max_count = 0
        for length in range(6, 20):
            for i in range(len(text) - 2 * length):
                sub = text[i:i+length]
                if not sub.strip() or len(sub.strip()) < 4:
                    continue
                count = text.count(sub)
                if count > max_count:
                    max_count = count
        return max_count

    max_repeat_trans = get_max_repeat_count(translated_text.lower())
    if max_repeat_trans >= 5:
        max_repeat_orig = get_max_repeat_count(original_text.lower())
        if max_repeat_trans > 2.5 * max(1, max_repeat_orig):
            return True
            
    return False


def clean_ai_translation(text, original_text, segment_id=None):
    """
    [v21.0 SCRUBBER DE PENSAMENTO] 
    Limpa blocos de raciocínio interno da Gema 4 / Qwen antes de extrair a tradução.
    """
    if not text: return ""
    if is_hallucinated_number_translation(text, original_text):
        return ""
    if is_loop_hallucination(text, original_text):
        return ""
    
    if re.search(r'[\u4e00-\u9fff]', text):
        return ""
        
    def strip_prefix_if_needed(match):
        matched_str = match.group(0)
        if should_strip_prefix(matched_str, original_text, segment_id):
            return ""
        return matched_str
        
    text = re.sub(r'^(?:seg[-_]?\d+|\d+)\s*(?:[:.,]|-(?!\d))\s*|^(?:seg[-_]?\d+|\d+)\s+', strip_prefix_if_needed, text.strip(), flags=re.IGNORECASE)
    
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<\|channel\|?>thought.*?<channel\|?>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'\[THOUGHT\].*?\[/THOUGHT\]', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    for tag in ['<think>', '<thought>', '[thought]', '<|im_start|>thought']:
        if tag in text.lower():
            idx = text.lower().find(tag)
            text = text[:idx]
            
    text = text.strip()
    
    text_check = text.strip().strip('"').strip('<>').strip().lower()
    if text_check in ["tradução final adaptada", "traducao final adaptada", "translation", "think", "thought"]:
        return ""

    # [v2026.QUOTE_STRIPPER_FIX] Corrige bug que descartava a maior parte da frase caso ela contivesse aspas internas (como diálogo/citação).
    # Apenas remove as aspas se elas envolverem a string inteira.
    t_clean = text.strip()
    if (t_clean.startswith('"') and t_clean.endswith('"')) or (t_clean.startswith("'") and t_clean.endswith("'")):
        if len(t_clean) >= 2:
            t_clean = t_clean[1:-1].strip()
            
    t = t_clean
    t = re.sub(r'\(Limite:.*?\)', '', t).strip()
    
    # Se a tradução final ficou idêntica ao original em inglês, rejeita para forçar a contingência
    orig = original_text.strip().strip('"').strip("'").lower() if original_text else ""
    t_limpo = re.sub(r'[^\w\s]', '', t.lower())
    orig_limpo = re.sub(r'[^\w\s]', '', orig)
    if orig_limpo and t_limpo == orig_limpo:
        return ""

    orig = original_text.strip().strip('"') if original_text else ""
    separadores = [" -> ", " => ", " : ", " - "]
    
    for sep in separadores:
        if sep in t:
            parts = t.split(sep)
            primeira_parte = parts[0].strip().strip('"').lower()
            if orig and (orig.lower() in primeira_parte or primeira_parte in orig.lower()):
                return parts[-1].strip().strip('"')
            if len(parts) > 1:
                return parts[-1].strip().strip('"')

    if orig and t.lower().startswith(orig.lower()):
        rest = t[len(orig):].strip()
        rest = re.sub(r'^[:\-= \t>]+', '', rest).strip().strip('"')
        if rest: return rest

    t = re.sub(r'\b100\s*%\s*(?:de\s+)?do\b', 'todo o', t, flags=re.IGNORECASE)
    t = re.sub(r'\b100\s*%\s*(?:de\s+)?da\b', 'toda a', t, flags=re.IGNORECASE)
    t = re.sub(r'\b100\s*%\s*(?:de\s+)?dos\b', 'todos os', t, flags=re.IGNORECASE)
    t = re.sub(r'\b100\s*%\s*(?:de\s+)?das\b', 'todas as', t, flags=re.IGNORECASE)
    t = re.sub(r'\b100\s*%\s*de\b', 'todo o', t, flags=re.IGNORECASE)
    t = re.sub(r'\b100\s*%\s*', 'totalmente ', t, flags=re.IGNORECASE)
    t = re.sub(r'\b100\s+por\s+cento\b', 'cem por cento', t, flags=re.IGNORECASE)
    
    t = re.sub(r'\b\d+\s*\.\s*(?=[A-ZÀ-Ý])', '', t)

    t_final_check = t.strip().strip('"').strip('<>').strip().lower()
    bad_words = {
        "caracteres", "caractere", "chars", "char", "limite", "frase", "letras", "letra",
        "tom de voz", "tom de voz e categoria geral", "tom de voz e categoria geral:",
        "categoria geral", "limite de tamanho", "limite de caracteres",
        "tradução final adaptada", "traducao final adaptada", "translation", "think", "thought"
    }
    # [v2026.PUNCTUATION_STRIPPER] Remove pontos, vírgulas e reticências do texto todo (inclusive no final),
    # mantendo apenas ponto de interrogação ou exclamação no final para entonação, evitando pausas e a fala literal de "ponto".
    if t:
        t_str = t.strip()
        end_char = ""
        # Preserva apenas ponto de interrogação (?) ou exclamação (!) no final para manter o tom emocional
        if t_str and t_str[-1] in ["!", "?"]:
            end_char = t_str[-1]
            t_str = t_str[:-1]
        
        # Remove pontos, vírgulas e reticências de toda a string
        t_str = t_str.replace("...", " ").replace(".", " ").replace(",", " ").replace(";", " ")
        t_str = " ".join(t_str.split())
        t = t_str + end_char

    return t


def extract_json_from_ai(text):
    if not text: return {}
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end+1]
    try:
        return json.loads(text)
    except:
        return {}
