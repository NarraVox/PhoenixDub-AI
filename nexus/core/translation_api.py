# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import time
import logging
import json
import requests
from pathlib import Path

# Runtime globals injected by __init__.py namespace patching:
# ai_global_lock, get_gemma_model, find_gemma_model_path

def make_gema_request_with_retries(payload, timeout=600, retries=5, backoff_factor=2, is_translation=True):
    import requests
    with ai_global_lock:
        system_prompt = payload['messages'][0]['content'] if payload['messages'][0]['role'] == 'system' else ""
        user_prompt = payload['messages'][1]['content'] if len(payload['messages']) > 1 else payload['messages'][0]['content']
        
        prefill = ""
        if not is_translation:
            prefill = "# DOSSIÊ DE LOCALIZAÇÃO: LORE GLOBAL\n\n"
            
        llm = get_gemma_model()
        is_qwen = False
        p = find_gemma_model_path()
        if p and "qwen" in p.name.lower():
            is_qwen = True
        elif llm and llm != "standalone_server" and hasattr(llm, "model_path"):
            if "qwen" in str(llm.model_path).lower():
                is_qwen = True
                
        if is_qwen:
            if system_prompt:
                full_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n{prefill}"
            else:
                full_prompt = f"<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n{prefill}"
            stop_tokens = ["<|im_end|>", "<|im_start|>"]
        else:
            if system_prompt:
                full_prompt = f"<start_of_turn>user\n{system_prompt}\n\n{user_prompt}<end_of_turn>\n<start_of_turn>model\n{prefill}"
            else:
                full_prompt = f"<start_of_turn>user\n{user_prompt}<end_of_turn>\n<start_of_turn>model\n{prefill}"
            stop_tokens = ["<end_of_turn>"]

        if llm and llm != "standalone_server":
            try:
                response_data = llm(
                    full_prompt,
                    temperature=payload.get('temperature', 0.3),
                    max_tokens=payload.get('max_tokens', 1024),
                    stop=payload.get('stop', stop_tokens)
                )
                chat_compat_data = {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": prefill + response_data['choices'][0]['text']
                            }
                        }
                    ]
                }
                class MockResponse:
                    def __init__(self, json_data):
                        self._json_data = json_data
                        self.status_code = 200
                    def json(self): return self._json_data
                    def raise_for_status(self): pass
                return MockResponse(chat_compat_data)
            except Exception as e:
                logging.error(f"Erro no motor nativo: {e}")

        urls = [
            "http://127.0.0.1:8080/v1/completions",
            "http://127.0.0.1:1234/v1/completions"
        ]
        
        last_err = ""
        for url in urls:
            for attempt in range(10):
                try:
                    completions_payload = {
                        "prompt": full_prompt,
                        "temperature": payload.get('temperature', 0.3),
                        "max_tokens": payload.get('max_tokens', 1024),
                        "model": "local-model",
                        "stop": payload.get('stop', stop_tokens)
                    }
                    res = requests.post(url, json=completions_payload, timeout=timeout)
                    
                    if res.status_code == 200:
                        res_json = res.json()
                        chat_compat_data = {
                            "choices": [
                                {
                                    "message": {
                                        "role": "assistant",
                                        "content": prefill + res_json['choices'][0]['text']
                                    }
                                }
                            ]
                        }
                        class MockResponse:
                            def __init__(self, json_data):
                                    self._json_data = json_data
                                    self.status_code = 200
                            def json(self): return self._json_data
                            def raise_for_status(self): pass
                        return MockResponse(chat_compat_data)
                        
                    elif res.status_code == 503:
                        logging.info(f"⏳ [Aguardando] O motor {url} ainda está carregando o modelo... (Tentativa {attempt+1}/10)")
                        time.sleep(5)
                        continue
                    else:
                        last_err = f"Status {res.status_code} em {url}"
                        logging.warning(f"⚠️ Servidor {url} retornou erro: {res.text[:100]}")
                        break
                except Exception as e:
                    last_err = str(e)
                    break

        raise RuntimeError(f"❌ FALHA GERAL: Nenhum motor de IA respondeu. (Último erro: {last_err})")
