#!/usr/bin/env bash
# ==============================================================================
# 1-Click Launcher for LogShield (Linux / macOS)
# Runs the complete platform (FastAPI REST API & Web Dashboard) & opens browser
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# ANSI Colors
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_CYAN="\033[36m"
C_GREEN="\033[32m"
C_YELLOW="\033[33m"

# Detect Python interpreter (.venv preferred)
if [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    PYTHON="python"
fi

echo -e "${C_BOLD}${C_CYAN}======================================================================${C_RESET}"
echo -e "${C_BOLD}  LOGSHIELD — DISTRIBUTED LOG ANALYTICS & SECURITY DETECTION PLATFORM${C_RESET}"
echo -e "${C_BOLD}${C_CYAN}======================================================================${C_RESET}"

# Verify core deliverable exists; if missing, generate on first run
if [ ! -f "web_dashboard_data.json" ] || [ ! -f "hourly_404_errors.csv" ]; then
    echo -e "${C_YELLOW}[*] Generating initial lakehouse analytics deliverables...${C_RESET}"
    "$PYTHON" run_analysis.py
fi

echo -e "${C_GREEN}[+] Launching LogShield services & Web Dashboard...${C_RESET}"
exec "$PYTHON" serve.py 8080 --open "$@"
