@echo off
rem Abre la interfaz gráfica de Nova (usa el entorno virtual .venv si existe)
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" interfaz.py
) else (
    python interfaz.py
)
if errorlevel 1 pause
