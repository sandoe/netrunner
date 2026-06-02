# Netrunner

Netrunner is a comprehensive network and Linux management tool featuring AI-driven orchestration, live telemetry, and configuration automation.

## Features
- **Node Management:** Organize and manage Linux servers, Raspberry Pis, and GNS3/Network devices.
- **Live Telemetry:** Real-time diagnostics for network interfaces, routing, firewall rules, and system metrics.
- **Config Automation:** Generate and apply complex configurations (VLANs, NAT, WireGuard, Firewall, Services).
- **Interactive Terminal:** Integrated SSH/Telnet terminal with connection pooling.
- **AI Agent:** Chat-based orchestration for managing nodes and topology using tool-calling.
- **MCP Server:** Model Context Protocol integration for AI clients like Claude.
- **GNS3 Integration:** Sync nodes and links directly from GNS3 projects.

## Setup

### Prerequisites
- Python 3.10+
- Node.js LTS (includes `npm`)

### Quick Start
Linux/macOS:

```bash
./start.sh
```

Windows PowerShell:

```powershell
.\start.ps1
```

Windows Command Prompt:

```bat
start.bat
```

The launcher will create a Python virtual environment, install backend
dependencies, install/build the frontend, initialize the SQLite database, and
start Netrunner on `http://localhost:8000`.

Default login for teaching/local installs:

- Username: `admin`
- Password: `admin`

Netrunner creates the missing default users on startup. Existing users are not
overwritten. To choose safer first-run passwords, set
`NETRUNNER_ADMIN_PASSWORD` and/or `NETRUNNER_ANALYST_PASSWORD` before the first
start.

## Architecture
- **Backend:** FastAPI (Python)
- **Frontend:** Vue 3 + TypeScript + Vite
- **Storage:** SQLite (Migrated from JSON)
- **Communication:** WebSockets (Terminal), REST API
