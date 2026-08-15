@echo off
cd /d "%~dp0"
title Push cream paper theme to GitHub

echo ============================================
echo  Pushing to github.com/eswarorsu/NiRaConChem-AI
echo ============================================
echo.
echo Commit to be pushed:
git log -1 --oneline
echo.

git push origin main

echo.
if errorlevel 1 (
  echo [FAILED] Push did not complete. Read the message above.
  echo If it asked you to sign in, complete the sign-in and run this again.
) else (
  echo [DONE] Pushed successfully.
)
echo.
pause
