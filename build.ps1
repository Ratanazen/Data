# ==============================================================================
# Build & Automation Script for Assignment 2 (Windows / Mac PowerShell)
# ==============================================================================
param (
    [Parameter(Position=0)]
    [string]$Action = "all",
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Detect Python interpreter
if (Test-Path "$ScriptDir\.venv\Scripts\python.exe") {
    $Python = "$ScriptDir\.venv\Scripts\python.exe"
} elseif (Test-Path "$ScriptDir/.venv/bin/python") {
    $Python = "$ScriptDir/.venv/bin/python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $Python = "py"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $Python = "python3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Python = "python"
} else {
    Write-Error "Python 3 is required but was not found in PATH or .venv."
}

function Show-Header ($text) {
    Write-Host "====================================================================" -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor White
    Write-Host "====================================================================" -ForegroundColor Cyan
}

switch ($Action.ToLower()) {
    "help" {
        Show-Header "📊 LOG FILE ANALYSIS — POWERSHELL AUTOMATION"
        Write-Host "Usage: .\build.ps1 [check | build | web | report | test | clean | all] [-Port 8080]"
        Write-Host ""
    }
    "check" {
        Show-Header "🔍 Checking Environment & Deliverables"
        Write-Host "[*] Python interpreter: $Python" -ForegroundColor Blue
        & $Python -c "import pandas, numpy, matplotlib, seaborn; print('  [OK] Core analytics libraries available')"
        if (Test-Path "server.log") {
            Write-Host "  [OK] server.log exists" -ForegroundColor Green
        } else {
            Write-Host "  [!] server.log missing" -ForegroundColor Yellow
        }
        $files = @("hourly_404_errors.csv", "status_code_breakdown.csv", "heatmap_day_hour_404.csv",
                   "top_404_paths.csv", "daily_404_trend.csv", "summary_stats.txt",
                   "404_errors_by_hour.png", "404_heatmap_day_hour.png", "top_404_paths.png",
                   "404_daily_trend.png", "index.html", "docker-compose.cluster.yml", "cluster-configs\yarn-site.xml")
        foreach ($f in $files) {
            if (Test-Path $f) {
                Write-Host "  [OK] $f" -ForegroundColor Green
            } else {
                Write-Host "  [!] $f MISSING" -ForegroundColor Red
            }
        }
    }
    "build" {
        Show-Header "⚡ Running Data Pipeline & Generating Artifacts"
        & $Python run_analysis.py
        & $Python export_report.py
        Write-Host "[✓] Build complete! All figures, CSVs, and Web data generated." -ForegroundColor Green
    }
    "web" {
        Show-Header "🌐 Launching Web Dashboard (Port $Port)"
        Start-Process "http://localhost:$Port/"
        & $Python serve.py $Port
    }
    "report" {
        Show-Header "📄 Exporting HTML Report"
        & $Python export_report.py
        Write-Host "[✓] Generated: Log_File_Analysis_Report.html" -ForegroundColor Green
    }
    "test" {
        Show-Header "🧪 Running Automated Unit Tests"
        & $Python -m unittest discover -s tests -p "test_*.py"
        Write-Host "[✓] All unit tests passed!" -ForegroundColor Green
    }
    "clean" {
        Show-Header "🧹 Cleaning Temporary Files"
        Get-ChildItem -Path . -Include __pycache__,*.pyc -Recurse -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "[✓] Clean complete." -ForegroundColor Green
    }
    "all" {
        Show-Header "🚀 Full Pipeline Execution"
        & $MyInvocation.MyCommand.Path clean
        Write-Host ""
        & $MyInvocation.MyCommand.Path check
        Write-Host ""
        & $MyInvocation.MyCommand.Path test
        Write-Host ""
        & $MyInvocation.MyCommand.Path build
        Write-Host ""
        Write-Host "🎉 Ready! Run .\build.ps1 web to launch the dashboard." -ForegroundColor Green
    }
    default {
        Write-Host "Unknown command '$Action'. Run .\build.ps1 help for usage." -ForegroundColor Red
    }
}
