import PyInstaller.__main__
import os
import shutil
from pathlib import Path

def build_nexus_pro():
    print("Iniciando Build do Nexus AI Professional (Modo de Compatibilidade)...")
    
    app_name = "Nexus_AI_Pro"
    entry_point = "nexus_app.py"
    
    # Limpeza profunda
    for folder in ['build', 'dist', '__pycache__']:
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)

    # Configurações do PyInstaller
    # Usamos --collect-all para evitar o bug de analise de bytecode (IndexError)
    params = [
        entry_point,
        f'--name={app_name}',
        '--onefile',
        '--noconsole',
        '--clean',
        '--collect-all=webview',
        '--collect-all=clr_loader',
        '--collect-all=pythonnet',
        # Incluindo a pasta client (interface)
        '--add-data=client;client',
        '--add-data=requirements_RTX.txt;.',
        '--add-data=requirements_CPU.txt;.',
    ]

    print(f"Empacotando recursos (Coleta Bruta) e gerando {app_name}.exe...")
    try:
        PyInstaller.__main__.run(params)
    except Exception as e:
        print(f"Erro durante o build: {e}")
        return

    # Limpeza pós-build
    if os.path.exists(f"{app_name}.spec"):
        os.remove(f"{app_name}.spec")
        
    print("\n" + "="*50)
    print(f"SUCESSO! O seu programa principal está em: dist/{app_name}.exe")
    print("="*50)

if __name__ == "__main__":
    build_nexus_pro()


