@echo off
cd /d "C:\IA_dublagem\nexus_godogen"
title Nexus Godogen - Central Control Suite

echo ==================================================
echo   VERIFICANDO E INSTALANDO DEPENDENCIAS...
echo ==================================================
echo.
"C:\IA_dublagem\env\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo ==================================================
echo   INICIANDO SERVIDOR DE IA LOCAL (LLAMA.CPP)...
echo ==================================================
echo.

:: Dispara o servidor da API OpenAI do llama-cpp-python em uma janela visível que mantém os logs abertos
start "Servidor IA Local" cmd /k C:\IA_dublagem\env\Scripts\python.exe C:\IA_dublagem\nexus\build_tools\run_llama_server.py --model "C:\IA_dublagem\_MODELS_\Qwen3.5-4B-Q4_K_M.gguf" --port 1234 --n_ctx 16384 --flash_attn True --n_gpu_layers 33 --cache True --cache_size 1073741824 --use_mmap False

echo Aguardando o modelo carregar na GPU (8 segundos)...
timeout /t 8 /nobreak >nul

echo.
echo ==================================================
echo   INICIANDO O NEXUS GODOGEN SERVER...
echo ==================================================
echo.
"C:\IA_dublagem\env\Scripts\python.exe" nexus_godogen_server.py

echo.
echo ==================================================
echo   FECHANDO SERVIDOR DE IA E LIBERANDO VRAM...
echo ==================================================
echo.
:: Encerra o processo do servidor local para liberar a GPU
taskkill /F /FI "WINDOWTITLE eq Servidor IA Local*" >nul 2>&1
echo VRAM da RTX 3050 liberada com sucesso!
echo.
pause
