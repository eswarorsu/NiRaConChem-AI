@echo off
title NIRACONCHEM AI - Backend
cd /d "%~dp0backend"

echo ============================================
echo  NIRACONCHEM AI - Backend (FastAPI)
echo ============================================
echo.

if not exist "venv\Scripts\python.exe" (
  echo [ERROR] No virtualenv found at backend\venv
  echo Create one with:  python -m venv venv
  echo.
  pause
  exit /b 1
)

echo Checking dependencies (importing the real app)...
venv\Scripts\python.exe -c "import app.main" 2>nul
if errorlevel 1 (
  echo Import failed - installing/repairing dependencies from requirements.txt...
  venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo [ERROR] Dependency install failed. Check your internet connection.
    pause
    exit /b 1
  )
  echo Re-checking import...
  venv\Scripts\python.exe -c "import app.main"
  if errorlevel 1 (
    echo.
    echo [ERROR] App still fails to import. Full error:
    venv\Scripts\python.exe -c "import app.main"
    pause
    exit /b 1
  )
) else (
  echo Dependencies OK.
)

echo.
echo Starting API on http://127.0.0.1:8000
echo Health check: http://127.0.0.1:8000/health
echo Press CTRL+C to stop.
echo.
venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo Backend stopped.
pause
