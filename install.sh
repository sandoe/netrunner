#!/usr/bin/env bash
# Backwards-compatible entry point. start.sh owns the deployment workflow.

set -euo pipefail
cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")"
exec ./start.sh "${1:-start}"
