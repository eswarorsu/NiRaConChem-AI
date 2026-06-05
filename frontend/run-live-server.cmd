@echo off
cd /d "%~dp0"
npm.cmd run dev -- --port 3000 > next-live.log 2>&1
