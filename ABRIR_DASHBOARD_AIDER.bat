@echo off
title NarraVox Aider Dashboard - Logs
cd /d "%~dp0"

echo ==================================================
echo   INICIANDO O AIDER DASHBOARD CONTROLLER...
echo   (Mantenha esta janela aberta para ver os logs)
echo ==================================================
echo.

:: 1. Garante que o ambiente virtual existe
if not exist "env\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual 'env' nao encontrado na raiz!
    pause
    exit /b
)

:: 2. Inicia o Aider Dashboard e exibe os logs no console
"env\Scripts\python.exe" tools/aider_dashboard_app.py
