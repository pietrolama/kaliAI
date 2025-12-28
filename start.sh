#!/bin/bash

# Configuration
export PATH=$PATH:$HOME/.local/bin
export PYTHONPATH=$PYTHONPATH:.
export FLASK_DEBUG=true  # Enable debug mode (binds to 127.0.0.1 only)
export PYTHONUNBUFFERED=1  # Force real-time log output (no buffering)

# Banner
echo "============================================================================="
echo "   _____ ______ _____ _______ _____ ____  _   _    ___  "
echo "  / ____|  ____/ ____|__   __|_   _/ __ \| \ | |  / _ \ "
echo " | (___ | |__ | |       | |    | || |  | |  \| | | (_) |"
echo "  \___ \|  __|| |       | |    | || |  | | . \` |  \__, |"
echo "  ____) | |___| |____   | |   _| || |__| | |\  |    / / "
echo " |_____/|______\_____|  |_|  |_____\____/|_| \_|   /_/  "
echo "                                                        "
echo "   INITIALIZING SWARM ARCHITECTURE...                   "
echo "============================================================================="
echo "[*] Host: $(hostname) | User: $(whoami)"
echo "[*] Path: $(pwd)"

# 1. Check Podman
if ! command -v podman &> /dev/null; then
    echo "[!] CRITICAL: 'podman' not found. This architecture requires Rootless Podman."
    exit 1
fi
echo "[*] Podman: DETECTED"

# 2. Check Podman Compose
if ! command -v podman-compose &> /dev/null; then
    echo "[!] WARNING: 'podman-compose' not found in PATH."
    echo "[!] Attempting to use python module..."
    if ! python3 -m podman_compose --version &> /dev/null; then 
        echo "[!] CRITICAL: podman-compose not found. Install it with: pip install podman-compose"
        exit 1
    fi
else
    echo "[*] Podman-Compose: DETECTED"
fi

# 3. Env Check
if [ ! -f .env ]; then
    echo "[!] ERROR: .env file missing."
    exit 1
fi

# 4. Cleanup Ports
echo "[*] Clearing port 5000..."
lsof -ti:5000 | xargs kill -9 2>/dev/null

# 5. Activate Venv
echo "[*] Activating Neural Link (venv)..."
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
else
    echo "[!] Venv not found. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# 6. Load Env
export $(grep -v '^#' .env | xargs)

# 7. Start
echo "[*] Initializing GhostBrain Core..."
python3 -u run.py  # -u: unbuffered output for real-time logs
