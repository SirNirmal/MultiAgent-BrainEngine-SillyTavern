@echo off
title MultiAgent BrainEngine 2 - Uninstall
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on this computer.
    pause
    exit /b 1
)
echo ============================================================
echo   MultiAgent BrainEngine 2 - removing its packages
echo ============================================================
echo.
echo Removing: fastapi, uvicorn, openai
echo (Your diaries in engine\memory.db are NOT touched.)
echo.
python -m pip uninstall -y fastapi uvicorn openai
echo.
echo ============================================================
echo   Done.
echo   Note: small shared helper libraries may remain - they are
echo   harmless and other programs on your PC might use them.
echo ============================================================
pause
