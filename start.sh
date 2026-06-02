#!/usr/bin/env bash
# Netrunner - install dependencies and start the app.
set -e
cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Install it and try again."
    exit 1
fi

exec python3 scripts/start_netrunner.py "$@"
