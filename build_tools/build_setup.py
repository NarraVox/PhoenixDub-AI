import PyInstaller.__main__
import os
import shutil

def build_setup():
    # [ORGANIZATION FIX] Sobe para a raiz para garantir caminhos corretos
    os.chdir("..")

    print("Iniciando Build do Instalador Nexus AI (Setup)...")
    
    app_name = "Setup_Nexus"
    entry_point = os.path.join("build_tools", "nexus_setup.py")
    
    # Busca o executável gerado pelo Nuitka
    nuitka_exe = os.path.join("dist_nuitka", "nexus_app.exe")
    if os.path.exists(nuitka_exe):
        shutil.copy2(nuitka_exe, "Nexus_AI_Pro.exe")
        print("Executavel Nuitka detectado e preparado.")
    
    if not os.path.exists("Nexus_AI_Pro.exe"):
        print("AVISO: Nexus_AI_Pro.exe nao encontrado na raiz. O instalador pode falhar.")


    # [CLOUD-SYNC FIX] Centraliza arquivos temporarios do build
    base_temp = os.path.join("uploads", "_NEXUS_TEMP_", "_BUILD_")
    work_dir = os.path.join(base_temp, "build_work_setup")
    dist_dir = os.path.join(base_temp, "dist_work_setup")
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(dist_dir, exist_ok=True)

    site_packages = os.path.join(os.getcwd(), "env", "Lib", "site-packages")
    
    params = [
        entry_point,
        f'--name={app_name}',
        '--onefile',
        '--noconsole',
        '--clean',
        f'--workpath={work_dir}',
        f'--distpath={dist_dir}',
        '--exclude-module=webview', # Evita o crash de analise
        '--hidden-import=__future__', # CORREÇÃO: Força inclusao do modulo base
        '--hidden-import=clr',        # Necessario para o PythonNet no Windows
        # Embutir o programa principal e os codigos
        '--add-data=nexus_app.py;.',
        '--add-data=nexus_core.py;.',
        '--add-data=nexus_dub_video.py;.',
        '--add-data=nexus_dub_games.py;.',
        '--add-data=vpk_manager.py;.',
        '--add-data=client;client',
        '--add-data=requirements.txt;.',
        '--add-data=requirements_RTX.txt;.',
        '--add-data=requirements_AMD.txt;.',
        '--add-data=requirements_CPU.txt;.',
        f'--add-data={os.path.join(site_packages, "webview")};webview', # Adiciona webview manualmente
    ]

    print("Empacotando Instalador...")
    PyInstaller.__main__.run(params)

    print("\n" + "="*50)
    print(f"SUCESSO! O Instalador final está em: dist/{app_name}.exe")
    print("="*50)

if __name__ == "__main__":
    build_setup()
