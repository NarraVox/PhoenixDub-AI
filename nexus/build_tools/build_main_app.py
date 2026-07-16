import PyInstaller.__main__
import os
import shutil
from pathlib import Path

def build_nexus_pro():
    # [ORGANIZATION FIX] Sobe para a raiz para garantir caminhos corretos dinamicamente
    root_dir = Path(__file__).parent.parent.parent.resolve()
    os.chdir(root_dir)

    print("Iniciando Build do Nexus AI Professional (Modo de Compatibilidade)...")
    
    app_name = "Nexus_AI_Pro"
    entry_point = "Nexus_AI_Pro.py"
    
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
        f'--distpath={os.path.abspath(os.path.join(os.getcwd(), "dist"))}',
        f'--workpath={os.path.abspath(os.path.join(os.getcwd(), "build"))}',
        '--collect-all=webview',
        '--collect-all=clr_loader',
        '--collect-all=pythonnet',
        # Incluindo a pasta client (interface) com caminhos absolutos para evitar erro de .spec no PyInstaller
        f'--add-data={os.path.abspath(os.path.join(os.getcwd(), "nexus", "client"))};client',
        f'--add-data={os.path.abspath(os.path.join(os.getcwd(), "requirements.txt"))};.',
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
        
    # Copia o executável gerado para a raiz do repositório para o build_setup.py empacotar
    final_exe_src = os.path.join(os.getcwd(), "dist", f"{app_name}.exe")
    final_exe_dest = os.path.join(os.getcwd(), f"{app_name}.exe")
    
    if os.path.exists(final_exe_src):
        shutil.copy2(final_exe_src, final_exe_dest)
        print(f"\n[COPIA] Executavel copiado com sucesso para a raiz: {final_exe_dest}")
    else:
        print(f"\n[ERRO] O executavel {final_exe_src} nao foi gerado.")

    print("\n" + "="*50)
    print(f"SUCESSO! O seu programa principal esta em: dist/{app_name}.exe")
    print("="*50)

if __name__ == "__main__":
    build_nexus_pro()


