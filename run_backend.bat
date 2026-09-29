@echo off
REM ============================================================
REM  SYNOP / NEMO - Backend FastAPI (porta 8798)
REM
REM  Descobre um interpretador Python utilizavel. Antes rodava
REM  `python nemo_server.py` direto: quando o "python" do PATH e o
REM  alias da Microsoft Store, a janela abria e nao acontecia nada
REM  (aparentava travamento). Agora falha com mensagem clara.
REM ============================================================
cd /d "%~dp0"
title SYNOP Backend

set "PYTHON_EXE="

REM 1) python -c funciona de verdade?
python -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYTHON_EXE=python"

REM 2) Launcher do Python (Windows)
if not defined PYTHON_EXE (
    py -3 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=py -3"
)

REM 3) Interpretadores conhecidos do usuario
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYTHON_EXE if exist "%USERPROFILE%\python312\python.exe" set "PYTHON_EXE=%USERPROFILE%\python312\python.exe"

if not defined PYTHON_EXE (
    echo [ERRO] Nenhum interpretador Python funcional encontrado.
    echo.
    echo Instale o Python 3.11+ e marque "Add python.exe to PATH",
    echo ou ajuste PYTHON_EXE neste arquivo.
    echo.
    pause
    exit /b 1
)

echo Usando Python: %PYTHON_EXE%
%PYTHON_EXE% nemo_server.py

if errorlevel 1 (
    echo.
    echo [ERRO] O backend terminou com codigo de erro %errorlevel%.
    pause
)
