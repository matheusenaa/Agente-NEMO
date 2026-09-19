@echo off
title NEMO IDE Launcher
set "NEMO_ROOT=%~dp0"
cd /d "%NEMO_ROOT%"
echo ==========================================
echo  NEMO IDE - Iniciando componentes...
echo ==========================================
echo.
echo [1/3] Iniciando backend FastAPI (porta 8798) com dashboard embutido...
start "NEMO Backend" run_backend.bat

echo [2/3] Aguardando backend subir...
timeout /t 6 /nobreak >nul

echo [3/3] Dashboard pronto em http://127.0.0.1:8798/
echo.
echo Para desenvolvimento: use start_nemo_dev.bat (porta 5173).
echo.
echo Abrindo navegador no dashboard de producao...
start "" "http://127.0.0.1:8798/"

echo.
echo NEMO IDE rodando! Feche esta janela quando quiser encerrar.
pause