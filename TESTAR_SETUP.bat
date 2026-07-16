@echo off
title Nexus AI - AUTO-INSTALADOR INTELIGENTE
echo ==================================================
echo   PREPARANDO AMBIENTE DE INSTALACAO...
echo ==================================================
echo.

:: 1. Verifica se o token do Hugging Face já está configurado no sistema
if "%HF_TOKEN%"=="" (
    echo [HUGGING FACE] Nenhum Token do Hugging Face detectado no sistema.
    echo Para usar a Diarizacao automatica de oradores em videos, e preciso
    echo aceitar os termos de uso do pyannote/speaker-diarization-community-1
    echo e fornecer um Token de Leitura do Hugging Face.
    echo.
    set /p HF_TOKEN_INPUT="Cole seu Token do Hugging Face aqui (ou aperte Enter para pular): "
    if not "%HF_TOKEN_INPUT%"=="" (
        setx HF_TOKEN "%HF_TOKEN_INPUT%" >nul
        set HF_TOKEN=%HF_TOKEN_INPUT%
        echo %HF_TOKEN_INPUT%> token_hf.txt
        echo [OK] Token salvo com sucesso nas variaveis de ambiente e em token_hf.txt!
        echo.
    )
) else (
    echo [HUGGING FACE] Token do Hugging Face detectado e ativo no sistema.
    echo %HF_TOKEN%> token_hf.txt
    echo.
)

:: 2. Verifica se a pasta env existe, se nao, cria o basico
if not exist "env\Scripts\python.exe" (
    echo [PASSO 1] Criando novo ambiente virtual...
    python -m venv env
    if %errorlevel% neq 0 (
        echo [ERRO] Nao foi possivel criar o ambiente. Verifique se o Python esta instalado.
        pause
        exit
    )
)

:: 3. Garante que a biblioteca da JANELA (webview) esteja instalada no env
echo [PASSO 2] Sincronizando motor grafico e dependencias base...
.\env\Scripts\python.exe -m pip install pywebview --quiet

:: 4. Abre o instalador oficial (com suporte ao novo pipeline WhisperX)
echo [PASSO 3] Abrindo interface do Nexus AI (Suporte WhisperX Ativo)...
echo ==================================================
echo.
set PYTHONPATH=.
.\env\Scripts\python.exe nexus\build_tools\nexus_setup.py

echo.
echo ==================================================
echo   PROCESSO FINALIZADO.
echo ==================================================
pause
