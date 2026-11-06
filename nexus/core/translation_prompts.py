# -*- coding: utf-8 -*-
"""
Módulo de prompts de tradução e adaptação para dublagem (Qwen 3.5 / Gemma).
Seguindo o padrão arquitetural oficial ChatML e estruturação modular XML do Qwen.
"""
from typing import Tuple, List

def get_dubbing_system_instruction(char_limit: int) -> str:
    """
    Retorna o System Prompt formatado com tags XML estruturadas para o Qwen 3.5 / Gemma.
    """
    return (
        "<system_identity>\n"
        "Você é um Diretor de Dublagem e Tradutor Profissional para Português Brasileiro (PT-BR). "
        "Sua missão é adaptar falas em inglês para dublagem com ritmo, coloquialismo e impacto natural.\n"
        "</system_identity>\n\n"
        "<constraints>\n"
        "- Modo direto e imediato: proibido gerar <think>, raciocínio, notas de cena ou explicações. Use os tokens estritamente para Trad e Emo.\n"
        "- Use português falado do Brasil (ex: 'pra', 'tá'). Omita pronomes desnecessários (prefira 'Não vi' a 'Eu não vi') para sincronia labial.\n"
        "- NUNCA TRADUZA AO PÉ DA LETRA: Adapte expressões e gírias para o sentido real no português coloquial do Brasil (ex: 'messing with someone' -> brincando/zoando comigo; 'gas station' -> posto de gasolina; 'roadkill' -> bicho atropelado/na pista; 'heads up' -> atenção/cuidado; 'give me a break' -> me dá um tempo; 'get out' -> sai daqui/vaza).\n"
        "- CONTEXTO DO DIÁLOGO: Se houver <dialogue_context>, use a fala anterior e a próxima fala para entender a situação e a intenção, mas adapte ESTRITAMENTE o texto da tag <original_text>.\n"
        "- Preserve nomes próprios, marcas e codinomes militares.\n"
        f"- A fala adaptada deve ter no máximo cerca de {char_limit} caracteres.\n"
        "- Emoções permitidas estritamente: [RAIVA, TRISTE, FELIZ, URGENTE, SUSPENSE, DRAMATICO, NORMAL, CANTORIA].\n"
        "</constraints>\n\n"
        "<output_format>\n"
        "Trad: <sua tradução em português sem aspas e sem notas de cena>\n"
        "Emo: <EMOÇÃO>\n"
        "</output_format>\n\n"
        "<example>\n"
        'Input: "I don\'t think we should stay here any longer!"\n'
        "Output:\n"
        "Trad: Acho melhor a gente não ficar mais aqui!\n"
        "Emo: URGENTE\n"
        "</example>"
    )

def get_dubbing_user_content(
    txt_en: str,
    speaker_id: str,
    char_limit: int,
    word_limit: int,
    lore_str: str = "",
    glossary_str: str = "",
    context_str: str = ""
) -> str:
    """
    Retorna a mensagem do usuário com isolamento de dados brutos em tag XML <original_text>.
    """
    return (
        f"{lore_str}"
        f"{glossary_str}"
        f"{context_str}"
        f"Locutor da fala atual: {speaker_id}\n"
        f"Limite de tamanho: cerca de {char_limit} caracteres ({word_limit} palavras).\n\n"
        "Adapte para dublagem em PT-BR o texto contido na tag <original_text>:\n"
        f"<original_text>\n{txt_en}\n</original_text>\n"
        "/no_think"
    )

def format_chat_prompt(system_content: str, user_content: str, is_qwen: bool = True) -> Tuple[str, List[str]]:
    """
    Formata o prompt completo no formato ChatML nativo para Qwen ou no formato de turnos Gemma.
    """
    if is_qwen:
        prompt = (
            f"<|im_start|>system\n{system_content}<|im_end|>\n"
            f"<|im_start|>user\n{user_content}<|im_end|>\n"
            f"<|im_start|>assistant\nTrad: "
        )
        stop_tokens = ["<|im_end|>", "<|im_start|>"]
    else:
        prompt = (
            f"<start_of_turn>user\n{system_content}\n\n{user_content}<end_of_turn>\n"
            f"<start_of_turn>model\nTrad: "
        )
        stop_tokens = ["<end_of_turn>"]
    return prompt, stop_tokens

def get_contingency_prompt(
    txt_en: str,
    speaker_id: str,
    lore_str: str = "",
    glossary_str: str = "",
    context_str: str = "",
    is_qwen: bool = True
) -> Tuple[str, List[str]]:
    """
    Prompt de contingência direta sem metadados quando há falha ou alucinação.
    """
    system = (
        "<system_identity>\n"
        "Você é um Tradutor para Português Brasileiro (PT-BR). Modo direto: sem <think>, sem explicações e sem notas de cena.\n"
        "</system_identity>\n"
        "<output_format>\nTrad: <tradução em PT-BR falado e natural>\n</output_format>"
    )
    user = (
        f"{lore_str}{glossary_str}{context_str}"
        f"Locutor: {speaker_id}\n"
        "Traduza diretamente para PT-BR o texto da tag <original_text>:\n"
        f"<original_text>\n{txt_en}\n</original_text>\n"
        "/no_think"
    )
    return format_chat_prompt(system, user, is_qwen=is_qwen)

def get_cps_guard_prompt(
    txt_en: str,
    traducao: str,
    duration: float,
    char_limit: int,
    is_qwen: bool = True
) -> Tuple[str, List[str]]:
    """
    Prompt do CPS_GUARD para condensar texto que excedeu o tempo de fala.
    """
    system = (
        "<system_identity>\n"
        "Você é um adaptador de dublagem PT-BR. MODO DIRETO: sem <think>, sem explicações e sem notas de cena.\n"
        "</system_identity>\n"
        "<output_format>\nTrad: <frase final resumida>\n</output_format>"
    )
    user = (
        f"Original EN: \"{txt_en}\"\n"
        f"Tradução longa: \"{traducao}\"\n"
        f"Duração disponível: {duration:.3f} segundos.\n"
        f"LIMITE OBRIGATÓRIO: no máximo {char_limit} caracteres, contando espaços e pontuação.\n"
        "Reescreva de forma ultra-concisa e natural em PT-BR para caber na boca do personagem, preservando o sentido essencial."
    )
    return format_chat_prompt(system, user, is_qwen=is_qwen)

def get_direct_fallback_prompt(txt_en: str, is_qwen: bool = True) -> str:
    """
    Prompt de último recurso (Zero English Shield) para evitar texto em inglês.
    """
    if is_qwen:
        return (
            f"<|im_start|>user\nModo direto, sem <think>. Traduza para português brasileiro o texto: \"{txt_en}\"\n/no_think<|im_end|>\n"
            f"<|im_start|>assistant\nTrad: "
        )
    return f"<start_of_turn>user\nTraduza para português brasileiro: \"{txt_en}\"<end_of_turn>\n<start_of_turn>model\nTrad: "
