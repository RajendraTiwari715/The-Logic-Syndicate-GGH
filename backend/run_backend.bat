@echo off
echo ========================================================
echo Starting IBVAP ANPR AI Backend Server...
echo ========================================================

cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

if exist ".venv\Scripts\python.exe" (
    echo [INFO] Using virtual environment Python: .venv
    ".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    echo [INFO] Using system Python
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
)

pause
