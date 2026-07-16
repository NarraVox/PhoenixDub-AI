import os
import sys
import ctypes
from pathlib import Path

# --- INJEÇÃO DINÂMICA DE DLLS CUDA (v2026.RTX) ---
base_env = Path(sys.executable).parent.parent
site_packages = base_env / "Lib" / "site-packages"

# Coleta diretórios de DLLs
dll_dirs = [
    site_packages / "torch" / "lib",
    site_packages / "llama_cpp" / "lib",
]

# Adiciona ao path do Windows e DLL directory
for p in dll_dirs:
    if p.exists():
        os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(p))
            except Exception:
                pass

# Pré-carrega DLLs em ordem para resolver dependências no Windows (evitando falha winmode de ctypes)
preload_dlls = [
    # CUDA do PyTorch
    site_packages / "torch" / "lib" / "cudart64_12.dll",
    site_packages / "torch" / "lib" / "cublasLt64_12.dll",
    site_packages / "torch" / "lib" / "cublas64_12.dll",
    # llama_cpp
    site_packages / "llama_cpp" / "lib" / "ggml-base.dll",
    site_packages / "llama_cpp" / "lib" / "ggml.dll",
    site_packages / "llama_cpp" / "lib" / "ggml-cpu.dll",
    site_packages / "llama_cpp" / "lib" / "ggml-cuda.dll",
    site_packages / "llama_cpp" / "lib" / "mtmd.dll",
    site_packages / "llama_cpp" / "lib" / "llama.dll",
]

print("[INFO] Pré-carregando DLLs de GPU/CUDA...")
for dll_path in preload_dlls:
    if dll_path.exists():
        try:
            ctypes.CDLL(str(dll_path))
        except Exception as e:
            print(f"[AVISO] Falha ao pré-carregar {dll_path.name}: {e}")

# --- IMPORTA E INICIA O SERVIDOR DO LLAMA_CPP ---
try:
    import llama_cpp.server.__main__ as server_main
except ImportError:
    print("[ERRO] Dependências do servidor do llama-cpp-python ausentes.")
    print("Instalando dependências necessárias do servidor...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "llama-cpp-python[server]"])
    import llama_cpp.server.__main__ as server_main

def find_alternative_model(current_path):
    import os
    from pathlib import Path
    if current_path and os.path.exists(current_path):
        return current_path

    # Caminhos para verificar
    root = Path("C:/IA_dublagem")
    possible_dirs = [
        root / "_MODELS_",
        root,
        Path("_MODELS_"),
        Path("uploads/_MODELS_"),
        Path(".")
    ]
    
    # 1. Tenta nomes de arquivos conhecidos
    known_filenames = [
        "Qwen3.5-4B-Q4_K_M.gguf",
        "gemma-4-E4B-it-qat-UD-Q4_K_XL.gguf",
        "gemma-4-E4B-it-Q4_K_M.gguf"
    ]
    for d in possible_dirs:
        if d.exists() and d.is_dir():
            for name in known_filenames:
                p = d / name
                if p.exists():
                    return str(p.resolve())

    # 2. Busca qualquer outro arquivo qwen*.gguf ou gemma*.gguf
    for d in possible_dirs:
        if d.exists() and d.is_dir():
            qwen_files = list(d.glob("*Qwen3.5*.gguf")) + list(d.glob("*qwen*.gguf"))
            qwen_files = [f for f in qwen_files if "tts" not in f.name.lower() and "embed" not in f.name.lower() and "acestep" not in f.name.lower()]
            if qwen_files:
                return str(qwen_files[0].resolve())
                
            gguf_files = list(d.glob("*gemma-4*.gguf"))
            if not gguf_files:
                gguf_files = list(d.glob("*gemma*.gguf"))
            if gguf_files:
                return str(gguf_files[0].resolve())
                
    return current_path

if __name__ == "__main__":
    # Ajusta os argumentos de inicialização dinamicamente para otimização de RAM e cache
    args = sys.argv[1:]
    
    # 1. Resolve dinamicamente o modelo caso a rota fornecida não exista
    if "--model" in args:
        idx = args.index("--model")
        if idx + 1 < len(args):
            model_val = args[idx + 1]
            resolved_model = find_alternative_model(model_val)
            if resolved_model != model_val:
                print(f"[NEXUS_SERVER] 🔎 Modelo original '{model_val}' não encontrado.")
                print(f"[NEXUS_SERVER] 👉 Utilizando modelo alternativo resolvido: {resolved_model}")
                args[idx + 1] = resolved_model

    # 2. Injeta configurações otimizadas de RAM e Cache
    if "--cache" not in args:
        args.extend(["--cache", "True"])
        print("[NEXUS_SERVER] 🧠 Cache de Prompt / KV habilitado (--cache True)")
        
    if "--cache_size" not in args:
        args.extend(["--cache_size", "1073741824"]) # 1 GB
        print("[NEXUS_SERVER] 🧠 Tamanho do Cache configurado para 1GB (--cache_size 1073741824)")
        
    if "--use_mmap" not in args:
        args.extend(["--use_mmap", "False"])
        print("[NEXUS_SERVER] 🏎️ Mapeamento de Memória desabilitado para economizar RAM (--use_mmap False)")

    sys.argv = [sys.argv[0]] + args

    # Repassa os argumentos do terminal diretamente para o servidor oficial
    server_main.main()
