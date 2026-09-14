# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import re
import logging
import json
from pathlib import Path
from datetime import datetime

# Runtime globals injected by __init__.py namespace patching:
# load_game_profile, make_gema_request_with_retries, clean_ai_translation

def same_word_count_check(original, translated):
    words_orig = len(original.split())
    words_trans = len(translated.split())
    if words_orig == words_trans and words_orig > 5:
        return True
    return False


def gema_etapa_correcao_master(original_text, current_translation, duration, reason="sincronia", profile_id='padrao'):
    """
    [v14.50 CORRETOR MASTER] - O Agente que resolve tudo com adaptação natural e sem traduções secas.
    """
    profile = load_game_profile(profile_id)
    lore_text = profile.get("lore", "Gênero: Jogo de Ação e Sobrevivência.")
    ai_instructions = profile.get("ai_instructions", "Mantenha gírias de jogos/combate e coloquialidade em PT-BR.")
    target_chars = int(duration * 18)
    
    prompt = (
        f"Tarefa: Corretor Master de Dublagem v2026.\n"
        f"Contexto e Universo do Jogo (Lore): {lore_text}\n"
        f"Instruções do Perfil: {ai_instructions}\n"
        f"Problema Identificado: {reason}\n"
        f"Texto Original (EN): {original_text}\n"
        f"Tradução Atual (PT): {current_translation}\n"
        f"Meta de Tamanho: ~{target_chars} caracteres para caber em {duration:.2f}s.\n"
        f"Regras Críticas de Adaptação de Dublagem:\n"
        f"1. ADAPTAÇÃO AO LORE: Respeite estritamente o universo do jogo acima! Jamais confunda homônimos fora do contexto da cena (ex: em combate/zumbis, 'drawing' = atrair inimigos, NUNCA desenhar/pintar; 'loaded up' = equipado/com mochila; 'Zeds' = zumbis).\n"
        f"2. PROIBIDO FRASES SECAS: NUNCA gere palavras isoladas ou robóticas de 1 palavra só para bater tamanho (ex: NUNCA usar só 'Mochila!'). Se o tempo for curto, crie uma frase curta, fluida e natural (ex: 'Mochila pronta!').\n"
        f"3. DITOS COLOQUIAIS: Garanta 100% de coloquialidade e naturalidade em PT-BR falado no jogo.\n"
        f"Retorne APENAS a frase adaptada final entre aspas."
    )

    try:
        payload = {
            "messages": [
                {"role": "system", "content": "Você é um Diretor Executivo de Localização de Jogos. Responda apenas o texto corrigido entre aspas. Respeite o universo do jogo, priorize coloquialidade natural e proíba traduções robóticas ou de 1 palavra isolada."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4096
        }
        response = make_gema_request_with_retries(payload, is_translation=False)
        content = response.json()['choices'][0]['message']['content'].strip()
        final_text = clean_ai_translation(content, original_text)
        return final_text
    except Exception as e:
        logging.error(f"Erro no Agente de Correção Master: {e}")
        return current_translation


def gema_batch_corrector_master(failed_items, cenario_ctx, profile_id='padrao', job_dir=None):
    """
    [v14.60 SUPER TURBO BATCH CORRECTOR]
    """
    if not failed_items: return {}
    profile = load_game_profile(profile_id)
    lore_text = profile.get("lore", "Gênero: Jogo de Ação e Sobrevivência.")
    ai_instructions = profile.get("ai_instructions", "Coloquialidade PT-BR.")
    
    prompt = (
        f"Tarefa: Corretor Batch v2026.\n"
        f"Contexto do Jogo: {lore_text} | Instruções: {ai_instructions} | Cenário: {cenario_ctx}\n"
        f"Regras: Formato=id: \"Corrigido\"; Sem explicações; Respeite o contexto do jogo; Proibido frases secas de 1 palavra (ex: usar 'Mochila pronta!' em vez de só 'Mochila!'); Mantenha a dublagem fluida em PT-BR.\n"
        f"Entrada:\n"
    )
    for item in failed_items:
        prompt += f"- {item['id']}: EN=\"{item.get('original_text', '')}\" -> RUIM=\"{item.get('translated_text', '')}\"\n"

    try:
        payload = {
            "messages": [
                {"role": "system", "content": "Você é um Corretor de Dublagem Profissional. Responda apenas o ID e o texto entre aspas. Respeite o universo do jogo e proíba conversas ou respostas secas robóticas."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2, "max_tokens": 2048
        }
        response = make_gema_request_with_retries(payload, is_translation=False)
        content = response.json()['choices'][0]['message']['content'].strip()
        
        if job_dir:
            try:
                log_file = Path(job_dir) / "ia_batch_debug.log"
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n--- CORRETOR {datetime.now()} ---\n{content}\n")
            except: pass

        results = {}
        item_pattern = r'(?:^|\n)[ \t]*(?:[0-9]+\.?[ \t]*)?(?:id\s*[:\-]\s*)?([a-zA-Z0-9_\-\.]+)\s*[:\-=>]+\s*"?\s*(.*?)\s*"?(?=\n[ \t]*(?:[0-9]+\.?[ \t]*)?(?:id\s*[:\-]\s*)?[a-zA-Z0-9_\-\.]+\s*[:\-=>]+|$)'
        matches = re.finditer(item_pattern, content, re.DOTALL)
        for match in matches:
            clean_id = match.group(1).strip().lower()
            val = match.group(2).strip().strip('"')
            results[clean_id] = val
        return results
    except Exception as e:
        logging.error(f"Erro no Batch Corrector Master: {e}")
        return {}


def agente_2_matematico_python(texto_pt, duration):
    """
    [O Fiscal Matemático Frio - Agente 2]
    Calcula se a tradução PT-BR caberá mecanicamente no limitador TTS.
    """
    if not texto_pt or duration <= 0:
        return {"aprovado": False, "dossie": "Dados insuficientes ou texto vazio."}
        
    MAX_CPS = 18.5
    limite_max_caracteres = int(duration * MAX_CPS)
    commas = texto_pt.count(',')
    pontos = texto_pt.count('.') + texto_pt.count('!') + texto_pt.count('?')
    peso_pausas_em_caracteres = (commas * 8) + (pontos * 10)
    tamanho_efetivo = len(texto_pt) + peso_pausas_em_caracteres
    
    if tamanho_efetivo <= limite_max_caracteres:
        return {"aprovado": True, "dossie": ""}
        
    estouro = tamanho_efetivo - limite_max_caracteres
    dossie = (
        f"ALERTA DE SINCRONIA DE TEMPO! "
        f"Nós temos apenas {round(duration, 2)} segundos, o que permite um tamanho MÁXIMO de {limite_max_caracteres} letras. "
        f"A sua tradução bateu {tamanho_efetivo} letras (estimadas com pausas). "
        f"Você ESTOUROU o tempo. É estritamente OBRIGATÓRIO que você corte, no mínimo, {estouro + 5} letras dessa tradução "
        f"reescrevendo-a de forma natural e resumida."
    )
    return {"aprovado": False, "dossie": dossie}


def agente_3_adaptador_final_lqa(original_text, translated_text, dossie, timeout=3600):
    """
    [O Editor Chefe - Agente 3]
    """
    prompt = f'''
VOCE E UM EDITOR DE DUBLAGEM GENIO. A traducao chegou, mas ELA E GRANDE DEMAIS PARA O TEMPO DO AUDIO.

[DIAGNOSTICO DO FISCAL DE TEMPO]:
{dossie}

[INGLES ORIGINAL A TITULO DE CONTEXTO]:
"{original_text}"

[TRADUCAO ORIGINAL - VOCE DEVE ENCURTAR ISSO]:
"{translated_text}"

[SUA TAREFA]:
Reescreva a [TRADUCAO ORIGINAL]. Seja agressivo nos cortes de palavras inuteis. Use contracoes ("Nos estamos" vira "Estamos", "De o" vira "Do", "Para" vira "Pra"). Mantenha a emocao natural do Brasil.

[FORMATO EXIGIDO]:
"Sua adaptacao curtinha final vai aqui dentro das aspas, e MAIS NADA."

Responda APENAS com a nova traducao resumida e perfeita. Nenhuma palavra de explicacao.
'''
    payload = {
        "messages": [
            {"role": "system", "content": "O texto não cabe! Adaptando, resumindo e retornando só a versão PT-BR reescrita e ultra-condensada dentro de aspas."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1024
    }
    
    try:
        response = make_gema_request_with_retries(payload, timeout=timeout, is_translation=False)
        content = response.json()['choices'][0]['message']['content'].strip()
        return clean_ai_translation(content, original_text)
    except Exception as e:
        logging.error(f"Erro Crítico no Agente 3 Adaptador: {e}")
        return translated_text
