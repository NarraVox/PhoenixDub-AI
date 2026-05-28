import os
import sys
import subprocess
import shutil

def build_debug():
    print("GERANDO VERSÃO DE DEBUG (COM CONSOLE)...")
    nuitka_cmd = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        "--windows-console-mode=attach", # Permite ver o erro no terminal
        "--enable-plugin=tk-inter",
        "--enable-plugin=pywebview",
        "--include-package=proxy_tools",
        "--include-package=bottle",
        "--output-dir=dist_debug",
        "--assume-yes",
        "--output-filename=Nexus_DEBUG",
        "nexus_app.py"
    ]
    subprocess.run(nuitka_cmd)
    print("DEBUG PRONTO: dist_debug/Nexus_DEBUG.exe")

if __name__ == "__main__":
    build_debug()
