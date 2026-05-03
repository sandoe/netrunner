#!/usr/bin/env bash
# Netrunner — start backend + optionally build frontend
set -e
cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Install it and try again."
    exit 1
fi

# Install Python deps if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
. .venv/bin/activate
pip install -q -r backend/requirements.txt

# Build frontend if dist doesn't exist
if [ ! -d "frontend/dist" ] && command -v npm >/dev/null 2>&1; then
    echo "Building frontend..."
    cd frontend
    npm install --silent
    npm run build
    cd ..
fi

echo "Starting Netrunner on http://localhost:8000"
exec python3 netrunner.py "$@"
