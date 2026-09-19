@echo off
title NEMO Diagnostic
cd /d "%~dp0"
chcp 65001 >nul
echo ==========================================
echo  NEMO Diagnostic - Verificacao do sistema
echo ==========================================
echo.
python start_nemo.py --check
echo.
echo ==========================================
pause