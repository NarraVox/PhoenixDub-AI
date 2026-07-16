import PyInstaller.__main__
import os
import shutil

def build_setup():
    # [ORGANIZATION FIX] Sobe para a raiz para garantir caminhos corretos
    os.chdir("..")

    print("Iniciando Build do Instalador Nexus AI (Setup)...")
    
    app_name = "Setup_Nexus"
    entry_point = os.path.join("nexus", "build_tools", "nexus_setup.py")
    
    # Busca o executável gerado pelo Nuitka ou PyInstaller
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

    # Detecta a pasta do pacote webview dinamicamente para funcionar em qualquer ambiente (local ou nuvem)
    import importlib.util
    spec = importlib.util.find_spec("webview")
    if spec and spec.submodule_search_locations:
        webview_path = spec.submodule_search_locations[0]
        print(f"Detectado webview path dinamicamente: {webview_path}")
    else:
        site_packages = os.path.join(os.getcwd(), "env", "Lib", "site-packages")
        webview_path = os.path.join(site_packages, "webview")
        print(f"Webview nao detectado dinamicamente. Usando fallback: {webview_path}")
    
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
        '--add-data=Nexus_AI_Pro.exe;.',
        '--add-data=nexus/nexus_app.py;.',
        '--add-data=vpk_manager.py;.',
        '--add-data=nexus/client;client',
        '--add-data=requirements.txt;.',
        f'--add-data={webview_path};webview', # Adiciona webview manualmente
    ]

    print("Empacotando Instalador...")
    PyInstaller.__main__.run(params)

    # Copia o executável gerado para a pasta dist/ na raiz do projeto
    final_exe_src = os.path.join(dist_dir, f"{app_name}.exe")
    final_exe_dest_dir = os.path.join(os.getcwd(), "dist")
    os.makedirs(final_exe_dest_dir, exist_ok=True)
    final_exe_dest = os.path.join(final_exe_dest_dir, f"{app_name}.exe")
    
    if os.path.exists(final_exe_src):
        shutil.copy2(final_exe_src, final_exe_dest)
        print(f"\n[COPIA] Executável copiado com sucesso para: {final_exe_dest}")
    else:
        print(f"\n❌ ERRO: O executável {final_exe_src} não foi gerado.")

    print("\n" + "="*50)
    print(f"SUCESSO! O Instalador final está em: dist/{app_name}.exe")
    print("="*50)

if __name__ == "__main__":
    build_setup()
