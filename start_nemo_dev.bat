@echo off
title NEMO IDE - Modo Desenvolvimento
set "NEMO_ROOT=%~dp0"
cd /d "%NEMO_ROOT%"
echo ==========================================
echo  NEMO IDE - Modo desenvolvimento
echo ==========================================
echo [1/2] Iniciando backend FastAPI (porta 8798)...
start "NEMO Backend" run_backend.bat
timeout /t 6 /nobreak >nul

echo [2/2] Iniciando frontend Vite (porta 5173) com HMR...
start "NEMO Dashboard" run_dashboard_dev.bat
timeout /t 5 /nobreak >nul

echo.
echo Abrindo navegador em http://localhost:5173/
start "" "http://localhost:5173/"
echo NEMO IDE dev rodando! Feche esta janela quando quiser encerrar.
pause