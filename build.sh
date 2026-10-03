#!/usr/bin/env bash
# ==============================================================================
# Build & Automation Script for Assignment 2: Log File Analysis (Hadoop & PySpark)
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# ANSI Colors & Emojis
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_CYAN="\033[36m"
C_GREEN="\033[32m"
C_RED="\033[31m"
C_YELLOW="\033[33m"
C_BLUE="\033[34m"
C_MAGENTA="\033[35m"

# Detect Python interpreter (.venv preferred, fallback to system python3)
if [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    PYTHON="python"
fi

print_header() {
    echo -e "${C_BOLD}${C_CYAN}====================================================================${C_RESET}"
    echo -e "  $1"
    echo -e "${C_BOLD}${C_CYAN}====================================================================${C_RESET}"
}

cmd_help() {
    print_header "📊 LOG FILE ANALYSIS — BUILD & RUN AUTOMATION"
    echo -e "Usage: ./build.sh [COMMAND | OPTION]"
    echo ""
    echo -e "${C_BOLD}Commands:${C_RESET}"
    echo -e "  ${C_GREEN}check${C_RESET}       🔍 Audit environment, dependencies, log integrity, & artifacts"
    echo -e "  ${C_GREEN}build${C_RESET}       ⚡ Run data pipeline, generate CSVs, high-res PNGs, & JSON"
    echo -e "  ${C_GREEN}web${C_RESET} [port]  🌐 Start the local interactive Web Dashboard (default: 8080)"
    echo -e "  ${C_GREEN}report${C_RESET}      📄 Re-export standalone HTML report (Log_File_Analysis_Report.html)"
    echo -e "  ${C_GREEN}test${C_RESET}        🧪 Run automated unit test suite (9 test cases)"
    echo -e "  ${C_GREEN}clean${C_RESET}       🧹 Remove bytecode, caches, and temporary files"
    echo -e "  ${C_GREEN}all${C_RESET}         🚀 Complete workflow: clean, check, test, build, and verify"
    echo -e "  ${C_GREEN}help${C_RESET}        📖 Show this help message"
    echo ""
    echo -e "${C_BOLD}Options:${C_RESET}"
    echo -e "  --port=<PORT> Specify web server port (e.g. ./build.sh web --port=3000)"
    echo -e "  --help        Display this help text"
    echo ""
}

cmd_check() {
    print_header "🔍 Checking Environment & Dependencies"
    echo -e "${C_BLUE}[*] Python interpreter:${C_RESET} $PYTHON ($($PYTHON --version))"
    
    # Check packages
    $PYTHON -c "
for pkg in ['pandas', 'numpy', 'matplotlib', 'seaborn']:
    try:
        __import__(pkg)
        print(f'  \033[32m[✓]\033[0m {pkg:<12} available')
    except ImportError:
        print(f'  \033[31m[!]\033[0m {pkg:<12} NOT installed')
"
    
    # Check log file
    if [ -f "server.log" ]; then
        LINES=$(wc -l < server.log)
        echo -e "  ${C_GREEN}[✓]${C_RESET} server.log exists ($LINES lines)"
    else
        echo -e "  ${C_RED}[!]${C_RESET} server.log missing! Run build.sh build to generate."
    fi

    # Check deliverable files
    echo ""
    echo -e "${C_BLUE}[*] Checking deliverable files:${C_RESET}"
    for f in hourly_404_errors.csv status_code_breakdown.csv heatmap_day_hour_404.csv top_404_paths.csv daily_404_trend.csv summary_stats.txt 404_errors_by_hour.png 404_heatmap_day_hour.png top_404_paths.png 404_daily_trend.png index.html; do
        if [ -f "$f" ]; then
            echo -e "  ${C_GREEN}[✓]${C_RESET} $f ($(ls -lh "$f" | awk '{print $5}'))"
        else
            echo -e "  ${C_YELLOW}[!]${C_RESET} $f ${C_RED}MISSING${C_RESET}"
        fi
    done
}

cmd_build() {
    print_header "⚡ Running Data Analysis & Generating Artifacts"
    $PYTHON run_analysis.py
    $PYTHON export_report.py
    echo ""
    echo -e "${C_GREEN}[✓] Build complete! All figures, CSVs, and Web data generated.${C_RESET}"
}

cmd_web() {
    PORT="${1:-8080}"
    # check for --port= flag
    for arg in "$@"; do
        if [[ "$arg" =~ ^--port=([0-9]+)$ ]]; then
            PORT="${BASH_REMATCH[1]}"
        elif [[ "$arg" =~ ^[0-9]+$ ]]; then
            PORT="$arg"
        fi
    done
    print_header "🌐 Launching Interactive Web Dashboard"
    $PYTHON serve.py "$PORT"
}

cmd_report() {
    print_header "📄 Exporting HTML Report"
    $PYTHON export_report.py
    echo -e "${C_GREEN}[✓] Report exported to: Log_File_Analysis_Report.html${C_RESET}"
}

cmd_test() {
    print_header "🧪 Running Automated Unit Tests"
    $PYTHON -m unittest discover -s tests -p "test_*.py"
    echo -e "${C_GREEN}[✓] All unit tests passed successfully!${C_RESET}"
}

cmd_clean() {
    print_header "🧹 Cleaning Temporary Files"
    rm -rf __pycache__ tests/__pycache__ .pytest_cache *.pyc
    echo -e "${C_GREEN}[✓] Clean completed.${C_RESET}"
}

ACTION="${1:-all}"
shift || true

case "$ACTION" in
    check|--check)
        cmd_check
        ;;
    build|run|--build)
        cmd_build
        ;;
    web|serve|--web)
        cmd_web "$@"
        ;;
    report|--report)
        cmd_report
        ;;
    test|--test)
        cmd_test
        ;;
    clean|--clean)
        cmd_clean
        ;;
    all|--all)
        cmd_clean
        cmd_check
        echo ""
        cmd_test
        echo ""
        cmd_build
        echo ""
        print_header "🎉 Ready to Explore"
        echo -e "  ${C_CYAN}• Launch Web Dashboard :${C_RESET} ./build.sh web"
        echo -e "  ${C_CYAN}• Direct Browser Link  :${C_RESET} file://$DIR/index.html"
        echo -e "  ${C_CYAN}• Standalone HTML Report:${C_RESET} file://$DIR/Log_File_Analysis_Report.html"
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        cmd_help
        exit 1
        ;;
esac
