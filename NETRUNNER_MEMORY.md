# Netrunner — Projekt Hukommelse & Roadmap

> Dette dokument fungerer som "hukommelse" for AI-agenter der arbejder på Netrunner.
> Sidst opdateret: 2026-06-20

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
| **Social Engineering** | ✅ Fuldt | Phishing templates, pretexting scenarios, campaign tracking |
| **WiFi Angreb** | ✅ Fuldt | Deauth, evil twin, WPA handshake capture, aircrack-ng cracking |
| **Lateral Movement** | ✅ Fuldt | SSH tunnels, SOCKS proxy, pivot chains, local/remote forwarding |
| **Privilege Escalation** | ✅ Fuldt | SUID exploits, sudo misconfigs, docker escape, capabilities detection |
| **Exfiltration** | ✅ Fuldt | DNS, ICMP, HTTP covert channels + detection |

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
| **Ægte IDS/IPS** | ✅ Fuldt | Scapy packet analysis (ARP spoof, port scan, DNS tunnel, DDoS) |
| **Node Isolation** | ✅ Fuldt | Real iptables via SSH med verificering og release |
| **SOAR Actions** | ✅ Fuldt | block_ip, isolate_node udføres rent faktisk mod infrastrukturen |
| **Log Aggregation** | ✅ Fuldt | Centraliseret log fra alle nodes (journalctl, syslog, auth, dmesg) |
| **Forensics UI** | ✅ Fuldt | Volatility3 integration, memory dump, disk analysis, timeline |
| **Compliance Framework** | ✅ Fuldt | CIS Benchmark & NIST 800-53 scanning (32 checks) |
| **Incident Response** | ✅ Fuldt | Struktureret IR-workflow med phases, evidence, playbooks |

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
| WiFi Attacks (Deauth/Evil Twin/WPA Crack) | ✅ Fuldt |
| Forensics Lab (Volatility3/Disk Analysis) | ✅ Fuldt |
| Compliance Scanner (CIS/NIST) | ✅ Fuldt |
| Lateral Movement (SSH Tunnels/SOCKS/Pivots) | ✅ Fuldt |
| Log Aggregation (Centralized) | ✅ Fuldt |
| Social Engineering Toolkit | ✅ Fuldt |
| Privilege Escalation Scanner | ✅ Fuldt |
| Incident Response Workflow | ✅ Fuldt |
| Exfiltration (DNS/ICMP/HTTP) | ✅ Fuldt |

---

## 🗺️ Roadmap — Status

### Fase 1 (Kritisk — gør systemet brugbart) ✅ KOMPLET

| # | Feature | Status | Implementeret |
|---|---------|--------|---------------|
| 1 | **Ægte IDS** (scapy packet analysis) | ✅ | `backend/services/ids_engine.py` |
| 2 | **Node isolation virkelig** (iptables via SSH) | ✅ | `backend/core/defense.py` |
| 3 | **WiFi angreb** (deauth, evil twin, WPA cracking) | ✅ | `backend/core/wifi_attack.py` |
| 4 | **SOAR actions udføres** (block_ip, isolate_node) | ✅ | `backend/services/soar_playbooks.py` |

### Fase 2 (Vigtigt — gør systemet enterprise) ✅ KOMPLET

| # | Feature | Status | Implementeret |
|---|---------|--------|---------------|
| 5 | **Forensics UI** (Volatility3 + timeline) | ✅ | `backend/core/forensics.py` + `ForensicsView.vue` |
| 6 | **Compliance scanning** (CIS/NIST 32 checks) | ✅ | `backend/core/compliance.py` + `ComplianceView.vue` |
| 7 | **Lateral movement UI** (SSH tunnels, SOCKS, pivots) | ✅ | `backend/core/lateral_movement.py` + `LateralMovementView.vue` |
| 8 | **Log aggregation** (centraliseret fra alle nodes) | ✅ | `backend/core/log_aggregation.py` + `LogAggregationView.vue` |

### Fase 3 (Nice-to-have) ✅ KOMPLET

| # | Feature | Status | Implementeret |
|---|---------|--------|---------------|
| 9 | **Social engineering** (phishing, pretexting) | ✅ | `backend/core/social_engineering.py` + `SocialEngineeringView.vue` |
| 10 | **Privilege escalation scanning** | ✅ | `backend/core/privesc.py` + `PrivescView.vue` |
| 11 | **Incident Response workflow** | ✅ | `backend/core/incident_response.py` + `IncidentResponseView.vue` |

### Fase 4 ✅ KOMPLET

| # | Feature | Status | Implementeret |
|---|---------|--------|---------------|
| 12 | **Exfiltration** (DNS/ICMP/HTTP covert channels) | ✅ | `backend/core/exfiltration.py` + `ExfiltrationView.vue` |
| 13 | **UI/UX polish** (Red/Blue Team navigation) | ✅ | `frontend/src/App.vue` |

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
- Tests fejler pga. log-fil rettighedsfejl (`data/logs/netrunner.log`)
- Backend kører som root i Docker containeren
- WiFi angreb kræver monitor mode interface (ikke tilgængeligt i Docker)
- Volatility3 skal installeres på målknoder for memory forensics

---

## 📁 Viktige Filer at Kende

| Formål | Fil |
|--------|-----|
| WiFi sikkerhedsgeneratorer | `backend/generators/wifi_security.py` |
| WiFi angreb | `backend/core/wifi_attack.py` |
| PMF generator | `backend/generators/network.py` (gen_pmf) |
| Network generatorer | `backend/generators/network.py` |
| Preview router | `backend/routers/preview.py` |
| ConfigPanel (frontend) | `frontend/src/components/ConfigPanel.vue` |
| Kismet integration | `backend/routers/kismet.py` + `backend/core/kismet.py` |
| IDS engine (scapy) | `backend/services/ids_engine.py` |
| Node isolation (iptables) | `backend/core/defense.py` |
| SOAR playbooks | `backend/routers/playbooks.py` + `backend/services/soar_playbooks.py` |
| Forensics (Volatility3) | `backend/core/forensics.py` |
| Compliance scanning | `backend/core/compliance.py` |
| Lateral movement | `backend/core/lateral_movement.py` |
| Log aggregation | `backend/core/log_aggregation.py` |
| Social engineering | `backend/core/social_engineering.py` |
| Privilege escalation | `backend/core/privesc.py` |
| Incident response | `backend/core/incident_response.py` |
| Exfiltration | `backend/core/exfiltration.py` |
| App.vue (Ctrl+K) | `frontend/src/App.vue` |
| Router definitions | `frontend/src/router/index.ts` |
