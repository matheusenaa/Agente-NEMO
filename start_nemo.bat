@echo off
title NEMO IDE Launcher
echo ==========================================
echo  NEMO IDE - Iniciando componentes...
echo ==========================================
echo.

REM Diretório raiz do projeto
set "NEMO_ROOT=%~dp0"
cd /d "%NEMO_ROOT%"

echo [1/3] Iniciando backend FastAPI (porta 8798)...
start "NEMO Backend" cmd /k "cd /d "%NEMO_ROOT%" && python -c "import sys; sys.path.insert(0, r'%NEMO_ROOT%'); import nemo_server as ns; import uvicorn; uvicorn.run(ns.app, host=ns.DEFAULT_HOST, port=ns.DEFAULT_PORT, log_level='info')""

echo [2/3] Aguardando backend subir...
timeout /t 5 /nobreak >nul

echo [3/3] Iniciando frontend dev server (porta 5173)...
start "NEMO Dashboard" cmd /k "cd /d "%NEMO_ROOT%\dashboard" && npm run dev"

echo.
echo Backend e Frontend iniciados em janelas separadas.
echo Abrindo navegador em http://localhost:5173/ ...
start "" "http://localhost:5173/"

echo.
echo NEMO IDE rodando! Feche esta janela quando quiser encerrar.
pause