@echo off
REM ==============================================================================
REM LogShield 1-Click Launcher (Windows CMD / File Explorer)
REM Double-click this file in Windows File Explorer to start
REM ==============================================================================
cd /d "%~dp0"

if exist .venv\Scripts\python.exe (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

if not exist .venv (
    echo [*] Setting up Python virtual environment for Windows...
    python -m venv .venv
    set PYTHON=.venv\Scripts\python.exe
    "%PYTHON%" -m pip install --upgrade pip
    "%PYTHON%" -m pip install -r requirements.txt
)

echo [*] Launching LogShield on Windows...
"%PYTHON%" app.py %*
if %ERRORLEVEL% NEQ 0 (
    echo [!] Server exited with error code %ERRORLEVEL%
    pause
)
