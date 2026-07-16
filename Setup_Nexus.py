# Copyright (c) 2026 Paulo Henrik Carvalho de Araujo
# Licensed under the Apache License, Version 2.0

import sys
import os

# Garante que o diretorio do executavel ou do script esta no sys.path
if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Se for apenas um teste de importacoes do CI/CD, verifica e encerra
if os.environ.get("TEST_IMPORTS") == "1":
    print("Verificando importacoes do instalador...")
    import nexus.build_tools.nexus_setup as nexus_setup
    import webview
    print("[OK] Importacoes do instalador validadas com sucesso!")
    sys.exit(0)

import nexus.build_tools.nexus_setup as nexus_setup

if __name__ == '__main__':
    nexus_setup.main()
