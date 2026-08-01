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


def fast_tactical_translator(txt_en):
    clean = txt_en.strip()
    c_lower = re.sub(r'[\!\?\.\,]', '', clean.lower()).strip()

    clock_map = {
        "1": "uma hora", "one": "uma hora",
        "2": "duas horas", "two": "duas horas",
        "3": "três horas", "three": "três horas",
        "4": "quatro horas", "four": "quatro horas",
        "5": "cinco horas", "five": "cinco horas",
        "6": "seis horas", "six": "seis horas",
        "7": "sete horas", "seven": "sete horas",
        "8": "oito horas", "eight": "oito horas",
        "9": "nove horas", "nine": "nove horas",
        "10": "dez horas", "ten": "dez horas",
        "11": "onze horas", "eleven": "onze horas",
        "12": "doze horas", "twelve": "doze horas"
    }

    m_clock = re.search(r'contact(?:\s+at)?\s+(1[0-2]|[1-9]|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)(?:\s+o\'?clock)?', c_lower)
    if m_clock:
        num = m_clock.group(1)
        pt_time = clock_map.get(num, num)
        return f"Contato às {pt_time}!", "URGENTE"

    cardinal_map = {
        "north": "ao Norte", "south": "ao Sul", "east": "a Leste", "west": "a Oeste",
        "northeast": "a Nordeste", "northwest": "a Noroeste", "southeast": "a Sudeste", "southwest": "a Sudoeste"
    }

    for en_dir, pt_dir in cardinal_map.items():
        if c_lower in [f"contact {en_dir}", f"contact to the {en_dir}", f"contact to {en_dir}", f"enemies to the {en_dir}", f"tigers to the {en_dir}", f"contact {en_dir}"]:
            return f"Contato {pt_dir}!", "URGENTE"
        if c_lower == en_dir:
            return f"{pt_dir.replace('a ', '').replace('ao ', '').capitalize()}!", "URGENTE"

    floor_map = {
        "first floor": "no primeiro andar",
        "1st floor": "no primeiro andar",
        "second floor": "no segundo andar",
        "2nd floor": "no segundo andar",
        "third floor": "no terceiro andar",
        "3rd floor": "no terceiro andar",
        "ground floor": "no térreo",
        "roof": "no telhado",
        "rooftop": "no telhado",
        "balcony": "na varanda",
        "window": "na janela",
        "doorway": "na porta"
    }

    for fl_en, fl_pt in floor_map.items():
        if fl_en in c_lower:
            if "contact" in c_lower:
                return f"Contato {fl_pt}!", "URGENTE"
            elif "movement" in c_lower or "moving" in c_lower:
                return f"Movimento {fl_pt}!", "URGENTE"
            elif "roger" in c_lower or "copy" in c_lower:
                return f"Ciente, {fl_pt}!", "NORMAL"

    ack_dict = {
        "roger that": ("Copiado!", "NORMAL"),
        "copy that": ("Copiado!", "NORMAL"),
        "roger": ("Copiado!", "NORMAL"),
        "copy": ("Copiado!", "NORMAL"),
        "affirmative": ("Afirmativo!", "NORMAL"),
        "negative": ("Negativo!", "NORMAL"),
        "on it": ("Em andamento!", "URGENTE"),
        "got it": ("Copiado!", "NORMAL")
    }
    if c_lower in ack_dict:
        pt_t, emo = ack_dict[c_lower]
        return pt_t, emo

    tactical_dict = {
        "противник, два часа дня!": ("Inimigo, 2 horas!", "URGENTE"),
        "пехота, 12 часов!": ("Infanteria, 12 horas!", "URGENTE"),
        "цель слева!": ("Alvo à esquerda!", "URGENTE"),
        "атакуют слева!": ("Atacam pela esquerda!", "URGENTE"),
        "цель 7 часов!": ("Alvo 7 horas!", "URGENTE"),
        "обходят нас с тыла!": ("Eles nos flanqueiam pela retaguarda!", "URGENTE"),
        "противник с тыла!": ("Inimigo pela retaguarda!", "URGENTE"),
        "противник справа!": ("Inimigo à direita!", "URGENTE"),
        "противник, час дня!": ("Inimigo 1 hora!", "URGENTE"),
        "впереди враг!": ("Inimigo à frente!", "URGENTE"),
        "противник 10 часов!": ("Inimigo 10 horas!", "URGENTE"),
        "замечен противник на юго-западе!": ("Inimigo avistado ao Sudoeste!", "URGENTE"),
        "противник северо-запад!": ("Inimigo Noroeste!", "URGENTE"),
        "подходит с востока!": ("Aproxima-se pelo Leste!", "URGENTE"),
        "вижу противника на два часа!": ("Vejo inimigo às 2 horas!", "URGENTE"),
        "вражеская пехота на 12 часов!": ("Infanteria inimiga às 12 horas!", "URGENTE"),
        "они атакуют слева!": ("Eles atacam pela esquerda!", "URGENTE"),
        "враг сзади!": ("Inimigo atrás!", "URGENTE"),
        "справа! справа!": ("À direita! À direita!", "URGENTE"),
        "вижу противника справа!": ("Vejo inimigo à direita!", "URGENTE"),
        "противник на один час!": ("Inimigo a 1 hora!", "URGENTE"),
        "впереди солдаты противника!": ("Soldados inimigos à frente!", "URGENTE"),
        "впереди враг! огонь!": ("Inimigo à frente! Fogo!", "URGENTE"),
        "вижу противника на 10 часов!": ("Vejo inimigo às 10 horas!", "URGENTE"),
        "вражеская цель на западе!": ("Alvo inimigo ao Oeste!", "URGENTE"),
        "они атакуют с юго-востока!": ("Eles estão atacando pelo Sudeste!", "URGENTE"),
        "противник на юге!": ("Inimigo ao Sul!", "URGENTE"),
        "противник! северо-запад!": ("Inimigo! Noroeste!", "URGENTE"),
        "противник на северо-востоке!": ("Inimigo ao Nordeste!", "URGENTE"),
        "цель на севере!": ("Alvo ao Norte!", "URGENTE"),
        "ходят с востока!": ("Eles vêm do Leste!", "URGENTE"),
        "first floor, roger that!": ("Primeiro andar, copiado!", "URGENTE"),
        "contact 7 o'clock!": ("Contato 7 horas!", "URGENTE"),
        "contact 6 o'clock!": ("Contato 6 horas!", "URGENTE"),
        "showtime, 12 o'clock!": ("Hora do show, 12 horas!", "URGENTE"),
        "contact, you're 11 o'clock!": ("Contato, às 11 horas!", "URGENTE"),
        "conte to the north east!": ("Contato ao Nordeste!", "URGENTE"),
        "hey! check your fire!": ("Ei! Cuidado com os tiros!", "URGENTE"),
        "contact at five o'clock!": ("Contato às 5 horas!", "URGENTE"),
        "4 o'clock!": ("4 horas!", "URGENTE"),
        "contact, three o'clock!": ("Contato, 3 horas!", "URGENTE"),
        "contact at two o'clock!": ("Contato às 2 horas!", "URGENTE"),
        "contact! 11 o'clock!": ("Contato! 11 horas!", "URGENTE"),
        "10 o'clock!": ("10 horas!", "URGENTE"),
        "contact west!": ("Contato a Oeste!", "URGENTE"),
        "contact to the southwest!": ("Contato ao Sudoeste!", "URGENTE"),
        "contact south east!": ("Contato ao Sudeste!", "URGENTE"),
        "contact south!": ("Contato ao Sul!", "URGENTE"),
        "contact northwest!": ("Contato ao Noroeste!", "URGENTE"),
        "contact to the north east!": ("Contato ao Nordeste!", "URGENTE"),
        "contact north!": ("Contato ao Norte!", "URGENTE"),
        "contact east!": ("Contato a Leste!", "URGENTE"),
        "friendly fire!": ("Fogo amigo!", "URGENTE"),
        "contact at nine o'clock.": ("Contato às 9 horas.", "URGENTE"),
        "contact 8 o'clock!": ("Contato 8 horas!", "URGENTE"),
        "contact seven o'clock!": ("Contato 7 horas!", "URGENTE"),
        "contact six o'clock.": ("Contato 6 horas.", "URGENTE"),
        "contact at five o'clock.": ("Contato às 5 horas.", "URGENTE"),
        "contact four o'clock!": ("Contato 4 horas!", "URGENTE"),
        "contact three o'clock.": ("Contato 3 horas.", "URGENTE"),
        "contact at two o'clock.": ("Contato às 2 horas.", "URGENTE"),
        "contact at 10 o'clock.": ("Contato às 10 horas.", "URGENTE"),
        "contact to the west!": ("Contato ao Oeste!", "URGENTE"),
        "contact southwest!": ("Contato ao Sudoeste!", "URGENTE"),
        "contact southeast!": ("Contato ao Sudeste!", "URGENTE"),
        "contact north west!": ("Contato ao Noroeste!", "URGENTE"),
        "contact to the north east.": ("Contato ao Nordeste.", "URGENTE"),
        "contact to the north!": ("Contato ao Norte!", "URGENTE"),
        "contact to the east.": ("Contato a Leste.", "URGENTE"),
        "friendly fire! friendly fire!": ("Fogo amigo! Fogo amigo!", "URGENTE"),
        "hey, check your fire!": ("Ei, cuidado com os tiros!", "URGENTE"),
        "check your fire!": ("Cuidado com os tiros!", "URGENTE"),
        "the tall blue one on the left!": ("O azul alto à esquerda!", "URGENTE"),
        "contact! nine o'clock!": ("Contato! 9 horas!", "URGENTE"),
        "contact, seven o'clock!": ("Contato, 7 horas!", "URGENTE"),
        "contact! six o'clock!": ("Contato! 6 horas!", "URGENTE"),
        "contact 4 o'clock!": ("Contato 4 horas!", "URGENTE"),
        "contact! three o'clock!": ("Contato! 3 horas!", "URGENTE"),
        "contact two o'clock!": ("Contato 2 horas!", "URGENTE"),
        "contact one o'clock!": ("Contato 1 hora!", "URGENTE"),
        "contact! 12 o'clock!": ("Contato! 12 horas!", "URGENTE"),
        "contact 11 o'clock!": ("Contato 11 horas!", "URGENTE"),
        "contact, 10 o'clock!": ("Contato, 10 horas!", "URGENTE"),
        "coming from the west!": ("Vindo do Oeste!", "URGENTE"),
        "enemy southwest.": ("Inimigo a sudoeste.", "URGENTE"),
        "enemy to the south!": ("Inimigo ao sul!", "URGENTE"),
        "enemies to the northwest!": ("Inimigos ao noroeste!", "URGENTE"),
        "enemies to the northeast.": ("Inimigos ao nordeste.", "URGENTE"),
        "to the north!": ("Ao Norte!", "URGENTE"),
        "enemies in the white building!": ("Inimigos no edifício branco!", "URGENTE"),
        "enemies on the roof of the tall building!": ("Inimigos no teto do edifício alto!", "URGENTE"),
        "contact at 11 o'clock!": ("Contato às 11 horas!", "URGENTE"),
        "contact at 10 o'clock!": ("Contato às 10 horas!", "URGENTE"),
        "contact at 9 o'clock!": ("Contato às 9 horas!", "URGENTE"),
        "contact at 8 o'clock!": ("Contato às 8 horas!", "URGENTE"),
        "contact at 7 o'clock!": ("Contato às 7 horas!", "URGENTE"),
        "contact at 6 o'clock!": ("Contato às 6 horas!", "URGENTE"),
        "contact at 5 o'clock!": ("Contato às 5 horas!", "URGENTE"),
        "contact at 4 o'clock!": ("Contato às 4 horas!", "URGENTE"),
        "contact at 3 o'clock!": ("Contato às 3 horas!", "URGENTE"),
        "contact at 2 o'clock!": ("Contato às 2 horas!", "URGENTE"),
        "contact at 1 o'clock!": ("Contato a 1 hora!", "URGENTE"),
        "contact at 12 o'clock!": ("Contato às 12 horas!", "URGENTE"),
        "the west": ("Ao Oeste", "URGENTE"),
        "i see enemies to the southwest!": ("Vejo inimigos ao sudoeste!", "URGENTE"),
        "they're attacking from the southeast!": ("Estão atacando pelo sudeste!", "URGENTE"),
        "the south!": ("Ao Sul!", "URGENTE"),
        "northwest.": ("Noroeste.", "URGENTE"),
        "i see enemies to the north east!": ("Vejo inimigos ao nordeste!", "URGENTE"),
        "i see them to the north!": ("Estou vendo eles ao norte!", "URGENTE"),
        "soldiers approaching from the east!": ("Soldados se aproximando pelo leste!", "URGENTE"),
        "quit showing off.": ("Pare de se amostrar.", "URGENTE"),
        "that's a new personal best.": ("Esse é um novo recorde pessoal.", "URGENTE"),
        "you can do better than that.": ("Você pode fazer melhor que isso.", "URGENTE"),
        "sprint to the finish!": ("Pique total para a chegada!", "URGENTE"),
        "drop those tangos!": ("Derrube esses alvos!", "URGENTE"),
        "on your go, frost.": ("Quando quiser, Frost.", "URGENTE"),
        "dogs approaching!": ("Cães se aproximando!", "URGENTE"),
        "move, move, move!": ("Mova-se, mova-se, mova-se!", "URGENTE"),
        "no good. run it again.": ("Insuficiente. Faça de novo.", "URGENTE"),
        "nicely done.": ("Belo trabalho.", "URGENTE"),
        "we got stragglers!": ("Temos retardatários!", "URGENTE"),
        "we're gonna need another way out of here!": ("Precisamos de outra saída daqui!", "URGENTE"),
        "all clear!": ("Tudo limpo!", "URGENTE"),
        "i see him!": ("Estou vendo ele!", "URGENTE"),
        "i'm good!": ("Estou bem!", "URGENTE"),
        "we're clear!": ("Tudo limpo!", "URGENTE"),
        "the president is secure!": ("O Presidente está em segurança!", "URGENTE"),
        "we gotta go now!": ("Temos que ir agora!", "URGENTE"),
        "any bright ideas?": ("Alguma ideia brilhante?", "URGENTE"),
        "there they are!": ("Eles estão ali!", "URGENTE"),
        "contact 12 o'clock!": ("Contato às 12 horas!", "URGENTE"),
        "watch the left flank!": ("Cuidado com o flanco esquerdo!", "URGENTE"),
        "i hope this works.": ("Espero que isso funcione.", "URGENTE"),
        "sniper in the tower!": ("Atirador na torre!", "URGENTE"),
        "get down!": ("Se abaixa!", "URGENTE"),
        "stay with me, son!": ("Fica comigo, garoto!", "URGENTE"),
        "makarov knows yuri...": ("O Makarov... conhece o... Yuri...", "URGENTE"),
        "price, we have to move!": ("Price, temos que sair daqui!", "URGENTE"),
        "soap! no! no, no, no!": ("Soap! Não! Não, não, não!", "URGENTE"),
        "perfect.": ("Perfeito!", "URGENTE"),
        "move up.": ("Avançar!", "URGENTE"),
        "do you like the smell of this place? come on, let's go!": ("Gosta do cheiro deste lugar? Vamos, mexam-se!", "URGENTE"),
        "hurry, we don't have much time!": ("Rápido, não temos muito tempo!", "URGENTE"),
        "give me your hand.": ("Me dá a sua mão.", "URGENTE"),
        "what took you so long?": ("Por que demorou tanto?", "URGENTE"),
        "cough cough cough": ("Cough Cough Cough", "URGENTE"),
        "hold your fire!": ("Cessar fogo!", "URGENTE"),
        "friendly forces in the area!": ("Aliados na área!", "URGENTE"),
        "danger close!": ("Perigo próximo!", "URGENTE"),
        "firing 40mm.": ("Disparando 40mm!", "URGENTE"),
        "firing 105mm.": ("Disparando 105mm!", "URGENTE"),
        "target destroyed!": ("Alvo destruído!", "URGENTE"),
        "direct hit!": ("Impacto direto!", "URGENTE"),
        "solid kill.": ("Baixa confirmada!", "URGENTE"),
        "good kill.": ("Boa baixa!", "URGENTE"),
        "good tone, fox 3.": ("Tom bom, Fox 3!", "URGENTE"),
        "circling around to the north.": ("Circulando pelo norte.", "URGENTE"),
        "take out those guys.": ("Elimina aqueles caras!", "URGENTE"),
        "roger.": ("Copiado!", "URGENTE"),
        "fire on that building.": ("Fogo naquele prédio!", "URGENTE"),
        "flares, flares.": ("Flares, Flares!", "URGENTE"),
        "light it up.": ("Abre fogo!", "URGENTE"),
        "good job.": ("Bom trabalho!", "URGENTE"),
        "roger, overlord. we're inbound.": ("Copiado, Overlord. Estamos a caminho.", "URGENTE"),
        "roger that, 24.": ("Copiado, 24.", "URGENTE"),
        "im hit!": ("Fui atingido!", "URGENTE"),
        "man down!": ("Soldado abatido!", "URGENTE"),
        "target neutralized!": ("Alvo neutralizado!", "URGENTE"),
        "target down!": ("Alvo abatido!", "URGENTE"),
        "tango down!": ("Inimigo abatido!", "URGENTE"),
        "area clear!": ("Área limpa!", "URGENTE"),
        "clear!": ("Limpo!", "URGENTE"),
        "grenade!": ("Granada!", "URGENTE"),
        "rpg!": ("RPG à vista!", "URGENTE"),
        "cover me!": ("Me dá cobertura!", "URGENTE"),
        "reloading!": ("Recarregando!", "URGENTE"),
        "watch your fire!": ("Cuidado com o fogo amigo!", "URGENTE"),
        "providing cover fire, move up!": ("Dando fogo de cobertura, avança!", "URGENTE"),
        "adios.": ("Até mais.", "URGENTE"),
        "the balcony's clear!": ("A varanda está limpa!", "URGENTE"),
        "contact!": ("Contato!", "URGENTE"),
        "got you covered!": ("Cobertura garantida!", "URGENTE"),
        "i'm on it.": ("Deixa comigo!", "URGENTE"),
        "raj.": ("Copiado!", "URGENTE"),
        "contact memorial building to the north.": ("Contato no Edifício Memorial ao norte!", "URGENTE"),
        "shooter's in the store below. switch them off.": ("Atirador na loja abaixo. Neutraliza ele!", "URGENTE"),
        "we got company!": ("Temos companhia!", "URGENTE"),
        "moving!": ("EM MOVIMENTO!", "URGENTE"),
        "russian armor incoming!": ("Blindados russos se aproximando!", "URGENTE"),
        "truck, you getting anything on your comms?": ("Truck, pegou alguma coisa no rádio?", "URGENTE"),
        "i like it.": ("Assim que se faz!", "URGENTE"),
        "frost, get in here!": ("Frost, vem pra cá!", "URGENTE"),
        "contact front hostels in the open!": ("Contato à frente! Inimigos a campo aberto!", "URGENTE"),
        "no shit!": ("Sério mesmo?!", "URGENTE"),
        "move move move!": ("VAI! VAI! VAI!", "URGENTE"),
        "we're good!": ("Estamos bem!", "URGENTE"),
        "we got you loud and clear.": ("Copiado alto e claro!", "URGENTE"),
        "good kill, good kill.": ("Alvo destruído, boa baixa!", "URGENTE"),
        "good tone, fox 3, fox 3.": ("Tom bom! Fox 3, Fox 3!", "URGENTE"),
        "check your fire": ("Cuidado com o fogo amigo!", "RAIVA"),
        "jack your fire": ("Cuidado com o fogo amigo!", "RAIVA"),
        "watch your fire": ("Cuidado com o fogo amigo!", "RAIVA"),
        "friendly fire friendly fire": ("Fogo amigo! Fogo amigo!", "RAIVA"),
        "friendly fire": ("Fogo amigo!", "RAIVA"),
        "reloading": ("Recarregando!", "URGENTE"),
        "im reloading": ("Tô recarregando!", "URGENTE"),
        "reloading get cover": ("Recarregando, busca cobertura!", "URGENTE"),
        "cover me": ("Me dá cobertura!", "URGENTE"),
        "cover me im reloading": ("Me dá cobertura, tô recarregando!", "URGENTE"),
        "grenade": ("Granada!", "URGENTE"),
        "frag out": ("Lançando granada!", "URGENTE"),
        "flashbang out": ("Lançando granada de luz!", "URGENTE"),
        "smoke out": ("Lançando fumaça!", "URGENTE"),
        "rpg": ("RPG à vista!", "URGENTE"),
        "sniper": ("Atirador de elite!", "URGENTE"),
        "sniper get down": ("Atirador de elite, se abaixa!", "URGENTE"),
        "man down": ("Soldado abatido!", "DRAMATICO"),
        "im hit": ("Fui atingido!", "URGENTE"),
        "im hit im hit": ("Fui atingido! Fui atingido!", "URGENTE"),
        "taking fire": ("Sob fogo inimigo!", "URGENTE"),
        "under fire": ("Sob fogo inimigo!", "URGENTE"),
        "clear": ("Limpo!", "NORMAL"),
        "area clear": ("Área limpa!", "NORMAL"),
        "all clear": ("Tudo limpo!", "NORMAL"),
        "move move": ("VAI! VAI!", "URGENTE"),
        "move up": ("Avançar!", "URGENTE"),
        "move in": ("Entrando!", "URGENTE"),
        "push forward": ("Avançar!", "URGENTE"),
        "fall back": ("Recuar!", "URGENTE"),
        "hold your ground": ("Mantenham a posição!", "RAIVA"),
        "hold this position": ("Mantenham esta posição!", "RAIVA"),
        "get down": ("Se abaixa!", "URGENTE"),
        "get in cover": ("Busquem cobertura!", "URGENTE"),
        "head down": ("Cabeça baixa!", "URGENTE"),
        "area secure": ("Área limpa!", "NORMAL"),
        "flash out": ("Lançando atordoante!", "URGENTE"),
        "throwing frag": ("Lançando granada!", "URGENTE"),
        "throw in c4": ("Instalando C4!", "URGENTE"),
        "deploying c4": ("Instalando C4!", "URGENTE"),
        "im bleeding out": ("Estou sangrando!", "DRAMATICO"),
        "hurry im bleeding out": ("Rápido, estou sangrando!", "DRAMATICO"),
        "on comms": ("Na frequência!", "NORMAL"),
        "contacting hq": ("Contatando o Comando!", "NORMAL"),
        "target neutralized": ("Alvo neutralizado!", "NORMAL"),
        "target down": ("Alvo abatido!", "URGENTE"),
        "tango down": ("Inimigo abatido!", "URGENTE"),
        "enemy down": ("Inimigo no chão!", "URGENTE"),
        "hes down": ("Ele caiu!", "URGENTE"),
        "mark and drop zone": ("Marcando zona de pouso!", "NORMAL"),
        "russian armor incoming": ("Blindados russos se aproximando!", "URGENTE"),
        "move move move": ("VAI! VAI! VAI!", "URGENTE"),
        "moving": ("EM MOVIMENTO!", "URGENTE"),
        "we got company": ("Temos companhia!", "URGENTE"),
        "got you covered": ("Cobertura garantida!", "NORMAL"),
        "providing cover fire move up": ("Fogo de cobertura, avança!", "URGENTE"),
        "the balconys clear": ("A varanda está limpa!", "NORMAL"),
        "contact": ("Contato!", "URGENTE"),
        "we got you loud and clear": ("Copiado alto e claro!", "NORMAL"),
        "were good": ("Estamos bem!", "NORMAL"),
        "im on it": ("Deixa comigo!", "NORMAL")
    }

    if c_lower in tactical_dict:
        pt_t, emo = tactical_dict[c_lower]
        return pt_t, emo

    return None, None

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
            "15. PRESERVAÇÃO DE NOMES E CODINOMES DE PERSONAGENS: NUNCA altere ou traduza codinomes militares ou nomes próprios ingleses de pessoas (mantenha 'Frost', 'Sandman', 'Soap', 'Granite', 'Valkyrie', 'Roach' exatamente iguais se referirem a pessoas ou equipes, NUNCA mude para 'Frio', 'Fria', 'Sabão', 'Granito' ou traduções literais. Caso a palavra se refira ao objeto físico real em outro contexto, como 'sabonete/sabão' para a palavra 'soap', traduza normalmente).\n"
            "16. RIGOR GRAMATICAL BRASILEIRO: NUNCA invente palavras no português (ex: não use 'expulsoar' em vez de 'expulsar'). Garanta a concordância gramatical correta e a naturalidade coloquial das expressões (ex: use 'desumano' em vez de 'inumano'; 'viver nas próprias fezes' em vez de 'na própria fezes'; 'acorrentados' em vez de 'encadeados').\n"
            "17. CORREÇÃO DE TRANCRICAO (ASR REPAIR): O texto original em inglês foi gerado por um modelo de áudio (Whisper) e pode conter erros de audição (ex: transcrever 'root to port' em vez de 'ripped apart' em uma cena de guerra). Use o Contexto da Cena fornecido para deduzir o sentido correto do que o locutor quis dizer caso o texto original pareça estranho ou sem sentido, e gere a tradução baseada na fala corrigida."
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
            # [v2026.FAST_MODE] Prefill 'Trad:' forca resposta direta sem thinking prolixo.
            # Budget Forcing via prompt nao funciona no llama.cpp: o modelo 4B ignora
            # limites quantitativos e gera 200-400 tokens de thinking em vez de 30,
            # tornando cada frase 7x mais lenta (37s vs 5s). Revertido para modo rapido.
            # Qualidade ja e 89.6% com dicionario tatico + 17 regras do sistema.
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
        
        # max_tokens: 64 tokens e suficiente para Trad: + Emo: com prefill direto
        max_tokens_to_use = 64
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
