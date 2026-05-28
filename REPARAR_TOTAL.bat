@echo off
title NARRAVOX - LIMPEZA FINAL DE PROCESSOS
echo ==================================================
echo   DESBLOQUEANDO ARQUIVOS DO SISTEMA...
echo ==================================================
echo.

:: Fecha o Python e o motor de janelas do Edge que o Windows usa
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM pythonw.exe /T >nul 2>&1
taskkill /F /IM msedgewebview2.exe /T >nul 2>&1
taskkill /F /IM "Microsoft.Web.WebView2.Core.dll" /T >nul 2>&1

echo Aguardando 5 segundos para o Windows soltar os arquivos...
timeout /t 5 /nobreak >nul

:: Tenta liberar as permissoes da pasta se estiverem presas
echo Liberando permissao da pasta env...
takeown /f "env" /r /d y >nul 2>&1
icacls "env" /grant everyone:F /t >nul 2>&1

echo Removendo ambiente antigo para limpeza total...
rd /s /q "env" >nul 2>&1

if exist "env" (
    echo.
    echo [!!!] ATENCAO: A pasta 'env' ainda esta presa.
    echo Tente renomear a pasta 'env' para 'env_velha' manualmente e rode o setup.
) else (
    echo [SUCESSO] Caminho livre! 
    echo.
    echo ==================================================
    echo   REINICIANDO INSTALADOR (VERSAO 2026)...
    echo ==================================================
    pause
    python build_tools/nexus_setup.py
)
pause
