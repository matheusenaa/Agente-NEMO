@echo off
title SYNOP Launcher
set "SYNOP_ROOT=%~dp0"
cd /d "%SYNOP_ROOT%"
echo ==========================================
echo  SYNOP - Iniciando componentes...
echo ==========================================
echo.

REM Verificar se a porta 8798 ja esta em uso (somente em ESCUTA)
netstat -ano | findstr "LISTENING" | findstr ":8798" >nul
if %errorlevel% equ 0 (
    echo [ERRO] Porta 8798 ja esta em uso. Encerre o processo anterior ou use outra porta.
    echo.
    echo Processos na porta 8798:
    netstat -ano | findstr "LISTENING" | findstr ":8798"
    echo.
    if defined SYNOP_NO_PAUSE exit /b 1
    pause
    exit /b 1
)

echo [1/3] Iniciando backend FastAPI (porta 8798) com dashboard embutido...
start "SYNOP Backend" run_backend.bat

echo [2/3] Aguardando backend subir...
set MAX_WAIT=30
set WAITED=0
:WAIT_LOOP
timeout /t 2 /nobreak >nul
set /a WAITED+=2
curl -s http://127.0.0.1:8798/api/nemo/health >nul 2>&1
if %errorlevel% equ 0 (
    echo Backend respondeu com sucesso!
    goto :BACKEND_READY
)
if %WAITED% geq %MAX_WAIT% (
    echo [ERRO] Timeout: backend nao respondeu apos %MAX_WAIT% segundos.
    echo Verifique a janela "SYNOP Backend" para erros.
    if not defined SYNOP_NO_PAUSE pause
    exit /b 1
)
goto :WAIT_LOOP

:BACKEND_READY
echo [3/3] Dashboard pronto em http://127.0.0.1:8798/
echo.
echo Para desenvolvimento: use start_nemo_dev.bat (porta 5173).
echo.

REM Nao abre o navegador em execucao nao interativa (testes, CI, agents).
if not defined SYNOP_NO_PAUSE (
    echo Abrindo navegador no dashboard de producao...
    start "" "http://127.0.0.1:8798/"
)

echo.
echo SYNOP rodando! Feche a janela "SYNOP Backend" para encerrar.
if not defined SYNOP_NO_PAUSE pause
exit /b 0