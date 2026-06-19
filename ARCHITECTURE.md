# Netrunner SIEM / XDR - Project Architecture & Memory

Dette dokument fungerer som "hukommelse" for AI-agenter. Hvis du arbejder på Netrunner-projektet, skal du bruge dette som reference for at forstå, hvordan alt hænger sammen.

## 🎯 Formål
Netrunner er et enterprise-level Command & Control (C2) / SIEM (Security Information and Event Management) og XDR system. 
Det har et **Cyberpunk / Matrix / Neon**-visuelt tema på frontend.

## 🏗️ Stakken
- **Backend:** Python + FastAPI + SQLAlchemy + SQLite (via Alembic)
- **Frontend:** Vue.js 3 (Composition API) + TypeScript + Vite + Chart.js
- **API Client:** OpenAPI-TS (genererer TS SDK fra FastAPI)

## 📂 Nøglemapper
- `backend/main.py`: Indgangspunkt for FastAPI. Håndterer lifespan, baggrunds-tasks (IDS, Vuln Scanner, Threat Intel) og inkluderer alle routers.
- `backend/core/db.py`: Database-opsætning. Indeholder alle ORM modeller (`IntegrationModel`, `AuditLogModel`, `AlertModel`, `ThreatIntelModel`, etc.) samt async CRUD-funktioner.
- `backend/routers/`: Indeholder API endpoints (f.eks. `analytics.py`, `playbooks.py`, `hunting.py`).
- `backend/services/`: Baggrundstjenester (f.eks. `threat_intel.py`, `ids_engine.py`, `vuln_scanner.py`).
- `frontend/src/views/`: Vue Views. 
- `frontend/src/router/index.ts`: Opsætning af side-ruter.
- `frontend/src/api_client/`: Autogenereret kode fra OpenAPI spec. Kør *aldrig* manuelle ændringer her.

## 🔐 Kerne-Features (Enterprise Level)
1. **Analytics & CISO Dashboard**: `/dashboard` viser threat trends og mitigation rates. Drevet af `analytics.py`.
2. **Threat Intelligence Feed (TiF)**: `threat_intel.py` kører i baggrunden og populerer databasen med 'bad IPs'. `ids_engine.py` krydstjekker netværksalarmer mod databasen og mærker dem som `[KNOWN THREAT]`.
3. **Advanced Threat Hunting**: `/hunting` tillader søgning på tværs af `Alerts` og `Audit Logs` med regex-lignende hastighed.
4. **Audit Logging (CISO Trail)**: Alle kritiske ændringer (f.eks. når en playbook gemmes i `playbooks.py`) udløser `insert_audit_log` for compliance.
5. **Integrations**: `/integrations` tillader webhooks til eksterne systemer som Slack, Splunk og Teams.

## 🛠️ Ofte Brugte Kommandoer
- **Generer API Client (Frontend)**:
  `PYTHONPATH=. .venv/bin/python3 -c "import json; from backend.main import app; print(json.dumps(app.openapi()))" > backend/openapi.json && cd frontend && npx @hey-api/openapi-ts -i ../backend/openapi.json -o src/api_client -c @hey-api/client-fetch`
- **Kør Backend Tests**: `pytest backend/tests/`
- **Alembic Database Migrationer**: 
  Når `db.py` ændres, brug `rm -rf backend/alembic/versions/*` og kør en full squash (da dette er dev): 
  `PYTHONPATH=backend .venv/bin/alembic -c backend/alembic.ini revision --autogenerate -m "schema"`
  `PYTHONPATH=backend .venv/bin/alembic -c backend/alembic.ini upgrade head`

## 🧠 Design Filosofi
- Ingen standard Bootstrap/Tailwind. Al CSS skrives custom i "Cyberpunk" stil med neon-glød (box-shadows) og dark mode (sort/blå farver).
- Al frontend data hentes asynkront via `@hey-api/client-fetch` functions under `onMounted`.
- Backend er fuldt async; SQLAlchemy bruger `AsyncSessionLocal`.
