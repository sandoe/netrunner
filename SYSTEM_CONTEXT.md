# SYSTEM_CONTEXT.md (Netrunner AI Memory)

**IMPORTANT INSTRUCTION TO AI AGENTS:** 
This document contains the core architectural constraints, folder structures, and technical definitions of the **Netrunner** platform. You MUST read and adhere to this document when suggesting features, refactoring code, or debugging. 

---

## 1. Platform Overview
**Netrunner** is an advanced Cybersecurity Command & Control (C2) and NOC (Network Operations Center) dashboard. 
It provides a "single pane of glass" for network topology visualization, threat hunting, alerts management, remote host execution, and physical MCU / USB payload delivery.

Its UI is designed to look highly technical, "cyberpunk", and terminal-like.

---

## 2. Technology Stack
- **Frontend**: Vue 3 (Composition API), Vite, TypeScript.
  - **Styling**: Pure CSS with CSS Variables (`var(--bg)`, `var(--cyan)`, etc.). No Tailwind unless specifically configured.
  - **Terminal UI**: `xterm.js` is used extensively for embedded terminal interfaces.
  - **Graphing**: D3.js is used for topology and knowledge graphs.
- **Backend**: Python 3.10+, FastAPI, Uvicorn.
  - **Asynchronous**: Uses `asyncio`, WebSockets, and Pydantic models.
- **Databases**: 
  - PostgreSQL (Primary persistence)
  - Redis (Pub/Sub, Caching)
  - InfluxDB (Time-series metrics)
- **Agent**: A remote agent written in Go (`/agent`) designed to execute workloads and reverse-shell commands.
- **Infrastructure**: Docker Compose (`docker-compose.yml`) orchestrates all services.

---

## 3. Directory Structure

### `frontend/src/`
- `views/`: High-level page components mapped to routes.
  - `DashboardView.vue`
  - `NetworkControllerView.vue` (Topology)
  - `HostControlView.vue` (Remote execution / PTY)
  - `ThreatHuntingView.vue`
  - `PlaybooksView.vue`
  - `DatabaseControlView.vue`
- `components/`: Reusable UI components.
  - `AiChatSidebar.vue` (The embedded AI Assistant terminal)
  - `Terminal.vue` (Generic xterm.js wrapper)
  - `TopologyView.vue`
- `api/`: API clients and WebSocket managers (`client.ts`).
- `stores/`: Pinia or custom state management for Vue.
- `router/`: Vue Router definitions (`index.ts`).

### `backend/`
- `main.py`: Entry point for the FastAPI application. Registers all routers and background tasks.
- `routers/`: Endpoint controllers categorized by domain.
  - `ai.py`: Handles `/api/ai/*` (Including WebSocket PTY for `opencode`).
  - `telemetry.py`: Handles `/api/telemetry/ui` (Records user UI clicks for AI context).
  - `terminal.py`: Handles multiplexing standard terminals.
  - `nodes.py`, `links.py`, `gns3.py`: Topology endpoints.
  - `bruteforce.py`, `defense.py`, `threats.py`: Security operation endpoints.
  - `usb.py`, `mcu.py`: Physical hardware endpoints.
- `core/`: Core business logic, configuration, state (`state.py`), and authentication (`auth.py`).

### `data/`
- `ui_context.log`: A rolling log file containing real-time user UI events (clicks, navigations). **AI Agents should read this file to understand what the user is currently looking at in the frontend.**

---

## 4. Key Architectural Patterns

### 1. WebSockets vs. HTTP
Netrunner relies heavily on WebSockets for real-time data:
- Terminals use WebSockets (`/ws/...`) attached to `pty` instances on the backend.
- Telemetry and Alerts are broadcasted via WebSockets.
- Standard CRUD operations use standard HTTP REST `GET`/`POST`/`PUT`.

### 2. Dependency Injection & Auth
Most HTTP endpoints are secured via FastAPI dependencies:
```python
@router.get("/example", dependencies=[Depends(AUTH)])
```
WebSocket endpoints have their own authentication wrapper:
```python
if await authenticate_ws(websocket) is None: return
```

### 3. AI Assistant Context (UI Telemetry)
The user can toggle "Share UI Context" in the frontend (`AiChatSidebar.vue`). When enabled, the frontend hooks into `router.afterEach` and `window.addEventListener('click')` to POST events to `backend/routers/telemetry.py`.
These events are written to `data/ui_context.log`. 
**If the user asks "What am I looking at?", you must tail or grep `data/ui_context.log` to find the most recent UI events.**

### 4. Embedded PTY for AI (`opencode`)
The AI Assistant in the frontend is NOT a standard chatbot UI. It is an `xterm.js` terminal connected to a Python backend that spawns an interactive PTY shell running an AI CLI (e.g., `opencode`). 
This means the user interacts with the AI via a pseudo-terminal.

---

## 5. Development Guidelines for AI

1. **Do not use absolute paths for Docker containers**: Remember that the code runs inside Docker containers. For instance, `/app` is the working directory for both frontend and backend inside their respective containers.
2. **Frontend Rebuilds**: If you modify `frontend/src/*`, the `netrunner-platform` container must be rebuilt using `docker compose build netrunner && docker compose up -d netrunner` because the frontend is statically built during the Docker build process. It does not use Vite's hot-module-replacement in production mode.
3. **Backend Reloads**: The backend runs with Uvicorn. However, structural changes or new routers usually require a restart: `docker compose restart netrunner`.
4. **Tool selection**: Prefer precision. Do not use generic tools (`cat | grep` or `sed`) if specialized tools (`grep_search` or `multi_replace_file_content`) are available.
5. **Preserve UI Aesthetics**: Always use the existing CSS variables (e.g., `var(--bg2)`, `var(--cyan)`, `var(--pink)`) and maintain the "cyber" aesthetic (monospaced fonts, glowing borders, dark backgrounds).
