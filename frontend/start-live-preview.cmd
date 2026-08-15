@echo off
cd /d "%~dp0"
title NiRaConChem AI - live preview

echo Checking whether a dev server is already on port 3000...
powershell -NoProfile -Command "$c=New-Object Net.Sockets.TcpClient; try{$c.Connect('127.0.0.1',3000);$c.Close();exit 0}catch{exit 1}"

if %errorlevel%==0 goto :open

echo Starting Next.js dev server on http://localhost:3000 ...
start "NiRaConChem dev server" cmd /c "npm.cmd run dev -- --port 3000 > next-live.log 2>&1"

echo Waiting for it to compile ^(first build can take ~30s^)...
powershell -NoProfile -Command "for($i=0;$i -lt 90;$i++){$c=New-Object Net.Sockets.TcpClient; try{$c.Connect('127.0.0.1',3000);$c.Close();exit 0}catch{Start-Sleep -Milliseconds 1000}}; exit 1"

if not %errorlevel%==0 (
  echo.
  echo Server did not come up in time. See next-live.log for the reason.
  pause
  exit /b 1
)

:open
echo Opening http://localhost:3000
start "" http://localhost:3000
exit /b 0
