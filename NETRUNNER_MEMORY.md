# Netrunner — Projekt Hukommelse & Roadmap

> Dette dokument fungerer som "hukommelse" for AI-agenter der arbejder på Netrunner.
> Sidst opdateret: 2026-06-21

---

## 🎯 Formål
Netrunner er et enterprise-level C2 / SIEM / XDR system med Cyberpunk/Matrix/Neon-tema.

## 🏗️ Stakken
- **Backend:** Python + FastAPI + SQLAlchemy + SQLite (via Alembic)
- **Frontend:** Vue.js 3 (Composition API) + TypeScript + Vite + Chart.js
- **Deployment:** Docker Compose (netrunner-platform, postgres, redis, influxdb, mux)
- **API Client:** Custom `req()` wrapper + generiske `api.get()`/`api.post()` til nye views

## 📂 Nøglemapper
- `backend/main.py` — FastAPI indgangspunkt, lifespan, baggrunds-tasks
- `backend/core/db.py` — ORM modeller + async CRUD
- `backend/routers/` — API endpoints (62+ filer)
- `backend/services/` — Baggrundstjenester (IDS, Vuln Scanner, Threat Intel, SOAR)
- `backend/core/` — Kerne-moduler (34+ filer)
- `backend/generators/` — Shell-kommando generators (network, firewall, linux, windows, rpi, docker, wifi_security)
- `frontend/src/views/` — Vue Views (18 routede sider)
- `frontend/src/components/` — Vue Components (47 komponenter)

## 🛠️ Ofte Brugte Kommandoer
- **Build Frontend:** `cd frontend && npm run build`
- **Deploy til Container:** Se deployment-sektion nedenfor
- **Kør Backend Tests:** `pytest backend/tests/`
- **Generer API Client:** `PYTHONPATH=. .venv/bin/python3 -c "import json; from backend.main import app; print(json.dumps(app.openapi()))" > backend/openapi.json && cd frontend && npx @hey-api/openapi-ts -i ../backend/openapi.json -o src/api_client -c @hey-api/client-fetch`

---

## ⚠️ KRITISK: Deployment-procedure

### Backend-filer (IKKE monteret som volume!)
Containeren `netrunner-platform` har **IKKE** backend-koderne monteret som volume. Kun frontend `dist/` og data-mapperne er tilgængelige.
Når backend-filer ændres, skal de **kopieres ind i containeren**:

```bash
# Kopier alle nye backend-filer
docker cp backend/routers/<fil>.py netrunner-platform:/app/backend/routers/<fil>.py
docker cp backend/core/<fil>.py netrunner-platform:/app/backend/core/<fil>.py
docker cp backend/services/<fil>.py netrunner-platform:/app/backend/services/<fil>.py
docker cp backend/main.py netrunner-platform:/app/backend/main.py
docker restart netrunner-platform
```

### Containerens mounts:
```
/ -> /host
/home/aso/Dokumenter/github/netrunner/data -> /app/data
/home/aso/.config/GNS3/2.2 -> /root/.config/GNS3/2.2
/home/aso/.ssh -> /root/.ssh
/var/run/docker.sock -> /var/run/docker.sock
/etc/wireguard -> /etc/wireguard
/dev -> /dev
/run/udev -> /run/udev
/var/run/dbus/system_bus_socket -> /var/run/dbus/system_bus_socket
```

### Frontend-deployment:
```bash
cd frontend && npm run build
docker exec netrunner-platform rm -rf /app/frontend/dist
docker cp frontend/dist/. netrunner-platform:/app/frontend/dist/
docker restart netrunner-platform
```

### Log-fil problem:
`data/logs/netrunner.log` ejes af root. Slet og genopret med `chmod 666` før backend kan logge.

---

## 🔐 Nuværende Sikkerhedsfeatures

### Implementeret (Fuldt)
| Feature | Backend | Frontend |
|---------|---------|----------|
| PMF (802.11w) | `gen_pmf()` i `network.py` | ConfigPanel form |
| WPA3-SAE | `gen_wpa3_sae()` i `wifi_security.py` | ConfigPanel form |
| OWE (Open Encryption) | `gen_owe()` i `wifi_security.py` | ConfigPanel form |
| 802.1X / EAP-TLS | `gen_eaptls()` i `wifi_security.py` | ConfigPanel form |
| WiFi Angreb | `wifi_attack.py` | `WifiAttackView.vue` |
| Forensics Lab | `forensics.py` | `ForensicsView.vue` |
| Compliance Scanner | `compliance.py` | `ComplianceView.vue` |
| Lateral Movement | `lateral_movement.py` | `LateralMovementView.vue` |
| Log Aggregation | `log_aggregation.py` | `LogAggregationView.vue` |
| Social Engineering | `social_engineering.py` | `SocialEngineeringView.vue` |
| Privilege Escalation | `privesc.py` | `PrivescView.vue` |
| Incident Response | `incident_response.py` | `IncidentResponseView.vue` |
| Exfiltration | `exfiltration.py` | `ExfiltrationView.vue` |
| IDS/IPS (scapy) | `ids_engine.py` | Alerts/Events |
| Node Isolation (iptables) | `defense.py` | HostControl |
| SOAR Actions | `soar_playbooks.py` | Playbooks |

---

## 📊 Komplet Kapabilitets-audit

### Red Team (Offensive)

| Kapabilitet | Status | Detaljer |
|-------------|--------|----------|
| Network Scanning (Nmap) | ✅ | Remote/local, XML parsing, quick/comprehensive/vuln profiles |
| Credential Brute Force | ✅ | SSH/FTP/MySQL/PostgreSQL/RDP, wordlist + algorithmic |
| Red Team Payloads | ✅ | Scapy DNS spoofing, Impacket SMB relay, Volatility, YARA |
| MITRE ATT&CK Mapping | ✅ | Live matrix med real-time detection tracking |
| Chaos Engineering | ✅ | Scapy/YARA/Shodan, manual attack injection |
| Traffic Shaping (tc netem) | ✅ | Latency, jitter, packet loss |
| Honeypots | ✅ | "Project Mirage" (custom SSH) + Cowrie (Docker) |
| WiFi CSI Surveillance | ✅ | ESP32/RPi beacons, Nexmon, motion/breathing/heart rate |
| Bluetooth Attacks | ✅ | BLE scan, GATT, pairing, L2Ping flood |
| MCU/IoT Exploitation | ✅ | Serial, firmware flash, code deployment |
| USB/Serial Exploitation | ✅ | Device detection, serial write, port nuke |
| Reconnaissance | ✅ | Nmap + host import til topology |
| C2 (Command & Control) | ✅ | SSH/Telnet sessions, Go agent, real-time exec |
| Social Engineering | ✅ | Phishing templates, pretexting scenarios, campaign tracking |
| WiFi Angreb | ✅ | Deauth, evil twin, WPA handshake capture, aircrack-ng cracking |
| Lateral Movement | ✅ | SSH tunnels, SOCKS proxy, pivot chains, local/remote forwarding |
| Privilege Escalation | ✅ | SUID exploits, sudo misconfigs, docker escape, capabilities |
| Exfiltration | ✅ | DNS, ICMP, HTTP covert channels + detection |

### Blue Team (Defensiv)

| Kapabilitet | Status | Detaljer |
|-------------|--------|----------|
| SIEM Alert Management | ✅ | CRUD med severity/status/assignee workflow |
| Threat Hunting | ✅ | Regex-søgning på tværs af alerts og audit logs |
| Audit Logging (Compliance) | ✅ | Alle kritiske ændringer logges |
| Executive Dashboard (CISO) | ✅ | Metrics, threat trends, mitigation rates |
| Security Reports | ✅ | Markdown → PDF/DOCX/TEX via Pandoc |
| Reachability Monitoring | ✅ | TCP probing med transition alerting |
| Knowledge Graph | ✅ | NetworkX + vis.js + LLM analyse |
| MITRE ATT&CK Inference | ✅ | Regex-baseret technique mapping |
| IDS/IPS (scapy) | ✅ | ARP spoof, port scan, DNS tunnel, DDoS detection |
| Node Isolation | ✅ | Real iptables via SSH + verificering + release |
| SOAR Actions | ✅ | block_ip, isolate_node udføres rent faktisk |
| Log Aggregation | ✅ | Centraliseret fra alle nodes |
| Forensics Lab | ✅ | Volatility3, memory dump, disk analysis, timeline |
| Compliance Framework | ✅ | CIS Benchmark & NIST 800-53 (32 checks) |
| Incident Response | ✅ | Struktureret workflow med phases, evidence, playbooks |

---

## 🗺️ Roadmap — Alle Faser KOMPLET

### Fase 1 (Kritisk) ✅ KOMPLET
1. Ægte IDS (scapy packet analysis) — `backend/services/ids_engine.py`
2. Node isolation (iptables via SSH) — `backend/core/defense.py`
3. WiFi angreb (deauth, evil twin, WPA cracking) — `backend/core/wifi_attack.py`
4. SOAR actions udføres — `backend/services/soar_playbooks.py`

### Fase 2 (Enterprise) ✅ KOMPLET
5. Forensics UI (Volatility3 + timeline) — `backend/core/forensics.py` + `ForensicsView.vue`
6. Compliance scanning (CIS/NIST 32 checks) — `backend/core/compliance.py` + `ComplianceView.vue`
7. Lateral movement UI — `backend/core/lateral_movement.py` + `LateralMovementView.vue`
8. Log aggregation — `backend/core/log_aggregation.py` + `LogAggregationView.vue`

### Fase 3 (Nice-to-have) ✅ KOMPLET
9. Social engineering — `backend/core/social_engineering.py` + `SocialEngineeringView.vue`
10. Privilege escalation scanning — `backend/core/privesc.py` + `PrivescView.vue`
11. Incident Response workflow — `backend/core/incident_response.py` + `IncidentResponseView.vue`

### Fase 4 ✅ KOMPLET
12. Exfiltration (DNS/ICMP/HTTP) — `backend/core/exfiltration.py` + `ExfiltrationView.vue`
13. UI/UX polish (Red/Blue Team navigation) — `frontend/src/App.vue`
14. WiFi Attack view — `frontend/src/views/WifiAttackView.vue`

---

## 🐛 Kendte Issues & Løsninger

### Løst i denne session (2026-06-21)
1. **Frontend hvid skærm** — Assets blev ikke korrekt kopieret til containeren. Løsning: `docker exec rm -rf /app/frontend/dist` før `docker cp`.
2. **Alle nye views viste ikke data** — `api.get()`/`api.post()` manglede i API clienten. Alle views brugte axios-style kald. Løsning: Tilføjet generiske `get`/`post` metoder til `api` objektet.
3. **Node-select var tomme i alle Red/Blue Team views** — Backend `/nodes` returnerer dict `{ "id": {...} }`, men views forventede `{ nodes: [...] }`. Løsning: `Object.values(nodesRes.data || {})` i alle 6 views.
4. **LogAggregationView kunne ikke søge** — Manglende params-understøttelse i `api.get()`. Løsning: Tilføjet `config.params` håndtering i get-metoden.
5. **WiFi Attacks manglede view** — Ingen `WifiAttackView.vue` eller route. Løsning: Oprettet komplet view med 7 tabs + tilføjet route.
6. **WiFi Attack backend ikke i containeren** — Alle nye backend-moduler manglede i containeren. Løsning: Kopieret alle 9 nye router- og core-filer.
7. **WiFi Scan returnerede intet** — Scan-endpunktet brugte query params, frontend sendte JSON body. Løsning: Oprettet `ScanRequest` Pydantic model til scan-endpointet.
8. **`[object Object]` i fejlbeskeder** — `new Error(data.detail)` når `detail` er array/object fra FastAPI. Løsning: `JSON.stringify()` i req-funktionen.
9. **SOAR Playbooks POST 500** — `created_at` manglede i playbook doc ved oprettelse. Rettet i `backend/routers/playbooks.py`.
10. **Privesc Scanner fejlede altid** — `privesc.py` brugte `get_credential()` som ikke eksisterer. Skal være `load_credentials()`. Rettet i `backend/routers/privesc.py`.
11. **PrivescView scroll-problemer** — Viewet kunne ikke scrolle. Tilføjet `max-height` og `overflow-y: auto` til main container og results section.

### Kendte issues (stående)
- WiFi angreb kræver monitor mode interface (ikke tilgængeligt i Docker)
- Volatility3 skal installeres på målknoder for memory forensics
- `data/logs/netrunner.log` ejes af root — slet og genopret med `chmod 666`
- Frontend build advarsel: chunks > 500 kB (7.7MB) — brug dynamic import/code splitting
- `iw` ikke tilgængeligt i containeren (kun host)
- **Topology/Discovery**: Nodes vises IKKE automatisk. Kræver:
  1. Manuel scanning via **Recon** visning (vælg node → indtast netværk f.eks. `192.168.1.0/24` → scan → import)
  2. LLDP kun opdager direkte tilsluttede naboer, ikke hele netværket
  3. Reachability tjekker kun eksisterende nodes' status

---

## 📁 Viktige Filer at Kende

| Formål | Fil |
|--------|-----|
| WiFi sikkerhedsgeneratorer | `backend/generators/wifi_security.py` |
| WiFi angreb (backend) | `backend/core/wifi_attack.py` |
| WiFi angreb (router) | `backend/routers/wifi_attack.py` |
| WiFi angreb (frontend) | `frontend/src/views/WifiAttackView.vue` |
| Forensics (backend) | `backend/core/forensics.py` |
| Compliance (backend) | `backend/core/compliance.py` |
| Lateral movement (backend) | `backend/core/lateral_movement.py` |
| Log aggregation (backend) | `backend/core/log_aggregation.py` |
| Social engineering (backend) | `backend/core/social_engineering.py` |
| Privilege escalation (backend) | `backend/core/privesc.py` |
| Incident response (backend) | `backend/core/incident_response.py` |
| Exfiltration (backend) | `backend/core/exfiltration.py` |
| IDS engine (scapy) | `backend/services/ids_engine.py` |
| Node isolation (iptables) | `backend/core/defense.py` |
| SOAR playbooks | `backend/services/soar_playbooks.py` |
| API client | `frontend/src/api/client.ts` |
| Router definitions | `frontend/src/router/index.ts` |
| App navigation | `frontend/src/App.vue` |
| ConfigPanel (frontend) | `frontend/src/components/ConfigPanel.vue` |
| Kismet integration | `backend/routers/kismet.py` + `backend/core/kismet.py` |
| Preview router | `backend/routers/preview.py` |
| PMF generator | `backend/generators/network.py` (gen_pmf) |

---

## 🏗️ Implementerings Mønstre

### Ny Backend Router + Core Module
1. Opret `backend/core/<name>.py` med forretningslogik
2. Opret `backend/routers/<name>.py` med FastAPI router + Pydantic modeller
3. Import + registrer i `backend/main.py`: `from .routers import <name>` + `app.include_router(<name>.router, prefix="/api", dependencies=AUTH)`
4. Kopier til container: `docker cp backend/routers/<name>.py netrunner-platform:/app/backend/routers/` + `docker cp backend/core/<name>.py netrunner-platform:/app/backend/core/`
5. Genstart: `docker restart netrunner-platform`

### Ny Frontend View
1. Opret `frontend/src/views/<Name>View.vue`
2. Tilføj import + route i `frontend/src/router/index.ts`
3. Tilføj navigation-knap i `frontend/src/App.vue` sidebar (under RED TEAM eller BLUE TEAM gruppe)
4. Brug `import { api } from '../api/client'` og `api.get()`/`api.post()` til API-kald
5. Tilføj node-dropdown med `Object.values(nodesRes.data || {})` (ikke `.nodes`!)
6. Build + deploy: `cd frontend && npm run build` + deploy-procedure

### API Client Mønster
```typescript
// Nye views bruger api.get() og api.post() som wrapper
const res = await api.get('/endpoint')       // returns { data: ... }
const res = await api.post('/endpoint', body) // returns { data: ... }

// Eksisterende views bruger navngivne metoder
const nodes = await api.listNodes()  // returns Record<string, NrNode>
```

### Node-Response Format
Backend `/nodes` returnerer: `{ "nodeId": { id, name, host, ... } }` (dict)
Frontend forventede: `{ nodes: [...] }` (array)
**Løsning:** `nodes.value = Object.values(res.data || {})`
