@echo off
REM ==============================================================================
REM Build & Automation Script for Assignment 2 (Windows Command Prompt)
REM ==============================================================================

setlocal enabledelayedexpansion

cd /d "%~dp0"

REM Detect Python executable (check .venv, py, python)
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    where py >nul 2>nul
    if !errorlevel! equ 0 (
        set "PYTHON=py -3"
    ) else (
        where python >nul 2>nul
        if !errorlevel! equ 0 (
            set "PYTHON=python"
        ) else (
            echo [!] Python not found in PATH or .venv! Please install Python 3.
            exit /b 1
        )
    )
)

set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=all"

if /i "%ACTION%"=="help" goto cmd_help
if /i "%ACTION%"=="--help" goto cmd_help
if /i "%ACTION%"=="check" goto cmd_check
if /i "%ACTION%"=="--check" goto cmd_check
if /i "%ACTION%"=="build" goto cmd_build
if /i "%ACTION%"=="run" goto cmd_build
if /i "%ACTION%"=="--build" goto cmd_build
if /i "%ACTION%"=="web" goto cmd_web
if /i "%ACTION%"=="serve" goto cmd_web
if /i "%ACTION%"=="--web" goto cmd_web
if /i "%ACTION%"=="report" goto cmd_report
if /i "%ACTION%"=="--report" goto cmd_report
if /i "%ACTION%"=="test" goto cmd_test
if /i "%ACTION%"=="--test" goto cmd_test
if /i "%ACTION%"=="clean" goto cmd_clean
if /i "%ACTION%"=="--clean" goto cmd_clean
if /i "%ACTION%"=="all" goto cmd_all
if /i "%ACTION%"=="--all" goto cmd_all

:cmd_help
echo ====================================================================
echo   LOG FILE ANALYSIS (WINDOWS BATCH AUTOMATION)
echo ====================================================================
echo Usage: build.bat [check ^| build ^| web ^| report ^| test ^| clean ^| all ^| help]
echo.
echo Commands:
echo   check   - Audit environment, packages, and deliverables
echo   build   - Run data pipeline, generate CSVs, PNGs, and JSON
echo   web     - Launch local Web Dashboard (default port 8080)
echo   report  - Re-export standalone HTML report
echo   test    - Run 10 automated unit tests
echo   clean   - Delete pycache and temporary files
echo   all     - Full sequence: clean, check, test, build
echo.
exit /b 0

:cmd_check
echo ====================================================================
echo   Checking Environment & Deliverables (Windows)
echo ====================================================================
echo [*] Python interpreter: %PYTHON%
%PYTHON% -c "import pandas, numpy, matplotlib, seaborn; print('[v] Core analytics packages available')" 2>nul || echo [!] Some packages missing. Run: pip install -r requirements.txt
if exist "server.log" (
    echo [v] server.log exists
) else (
    echo [!] server.log missing
)
for %%f in (hourly_404_errors.csv status_code_breakdown.csv heatmap_day_hour_404.csv top_404_paths.csv daily_404_trend.csv summary_stats.txt 404_errors_by_hour.png 404_heatmap_day_hour.png top_404_paths.png 404_daily_trend.png index.html) do (
    if exist "%%f" (
        echo [v] %%f
    ) else (
        echo [!] %%f MISSING
    )
)
exit /b 0

:cmd_build
echo ====================================================================
echo   Running Data Pipeline ^& Generating Artifacts
echo ====================================================================
%PYTHON% run_analysis.py
%PYTHON% export_report.py
echo [v] Build complete!
exit /b 0

:cmd_web
set "PORT=%~2"
if "%PORT%"=="" set "PORT=8080"
echo ====================================================================
echo   Launching Interactive Web Dashboard (Port %PORT%)
echo ====================================================================
start "" http://localhost:%PORT%/
%PYTHON% serve.py %PORT%
exit /b 0

:cmd_report
echo [*] Exporting HTML Report...
%PYTHON% export_report.py
echo [v] Report exported: Log_File_Analysis_Report.html
exit /b 0

:cmd_test
echo ====================================================================
echo   Running Automated Unit Tests
echo ====================================================================
%PYTHON% -m unittest discover -s tests -p "test_*.py"
echo [v] Unit tests completed!
exit /b 0

:cmd_clean
echo [*] Cleaning temporary files...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
del /q *.pyc 2>nul
echo [v] Clean completed.
exit /b 0

:cmd_all
call :cmd_clean
echo.
call :cmd_check
echo.
call :cmd_test
echo.
call :cmd_build
echo.
echo ====================================================================
echo   Ready! To launch the web dashboard, run: build.bat web
echo ====================================================================
exit /b 0
