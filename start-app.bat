@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-app.ps1"

if errorlevel 1 (
    echo.
    echo FundamentalIQ could not start. Review the error above.
    pause
)
