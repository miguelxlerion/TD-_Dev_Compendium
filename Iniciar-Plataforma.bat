@echo off
REM Lanzador de la plataforma Total Darkness (doble clic).
REM Detecta puertos en uso y arranca el servidor en el primero libre.
title TD Dev Compendium
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] No se encontro Python. Instalalo desde https://www.python.org/downloads/
  echo y vuelve a intentarlo.
  pause
  exit /b 1
)
python tools\launcher.py
pause
