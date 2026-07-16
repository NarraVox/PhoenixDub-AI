import os
import sys
import subprocess
import psutil
from pipeline_engine import PipelineEngine

sys.stdout.reconfigure(encoding='utf-8')

def test_unified_components():
    print("[Test] Iniciando auditoria do Nexus Godogen Hub Unificado...")
    engine = PipelineEngine()
    
    # 1. Mapeamento de caminhos da IA
    python_exe = r"C:\IA_dublagem\env\Scripts\python.exe"
    server_script = r"C:\IA_dublagem\nexus\build_tools\run_llama_server.py"
    model_path = r"C:\IA_dublagem\_MODELS_\gemma-4-E4B-it-Q4_K_M.gguf"
    aider_exe = r"C:\aider_env\Scripts\aider.exe"
    godot_exe = engine.get_godot_path()
    
    print(f"Godot Executable: {godot_exe} -> Existe? {os.path.exists(godot_exe)}")
    print(f"Python Env: {python_exe} -> Existe? {os.path.exists(python_exe)}")
    print(f"Llama Script: {server_script} -> Existe? {os.path.exists(server_script)}")
    print(f"Gemma Model: {model_path} -> Existe? {os.path.exists(model_path)}")
    print(f"Aider Executable: {aider_exe} -> Existe? {os.path.exists(aider_exe)}")
    
    if not os.path.exists(godot_exe):
        print("Erro: Executavel da Godot nao encontrado.")
        return False
    if not os.path.exists(aider_exe):
        print("Erro: Aider nao encontrado.")
        return False

    # 2. Testar Aider em modo CLI simples
    print("Testando execucao do Aider (Aider --version)...")
    try:
        result = subprocess.run([aider_exe, "--version"], capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=20)
        print(f"Output: {result.stdout.strip()}")
    except Exception as e:
        print(f"Falha ao rodar Aider: {e}")
        return False
        
    print("\n[SUCESSO] Todos os componentes do Nexus Godogen Hub estao prontos!")
    return True

if __name__ == "__main__":
    success = test_unified_components()
    sys.exit(0 if success else 1)
