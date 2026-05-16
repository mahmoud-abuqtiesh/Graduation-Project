@echo off
REM Windows wrapper for scripts\sync_pi.py.
setlocal
set "REPO_ROOT=%~dp0.."
if not exist "%REPO_ROOT%\venv\Scripts\python.exe" (
    echo [sync_pi] venv not found at %REPO_ROOT%\venv. Run setup_windows.bat first.
    exit /b 1
)
"%REPO_ROOT%\venv\Scripts\python.exe" "%REPO_ROOT%\scripts\sync_pi.py" %*
exit /b %ERRORLEVEL%
