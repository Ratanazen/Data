#!/usr/bin/env bash
# ==============================================================================
# Build & Automation Script for Assignment 2: Log File Analysis
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Detect Python interpreter (.venv preferred, fallback to system python3)
if [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    PYTHON="python"
fi

print_header() {
    echo "===================================================================="
    echo "  $1"
    echo "===================================================================="
}

cmd_check() {
    print_header "Checking Environment & Dependencies"
    echo "[*] Python interpreter: $PYTHON ($($PYTHON --version))"
    
    # Check packages
    $PYTHON -c "
for pkg in ['pandas', 'numpy', 'matplotlib', 'seaborn']:
    try:
        __import__(pkg)
        print(f'  [✓] {pkg:<12} available')
    except ImportError:
        print(f'  [!] {pkg:<12} NOT installed')
"
    
    # Check log file
    if [ -f "server.log" ]; then
        LINES=$(wc -l < server.log)
        echo "  [✓] server.log exists ($LINES lines)"
    else
        echo "  [!] server.log missing! Run build.sh build to generate."
    fi

    # Check deliverables
    echo ""
    echo "[*] Checking deliverable files:"
    for f in hourly_404_errors.csv status_code_breakdown.csv heatmap_day_hour_404.csv top_404_paths.csv daily_404_trend.csv summary_stats.txt 404_errors_by_hour.png 404_heatmap_day_hour.png top_404_paths.png 404_daily_trend.png index.html; do
        if [ -f "$f" ]; then
            echo "  [✓] $f ($(ls -lh "$f" | awk '{print $5}'))"
        else
            echo "  [!] $f MISSING"
        fi
    done
}

cmd_build() {
    print_header "Running Data Analysis & Generating Artifacts"
    $PYTHON run_analysis.py
    $PYTHON export_report.py
    echo ""
    echo "[✓] Build complete! All figures, CSVs, and Web data generated."
}

cmd_web() {
    print_header "Launching Interactive Web Dashboard"
    $PYTHON serve.py "$@"
}

cmd_report() {
    print_header "Exporting HTML Report"
    $PYTHON export_report.py
    echo "[✓] Report exported to: Log_File_Analysis_Report.html"
}

case "${1:-all}" in
    check)
        cmd_check
        ;;
    build|run)
        cmd_build
        ;;
    web|serve)
        shift || true
        cmd_web "$@"
        ;;
    report)
        cmd_report
        ;;
    all)
        cmd_check
        echo ""
        cmd_build
        echo ""
        print_header "Ready to Explore"
        echo "  - To launch the Web Dashboard : ./build.sh web"
        echo "  - Or open directly in browser : file://$DIR/index.html"
        echo "  - View HTML Report            : file://$DIR/Log_File_Analysis_Report.html"
        ;;
    *)
        echo "Usage: ./build.sh [check | build | web | report | all]"
        exit 1
        ;;
esac
