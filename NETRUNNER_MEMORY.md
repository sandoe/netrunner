# Netrunner — Projekt Hukommelse & Roadmap

> Dette dokument fungerer som "hukommelse" for AI-agenter der arbejder på Netrunner.
> Sidst opdateret: 2026-06-19

---

## 🎯 Formål
Netrunner er et enterprise-level C2 / SIEM / XDR system med Cyberpunk/Matrix/Neon-tema.

## 🏗️ Stakken
- **Backend:** Python + FastAPI + SQLAlchemy + SQLite (via Alembic)
- **Frontend:** Vue.js 3 (Composition API) + TypeScript + Vite + Chart.js
- **Deployment:** Docker Compose (netrunner-platform, postgres, redis, influxdb, mux)
- **API Client:** OpenAPI-TS (genererer TS SDK fra FastAPI)

## 📂 Nøglemapper
- `backend/main.py` — FastAPI indgangspunkt, lifespan, baggrunds-tasks
- `backend/core/db.py` — ORM modeller + async CRUD
- `backend/routers/` — API endpoints (53 filer)
- `backend/services/` — Baggrundstjenester (IDS, Vuln Scanner, Threat Intel, SOAR)
- `backend/core/` — Kerne-moduler (25 filer)
- `backend/generators/` — Shell-kommando generators (network, firewall, linux, windows, rpi, docker, wifi_security)
- `frontend/src/views/` — Vue Views (10 routede sider)
- `frontend/src/components/` — Vue Components (47 komponenter)

## 🛠️ Ofte Brugte Kommandoer
- **Generer API Client:** `PYTHONPATH=. .venv/bin/python3 -c "import json; from backend.main import app; print(json.dumps(app.openapi()))" > backend/openapi.json && cd frontend && npx @hey-api/openapi-ts -i ../backend/openapi.json -o src/api_client -c @hey-api/client-fetch`
- **Kør Backend Tests:** `pytest backend/tests/`
- **Alembic Migrationer:** `rm -rf backend/alembic/versions/* && PYTHONPATH=backend .venv/bin/alembic -c backend/alembic.ini revision --autogenerate -m "schema" && PYTHONPATH=backend .venv/bin/alembic -c backend/alembic.ini upgrade head`
- **Build Frontend:** `cd frontend && npm run build`
- **Deploy til Container:** `docker cp frontend/dist/index.html netrunner-platform:/app/frontend/dist/index.html && docker cp frontend/dist/assets netrunner-platform:/app/frontend/dist/assets && docker restart netrunner-platform`

---

## 🔐 Nuværende Sikkerhedsfeatures

### Implementeret (Fuldt)
| Feature | Backend | Frontend | Ctrl+K |
|---------|---------|----------|--------|
| PMF (802.11w) | `gen_pmf()` i `network.py` | ConfigPanel form | ✅ |
| WPA3-SAE | `gen_wpa3_sae()` i `wifi_security.py` | ConfigPanel form | ✅ |
| OWE (Open Encryption) | `gen_owe()` i `wifi_security.py` | ConfigPanel form | ✅ |
| 802.1X / EAP-TLS | `gen_eaptls()` i `wifi_security.py` | ConfigPanel form | ✅ |
| WIPS Rogue AP Detection | `/api/kismet/rogue-aps` i `kismet.py` | Kismet view | ❌ |

### WiFi Sikkerhed — Generator Mønster
- **Filer:** `backend/generators/wifi_security.py`
- **Registration:** `backend/routers/preview.py` — import + elif case
- **Typer:** `wpa3-sae`, `owe`, `eaptls`
- **Hver generator understøtter:** client + ap mode, nmcli + wpa_supplicant + hostapd

---

## 📊 Komplet Kapabilitets-audit

### Red Team (Offensive)

| Kapabilitet | Status | Detaljer |
|-------------|--------|----------|
| Network Scanning (Nmap) | ✅ Fuldt | Remote/local, XML parsing, quick/comprehensive/vuln profiles |
| Credential Brute Force | ✅ Fuldt | SSH/FTP/MySQL/PostgreSQL/RDP, wordlist + algorithmic, pause/resume |
| Red Team Payloads | ✅ Fuldt | Scapy DNS spoofing, Impacket SMB relay, Volatility, YARA, mitmproxy, Shodan |
| MITRE ATT&CK Mapping | ✅ Fuldt | Live matrix med real-time detection tracking |
| Chaos Engineering | ✅ Fuldt | Scapy/YARA/Shodan, manual attack injection (SQLi, XSS, LFI) |
| Traffic Shaping (tc netem) | ✅ Fuldt | Latency, jitter, packet loss |
| Honeypots | ✅ Fuldt | "Project Mirage" (custom SSH) + Cowrie (Docker) |
| WiFi CSI Surveillance | ✅ Fuldt | ESP32/RPi beacons, Nexmon, motion/breathing/heart rate |
| Bluetooth Attacks | ✅ Fuldt | BLE scan, GATT, pairing, L2Ping flood |
| MCU/IoT Exploitation | ✅ Fuldt | Serial, firmware flash, code deployment |
| USB/Serial Exploitation | ✅ Fuldt | Device detection, serial write, port nuke |
| Reconnaissance | ✅ Fuldt | Nmap + host import til topology |
| C2 (Command & Control) | ✅ Fuldt | SSH/Telnet sessions, Go agent, real-time exec |
| **Social Engineering** | ❌ Mangler | Ingen phishing, pretexting, credential harvesting |
| **WiFi Angreb** | ⚠️ Delvist | CSI findes, men mangler: deauth, evil twin, WPA cracking, packet injection |
| **Lateral Movement** | ❌ Mangler | Ingen SSH tunnels, SOCKS proxy, pass-the-hash UI |
| **Privilege Escalation** | ❌ Mangler | Ingen privesc scanning (LinPEAS/WinPEAS) |
| **Exfiltration** | ❌ Mangler | Ingen DNS/ICMP tunneling værktøjer |

### Blue Team (Defensiv)

| Kapabilitet | Status | Detaljer |
|-------------|--------|----------|
| SIEM Alert Management | ✅ Fuldt | CRUD med severity/status/assignee workflow |
| Threat Hunting | ✅ Fuldt | Regex-søgning på tværs af alerts og audit logs |
| Audit Logging (Compliance) | ✅ Fuldt | Alle kritiske ændringer logges |
| Executive Dashboard (CISO) | ✅ Fuldt | Metrics, threat trends, mitigation rates |
| Security Reports | ✅ Fuldt | Markdown → PDF/DOCX/TEX via Pandoc |
| Reachability Monitoring | ✅ Fuldt | TCP probing med transition alerting |
| Knowledge Graph | ✅ Fuldt | NetworkX + vis.js + LLM analyse |
| MITRE ATT&CK Inference | ✅ Fuldt | Regex-baseret technique mapping |
| Threat Intel Feed | ⚠️ Delvist | AlienVault OTX API + mock data, DB cross-referencing virker |
| SOAR Playbooks | ⚠️ Delvist | UI + condition evaluation virker, men actions er log-only |
| **Ægte IDS/IPS** | ⚠️ Stub | `ids_engine.py` genererer tilfældige alerts — ingen rigtig pakkeanalyse |
| **Node Isolation** | ⚠️ Simuleret | `defense.py` returnerer strings — udfører ikke iptables |
| **SOAR Actions** | ⚠️ Log-only | block_ip, isolate_node logges men udføres ikke |
| **Log Aggregation** | ⚠️ Delvist | SSH journalctl tailing, men ikke centraliseret på tværs af nodes |
| **Forensics UI** | ❌ Mangler | Volatility-script findes men ingen UI |
| **Compliance Framework** | ❌ Mangler | Ingen CIS/NIST/ISO 27001 scanning |
| **Incident Response** | ⚠️ Delvist | Isolation + playbooks findes, men ingen struktureret IR-workflow |

### Shared / Infrastructure

| Kapabilitet | Status |
|-------------|--------|
| Node Management | ✅ Fuldt |
| Network Topology (Cytoscape.js) | ✅ Fuldt |
| GNS3 Integration | ✅ Fuldt |
| VPN (WireGuard) | ✅ Fuldt |
| Kubernetes (K3s) | ✅ Fuldt |
| Docker Management | ✅ Fuldt |
| SDN (Network Config + Hotspot) | ✅ Fuldt |
| SSH/Telnet Terminal (xterm.js) | ✅ Fuldt |
| AI Assistant (LLM + tool-calling) | ✅ Fuldt |
| MCP Server | ✅ Fuldt |
| Deep Packet Inspection | ✅ Fuldt |
| Real-Time Telemetry | ✅ Fuldt |
| Credential Vault (Fernet) | ✅ Fuldt |
| JWT Authentication | ✅ Fuldt |
| API Rate Limiting | ✅ Fuldt |
| MCU/IoT IDE | ✅ Fuldt |
| USB/Serial Management | ✅ Fuldt |
| WiFi Security Config (PMF/WPA3/OWE/EAP-TLS) | ✅ Fuldt |

---

## 🗺️ Roadmap — Manglende Features

### Fase 1 (Kritisk — gør systemet brugbart)

| # | Feature | Team | Kompleksitet | Estimat |
|---|---------|------|:---:|---------|
| 1 | **Ægte IDS** (Suricata/Snort integration) | Blue | Høj | 3-5 dage |
| 2 | **Node isolation virkelig** (iptables udføres faktisk) | Blue | Medium | 1-2 dage |
| 3 | **WiFi angreb** (deauth, evil twin, WPA cracking) | Red | Høj | 3-5 dage |
| 4 | **SOAR actions udføres** (block_ip, isolate_node virker) | Blue | Medium | 1-2 dage |

### Fase 2 (Vigtigt — gør systemet enterprise)

| # | Feature | Team | Kompleksitet | Estimat |
|---|---------|------|:---:|---------|
| 5 | **Forensics UI** (Volatility + timeline analysis) | Blue | Høj | 5-7 dage |
| 6 | **Compliance scanning** (CIS Benchmarks, NIST) | Blue | Medium | 3-5 dage |
| 7 | **Lateral movement UI** (SSH tunnels, SOCKS proxy, pivoting) | Red | Medium | 2-3 dage |
| 8 | **Log aggregation** (Loki/ELK connector, centraliseret søgning) | Blue | Høj | 5-7 dage |

### Fase 3 (Nice-to-have)

| # | Feature | Team | Kompleksitet | Estimat |
|---|---------|------|:---:|---------|
| 9 | Social engineering værktøjer (phishing, pretexting) | Red | Medium | 3-5 dage |
| 10 | Privilege escalation scanning (LinPEAS/WinPEAS) | Red | Medium | 2-3 dage |
| 11 | Incident Response workflow (evidence chain, containment→eradication) | Blue | Høj | 5-7 dage |

---

## 🏗️ Implementerings Mønstre

### Ny Generator (Backend)
1. Opret `backend/generators/<name>.py` med funktioner der returnerer `list[str]`
2. Import i `backend/routers/preview.py`
3. Registrer som `elif t == "<type>": cmds = gen_<func>(cfg)`
4. Test: `PYTHONPATH=. .venv/bin/python3 -c "from backend.generators.<name> import <func>; print(<func>({}))"`

### Ny Form (Frontend ConfigPanel)
1. Tilføj `{ type: '<type>', label: 'Label' }` i CONFIG_CATEGORIES
2. Opret `default<Type>Form()` factory
3. Opret `ref(default<Type>Form())`
4. Opret `sync<Type>Form()` funktion
5. Registrer i `syncFnMap`, `defaultsMap`, `formRefsMap`
6. Tilføj watcher
7. Tilføj HTML template (`v-if="activeType === '<type>'"`)
8. Tilføj interface click handler
9. Byg: `cd frontend && npm run build`
10. Deploy: `docker cp ... netrunner-platform:/app/frontend/dist/ && docker restart netrunner-platform`

### Ctrl+K Genvej (App.vue)
```javascript
cmds.push({ id: '<id>', label: 'Label', icon: '🔧', run: () => {
  if (store.selected?.id) {
    viewMode.value = 'node' as any
    activeTab.value = 'system' as any
    nextTick(() => window.dispatchEvent(new CustomEvent('open-config-type', { detail: '<type>' })))
  } else { flash('Select a node first', 'err') }
} })
```

### Docker Deployment
Frontenden serveres fra containeren (`netrunner-platform`), ikke fra værten.
Efter `npm run build` skal filerne kopieres ind i containeren:
```bash
docker cp frontend/dist/index.html netrunner-platform:/app/frontend/dist/index.html
docker cp frontend/dist/assets netrunner-platform:/app/frontend/dist/assets
docker restart netrunner-platform
```

---

## 🐛 Kendte Issues
- `ids_engine.py` er en stub — genererer tilfældige alerts, ikke rigtig pakkeanalyse
- `defense.py` node isolation returnerer log-strings, udfører ikke iptables
- SOAR playbook actions er log-only, udføres ikke mod infrastrukturen
- Tests fejler pga. log-fil rettighedsfejl (`data/logs/netrunner.log`)
- Backend kører som root i Docker containeren

---

## 📁 Viktige Filer at Kende

| Formål | Fil |
|--------|-----|
| WiFi sikkerhedsgeneratorer | `backend/generators/wifi_security.py` |
| PMF generator | `backend/generators/network.py` (gen_pmf) |
| Network generatorer | `backend/generators/network.py` |
| Preview router | `backend/routers/preview.py` |
| ConfigPanel (frontend) | `frontend/src/components/ConfigPanel.vue` |
| Kismet integration | `backend/routers/kismet.py` + `backend/core/kismet.py` |
| IDS engine (stub) | `backend/services/ids_engine.py` |
| Node isolation (simuleret) | `backend/core/defense.py` |
| SOAR playbooks | `backend/routers/playbooks.py` + `backend/services/soar_playbooks.py` |
| App.vue (Ctrl+K) | `frontend/src/App.vue` |
| Router definitions | `frontend/src/router/index.ts` |
