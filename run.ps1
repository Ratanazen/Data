# ==============================================================================
# LogShield 1-Click Launcher (Windows PowerShell)
# Run in PowerShell: .\run.ps1
# ==============================================================================
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$PythonPath = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonPath)) {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $PythonPath = "python"
    } else {
        Write-Error "Python is not installed or not in PATH."
    }
}

Write-Host "[*] Launching LogShield via PowerShell..." -ForegroundColor Cyan
& $PythonPath (Join-Path $ScriptDir "app.py") @args
