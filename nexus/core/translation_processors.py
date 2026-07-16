# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import time
import logging
import json
import re
import requests
from pathlib import Path
from datetime import datetime

# Runtime globals injected by __init__.py namespace patching:
# get_local_gemma_engine, get_gemma_model, find_gemma_model_path, load_game_profile
# make_gema_request_with_retries, clean_ai_translation, is_hallucinated_number_translation
# is_loop_hallucination, should_strip_prefix, detect_game_genre, generar_lore_global
# vocal_noises

_ACTIVE_STANDALONE_PORT = None

def gema_batch_processor_v2(batch, cenario_ctx, glossary={}, profile_id='padrao', job_dir=None, target_lang='pt'):
    if not batch: return {}
    
    from nexus.core import model_loader
    active_engine = getattr(model_loader, '_LOCAL_LLM_INSTANCE', None)
    if active_engine is not None:
        return _process_with_local_engine(active_engine, batch, cenario_ctx, glossary, target_lang, job_dir=job_dir)
    
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
        return _process_with_local_engine(None, batch, cenario_ctx, glossary, target_lang, job_dir=job_dir)
    
    local_engine = get_local_gemma_engine()
    if local_engine:
        return _process_with_local_engine(local_engine, batch, cenario_ctx, glossary, target_lang, job_dir=job_dir)

    logging.warning("⚠️ AGUARDANDO MODELO GGUF NA PASTA _MODELS_...")
    time.sleep(5)
    return {}


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
        context_str = f"CONTEXTO DA CENA E TOM DE VOZ:\n{context}\n\n"
        
    lore_str = ""
    if isinstance(glossary, dict) and 'lore_global' in glossary and glossary['lore_global']:
        lore_cleaned = re.sub(r'<think>.*?</think>', '', glossary['lore_global'], flags=re.DOTALL | re.IGNORECASE)
        for tag in ['<think>', '<thought>', '[thought]', '<|im_start|>thought']:
            if tag in lore_cleaned.lower():
                idx = lore_cleaned.lower().find(tag)
                lore_cleaned = lore_cleaned[:idx]
        lore_cleaned = lore_cleaned.strip()
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

    def call_engine(prompt, max_tokens=256, temperature=0.1, stop=["<end_of_turn>"]):
        if llm:
            try:
                res = llm(prompt, max_tokens=max_tokens, temperature=temperature, stop=stop)
                return res['choices'][0]['text'].strip()
            except Exception as e:
                logging.error(f"Erro no motor local: {e}")
            return ""

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
                    "stop": stop
                }
                res = requests.post(url, json=payload, timeout=5)
                if res.status_code == 200:
                    return res.json()['choices'][0]['text'].strip()
            except:
                continue
        return ""

    for seg in batch:
        txt_en = seg.get('original_text', seg.get('text', '')).strip()
        if any(ord(char) > 0x3000 for char in txt_en):
            results[str(seg['id']).lower()] = {"text": txt_en, "emotion": "CANTORIA"}
            continue
        
        clean_txt = txt_en.lower().replace("!", "").replace("?", "").replace(".", "").replace(",", "").strip()
        real_words = {"no", "yes", "yeah", "go", "we", "he", "me", "us", "hi", "in", "on", "it", "do", "up", "so", "to", "be", "if", "is"}
        is_reaction = (clean_txt in vocal_noises or len(clean_txt) <= 2) and (clean_txt not in real_words)
        
        if is_reaction:
            results[str(seg['id']).lower()] = {"text": txt_en, "emotion": "CANTORIA"}
            continue

        duration = float(seg.get('end', 0.0)) - float(seg.get('start', 0.0))
        if duration <= 0:
            duration = 2.0
            
        next_gap = seg.get('gap_to_next', 999.0)
        min_chars = 18 if next_gap < 1.0 else 25
        
        # [v2026.TIGHT_TIME_CEILING] Limita o tamanho máximo de caracteres da tradução com base no tempo de tela real
        # se o tempo for apertado, forçando o tradutor a resumir/encurtar a frase para que caiba no áudio.
        max_duration_chars = max(min_chars, int(duration * 16.0))
        base_limit = max(min_chars, int(len(txt_en) * 1.25))
        char_limit = min(base_limit, max_duration_chars)
        word_limit = max(8, int(char_limit / 4.5))
        
        is_qwen = False
        from nexus.core.model_loader import find_gemma_model_path
        p = find_gemma_model_path()
        if p and "qwen" in p.name.lower():
            is_qwen = True
        elif llm and hasattr(llm, "model_path") and "qwen" in str(llm.model_path).lower():
            is_qwen = True
        model_name = "Qwen 3.5" if is_qwen else "Gemma 4"
        system_instruction = (
            "Você é um Tradutor e Adaptador de Dublagem profissional para Português Brasileiro (PT-BR).\n"
            "Sua missão é adaptar a fala original de forma coloquial, fluida e natural para dublagem, mantendo a emoção e o limite de tempo.\n\n"
            "REGRAS CRÍTICAS:\n"
            "1. COLOQUIALISMO: Use linguagem falada e natural (ex: 'pra', 'tá', 'você'). Evite estruturas formais.\n"
            "2. GÊNERO: Adapte adjetivos ao gênero gramatical do Locutor informado (Masculino/Feminino).\n"
            "3. ESCRITA POR EXTENSO: Escreva todos os números e porcentagens por extenso em português (exemplo: escreva 'dez' em vez de '10').\n"
            "4. EVITE LITERALIDADES: Traduza expressões e gírias pelo sentido cultural (ex: 'piece of cake' -> 'moleza'; 'bullshit' -> 'besteira').\n"
            "5. TRADUÇÃO OBRIGATÓRIA DE GÍRIAS INGLÊSAS: NUNCA mantenha gírias em inglês como 'Bro', 'Man', 'Dude', 'Yeah', 'Okay', 'Shit'. Traduza-as OBRIGATORIAMENTE para termos coloquiais equivalentes em português brasileiro (ex: 'Bro/Dude' -> 'Cara/Mano/Velho'; 'Yeah/Okay' -> 'É/Sim/Beleza'; 'Shit' -> 'Merda/Porra').\n"
            "6. EVITE REPETIR INGLÊS EM FRASES GARBLADAS: Se o texto original parecer confuso, estranho ou gramaticalmente incorreto em inglês (ex: 'fucking over simulate me'), deduza o sentido aproximado ou a fonética e traduza para o português de forma natural. NUNCA copie a frase em inglês ou repita termos em inglês na tradução.\n"
            "7. PROIBIDO CHINÊS / MANDARIM: Você deve responder estritamente em PORTUGUÊS DO BRASIL. Nunca use caracteres chineses sob nenhuma circunstância. Não responda em chinês.\n"
            "8. LIMITE DE CARACTERES: A tradução DEVE ter no máximo {char_limit} caracteres.\n"
            "9. EMOÇÃO: Escolha uma emoção: [RAIVA, TRISTE, FELIZ, URGENTE, SUSPENSE, DRAMATICO, NORMAL, CANTORIA].\n"
            "10. TRADUÇÃO COMPLETA: Nunca deixe o texto em inglês ou sem traduzir. Sempre adapte tudo.\n"
            "11. FORMATO DE RETORNO OBRIGATÓRIO: Responda APENAS no formato abaixo. Nunca adicione explicações, aspas extras, notas ou prefixos/IDs:\n"
            "Trad: <tradução final adaptada>\n"
            "Emo: <EMOÇÃO>\n"
            "12. EVITE INVASÃO DE FRASES SEGUINTES: O texto em 'Texto original' pode terminar abruptamente no meio de uma frase (ex: terminando com 'It' ou 'the'). Traduza APENAS as palavras que estão fisicamente presentes no 'Texto original'. NUNCA deduza ou complete a frase com palavras que viriam a seguir se elas não estiverem no texto original.\n"
            "13. BLOQUEIO DE ALUCINAÇÕES (REPETIÇÕES): Se o texto original contiver repetições infinitas ou anormais causadas por falhas de transcrição (como 'I'm like, I'm like, I'm like...' repetido muitas vezes), NÃO traduza essas repetições. Em vez disso, retorne uma tradução vazia ou apenas uma ocorrência curta para evitar loops de áudio no TTS.\n"
            "14. FALA CONTÍNUA (SEM PAUSAS): A tradução deve ser focada em falar sem parar, de forma corrida e em fluxo contínuo. NUNCA insira pontos (.), vírgulas (,) ou reticências (...) no meio do texto do segmento. Junte todas as palavras e frases em um fluxo único sem pontuação interna para que a IA leia tudo de uma só vez (exemplo: prefira 'Desumano demais imagine' em vez de 'Desumano demais. Imagine.').\n"
            "15. PRESERVAÇÃO DE NOMES PRÓPRIOS: NUNCA altere a grafia de nomes próprios ingleses de pessoas, marcas ou lugares (mantenha 'Howie', 'Pennhurst', 'Home Depot' exatamente iguais, nunca mude para 'Howe' ou traduções literais).\n"
            "16. RIGOR GRAMATICAL BRASILEIRO: NUNCA invente palavras no português (ex: não use 'expulsoar' em vez de 'expulsar'). Garanta a concordância gramatical correta e a naturalidade coloquial das expressões (ex: use 'desumano' em vez de 'inumano'; 'viver nas próprias fezes' em vez de 'na própria fezes'; 'acorrentados' em vez de 'encadeados')."
        )

        speaker_id = seg.get('speaker', 'desconhecido')
        user_content = (
            f"{lore_str}"
            f"{glossary_str}"
            f"{context_str}"
            f"Locutor da fala atual: {speaker_id}\n"
            f"Limite de tamanho: A tradução deve ter no máximo {char_limit} caracteres (cerca de {word_limit} palavras).\n\n"
            f"Traduza o texto abaixo estritamente para Português Brasileiro (PT-BR):\n"
            f"Texto original: \"{txt_en}\""
        ).format(char_limit=char_limit)

        system_instruction_formatted = system_instruction.format(char_limit=char_limit)

        if is_qwen:
            # CORRIGIDO: Removido o prefill <think>\n</think> que quebra o Qwen 4B
            prompt_tradutor = (
                f"<|im_start|>system\n{system_instruction_formatted}<|im_end|>\n"
                f"<|im_start|>user\n{user_content}<|im_end|>\n"
                f"<|im_start|>assistant\nTrad: "
            )
            stop_tokens = ["<|im_end|>", "<|im_start|>"]
        else:
            prompt_tradutor = (
                f"<start_of_turn>user\n{system_instruction_formatted}\n\n{user_content}<end_of_turn>\n"
                f"<start_of_turn>model\nTrad: "
            )
            stop_tokens = ["<end_of_turn>"]
        
        max_tokens_to_use = 1536 if is_qwen else 256
        output_text = call_engine(prompt_tradutor, max_tokens=max_tokens_to_use, temperature=0.1, stop=stop_tokens)
        if not output_text or len(output_text) < 1:
            output_text = call_engine(prompt_tradutor, max_tokens=max_tokens_to_use, temperature=0.7, stop=stop_tokens)

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
        if not traducao or len(traducao) < 2 or is_hallucinated_number_translation(traducao, txt_en):
            was_contingency = True
            logging.info(f"[{model_name}] 🔄 {seg['id']} -> Tradução inválida ou alucinação ('{traducao_raw}'). Iniciando contingência...")
            user_content_relaxed = (
                f"{lore_str}"
                f"{glossary_str}"
                f"{context_str}"
                f"Locutor da fala atual: {speaker_id}\n"
                f"Traduza o texto abaixo estritamente para Português Brasileiro (PT-BR):\n"
                f"Texto original: \"{txt_en}\""
            )
            system_instruction_relaxed = (
                "Você é um Tradutor e Adaptador de Dublagem profissional para Português Brasileiro (PT-BR).\n"
                "Adapte a fala original para que soe natural, coloquial e caiba no tempo.\n\n"
                "REGRAS:\n"
                "1. COLOQUIALISMO: Use linguagem falada e natural (ex: 'pra', 'tá', 'você').\n"
                "2. GÊNERO: Adapte adjetivos/substantivos ao gênero do Locutor informado.\n"
                "3. ESCRITA POR EXTENSO: Escreva tudo por extenso em português. Nunca use números ou símbolos de porcentagem.\n"
                "4. EVITE LITERALIDADES: Traduza expressões pelo sentido cultural.\n"
                "5. TRADUÇÃO OBRIGATÓRIA DE GÍRIAS INGLÊSAS: NUNCA mantenha gírias em inglês como 'Bro', 'Man', 'Dude', 'Yeah', 'Okay', 'Shit'. Traduza-as OBRIGATORIAMENTE para termos coloquiais equivalentes em português brasileiro (ex: 'Bro/Dude' -> 'Cara/Mano/Velho'; 'Yeah/Okay' -> 'É/Sim/Beleza'; 'Shit' -> 'Merda/Porra').\n"
                "6. EVITE REPETIR INGLÊS EM FRASES GARBLADAS: Se o texto original parecer confuso ou gramaticalmente incorreto em inglês, deduza o sentido e traduza para o português de forma natural. NUNCA copie a frase em inglês ou repita termos em inglês.\n"
                "7. PROIBIDO CHINÊS / MANDARIM: Responda estritamente em PORTUGUÊS DO BRASIL. Nunca use caracteres chineses sob nenhuma circunstância. Não responda em chinês.\n"
                "8. EMOÇÃO: Escolha uma: [RAIVA, TRISTE, FELIZ, URGENTE, SUSPENSE, DRAMATICO, NORMAL, CANTORIA].\n"
                "9. FORMATO DE RETORNO: Responda APENAS no formato:\n"
                "Trad: <tradução final adaptada>\n"
                "Emo: <EMOÇÃO>\n"
                "10. EVITE INVASÃO DE FRASES SEGUINTES: Traduza APENAS as palavras fisicamente presentes no 'Texto original'.\n"
                "11. BLOQUEIO DE ALUCINAÇÕES (REPETIÇÕES): Se o original contiver repetições anômalas, não as traduza.\n"
                "12. FALA CONTÍNUA (SEM PAUSAS): A tradução deve ser focada em falar sem parar, de forma corrida e em fluxo contínuo. NUNCA insira pontos (.), vírgulas (,) ou reticências (...) no meio do texto do segmento. Junte todas as palavras em um fluxo único sem pontuação interna para evitar silêncios artificiais na IA de voz (exemplo: prefira 'Desumano demais imagine' em vez de 'Desumano demais. Imagine.').\n"
                "13. PRESERVAÇÃO DE NOMES PRÓPRIOS: NUNCA altere a grafia de nomes próprios ingleses de pessoas, marcas ou lugares (mantenha 'Howie', 'Pennhurst', 'Home Depot' exatamente iguais, nunca mude para 'Howe' ou traduções literais).\n"
                "14. RIGOR GRAMATICAL BRASILEIRO: NUNCA invente palavras no português (ex: não use 'expulsoar' em vez de 'expulsar'). Garanta a concordância gramatical correta e a naturalidade coloquial das expressões (ex: use 'desumano' em vez de 'inumano'; 'viver nas próprias fezes' em vez de 'na própria fezes'; 'acorrentados' em vez de 'encadeados')."
            )
            if is_qwen:
                # CORRIGIDO: Removido o prefill <think>\n</think> do retry
                prompt_relaxed = (
                    f"<|im_start|>system\n{system_instruction_relaxed}<|im_end|>\n"
                    f"<|im_start|>user\n{user_content_relaxed}<|im_end|>\n"
                    f"<|im_start|>assistant\nTrad: "
                )
            else:
                prompt_relaxed = (
                    f"<start_of_turn>user\n{system_instruction_relaxed}\n\n{user_content_relaxed}<end_of_turn>\n"
                    f"<start_of_turn>model\nTrad: "
                )
            output_relaxed = call_engine(prompt_relaxed, max_tokens=max_tokens_to_use, temperature=0.7, stop=stop_tokens)
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
            if traducao_relaxed and len(traducao_relaxed) >= 2 and not is_hallucinated_number_translation(traducao_relaxed, txt_en):
                traducao = traducao_relaxed
                logging.info(f"🔄 [RELAXED RETRY] Sucesso no retry de {seg['id']}: '{traducao}'")

        was_compressed = False

        emocao_limpa = clean_hallucination_wrapper(emocao_raw).split()
        emocao = emocao_limpa[0] if emocao_limpa else "NORMAL"
        if emocao not in ["RAIVA", "TRISTE", "FELIZ", "URGENTE", "SUSPENSE", "DRAMATICO", "NORMAL", "CANTORIA"]:
            emocao = "NORMAL"

        if not traducao or len(traducao) < 2:
            traducao = txt_en

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
