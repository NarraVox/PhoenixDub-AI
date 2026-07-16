# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import os
import sys
import json
import time
import subprocess
import logging
import threading
from pathlib import Path
import psutil

logger = logging.getLogger("AiderDashboard.Services")

# Globais de controle dos processos
server_process = None
aider_process = None
transcribe_process = None
render_process = None

ROOT_DIR = Path(__file__).parent.parent.resolve()
MODELS_DIR = Path("C:/IA_dublagem/_MODELS_")
CONFIG_PATH = ROOT_DIR / "nexus" / "core" / "server_config.json"
LOGS_DIR = ROOT_DIR / "logs"

SERVER_LOG = LOGS_DIR / "server_log.txt"
AIDER_LOG = LOGS_DIR / "aider_log.txt"
TRANSCRIBE_LOG = LOGS_DIR / "transcribe_log.txt"
RENDER_LOG = LOGS_DIR / "render_log.txt"

def get_gpu_memory():
    """Obtém dados da memória VRAM via nvidia-smi."""
    try:
        import torch
        if not torch.cuda.is_available():
            return {"free_mb": 0, "total_mb": 0, "used_mb": 0, "used_percent": 0, "error": True, "msg": "CUDA não disponível"}
        
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free,memory.total,memory.used", "--format=csv,nounits,noheader"],
            capture_output=True,
            text=True,
            check=True
        )
        lines = res.stdout.strip().split("\n")
        if lines:
            parts = [int(x.strip()) for x in lines[0].split(",")]
            return {
                "free_mb": parts[0], "total_mb": parts[1], "used_mb": parts[2],
                "used_percent": round((parts[2] / parts[1]) * 100, 1), "error": False
            }
    except Exception as e:
        logger.warning(f"Falha ao consultar GPU: {e}")
    return {"free_mb": 0, "total_mb": 6144, "used_mb": 0, "used_percent": 0, "error": True, "msg": "nvidia-smi falhou ou não encontrado"}

def get_system_stats():
    cpu_percent = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    gpu = get_gpu_memory()
    return {
        "cpu_percent": cpu_percent,
        "ram_used_gb": round(ram.used / (1024**3), 2),
        "ram_total_gb": round(ram.total / (1024**3), 2),
        "ram_percent": ram.percent,
        "gpu": gpu,
        "cpu_physical": psutil.cpu_count(logical=False) or 4,
        "cpu_logical": psutil.cpu_count(logical=True) or 4
    }

def get_models_list():
    models = []
    if MODELS_DIR.exists() and MODELS_DIR.is_dir():
        for item in MODELS_DIR.glob("*.gguf"):
            if "vae" in item.name.lower() or "embed" in item.name.lower():
                continue
            size_gb = round(item.stat().st_size / (1024**3), 2)
            models.append({"name": item.name, "path": str(item.resolve()), "size_gb": size_gb})
    models.sort(key=lambda x: x["name"])
    return models

def load_config():
    default_config = {
        "model_path": "C:/IA_dublagem/_MODELS_/Qwen3.5-4B-Q4_K_M.gguf",
        "n_ctx": 4096, "n_gpu_layers": 33, "flash_attn": True,
        "port": 1234, "host": "127.0.0.1"
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for k, v in saved.items():
                    default_config[k] = v
        except Exception as e:
            logger.error(f"Erro ao carregar config: {e}")
    return default_config

def save_config(config):
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar config: {e}")
        return False

def check_server_online(host, port):
    import requests
    url = f"http://{host}:{port}/v1/models"
    try:
        res = requests.get(url, timeout=1)
        return res.status_code == 200
    except:
        return False

def stop_processes():
    global server_process, aider_process, transcribe_process, render_process
    logger.info("Encerrando processos de background...")
    
    for p_name, p in [("Transcriber", transcribe_process), ("Renderer", render_process), ("Aider", aider_process), ("llama server", server_process)]:
        if p is not None:
            try:
                logger.info(f"Terminando {p_name}...")
                p.terminate()
                p.wait(timeout=2)
            except: pass
    
    transcribe_process = None
    render_process = None
    aider_process = None
    server_process = None
    
    if os.name == 'nt':
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'llama-server.exe', '/T'], capture_output=True)
            subprocess.run(['taskkill', '/F', '/IM', 'aider.exe', '/T'], capture_output=True)
        except Exception as e:
            logger.warning(f"Erro no taskkill: {e}")
            
    try:
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception as e:
        logger.warning(f"Erro no garbage collection CUDA: {e}")
    logger.info("VRAM limpa com sucesso.")
