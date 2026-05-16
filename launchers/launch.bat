@echo off
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo [EyeCursor] venv not found. Run setup_windows.bat first.
    pause
    exit /b 1
)
"venv\Scripts\python.exe" -m src.app.main %*
exit /b %ERRORLEVEL%
