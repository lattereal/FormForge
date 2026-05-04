@echo off
title FormForge v2.3 - Clear Logs
color 0C
cd /d "%~dp0.."
echo.
echo  This will delete all files in the logs\ folder.
set /p confirm=  Are you sure? (y/n): 
if /i "%confirm%"=="y" (
    del /q logs\*.*
    echo  Logs cleared.
) else (
    echo  Cancelled.
)
echo.
pause
