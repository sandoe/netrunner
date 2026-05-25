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

# Ensure self-signed certs for HTTPS/WSS exist
mkdir -p .certs
if [ ! -f ".certs/cert.pem" ] || [ ! -f ".certs/key.pem" ]; then
    echo "Generating self-signed SSL certificates for HTTPS/WSS..."
    openssl req -x509 -newkey rsa:4096 -keyout .certs/key.pem -out .certs/cert.pem -sha256 -days 365 -nodes -subj "/CN=localhost" 2>/dev/null
fi

echo "Starting Netrunner on https://localhost:8000"
exec python3 netrunner.py --ssl-keyfile .certs/key.pem --ssl-certfile .certs/cert.pem "$@"
