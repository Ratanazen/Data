@echo off
REM ==============================================================================
REM 1-Click Launcher for Windows Users (Double-click to start)
REM Runs LogShield REST API, Web Dashboard, and opens browser
REM ==============================================================================
cd /d "%~dp0"
echo ==============================================================================
echo   LOGSHIELD - DISTRIBUTED LOG ANALYTICS ^& SECURITY DETECTION PLATFORM
echo ==============================================================================

if exist .venv\Scripts\python.exe (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

if not exist web_dashboard_data.json (
    echo [*] Generating analytics deliverables...
    "%PYTHON%" run_analysis.py
)

echo [+] Starting LogShield Platform and opening Web Dashboard...
"%PYTHON%" serve.py 8080 --open
pause
