"""Shared JSON persistence without importing model loaders."""
import json
import logging
import os
import time
from pathlib import Path

def safe_json_write(data, path, indent=4, ensure_ascii=False, retries=5, delay=0.2):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + '.tmp')
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
    except Exception as e:
        logging.error(f"ERRO CRÍTICO ao escrever no ficheiro temporário {temp_path}: {e}")
        return
    for attempt in range(retries):
        try:
            os.replace(temp_path, path)
            return
        except PermissionError as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                logging.error(f"ERRO CRÍTICO na tentativa final de escrever em {path}: {e}")
        except Exception as e:
            logging.error(f"ERRO CRÍTICO inesperado ao substituir {path} com {temp_path}: {e}")
            break

def safe_json_read(path, retries=5, delay=0.1):
    path = Path(path)
    for attempt in range(retries):
        try:
            if not path.exists(): return None
            if path.stat().st_size == 0:
                raise json.JSONDecodeError("Ficheiro temporariamente vazio (sendo escrito)", "", 0)
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (PermissionError, OSError, json.JSONDecodeError) as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                if isinstance(e, json.JSONDecodeError):
                    logging.error(f"Ficheiro JSON corrompido detectado em {path} após {retries} tentativas: {e}")
                    corrupt_path = path.with_name(f"{path.stem}.corrupt_{int(time.time())}{path.suffix}")
                    try:
                        os.replace(path, corrupt_path)
                    except: pass
                return None
        except Exception:
            return None
    return None

