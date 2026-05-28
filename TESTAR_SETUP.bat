@echo off
title Nexus AI - AUTO-INSTALADOR INTELIGENTE
echo ==================================================
echo   PREPARANDO AMBIENTE DE INSTALACAO...
echo ==================================================
echo.

:: 1. Verifica se a pasta env existe, se nao, cria o basico
if not exist "env\Scripts\python.exe" (
    echo [PASSO 1] Criando novo ambiente virtual...
    python -m venv env
    if %errorlevel% neq 0 (
        echo [ERRO] Nao foi possivel criar o ambiente. Verifique se o Python esta instalado.
        pause
        exit
    )
)

:: 2. Garante que a biblioteca da JANELA (webview) esteja instalada no env
echo [PASSO 2] Sincronizando motor grafico...
.\env\Scripts\python.exe -m pip install pywebview --quiet

:: 3. Agora sim, abre o instalador oficial
echo [PASSO 3] Abrindo interface do Nexus AI...
echo.
.\env\Scripts\python.exe build_tools\nexus_setup.py

echo.
echo ==================================================
echo   PROCESSO FINALIZADO.
echo ==================================================
pause
