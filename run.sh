#!/usr/bin/env bash
# ==============================================================================
# LogShield 1-Click Launcher (Linux & macOS)
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Detect Python interpreter
if [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    PYTHON="python"
fi

# Auto-setup virtual environment if missing
if [ ! -d "$DIR/.venv" ] && command -v python3 &>/dev/null; then
    echo "[*] Creating virtual environment (.venv)..."
    python3 -m venv "$DIR/.venv"
    PYTHON="$DIR/.venv/bin/python"
    "$PYTHON" -m pip install -q --upgrade pip
    "$PYTHON" -m pip install -q -r "$DIR/requirements.txt"
fi

exec "$PYTHON" "$DIR/app.py" "$@"
