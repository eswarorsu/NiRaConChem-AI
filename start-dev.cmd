@echo off
title NIRACONCHEM AI - Launcher
echo Starting NIRACONCHEM AI (backend + frontend)...
echo.
echo Two windows will open. Leave both running.
echo   Backend  -> http://127.0.0.1:8000/health
echo   Frontend -> http://localhost:3000
echo.

start "NIRACONCHEM Backend" cmd /k "%~dp0start-backend.cmd"
timeout /t 2 /nobreak >nul
start "NIRACONCHEM Frontend" cmd /k "%~dp0start-frontend.cmd"

echo Launched. You can close this window.
timeout /t 5 /nobreak >nul
