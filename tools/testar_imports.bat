@echo off
chcp 65001 > nul
echo.
echo 🔍 [TESTE] Verificando integridade e sintaxe dos modulos do Nexus...
"C:\IA_dublagem\env\Scripts\python.exe" -c "import nexus.core"
if %errorlevel% neq 0 (
    echo.
    echo ❌ [ERRO] Falha na verificacao! Erro de sintaxe ou importacao detectado.
    exit /b 1
)
echo ✅ [OK] Todos os modulos foram importados com sucesso!
exit /b 0
