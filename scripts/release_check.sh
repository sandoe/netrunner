#!/usr/bin/env bash

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
    echo "Mangler .env. Kør ./start.sh init først."
    exit 1
fi

echo "[1/7] Shell og Compose-konfiguration"
bash -n start.sh install.sh scripts/release_check.sh
docker compose config --quiet

if [[ "${1:-}" != "--live-only" && -x .venv/bin/python3 && -d frontend/node_modules ]]; then
    echo "[2/7] Backendtests"
    .venv/bin/python3 -m pytest backend/tests -q

    echo "[3/7] Frontendtests"
    npm --prefix frontend run test:unit -- --run

    echo "[4/7] Produktionsbuild"
    npm --prefix frontend run build
elif [[ "${1:-}" == "--live-only" ]]; then
    echo "[2-4/7] Lokale build-gates sprunget over (--live-only)"
else
    echo "[2-4/7] Lokale build-gates ikke tilgængelige på denne Docker-vært"
    echo "         (de kræver .venv og frontend/node_modules; Docker-imaget er allerede bygget)"
fi

echo "[5/7] Containerstatus"
docker compose ps
docker compose exec -T netrunner \
    test -f /app/protocols/docker-compose.protocols.yml

echo "[6/7] Ikke-destruktiv live smoke-test"
python3 scripts/live_smoke.py

if [[ -d frontend/node_modules ]] && command -v google-chrome >/dev/null 2>&1; then
    echo "[7/7] Rollebaseret browsertest"
    npm --prefix frontend run test:e2e:release
else
    echo "[7/7] Browsertest ikke tilgængelig (kræver frontend/node_modules og Google Chrome)"
    echo "      Bekræft login og dashboard manuelt fra en elevmaskine."
fi

echo "RELEASE CHECK PASSED"
