@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado.
    echo Execute primeiro: py -m venv .venv
    echo Depois: .venv\Scripts\python -m pip install -r requirements.txt
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m streamlit run frontend\app.py
