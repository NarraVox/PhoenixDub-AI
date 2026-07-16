# Copyright (c) 2026 Paulo Henrik Carvalho de Araujo
# Licensed under the Apache License, Version 2.0

import sys
import os

# Garante que o diretorio do executavel ou do script esta no sys.path
if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nexus.nexus_app as nexus_app

if __name__ == '__main__':
    nexus_app.main()
