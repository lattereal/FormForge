@echo off
title FormForge v2.3 - Setup
color 0B
cd /d "%~dp0.."
echo.
echo  ============================================
echo   FormForge v2.3  --  Dependency Installer
echo  ============================================
echo.
echo  Installing required packages...
echo.
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo  Done! Run scripts\run.bat to launch.
echo.
pause
