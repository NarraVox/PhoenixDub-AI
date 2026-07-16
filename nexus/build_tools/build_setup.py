import PyInstaller.__main__
import os
import shutil

def build_setup():
    # [ORGANIZATION FIX] Sobe para a raiz para garantir caminhos corretos dinamicamente
    from pathlib import Path
    root_dir = Path(__file__).parent.parent.parent.resolve()
    os.chdir(root_dir)

    print("Iniciando Build do Instalador Nexus AI (Setup)...")
    
    app_name = "Setup_Nexus"
    entry_point = "Setup_Nexus.py"
    
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
        # EXCLUSÕES CRÍTICAS DE MÓDULOS DE ML E BIBLIOTECAS GRANDES (Evita que o instalador tente embutir bibliotecas pesadas)
        '--exclude-module=torch',
        '--exclude-module=torchaudio',
        '--exclude-module=torchvision',
        '--exclude-module=numpy',
        '--exclude-module=scipy',
        '--exclude-module=pandas',
        '--exclude-module=sklearn',
        '--exclude-module=numba',
        '--exclude-module=llvmlite',
        '--exclude-module=cv2',
        '--exclude-module=fastapi',
        '--exclude-module=uvicorn',
        '--exclude-module=anyio',
        '--exclude-module=whisperx',
        '--exclude-module=faster_whisper',
        '--exclude-module=llama_cpp',
        '--exclude-module=matplotlib',
        '--exclude-module=nltk',
        '--exclude-module=sqlalchemy',
        '--exclude-module=h5py',
        '--exclude-module=sympy',
        '--exclude-module=mpmath',
        '--exclude-module=transformers',
        '--exclude-module=tensorflow',
        '--exclude-module=timm',
        '--exclude-module=huggingface_hub',
        '--exclude-module=pyannote',
        '--exclude-module=speechbrain',
        '--exclude-module=sentencepiece',
        '--exclude-module=ctranslate2',
        '--exclude-module=tokenizers',
        '--exclude-module=pydub',
        '--exclude-module=av',
        '--hidden-import=__future__', # CORREÇÃO: Força inclusao do modulo base
        '--hidden-import=clr',        # Necessario para o PythonNet no Windows
        '--hidden-import=uuid',       # CORREÇÃO: Adiciona uuid exigido pelo webview
        '--hidden-import=ctypes',     # CORREÇÃO: Adiciona ctypes exigido pelo webview
        '--hidden-import=proxy_tools', # CORREÇÃO: Adiciona proxy_tools exigido pelo webview
        # Embutir o programa principal e os codigos com caminhos absolutos para evitar erros de localizacao no PyInstaller
        f'--add-data={os.path.abspath(os.path.join(os.getcwd(), "Nexus_AI_Pro.exe"))};.',
        f'--add-data={os.path.abspath(os.path.join(os.getcwd(), "nexus", "nexus_app.py"))};.',
        f'--add-data={os.path.abspath(os.path.join(os.getcwd(), "vpk_manager.py"))};.',
        f'--add-data={os.path.abspath(os.path.join(os.getcwd(), "nexus", "client"))};client',
        f'--add-data={os.path.abspath(os.path.join(os.getcwd(), "requirements.txt"))};.',
        f'--add-data={os.path.abspath(webview_path)};webview', # Adiciona webview manualmente
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
        print(f"\n[COPIA] Executavel copiado com sucesso para: {final_exe_dest}")
    else:
        print(f"\n[ERRO] O executavel {final_exe_src} nao foi gerado.")

    print("\n" + "="*50)
    print(f"SUCESSO! O Instalador final esta em: dist/{app_name}.exe")
    print("="*50)

if __name__ == "__main__":
    build_setup()
