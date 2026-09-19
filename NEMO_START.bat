@echo off
title NEMO - Iniciando
setlocal enableextensions

cd /d "%~dp0"
set "NEMO_ROOT=%~dp0"

echo ==========================================
echo  NEMO IDE - Sala de operacoes dos agentes
echo ==========================================
echo.

rem --- 1. Python ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH.
    echo  Instale o Python 3.10+ em https://www.python.org/downloads/
    echo  (marque a opcao "Add Python to PATH" durante a instalacao).
    pause
    exit /b 1
)

rem --- 2. Dependencias ---
echo [1/4] Verificando dependencias Python...
python -c "import fastapi, uvicorn" >nul 2>nul
if errorlevel 1 (
    echo  Instalando dependencias (pip install -r requirements.txt)...
    python -m pip install -r "requirements.txt"
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar dependencias.
        pause
        exit /b 1
    )
) else (
    echo  OK - dependencias presentes.
)

rem --- 3. Dashboard compilado ---
echo [2/4] Verificando dashboard...
if not exist "dashboard\dist\index.html" (
    echo  Dashboard nao compilado. Tentando build...
    pushd dashboard
    call npm.cmd install
    call npm.cmd run build
    popd
)
if not exist "dashboard\dist\index.html" (
    echo [AVISO] Dashboard nao foi compilado.
    echo  A API continuara disponivel, mas a interface nao abrira.
)

rem --- 4. .env ---
if not exist ".env" (
    echo [3/4] Arquivo .env nao encontrado - criando a partir do exemplo...
    copy ".env.example" ".env" >nul
)

rem --- 5. Inicia o servidor ---
echo [4/4] Iniciando NEMO IDE em http://127.0.0.1:8798/
echo.
start "NEMO Backend" /min cmd /c "cd /d "%NEMO_ROOT%" && python nemo_server.py"
timeout /t 5 /nobreak >nul
start "" "http://127.0.0.1:8798/"

echo.
echo NEMO IDE rodando! Caso o navegador nao tenha aberto,
echo acesse: http://127.0.0.1:8798/
echo.
echo Feche esta janela quando quiser encerrar o launcher.
pause