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

if __name__ == "__main__":
    # Repassa os argumentos do terminal diretamente para o servidor oficial
    server_main.main()
