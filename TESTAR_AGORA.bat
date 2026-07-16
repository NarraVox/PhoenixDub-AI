@echo off
title Nexus AI - MODO DESENVOLVEDOR (TESTE RAPIDO)
echo ==================================================
echo INICIANDO NEXUS AI SEM BUILD (MODO RAPIDO)
echo ==================================================
echo.

:: --- AJUSTE AUTOMÁTICO DE TDR (NVIDIA) ---
set "TDR_OK=0"

:: Verifica se o TdrDelay já está configurado (aceitando 10s ou 15s em formatos comuns)
for /f "tokens=3" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v TdrDelay 2^>nul') do (
    if "%%a"=="0xa" set "TDR_OK=1"
    if "%%a"=="0xf" set "TDR_OK=1"
    if "%%a"=="0x0000000a" set "TDR_OK=1"
    if "%%a"=="0x0000000f" set "TDR_OK=1"
    if "%%a"=="0x00000014" set "TDR_OK=1"
)

if "%TDR_OK%"=="1" goto :TDR_SUCCESS

echo [GPU] Ajustando tempo limite de resposta da GPU para evitar tela preta...
:: Verifica se tem privilégios de administrador
net session >nul 2>&1
if %errorlevel% equ 0 goto :APPLY_ADMIN

:: Caso precise de UAC para elevação
echo [UAC] Solicitando permissao de Administrador para aplicar o ajuste da GPU...
echo Set UAC = CreateObject("Shell.Application") > "%temp%\elevate.vbs"
echo UAC.ShellExecute "cmd.exe", "/c reg add HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers /v TdrDelay /t REG_DWORD /d 10 /f & reg add HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers /v TdrDdiDelay /t REG_DWORD /d 10 /f", "", "runas", 1 >> "%temp%\elevate.vbs"
wscript.exe "%temp%\elevate.vbs"
del "%temp%\elevate.vbs" 2>nul
echo [GPU] Ajuste enviado. Se voce aceitou o aviso do Windows, reinicie o PC depois para aplicar.
echo.
goto :START_APP

:APPLY_ADMIN
reg add "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v TdrDelay /t REG_DWORD /d 10 /f >nul
reg add "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v TdrDdiDelay /t REG_DWORD /d 10 /f >nul
echo [GPU] Ajuste de TdrDelay (10s) aplicado com sucesso!
echo.
goto :START_APP

:TDR_SUCCESS
echo [GPU] O tempo de resposta da GPU (TdrDelay) ja esta configurado corretamente.
echo.

:START_APP
set NEXUS_NATIVE_MODE=1
set PYTHONPATH=.
.\env\Scripts\python.exe nexus\nexus_app.py

echo.
echo ==================================================
echo PROGRAMA ENCERRADO.
echo ==================================================
pause
