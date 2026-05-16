@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo [EyeCursor] Windows setup starting...
echo.

set "PYEXE="
for %%V in (3.12 3.11) do (
    if not defined PYEXE (
        py -%%V --version >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            for /f "tokens=*" %%P in ('py -%%V -c "import sys;print(sys.executable)"') do set "PYEXE=%%P"
            echo [EyeCursor] Using Python %%V at !PYEXE!
        )
    )
)

if not defined PYEXE (
    echo [EyeCursor] ERROR: No suitable Python (3.11 or 3.12) found.
    echo Many of the dependencies ^(dlib, mediapipe, panda3d^) do not yet have
    echo Windows wheels for Python 3.13+. Install Python 3.11 or 3.12 from
    echo https://www.python.org/downloads/ and re-run this script.
    pause
    exit /b 1
)

if exist "venv\Scripts\python.exe" (
    echo [EyeCursor] venv already exists -- skipping creation.
) else (
    echo [EyeCursor] Creating venv...
    "%PYEXE%" -m venv venv
    if !ERRORLEVEL! NEQ 0 (
        echo [EyeCursor] ERROR: failed to create venv.
        pause
        exit /b 1
    )
)

echo [EyeCursor] Upgrading pip...
"venv\Scripts\python.exe" -m pip install --upgrade pip

echo [EyeCursor] Installing requirements ^(this may take a while -- torch is large^)...
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if !ERRORLEVEL! NEQ 0 (
    echo.
    echo [EyeCursor] WARNING: pip install reported errors.
    echo If 'dlib' failed: install Visual Studio Build Tools ^(C++ workload^),
    echo or 'pip install cmake' and retry. Some users use a prebuilt wheel.
    pause
    exit /b 1
)

echo.
echo [EyeCursor] Setup complete.
echo   - launch.bat            ^(main app^)
echo   - launch_criteria.bat   ^(criteria app^)
echo   - launch_game.bat       ^(game^)
echo.
echo To create desktop shortcuts run:  scripts\create_shortcuts.ps1
echo   ^(right-click -^> Run with PowerShell, or in PowerShell:
echo    powershell -ExecutionPolicy Bypass -File scripts\create_shortcuts.ps1^)
echo.
pause
