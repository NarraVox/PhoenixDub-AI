import PyInstaller.__main__
import os
import shutil
import sys

def build_all():
    site_packages = "C:\\Users\\Paulo Henrik\\AppData\\Local\\Programs\\Python\\Python310\\lib\\site-packages"
    
    print("="*50)
    print("INICIANDO BUILD TOTAL NEXUS AI PRO")
    print("="*50)

    # 1. Limpeza
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"Limpa: {folder}")

    # 2. Build do Aplicativo Principal (Nexus_AI_Pro.exe) usando Nuitka
    # Nota: Como já foi compilado antes, o Nuitka usará o CACHE e será muito mais rápido agora!
    print("\n[1/2] Compilando Aplicativo Principal com Nuitka (Usando Cache para velocidade)...")
    nuitka_cmd = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        "--windows-console-mode=disable",
        "--enable-plugin=tk-inter",
        "--enable-plugin=pywebview",
        "--include-package=proxy_tools",
        "--include-package=bottle",
        "--output-dir=dist_nuitka",
        "--assume-yes",
        "--output-filename=Nexus_AI_Pro",
        os.path.join("nexus", "nexus_app.py")
    ]
    
    import subprocess
    subprocess.run(nuitka_cmd)

    # Move o executável para a raiz
    nuitka_exe = os.path.join("dist_nuitka", "Nexus_AI_Pro.exe")
    if os.path.exists(nuitka_exe):
        shutil.copy2(nuitka_exe, "Nexus_AI_Pro.exe")
        print("Aplicativo Principal pronto!")
    else:
        print("ERRO: O Nuitka não gerou o executável.")
        return

    # 3. Build do Instalador (Setup_Nexus.exe) usando PyInstaller
    # Usamos flags para evitar a análise profunda que causa o crash
    print("\n[2/2] Compilando Instalador (Modo Rápido Protegido)...")
    setup_params = [
        os.path.join("nexus", "build_tools", "nexus_setup.py"),
        '--name=Setup_Nexus',
        '--onefile',
        '--noconsole',
        '--clean',
        '--add-data=Nexus_AI_Pro.exe;.',
        '--add-data=nexus/nexus_app.py;.',
        '--add-data=vpk_manager.py;.',
        '--add-data=nexus/client;client',
        '--add-data=requirements.txt;.',
        # Excluímos módulos pesados que causam o erro no PyInstaller
        '--exclude-module=psutil',
        '--exclude-module=webview',
        '--exclude-module=numpy',
        '--log-level=INFO',
    ]
    import PyInstaller.__main__
    PyInstaller.__main__.run(setup_params)

    print("\n" + "="*50)
    print("SUCESSO TOTAL!")
    print("Instalador Final: dist/Setup_Nexus.exe")
    print("="*50)

if __name__ == "__main__":
    build_all()
