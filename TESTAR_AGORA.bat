@echo off
title Nexus AI - MODO DESENVOLVEDOR (TESTE RAPIDO)
echo ==================================================
echo INICIANDO NEXUS AI SEM BUILD (MODO RAPIDO)
echo ==================================================
echo.
set NEXUS_NATIVE_MODE=1
.\env\Scripts\python.exe nexus_app.py
echo.
echo ==================================================
echo PROGRAMA ENCERRADO.
echo ==================================================
pause
