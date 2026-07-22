@echo off
title MultiAgent BrainEngine 2
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on this computer.
    echo Install it from https://www.python.org/downloads/ and tick "Add Python to PATH".
    pause
    exit /b 1
)
python -c "import uvicorn" >nul 2>nul
if errorlevel 1 (
    echo The required packages are not installed yet.
    echo Please run "Install Requirements.bat" first, then come back here.
    pause
    exit /b 1
)
python engine\launcher.py
