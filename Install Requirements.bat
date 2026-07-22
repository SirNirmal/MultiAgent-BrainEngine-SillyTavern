@echo off
title MultiAgent BrainEngine 2 - Install
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on this computer.
    echo Install it from https://www.python.org/downloads/ and tick "Add Python to PATH".
    pause
    exit /b 1
)
echo ============================================================
echo   MultiAgent BrainEngine 2 - installing required packages
echo ============================================================
echo.
python -m pip install -r engine\requirements.txt
if errorlevel 1 (
    echo.
    echo Something went wrong. Check the messages above.
    pause
    exit /b 1
)
echo.
echo ============================================================
echo   Done. You can now run "Start BrainEngine.bat".
echo ============================================================
pause
