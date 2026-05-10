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
- Node.js (for frontend build)
- `npm`

### Quick Start
1. Run `./start.sh` from the root directory.
2. The script will:
   - Create a Python virtual environment.
   - Install dependencies.
   - Build the frontend.
   - Start the backend on `http://localhost:8000`.

## Architecture
- **Backend:** FastAPI (Python)
- **Frontend:** Vue 3 + TypeScript + Vite
- **Storage:** SQLite (Migrated from JSON)
- **Communication:** WebSockets (Terminal), REST API
