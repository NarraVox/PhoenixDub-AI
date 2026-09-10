# Copyright (c) 2026 Paulo Henrik Carvalho de Araujo
# Licensed under the Apache License, Version 2.0

import sys
import os

# Garante que o diretorio do executavel ou do script esta no sys.path
if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)
    from pathlib import Path
    from nexus.distribution import deploy_runtime
    deploy_runtime(Path(sys.executable).parent)
    if os.environ.get('TEST_IMPORTS') != '1':
        os.chdir(Path(sys.executable).parent)
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# A replacement instance waits until the old Hub releases its port.
if '--wait-for-restart' in sys.argv:
    import socket
    import time
    sys.argv.remove('--wait-for-restart')
    deadline = time.monotonic() + 60
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(('127.0.0.1', 5000))
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise SystemExit('O Hub anterior não encerrou a tempo da reinicialização.')
        time.sleep(0.2)

# Se for apenas um teste de importacoes do CI/CD, verifica e encerra
if os.environ.get("TEST_IMPORTS") == "1":
    print("Verificando importacoes do aplicativo principal...")
    import nexus.nexus_app as nexus_app
    import nexus.core.security as security
    client = nexus_app.app.test_client()
    assert client.get('/api/app-version').status_code == 200
    assert client.get('/').status_code == 200
    assert client.get('/js/hub_updates.js').status_code == 200
    print("[OK] Importacoes do app principal validadas com sucesso!")
    with open("import_test_main_ok.txt", "w") as f:
        f.write("OK")
    sys.exit(0)

import nexus.nexus_app as nexus_app

if __name__ == '__main__':
    nexus_app.main()
