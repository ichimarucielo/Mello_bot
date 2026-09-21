@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado.
    echo Execute primeiro: scripts\setup_windows.bat
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
