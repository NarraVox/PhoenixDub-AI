@echo off
setlocal
pushd "%~dp0" || exit /b 1
title PhoenixDub AI - Instalador
set "PYTHONPATH=%CD%"
if exist "env\Scripts\python.exe" goto :venv
if exist "env\python.exe" goto :portable
if exist "env" goto :broken
python -c "import sys; assert (3,10) <= sys.version_info[:2] < (3,13), 'Use Python 3.10 a 3.12'"
if errorlevel 1 goto :failed
python -m venv env
if errorlevel 1 goto :failed
:venv
set "SETUP_PY=env\Scripts\python.exe"
goto :launch
:portable
set "SETUP_PY=env\python.exe"
:launch
"%SETUP_PY%" -c "import sys; assert (3,10) <= sys.version_info[:2] < (3,13), 'Use Python 3.10 a 3.12'"
if errorlevel 1 goto :failed
"%SETUP_PY%" -m pip install "pywebview>=5.0"
if errorlevel 1 goto :failed
echo Token Hugging Face: configure na interface. Modelo: pyannote/speaker-diarization-3.1
"%SETUP_PY%" Setup_Nexus.py
if errorlevel 1 goto :failed
popd
endlocal
exit /b 0
:broken
echo ERRO: env existe mas nao tem Python valido. Nenhum arquivo foi apagado.
:failed
echo ERRO: instalacao interrompida. Confira a mensagem acima; seu ambiente foi preservado.
pause
popd
endlocal
exit /b 1
