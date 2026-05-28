import os
import sys
import PyInstaller.__main__
import shutil
import time
import traceback

def clean_folder(folder):
    """Tenta deletar uma pasta, ignorando erros se estiver travada."""
    if os.path.exists(folder):
        print(f"Limpando {folder}...")
        for i in range(5):
            try:
                shutil.rmtree(folder)
                return
            except Exception:
                time.sleep(0.5)
        print(f"Aviso: Nao foi possivel limpar {folder} totalmente.")

def build():
    # [ORGANIZATION FIX] Sobe para a raiz para garantir caminhos corretos
    os.chdir("..")
    
    print("="*50)
    print("INICIANDO BUILD FINAL (MODO ROBUSTO)")
    print("="*50)

    # Pastas temporárias centralizadas para evitar sincronização do MEGA/Drive
    base_temp = os.path.join("uploads", "_NEXUS_TEMP_", "_BUILD_")
    work_dir = os.path.join(base_temp, "build_work")
    dist_dir = os.path.join(base_temp, "dist_work")
    
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(dist_dir, exist_ok=True)

    try:
        # Tenta limpar antes de começar
        clean_folder(work_dir)
        clean_folder(dist_dir)

        # 1. Aplicativo Principal
        print("\n[1/2] Compilando Aplicativo Principal...")
        app_params = [
            'nexus_app.py',
            '--name=Nexus_AI_Pro',
            '--onefile',
            '--noconsole',
            '--clean',
            f'--workpath={work_dir}',
            f'--distpath={dist_dir}',
            '--hidden-import=webview',
            '--hidden-import=proxy_tools',
            '--hidden-import=bottle',
            '--hidden-import=uuid',
            '--hidden-import=platform',
            '--hidden-import=logging',
            '--hidden-import=clr',
        ]
        PyInstaller.__main__.run(app_params)

        exe_path = os.path.join(dist_dir, "Nexus_AI_Pro.exe")
        if os.path.exists(exe_path):
            shutil.copy2(exe_path, "Nexus_AI_Pro.exe")
            print("Aplicativo Principal pronto!")
        else:
            print("ERRO no estágio 1: Arquivo nao gerado.")
            return

        # 2. Instalador
        print("\n[2/2] Compilando Instalador...")
        setup_params = [
            os.path.join('engines', 'nexus_setup.py'),
            '--name=Setup_Nexus',
            '--onefile',
            '--noconsole',
            '--clean',
            f'--workpath={work_dir}',
            f'--distpath={dist_dir}',
            '--add-data=Nexus_AI_Pro.exe;.',
            '--add-data=nexus_app.py;.',
            f'--add-data={os.path.join("engines", "nexus_core.py")};.',
            f'--add-data={os.path.join("engines", "nexus_dub_video.py")};.',
            f'--add-data={os.path.join("engines", "vpk_manager.py")};.',
            '--add-data=client;client',
            '--add-data=requirements_RTX.txt;.',
            '--add-data=requirements_CPU.txt;.',
        ]
        PyInstaller.__main__.run(setup_params)

        final_setup = os.path.join(dist_dir, "Setup_Nexus.exe")
        if os.path.exists(final_setup):
            shutil.copy2(final_setup, "Setup_Nexus.exe")
            print("\n" + "="*50)
            print("SUCESSO TOTAL!")
            print("Instalador pronto na pasta principal: Setup_Nexus.exe")
            print("="*50)
        else:
            print("ERRO no estágio 2: Instalador nao gerado.")

    except Exception:
        print("\n" + "!"*50)
        print("ERRO CRITICO DURANTE O BUILD:")
        traceback.print_exc()
        print("!"*50)

    finally:
        print("\nLimpando arquivos temporarios...")
        clean_folder(work_dir)
        clean_folder(dist_dir)

if __name__ == "__main__":
    build()
