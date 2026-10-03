@echo off
REM ==============================================================================
REM 1-Click Launcher for Windows Users (Double-click to start)
REM ==============================================================================
cd /d "%~dp0"
echo Starting Log File Analysis Web Dashboard...
call build.bat all
call build.bat web
pause
