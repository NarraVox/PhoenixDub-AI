@echo off
cd /d "C:\IA_dublagem"
title Aider Copilot Local - NarraVox

echo ==================================================
echo   INICIANDO SERVIDOR DE IA LOCAL (LLAMA.CPP)...
echo ==================================================
echo.

:: Dispara o servidor da API OpenAI do llama-cpp-python de forma minimizada usando o wrapper que corrige as DLLs
start "Servidor IA Local" /min "C:\IA_dublagem\env\Scripts\python.exe" "C:\IA_dublagem\build_tools\run_llama_server.py" --model "C:\IA_dublagem\_MODELS_\gemma-4-E4B-it-Q4_K_M.gguf" --port 1234 --n_ctx 8192 --n_gpu_layers -1


echo Aguardando o modelo carregar na GPU (8 segundos)...
timeout /t 8 /nobreak >nul

echo.
echo ==================================================
echo   INICIANDO O CHAT DO AIDER...
echo ==================================================
echo.

:: Executa o Aider isolado apontando para o nosso servidor local com a interface gráfica de chat
"C:\aider_env\Scripts\aider.exe" --openai-api-base http://localhost:1234/v1 --openai-api-key fake-key --model openai/gemma-4 --gui


echo.
echo ==================================================
echo   FECHANDO SERVIDOR DE IA E LIBERANDO VRAM...
echo ==================================================

:: Encerra o processo do servidor minimizado para liberar a GPU
taskkill /F /FI "WINDOWTITLE eq Servidor IA Local*" >nul 2>&1
echo VRAM da RTX 3050 liberada com sucesso!
echo.
pause
