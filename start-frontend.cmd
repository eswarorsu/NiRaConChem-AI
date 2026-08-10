@echo off
title NIRACONCHEM AI - Frontend
cd /d "%~dp0frontend"

echo ============================================
echo  NIRACONCHEM AI - Frontend (Next.js)
echo ============================================
echo.

if not exist "node_modules" (
  echo node_modules missing - running npm install...
  call npm install
  if errorlevel 1 (
    echo.
    echo [ERROR] npm install failed.
    pause
    exit /b 1
  )
)

echo Starting dev server on http://localhost:3000
echo Press CTRL+C to stop.
echo.
call npm run dev

echo.
echo Frontend stopped.
pause
