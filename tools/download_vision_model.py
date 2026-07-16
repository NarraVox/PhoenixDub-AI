import os
import sys
from pathlib import Path
from huggingface_hub import hf_hub_download

def main():
    model_dir = Path("C:/IA_dublagem/_MODELS_")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    repo = "bartowski/Qwen2-VL-2B-Instruct-GGUF"
    
    files = [
        "Qwen2-VL-2B-Instruct-Q4_K_M.gguf",
        "mmproj-Qwen2-VL-2B-Instruct-f16.gguf"
    ]
    
    print("=" * 60)
    print("      NARRAVOX - BAIXANDO MODELO DE VISÃO QWEN2-VL-2B")
    print("=" * 60)
    
    for f in files:
        target_path = model_dir / f
        if target_path.exists():
            print(f"[-] O arquivo {f} já existe. Pulando download.")
            continue
            
        print(f"[+] Baixando {f} de {repo}...")
        try:
            hf_hub_download(
                repo_id=repo,
                filename=f,
                local_dir=str(model_dir.resolve()),
                local_dir_use_symlinks=False
            )
            print(f"[+] Download de {f} concluído!")
        except Exception as e:
            print(f"[ERRO] Erro ao baixar {f}: {e}")
            sys.exit(1)
            
    print("\n[SUCESSO] Todos os downloads concluídos!")
    print(f"Arquivos salvos em: {model_dir}")

if __name__ == "__main__":
    main()
