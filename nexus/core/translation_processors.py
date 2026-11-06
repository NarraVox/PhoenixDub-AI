# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import time
import logging
import json
import re
import requests
from pathlib import Path
from datetime import datetime
from nexus.core.translation_prompts import (
    get_dubbing_system_instruction,
    get_dubbing_user_content,
    format_chat_prompt,
    get_contingency_prompt,
    get_cps_guard_prompt,
    get_direct_fallback_prompt
)

# Runtime globals injected by __init__.py namespace patching:
# get_local_gemma_engine, get_gemma_model, find_gemma_model_path, load_game_profile
# make_gema_request_with_retries, clean_ai_translation, is_hallucinated_number_translation
# is_loop_hallucination, should_strip_prefix, detect_game_genre, generar_lore_global
# vocal_noises

_ACTIVE_STANDALONE_PORT = None

def gema_batch_processor_v2(batch, cenario_ctx, glossary={}, profile_id='padrao', job_dir=None, target_lang='pt'):
    if not batch: return {}

    if not ensure_system_memory_safety("lote de tradução"):
        raise RuntimeError("RAM atingiu o limite de segurança antes do lote de tradução.")
    if not ensure_vram_safety("lote de tradução"):
        raise RuntimeError("VRAM atingiu 90%; lote de tradução bloqueado para evitar OOM.")
    
    from nexus.core import model_loader
    active_engine = getattr(model_loader, '_LOCAL_LLM_INSTANCE', None)
    if active_engine is not None:
        result = _process_with_local_engine(active_engine, batch, cenario_ctx, glossary, target_lang, job_dir=job_dir)
        if not ensure_vram_safety("lote de tradução após inferência"):
            unload_local_gemma_engine()
            raise RuntimeError("VRAM excedeu 90% durante tradução; motor local descarregado.")
        return result
    
    import requests
    server_online = False
    global _ACTIVE_STANDALONE_PORT
    
    if _ACTIVE_STANDALONE_PORT:
        try:
            res = requests.get(f"http://127.0.0.1:{_ACTIVE_STANDALONE_PORT}/v1/models", timeout=0.5)
            if res.status_code == 200:
                server_online = True
        except:
            _ACTIVE_STANDALONE_PORT = None

    if not server_online:
        for port in [1234, 8080]:
            try:
                res = requests.get(f"http://127.0.0.1:{port}/v1/models", timeout=0.5)
                if res.status_code == 200:
                    server_online = True
                    _ACTIVE_STANDALONE_PORT = port
                    logging.info(f"🌐 [BATCH] Servidor Standalone detectado na porta {port}. Usando inferência rápida de rede!")
                    break
            except:
                continue
            
    if server_online:
        result = _process_with_local_engine(None, batch, cenario_ctx, glossary, target_lang, job_dir=job_dir)
        if not ensure_vram_safety("servidor de tradução após inferência"):
            raise RuntimeError("VRAM excedeu 90% durante tradução; novas chamadas foram bloqueadas.")
        return result
    
    local_engine = get_local_gemma_engine()
    if local_engine:
        result = _process_with_local_engine(local_engine, batch, cenario_ctx, glossary, target_lang, job_dir=job_dir)
        if not ensure_vram_safety("lote de tradução após inferência"):
            unload_local_gemma_engine()
            raise RuntimeError("VRAM excedeu 90% durante tradução; motor local descarregado.")
        return result

    logging.warning("⚠️ AGUARDANDO MODELO GGUF NA PASTA MODELS...")
    time.sleep(5)
    return {}

from nexus.core.tactical_dict import fast_tactical_translator

def sanitize_prompt_metadata(text: str) -> str:
    """
    Remove nomes de pastas de jobs (PROJETO_...), timestamps (17AUG, 22H45),
    caminhos de arquivo do Windows e extensões técnicas (.wav, .mp3, uploads/)
    para que o LLM receba apenas o texto e contexto limpos.
    """
    if not text:
        return ""
    # Remove caminhos de arquivos absolutos ou uploads
    text = re.sub(r'[A-Za-z]:\\[^\s\n]+', '', text)
    text = re.sub(r'uploads[\\/][^\s\n]+', '', text)
    # Remove padrões de Job / Projeto (ex: PROJETO_17AUG_22H45_ALN ou 17AUG22H45)
    text = re.sub(r'PROJETO_[A-Za-z0-9_]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b\d{1,2}[A-Z]{3}\d{0,4}(?:_\d{1,2}[Hh]\d{2})?(?:_[A-Za-z0-9]+)?\b', '', text)
    # Remove extensões de arquivo
    text = re.sub(r'\.(?:wav|mp3|ogg|flac|m4a|json)\b', '', text, flags=re.IGNORECASE)
    # Preserva quebras de linha limpando apenas espacos horizontais repetidos
    return "\n".join(re.sub(r'[ \t]+', ' ', l).strip() for l in text.splitlines() if l.strip())

def is_isolated_reaction_or_grunt(text: str) -> bool:
    """
    Retorna True se o áudio for APENAS uma interjeição/grito/reação isolada sem fala real
    (ex: 'No!', 'No, no, no!', 'Oh no!', 'Yeah!', 'Uh-huh', 'Ahhh!').
    Todo mundo entende reações universais, então preserva o áudio original com a emoção do ator.
    Se houver qualquer outra fala junto (ex: 'No, no, it can't be gone'), retorna False para traduzir a fala inteira.
    """
    if not text:
        return True
    words = [re.sub(r'[^\w]', '', w.lower()) for w in text.split()]
    words = [w for w in words if w]
    if not words:
        return True

    universal_reactions = {
        "no", "nope", "nah", "yes", "yeah", "yep", "uh", "um", "uhhuh", "uhuh",
        "oh", "ah", "ahh", "ahhh", "argh", "ugh", "urgh", "ouch", "oof", "hey",
        "huh", "hmm", "hmmm", "ha", "haha", "hahaha", "shh", "shhh", "phew",
        "whoa", "woah", "wow", "grr", "gasp"
    }
    return all(w in universal_reactions for w in words)

def _process_with_local_engine(llm, batch, context, glossary, target_lang, job_dir=None):
    results = {}
    
    debug_file = None
    if job_dir:
        debug_file = Path(job_dir) / "gemma_debug_raw.txt"
        if not debug_file.exists():
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(f"=== CAIXA PRETA GEMMA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
    
    context_str = ""
    if context:
        clean_ctx = sanitize_prompt_metadata(context)
        if clean_ctx:
            context_str = f"{clean_ctx}\n\n" if "<dialogue_context>" in clean_ctx else f"CONTEXTO DA CENA:\n{clean_ctx}\n\n"
        
    lore_str = ""
    if isinstance(glossary, dict) and 'lore_global' in glossary and glossary['lore_global']:
        lore_cleaned = re.sub(r'<think>.*?</think>', '', glossary['lore_global'], flags=re.DOTALL | re.IGNORECASE)
        for tag in ['<think>', '<thought>', '[thought]', '<|im_start|>thought']:
            if tag in lore_cleaned.lower():
                idx = lore_cleaned.lower().find(tag)
                lore_cleaned = lore_cleaned[:idx]
        lore_cleaned = sanitize_prompt_metadata(lore_cleaned)
        if lore_cleaned:
            lore_str = f"LORE GLOBAL DO PROJETO (Use para entender o tom, contexto e termos):\n{lore_cleaned}\n\n"
        
    glossary_lines = []
    if isinstance(glossary, dict):
        for k, v in glossary.items():
            if k != 'lore_global' and v:
                glossary_lines.append(f"- {k} -> {v}")
    glossary_str = ""
    if glossary_lines:
        glossary_str = "GLOSSÁRIO OBRIGATÓRIO (Use as traduções abaixo se os termos aparecerem):\n" + "\n".join(glossary_lines) + "\n\n"

    def call_engine(prompt, max_tokens=64, temperature=0.1, stop=["<end_of_turn>", "<|im_end|>"]):
        if llm:
            try:
                res = llm(prompt, max_tokens=max_tokens, temperature=temperature, stop=stop)
                return res['choices'][0]['text'].strip()
            except Exception as e:
                logging.error(f"Erro no motor local: {e}")
            return ""

        # [v2026.TIMEOUT_FIX] Timeout aumentado para 120s — previne ciclo de retry
        # causado por timeout curto (5s) que gerava 40s por segmento.
        # O LLM local pode levar 5-15s por resposta dependendo do tamanho do prompt.
        _session = getattr(call_engine, '_session', None)
        if _session is None:
            import requests as _req
            call_engine._session = _req.Session()
            _session = call_engine._session

        urls = [
            "http://127.0.0.1:1234/v1/completions",
            "http://127.0.0.1:8080/v1/completions"
        ]
        for url in urls:
            try:
                import requests
                payload = {
                    "prompt": prompt,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "model": "local-model",
                    "stop": stop,
                    "cache_prompt": True  # [v2026.KV_CACHE_REUSE] Reutiliza o KV-Cache do sistema+lore+glossario no llama.cpp
                }
                res = _session.post(url, json=payload, timeout=120)
                if res.status_code == 200:
                    return res.json()['choices'][0]['text'].strip()
            except:
                continue
        return ""


    is_qwen = False
    try:
        from nexus.core.model_loader import find_gemma_model_path
        p = find_gemma_model_path()
        if p and "qwen" in p.name.lower():
            is_qwen = True
        elif llm and hasattr(llm, "model_path") and "qwen" in str(llm.model_path).lower():
            is_qwen = True
    except Exception:
        pass
    model_name = "Qwen 3.5" if is_qwen else "Gemma 4"

    for seg in batch:
        txt_en = seg.get('original_text', seg.get('text', '')).strip()
        if any(ord(char) > 0x3000 for char in txt_en):
            results[str(seg['id']).lower()] = {"text": txt_en, "emotion": "CANTORIA"}
            continue
        
        # [v2026.FAST_TACTICAL_ACCELERATOR] Tradução instantânea de comandos táticos recorrentes de combate
        fast_pt, fast_emo = fast_tactical_translator(txt_en)
        if fast_pt:
            results[str(seg['id']).lower()] = {"text": fast_pt, "emotion": fast_emo}
            continue

        # [v2026.REACTION_FILTER] Se o áudio for APENAS uma interjeição/grito/reação isolada (ex: 'No!', 'No, no, no!', 'Yeah!'),
        # preserva o áudio original com a atuação do ator. Se tiver diálogo junto, traduz a fala inteira.
        if is_isolated_reaction_or_grunt(txt_en):
            results[str(seg['id']).lower()] = {"text": txt_en, "emotion": "CANTORIA"}
            continue

        duration = float(seg.get('end', 0.0)) - float(seg.get('start', 0.0))
        if duration <= 0:
            duration = 2.0
            
        # O limite é mecânico: 18 caracteres por segundo, contando espaços.
        # A primeira tentativa recebe esse teto; só há uma segunda chamada se
        # a resposta final exceder o valor calculado abaixo.
        char_limit = max(1, int(duration * 18.0))
        word_limit = max(1, int(char_limit / 4.5))
        raw_spk = str(seg.get('speaker', 'desconhecido'))

        clean_spk = sanitize_prompt_metadata(raw_spk)

        speaker_id = clean_spk if clean_spk and clean_spk.lower() not in ["desconhecido", "unknown", "none", ""] else "Locutor"


        system_instruction_formatted = get_dubbing_system_instruction(char_limit=char_limit)

        user_content = get_dubbing_user_content(
            txt_en=txt_en,
            speaker_id=speaker_id,
            char_limit=char_limit,

            word_limit=word_limit,
            lore_str=lore_str,
            glossary_str=glossary_str,

            context_str=context_str

        )

        prompt_tradutor, stop_tokens = format_chat_prompt(system_instruction_formatted, user_content, is_qwen=is_qwen)
        
        # max_tokens: 128 tokens é suficiente para frases longas + Trad: + Emo: com prefill direto
        max_tokens_to_use = 128
        output_text = call_engine(prompt_tradutor, max_tokens=max_tokens_to_use, temperature=0.1, stop=stop_tokens)
        if not output_text or len(output_text) < 1:
            output_text = call_engine(prompt_tradutor, max_tokens=max_tokens_to_use, temperature=0.7, stop=stop_tokens)
        # Nota: tag-stripping do bloco <think> ocorre nas linhas abaixo (re.sub <think>...)

        output_text = re.sub(r'<think>.*?</think>', '', output_text, flags=re.DOTALL | re.IGNORECASE)
        output_text = re.sub(r'<thought>.*?</thought>', '', output_text, flags=re.DOTALL | re.IGNORECASE)
        output_text = re.sub(r'<\|channel\|?>thought.*?<channel\|?>', '', output_text, flags=re.DOTALL | re.IGNORECASE)
        output_text = re.sub(r'\[THOUGHT\].*?\[/THOUGHT\]', '', output_text, flags=re.DOTALL | re.IGNORECASE)
        
        for tag in ['<think>', '<thought>', '[thought]', '<|im_start|>thought']:
            if tag in output_text.lower():
                idx = output_text.lower().find(tag)
                output_text = output_text[:idx]

        output_text = output_text.strip()

        if output_text and not output_text.lower().strip().startswith("trad:"):
            output_text = "Trad: " + output_text.strip()

        traducao_raw = ""
        emocao_raw = "NORMAL"
        
        lines = [line.strip() for line in output_text.split('\n') if line.strip()]
        for line in lines:
            if line.lower().startswith("trad:"):
                traducao_raw = line[5:].strip().strip('"')
            elif line.lower().startswith("emo:"):
                emocao_raw = line[4:].strip().upper()
                
        if not traducao_raw and lines:
            first_line = lines[0]
            if not first_line.lower().startswith("emo:"):
                traducao_raw = first_line.strip('"')
                if len(lines) > 1 and lines[1].lower().startswith("emo:"):
                    emocao_raw = lines[1][4:].strip().upper()
        
        if not traducao_raw:
            traducao_raw = output_text.strip().strip('"')

        def clean_hallucination_wrapper(t):
            return clean_ai_translation(t, txt_en, seg.get('id'))

        traducao = clean_hallucination_wrapper(traducao_raw)

        was_contingency = False
        if not traducao or len(traducao) < 2 or is_hallucinated_number_translation(traducao, txt_en) or traducao.lower().strip() == txt_en.lower().strip():
            was_contingency = True
            logging.info(f"[{model_name}] 🔄 {seg['id']} -> Tradução inválida ou alucinação ('{traducao_raw}'). Iniciando contingência...")
            prompt_relaxed, stop_tokens = get_contingency_prompt(
            txt_en=txt_en,
            speaker_id=speaker_id,
            lore_str=lore_str,
            glossary_str=glossary_str,
            context_str=context_str,
            is_qwen=is_qwen

            )

            output_relaxed = call_engine(prompt_relaxed, max_tokens=max_tokens_to_use, temperature=0.3, stop=stop_tokens)
            if output_relaxed and not output_relaxed.lower().strip().startswith("trad:"):
                output_relaxed = "Trad: " + output_relaxed.strip()
            trad_relaxed = ""
            lines_rel = [line.strip() for line in output_relaxed.split('\n') if line.strip()]
            for line in lines_rel:
                if line.lower().startswith("trad:"):
                    trad_relaxed = line[5:].strip().strip('"')
            if not trad_relaxed and lines_rel:
                if not lines_rel[0].lower().startswith("emo:"):
                    trad_relaxed = lines_rel[0].strip('"')
            if not trad_relaxed:
                trad_relaxed = output_relaxed.strip().strip('"')
                
            traducao_relaxed = clean_hallucination_wrapper(trad_relaxed)
            if traducao_relaxed and len(traducao_relaxed) >= 2 and not is_hallucinated_number_translation(traducao_relaxed, txt_en) and traducao_relaxed.lower().strip() != txt_en.lower().strip():
                traducao = traducao_relaxed
                logging.info(f"🔄 [RELAXED RETRY] Sucesso no retry de {seg['id']}: '{traducao}'")

        was_compressed = False

        emocao_limpa = clean_hallucination_wrapper(emocao_raw).split()
        emocao = emocao_limpa[0] if emocao_limpa else "NORMAL"
        if emocao not in ["RAIVA", "TRISTE", "FELIZ", "URGENTE", "SUSPENSE", "DRAMATICO", "NORMAL", "CANTORIA"]:
            emocao = "NORMAL"

        # [v2026.ZERO_ENGLISH_SHIELD] Se tudo falhar, tenta um fallback direto de tradução rápida para não deixar em inglês
        if not traducao or len(traducao) < 2 or traducao.lower().strip() == txt_en.lower().strip():
            direct_prompt = get_direct_fallback_prompt(txt_en, is_qwen=is_qwen)
            out_direct = call_engine(direct_prompt, max_tokens=max_tokens_to_use, temperature=0.1, stop=stop_tokens).strip().strip('"')
            if out_direct and len(out_direct) >= 2:
                traducao = out_direct
            else:
                traducao = txt_en

        if not traducao or len(traducao) < 2:
            traducao = txt_en

        # [v2026.CPS_GUARD] Validação determinística pós-tradução.  Não faz
        # uma segunda chamada para os segmentos aprovados; somente a fala que
        # ultrapassar 18 CPS volta uma vez ao mesmo Qwen para ser condensada.
        if len(traducao) > char_limit:
            current_chars = len(traducao)
            logging.info(
                f"⏱️ [CPS_GUARD] {seg['id']} excedeu 18 CPS "
                f"({current_chars}/{char_limit} caracteres). Reescrevendo uma única vez..."
            )
            sync_prompt, sync_stop_tokens = get_cps_guard_prompt(
            txt_en=txt_en,
            traducao=traducao,
            duration=duration,
            char_limit=char_limit,
            is_qwen=is_qwen

            )

            sync_raw = call_engine(sync_prompt, max_tokens=max_tokens_to_use, temperature=0.1, stop=sync_stop_tokens)
            sync_raw = re.sub(r'<think>.*?</think>', '', sync_raw, flags=re.DOTALL | re.IGNORECASE).strip()
            sync_raw = re.sub(r'^trad\s*:\s*', '', sync_raw, flags=re.IGNORECASE).strip().strip('"')
            sync_raw = re.split(r'\s+emo\s*:\s*', sync_raw, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            sync_text = clean_hallucination_wrapper(sync_raw)
            is_leak = any(term in sync_text.lower() for term in ["segundos", "limite", "caracteres", "original en:", "tradução longa:"])
            if 2 <= len(sync_text) <= char_limit and not is_leak:
                traducao = sync_text
                was_compressed = True
                logging.info(f"✅ [CPS_GUARD] {seg['id']} sincronizada: {len(traducao)}/{char_limit} caracteres.")
            else:
                motivo = "vazamento de prompt" if is_leak else f"{len(sync_text)}/{char_limit}"
                logging.warning(
                    f"⚠️ [CPS_GUARD] Retry de {seg['id']} não gerou versão utilizável "
                    f"({motivo}). Mantendo a primeira tradução."
                )

        status_info = []
        if was_contingency: status_info.append("Contingência")
        if was_compressed: status_info.append(f"Encurtado")
        status_msg = " | ".join(status_info) if status_info else ""

        logging.info(f"✅ {seg['id']} -> Concluída ('{traducao}' - {emocao})")
        results[str(seg['id']).lower()] = {"text": traducao, "emotion": emocao, "status": status_msg}
        logging.info(f"🎭 [DUO-AGENT] {seg['id']} | T: {traducao} | E: {emocao}")

        if debug_file:
            try:
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] ID: {seg['id']} | T_RAW: '{traducao_raw}' | E_RAW: '{emocao_raw}'\n")
            except: pass
        
    return results


def gema_atomic_processor_v3(item, context_window_str, glossary={}, profile_id='padrao', job_dir=None):
    """
    [v2026.ACTING_PROCESSOR]
    Usa o Gemma 4 para traduzir e detectar a emoção da cena simultaneamente.
    """
    profile = load_game_profile(profile_id)
    ai_style = profile.get("ai_instructions", "Estilo: Tradução natural e orgânica (PT-BR).")
    
    glossary_str = ""
    if glossary:
        glossary_items = [f"- {en} -> {pt}" for en, pt in glossary.items()]
        glossary_str = "[GLOSSÁRIO OBRIGATÓRIO]:\n" + "\n".join(glossary_items)
        
    prompt = (
        f"Tarefa: Diretor de Dublagem e Tradutor Atômico v2026.\n"
        f"Perfil: {ai_style}\n{glossary_str}\n"
        f"Contexto da Cena:\n{context_window_str}\n\n"
        f"Regras de Ouro:\n"
        f"1. Traduza OBRIGATORIAMENTE para PT-BR (Brasileiro).\n"
        f"2. Analise o contexto e defina a emoção: [RAIVA, TRISTE, FELIZ, URGENTE, SUSPENSE, DRAMATICO, NORMAL].\n"
        f"3. Limite={int(item.get('duration', 0) * 16.0)} chars.\n"
        f"4. EVITE TRADUÇÃO LITERAL (AO PÉ DA LETRA): Traduza gírias e expressões para soar natural no português coloquial do Brasil. Exemplos:\n"
        f"   - 'That's a pretty good start.' -> 'É um bom começo.' ou 'Já é um ótimo começo.'\n"
        f"   - 'Where have you been?' -> 'Onde você esteve?' ou 'Por onde você andou?'\n"
        f"   - 'on board' -> 'a bordo' (se referindo a navios/naves/veículos), não 'aqui dentro'.\n"
        f"   - 'Well' no início da frase -> traduzir de forma natural como 'Bom...' ou 'Bem...'\n"
        f"   - 'No.' -> 'Não.' (Sempre traduza 'No' e 'Yeah', nunca deixe em inglês).\n"
        f"   - 'Yeah.' -> 'Sim.' ou 'É.' (Sempre traduza 'Yeah' e 'No').\n"
        f"   - 'tiptoes back in' -> 'volta de fininho' ou 'entra de mansinho'\n"
        f"   - 'lasers someone's face' -> 'frita a cara com laser' ou 'derrete o rosto com laser'\n"
        f"   - 'chop her' -> 'derrubá-lo' ou 'interceptar'\n"
        f"   - 'run the red' -> 'fura o sinal vermelho'\n"
        f"   - 'Copy that' -> 'Entendido!' / 'Copiado!'.\n"
        f"5. SEM OMISSÕES: Traduza a frase completa. Nunca omita complementos ou detalhes importantes.\n"
        f"6. NUNCA DÊ OPÇÕES OU ALTERNATIVAS: Retorne estritamente uma única tradução final.\n"
        f"7. PROIBIDO ADICIONAR PREFIXOS: Nunca inclua IDs de segmento (como 'seg_0', '00', '3:') ou contadores no início do texto traduzido. NUNCA retorne o limite de caracteres ou a palavra 'caracteres'/'chars' como sua tradução.\n\n"
        f"Entrada Alvo: ID={item['id']} | EN='{item.get('original_text', '')}'\n\n"
        f"Responda APENAS um JSON no formato: {{\"text\": \"sua_tradução\", \"emotion\": \"EMOÇÃO_DETECTADA\"}}"
    )

    payload = {
        "messages": [
            {"role": "system", "content": "Você é um Diretor de Localização Sênior. Responda APENAS o JSON solicitado. Nunca deixe o texto em inglês. Evite traduções literais e adapte gírias/expressões de forma natural para o português brasileiro."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3, "max_tokens": 1024
    }

    try:
        response = make_gema_request_with_retries(payload, is_translation=True)
        content = response.json()['choices'][0]['message']['content'].strip()
        json_str = re.search(r'\{.*\}', content, re.DOTALL)
        if json_str:
            data = json.loads(json_str.group())
            final_text = clean_ai_translation(data.get('text', '').strip(), item.get('original_text', ''))
            item['emotion'] = data.get('emotion', 'NORMAL').upper()
        else:
            final_text = clean_ai_translation(content, item.get('original_text', ''))
            item['emotion'] = "NORMAL"
        return final_text
    except Exception as e:
        logging.error(f"Erro no Processador Atômico [{item['id']}]: {e}")
        item['emotion'] = "NORMAL"
        return item.get('original_text', '')
