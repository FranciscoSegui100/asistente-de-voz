@echo off
rem Abre la interfaz grafica de Nova (usa el entorno virtual .venv si existe)
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" interfaz.py
) else (
    python interfaz.py
)
if errorlevel 1 pause
