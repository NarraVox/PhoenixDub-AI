# -*- coding: utf-8 -*-
import os
import sys
import logging
from pathlib import Path

# Configuração de caminhos e DLLs
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import ctypes
    base_env = Path(sys.executable).parent.parent
    site_packages = base_env / "Lib" / "site-packages"
    
    project_dir = Path(__file__).parent.parent.resolve()
    dll_paths = [
        site_packages / "llama_cpp" / "lib",
        project_dir / "env" / "tools_acestep",
        site_packages / "torch" / "lib",
        site_packages / "nvidia" / "cublas" / "bin",
        site_packages / "nvidia" / "cuda_runtime" / "bin",
        site_packages / "nvidia" / "cuda_nvrtc" / "bin"
    ]
    
    for p in dll_paths:
        if p.exists():
            os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                try: os.add_dll_directory(str(p))
                except: pass
            try: ctypes.windll.kernel32.SetDllDirectoryW(str(p))
            except: pass
except Exception as e:
    print(f"Aviso no carregamento de DLLs: {e}")

from nexus.core import model_loader
from llama_cpp.server.app import create_app
from llama_cpp.server.settings import Settings
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    print("=" * 60)
    print("        NEXUS LOCAL IA SERVER - REPLICANDO OPENAI API")
    print("        (llama-cpp-python / CUDA Acelerado)")
    print("=" * 60)
    print()

    import json
    config_path = Path(__file__).parent.parent / "nexus" / "core" / "server_config.json"
    
    # Valores padrão
    host = "127.0.0.1"
    port = 1234
    model_str = None
    n_gpu_layers = -1
    n_ctx = 4096
    flash_attn = True
    
    # Cálculo inteligente de threads para evitar travamentos (llama.cpp prefere cores físicos)
    try:
        import psutil
        physical_cores = psutil.cpu_count(logical=False) or 4
    except:
        import os
        physical_cores = os.cpu_count() // 2 or 2
    n_threads = max(1, physical_cores - 1)
    
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                host = config.get("host", host)
                port = config.get("port", port)
                model_str = config.get("model_path", model_str)
                n_gpu_layers = config.get("n_gpu_layers", n_gpu_layers)
                n_ctx = config.get("n_ctx", n_ctx)
                flash_attn = config.get("flash_attn", flash_attn)
                print(f"⚙️ Configurações carregadas de server_config.json")
        except Exception as e:
            print(f"⚠️ Erro ao ler server_config.json: {e}. Usando padrões.")
            
    if not model_str:
        model_path = model_loader.find_gemma_model_path()
        if not model_path:
            print("❌ ERRO: Modelo Qwen3.5 ou Gemma 4 não encontrado.")
            print("Por favor, execute o TESTAR_SETUP.bat para baixar o modelo de IA.")
            sys.exit(1)
        model_str = str(model_path)
    else:
        model_path = Path(model_str)

    print(f"📦 Modelo selecionado: {model_path.name}")
    print(f"🔌 Iniciando servidor em http://{host}:{port} ...")
    print(f"💡 Agora você pode rodar o Aider ou conectar qualquer programa na porta {port}.")
    print("-" * 60)

    # Configurações do servidor e do modelo em uma única classe flat Settings
    settings_kwargs = {
        "host": host,
        "port": port,
        "model": model_str,
        "model_alias": "openai/gemma-4", # Alias para compatibilidade Aider/OpenAI
        "n_gpu_layers": n_gpu_layers,
        "n_ctx": n_ctx,
        "flash_attn": flash_attn,
        "n_threads": n_threads,
        "offload_kqv": True,
        "use_mmap": False
    }

    # Detecção automática de modelo de visão Qwen2-VL
    if "qwen2-vl" in model_path.name.lower():
        mmproj_name = "mmproj-Qwen2-VL-2B-Instruct-f16.gguf"
        mmproj_path = model_path.parent / mmproj_name
        if mmproj_path.exists():
            print(f"👁️  [VISÃO] Modelo Qwen2-VL detectado! Carregando projetor mmproj: {mmproj_name}")
            settings_kwargs["clip_model_path"] = str(mmproj_path.resolve())
            settings_kwargs["chat_format"] = "qwen2-vl"
        else:
            print(f"⚠️ [AVISO] Modelo Qwen2-VL detectado, mas o projetor {mmproj_name} não foi encontrado em {model_path.parent}!")

    settings = Settings(**settings_kwargs)

    try:
        app = create_app(settings=settings)
        uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")
    except KeyboardInterrupt:
        print("\n👋 Servidor encerrado pelo usuário.")
    except Exception as e:
        print(f"\n❌ Falha ao iniciar servidor local: {e}")

if __name__ == "__main__":
    main()
