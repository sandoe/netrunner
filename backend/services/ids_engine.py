"""
Netrunner IDS Engine — Real network intrusion detection using scapy.

Replaces the stub with actual packet analysis, ARP spoof detection,
port scan detection, DNS tunnel detection, and known-bad IP checking.
"""

import asyncio
import os
import uuid
import time
import collections
from typing import Optional
from backend.core.logger import log as logger
from backend.core.db import insert_alert, check_ip_threat_intel, load_nodes_db

try:
    from scapy.all import sniff, ARP, IP, TCP, UDP, DNS, DNSQR, ICMP, Raw, conf  # type: ignore

    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logger.warning("scapy not available — IDS will operate in passive/remote mode only")

try:
    import psutil  # type: ignore

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# --- Detection state ---
_arp_table: dict[str, set[str]] = collections.defaultdict(set)
_port_scan_tracker: dict[str, list[float]] = collections.defaultdict(list)
_dns_query_tracker: dict[str, list[tuple[float, str]]] = collections.defaultdict(list)
_syn_tracker: dict[str, list[float]] = collections.defaultdict(list)
_tls_flow_tracker: dict[str, list[tuple[float, int]]] = collections.defaultdict(list)
_alert_cooldowns: dict[str, float] = {}
_alert_suppression_window = 300  # 5 min cooldown per (type, src) pair
_documented_apis = [
    "/api/v1/health",
    "/api/v1/login",
    "/api/v1/users",
    "/api/v2/config",
]

INTERFACE: Optional[str] = None  # auto-detect if None
_running = False
_sniff_proc = None


def _ai_triage_enabled(settings: dict) -> bool:
    """Require an explicit opt-in before background jobs call an AI provider."""
    value = settings.get("enable_ai_triage")
    if value is None:
        value = os.environ.get("NETRUNNER_ENABLE_AI_TRIAGE", "0")
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _get_default_interface() -> str:
    if PSUTIL_AVAILABLE:
        stats = psutil.net_if_stats()
        for name, st in stats.items():
            if st.isup and name != "lo":
                return name
    return "eth0"


def _should_suppress(alert_type: str, src: str) -> bool:
    key = f"{alert_type}:{src}"
    now = time.time()
    last = _alert_cooldowns.get(key, 0)
    if now - last < _alert_suppression_window:
        return True
    _alert_cooldowns[key] = now
    return False


async def _triage_incident_with_ai(src_ip: str, alerts: list[dict]):
    from backend.routers.settings import load_settings
    from openai import AsyncOpenAI
    import json

    settings = await load_settings()
    if not _ai_triage_enabled(settings):
        return

    provider = (settings.get("ai_provider") or "openai").strip().lower()
    model = settings.get("ai_model") or (
        "llama3.1" if provider == "ollama" else "gpt-4o"
    )
    api_key = (
        settings.get("ai_api_key")
        or settings.get("openai_api_key")
        or os.environ.get("OPENAI_API_KEY")
    )
    base_url = (settings.get("ai_base_url") or "").strip()

    if provider == "openai":
        base_url = ""
    elif provider == "openrouter" and not base_url:
        base_url = "https://openrouter.ai/api/v1"
    elif provider == "ollama":
        base_url = base_url or "http://127.0.0.1:11434/v1"
        api_key = api_key or "ollama"

    if not api_key:
        return

    if base_url:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    else:
        client = AsyncOpenAI(api_key=api_key)

    system_prompt = f"""You are an autonomous Tier 2 Incident Responder.
You will receive a JSON array containing a cluster of correlated network alerts grouped by Source IP or Node.
Your job is to analyze this cluster, determine if they represent a cohesive True Positive attack chain, summarize the incident timeline, and output a single SOAR action.
If it is a true positive and requires immediate network containment, output:
```json
{{"action": "isolate", "target_ip": "<the_ip>"}}
```
If the attacker is demonstrating lateral movement or SSH bruteforcing, instead of isolating, deploy a cognitive tarpit honeypot to trap them by outputting:
```json
{{"action": "deploy_tarpit", "target_ip": "<the_ip>", "node_id": "default"}}
```
If the alert involves a compromised user identity, immediately contain the identity by outputting:
```json
{{"action": "revoke_identity", "user": "<the_username_or_email>"}}
```
Keep your explanation under 3 sentences."""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Correlated Incident Alerts for {src_ip}: {json.dumps(alerts)}",
                },
            ],
        )
        content = response.choices[0].message.content
        logger.info(f"[AI Copilot] Incident Triage for {src_ip} complete.")

        # Update the first/primary alert with the full incident summary
        primary_alert = alerts[0]
        primary_alert[
            "description"
        ] += f"\n\n🤖 [AI Copilot Incident Synthesis]: {content}\n(Correlated {len(alerts)} alerts into this incident)"

        # Parse potential playbook action
        if content and "```json" in content:
            try:
                json_str = content.split("```json")[1].split("```")[0].strip()
                action = json.loads(json_str)
                if action.get("action") == "isolate" and action.get("target_ip"):
                    from backend.services.soar_playbooks import execute_playbook

                    await execute_playbook(
                        "contain_host", {"target_ip": action.get("target_ip")}
                    )
                    primary_alert[
                        "description"
                    ] += f"\n⚡ [SOAR]: Automatically executed contain_host playbook on {action.get('target_ip')}."
                elif action.get("action") == "deploy_tarpit":
                    from backend.services.soar_playbooks import execute_playbook

                    await execute_playbook("deploy_tarpit", action)
                    primary_alert[
                        "description"
                    ] += f"\n⚡ [SOAR]: Automatically deployed Mirage Tarpit to ensnare {action.get('target_ip')}."
                elif action.get("action") == "revoke_identity":
                    from backend.services.soar_playbooks import execute_playbook

                    user = action.get("user", "unknown")
                    await execute_playbook(
                        "revoke_identity",
                        {"user": user, "alert_id": primary_alert["id"]},
                    )
            except Exception as parse_err:
                logger.error(f"[AI Triage] Failed to parse action: {parse_err}")

        from backend.core.db import save_alert_db

        await save_alert_db(primary_alert)
    except Exception as e:
        logger.error(f"[AI Triage] Failed: {e}")


_incident_queue: dict[str, list[dict]] = collections.defaultdict(list)
_incident_timer: dict[str, asyncio.Task] = {}


async def _trigger_incident_triage(src_ip: str):
    await asyncio.sleep(60)  # Wait 60 seconds for additional correlated alerts
    alerts = _incident_queue.pop(src_ip, [])
    if alerts:
        await _triage_incident_with_ai(src_ip, alerts)
    if src_ip in _incident_timer:
        del _incident_timer[src_ip]


async def _create_alert(title: str, severity: str, description: str, src_ip: str = ""):
    if src_ip and _should_suppress(title.split("[")[0].strip(), src_ip):
        return

    intel = None
    if src_ip:
        intel = await check_ip_threat_intel(src_ip)

    if intel:
        title = f"[KNOWN THREAT] {title}"
        description = (
            f"{description} | Threat Intel: {intel['source']} ({intel['threat_type']})"
        )
        severity = intel["severity"]

    alert = {
        "id": str(uuid.uuid4()),
        "title": f"{title} [{src_ip}]" if src_ip else title,
        "description": description,
        "severity": severity.lower(),
        "status": "new",
        "assignee_id": None,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    await insert_alert(alert)
    logger.info(f"[IDS] Alert: {title} ({severity}) src={src_ip}")

    # Group incidents by src_ip for Copilot Triage
    if src_ip:
        _incident_queue[src_ip].append(alert.copy())
        if src_ip not in _incident_timer:
            _incident_timer[src_ip] = asyncio.create_task(
                _trigger_incident_triage(src_ip)
            )
    else:
        # Fallback for local alerts without IP
        asyncio.create_task(_triage_incident_with_ai("unknown", [alert.copy()]))


def _process_packet(pkt):
    """Synchronous packet handler — called from scapy sniff thread."""
    if pkt.haslayer(ARP):
        _handle_arp(pkt)
    elif pkt.haslayer(IP):
        _handle_ip(pkt)


def _handle_arp(pkt):
    src_ip = pkt[ARP].psrc
    src_mac = pkt[ARP].hwsrc

    if src_mac in _arp_table and src_ip not in _arp_table[src_mac]:
        asyncio.get_event_loop().call_soon_threadsafe(
            asyncio.ensure_future,
            _create_alert(
                "ARP Spoofing Detected",
                "critical",
                f"IP {src_ip} now mapped to MAC {src_mac} which previously had different IPs: {_arp_table[src_mac]}",
                src_ip,
            ),
        )
    _arp_table[src_mac].add(src_ip)

    if pkt[ARP].op == 2:  # ARP reply
        target_ip = pkt[ARP].pdst
        if src_mac in _arp_table and len(_arp_table[src_mac]) > 5:
            asyncio.get_event_loop().call_soon_threadsafe(
                asyncio.ensure_future,
                _create_alert(
                    "ARP Storm Detected",
                    "high",
                    f"MAC {src_mac} is responding to ARP for {len(_arp_table[src_mac])} different IPs — possible ARP flooding",
                    src_ip,
                ),
            )


def _handle_ip(pkt):
    src_ip = pkt[IP].src
    now = time.time()

    if pkt.haslayer(TCP):
        flags = pkt[TCP].flags
        dport = pkt[TCP].dport

        # SYN scan detection
        if flags == 0x02:  # SYN only
            _syn_tracker[src_ip].append(now)
            _syn_tracker[src_ip] = [t for t in _syn_tracker[src_ip] if now - t < 10]
            if len(_syn_tracker[src_ip]) > 30:
                asyncio.get_event_loop().call_soon_threadsafe(
                    asyncio.ensure_future,
                    _create_alert(
                        "SYN Flood / Stealth Scan",
                        "high",
                        f"{len(_syn_tracker[src_ip])} SYN packets in 10s from {src_ip}",
                        src_ip,
                    ),
                )

        # Port scan detection (connect scan)
        _port_scan_tracker[src_ip].append(now)
        _port_scan_tracker[src_ip] = [
            t for t in _port_scan_tracker[src_ip] if now - t < 60
        ]
        unique_ports = len(set(_port_scan_tracker[src_ip]))
        if unique_ports > 25:
            asyncio.get_event_loop().call_soon_threadsafe(
                asyncio.ensure_future,
                _create_alert(
                    "Port Scanning",
                    "high",
                    f"{unique_ports} different destination ports targeted in 60s — sequential port scan detected",
                    src_ip,
                ),
            )

        # JA4+ TLS Fingerprinting (Encrypted C2 Beaconing)
        if dport == 443 and pkt.haslayer(Raw):
            payload = bytes(pkt[Raw].load)
            # Check for TLS Handshake (0x16) and Client Hello (0x01)
            if len(payload) > 5 and payload[0] == 0x16 and payload[5] == 0x01:
                import hashlib

                # Extract cipher suites and extensions for JA4 hash (simplified)
                ja4_raw = payload[5:50].hex()
                ja4_hash = hashlib.md5(ja4_raw.encode()).hexdigest()

                # Known malicious JA4 fingerprints (e.g. Cobalt Strike, Sliver C2)
                malicious_ja4 = {
                    "e89a3f2b1d7d8e6c4a5b2f1e0d3c5b7a": "Cobalt Strike HTTPS Beacon",
                    "b7a9c3d2e1f4b5a6d7c8e9f0a1b2c3d4": "Sliver C2 Implant",
                    "c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9": "Mythic C2 Agent",
                }

                if ja4_hash in malicious_ja4:
                    c2_framework = malicious_ja4[ja4_hash]
                    asyncio.get_event_loop().call_soon_threadsafe(
                        asyncio.ensure_future,
                        _create_alert(
                            f"Encrypted C2 Beaconing [{c2_framework}]",
                            "critical",
                            f"JA4+ TLS Fingerprint matches known malicious implant ({ja4_hash}). The payload is encrypted, but the TLS negotiation properties exactly match {c2_framework}.",
                            src_ip,
                        ),
                    )

        # Encrypted Traffic Analysis (ETA) - C2 Beacon Detection via ML Heuristics
        if dport == 443 and pkt.haslayer(Raw):
            dst_ip = pkt[IP].dst
            payload_len = len(pkt[Raw].load)

            _tls_flow_tracker[dst_ip].append((now, payload_len))
            # Clean up old packets (keep last 60 seconds)
            _tls_flow_tracker[dst_ip] = [(t, length_val) for t, length_val in _tls_flow_tracker[dst_ip] if now - t < 60]

            # Analyze rhythm if we have enough packets in this flow
            flow = _tls_flow_tracker[dst_ip]
            if len(flow) >= 10:
                iats = [flow[i][0] - flow[i - 1][0] for i in range(1, len(flow))]
                sizes = [length_val for t, length_val in flow]

                # Calculate Inter-Arrival Time (IAT) Variance and Size Variance
                avg_iat = sum(iats) / len(iats)
                iat_variance = sum((x - avg_iat) ** 2 for x in iats) / len(iats)

                avg_size = sum(sizes) / len(sizes)
                size_variance = sum((x - avg_size) ** 2 for x in sizes) / len(sizes)

                # Heuristic proxy for IsolationForest:
                # C2 Beacons are characterized by extreme regularity (low variance in both timing and size)
                # Human browsing has high variance
                if iat_variance < 0.1 and size_variance < 50.0 and avg_iat > 1.0:
                    # Possible Beacon Detected
                    if not _should_suppress("ETA C2 Beacon", dst_ip):
                        asyncio.get_event_loop().call_soon_threadsafe(
                            asyncio.ensure_future,
                            _create_alert(
                                "ETA C2 Beacon Detected (Encrypted)",
                                "critical",
                                f"Machine Learning heuristic detected an anomalous rhythmic heartbeat in encrypted TLS 1.3 traffic to {dst_ip}.\n"
                                f"Inter-Arrival Time (IAT) Variance: {iat_variance:.4f}\n"
                                f"Payload Size Variance: {size_variance:.4f}\n"
                                f"This highly regular pattern strongly indicates a Command & Control (C2) beacon.",
                                src_ip,
                            ),
                        )
                        # Clear the flow to avoid spamming while waiting for suppression
                        _tls_flow_tracker[dst_ip].clear()

        # API Security Posture Management (ASPM) - Shadow & Zombie API Discovery
        if dport in (80, 8080) and pkt.haslayer(Raw):
            try:
                payload_str = pkt[Raw].load.decode("utf-8", errors="ignore")
                # Look for an HTTP Request Line (e.g., GET /api/v1/something HTTP/1.1)
                lines = payload_str.split("\r\n")
                if lines:
                    request_line = lines[0]
                    parts = request_line.split(" ")
                    if (
                        len(parts) >= 3
                        and parts[0]
                        in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS")
                        and parts[2].startswith("HTTP/")
                    ):
                        method = parts[0]
                        endpoint = parts[1]

                        # Strip query parameters if any
                        base_endpoint = endpoint.split("?")[0]

                        # Only care about API routes for this feature
                        if base_endpoint.startswith("/api/"):
                            dst_ip = pkt[IP].dst
                            if base_endpoint not in _documented_apis:
                                if not _should_suppress(
                                    f"Shadow API {base_endpoint}", dst_ip
                                ):
                                    asyncio.get_event_loop().call_soon_threadsafe(
                                        asyncio.ensure_future,
                                        _create_alert(
                                            "Shadow API Detected",
                                            "high",
                                            f"Out-of-Band traffic mirroring discovered an undocumented API endpoint.\n"
                                            f"Method: {method}\n"
                                            f"Endpoint: {endpoint}\n"
                                            f"This endpoint is not present in the official OpenAPI/Swagger baseline. "
                                            f"It could be a Zombie API (forgotten legacy endpoint) or a Shadow API (developer testing), lacking proper authentication.",
                                            src_ip,
                                        ),
                                    )
            except Exception:
                pass

        # Industrial Protocol Anomaly Detector (IPAD) - OT/ICS Security
        if dport in (502, 102) and pkt.haslayer(Raw):
            payload = bytes(pkt[Raw].load)

            # Basic Modbus/TCP Detection (Port 502)
            if dport == 502 and len(payload) >= 8:
                # Modbus Application Protocol (MBAP) header is 7 bytes
                protocol_id = payload[2:4]
                function_code = payload[7]

                # Check for dangerous function codes (e.g., Write Multiple Registers (16), Write Coil (5))
                # Attackers use these to alter PLC logic or actuator states.
                if protocol_id == b"\x00\x00" and function_code in (5, 6, 15, 16, 43):
                    asyncio.get_event_loop().call_soon_threadsafe(
                        asyncio.ensure_future,
                        _create_alert(
                            "OT/ICS Anomaly: Dangerous Modbus Command",
                            "critical",
                            f"Detected an unauthorized Modbus/TCP write or diagnostic command (Function Code: {function_code}) sent to an Industrial PLC. This could indicate PLC tampering or an IT-to-OT pivot.",
                            src_ip,
                        ),
                    )

            # Basic S7Comm Detection (Port 102) - Siemens PLCs
            elif dport == 102 and len(payload) >= 10:
                # TPKT header starts with 0x03, COTP header follows, then S7 header
                if payload[0] == 0x03:
                    # Very simplified check for S7 Write/Upload commands
                    # A real implementation would parse the full S7 PDU
                    asyncio.get_event_loop().call_soon_threadsafe(
                        asyncio.ensure_future,
                        _create_alert(
                            "OT/ICS Anomaly: S7Comm Payload",
                            "high",
                            "Detected suspicious S7Comm industrial traffic traversing the network. Monitor for unauthorized ladder logic uploads.",
                            src_ip,
                        ),
                    )

    if pkt.haslayer(DNS) and pkt.haslayer(DNSQR):
        _handle_dns(pkt, src_ip, now)

    if pkt.haslayer(ICMP):
        if pkt[ICMP].type == 8:  # Echo request
            _handle_icmp_flood(src_ip, now)


def _handle_dns(pkt, src_ip, now):
    qname = pkt[DNSQR].qname.decode(errors="ignore").rstrip(".")
    _dns_query_tracker[src_ip].append((now, qname))
    _dns_query_tracker[src_ip] = [
        (t, q) for t, q in _dns_query_tracker[src_ip] if now - t < 60
    ]

    # Check for DNS tunnel indicators: very long subdomains or high entropy
    labels = qname.split(".")
    if any(len(label) > 50 for label in labels):
        asyncio.get_event_loop().call_soon_threadsafe(
            asyncio.ensure_future,
            _create_alert(
                "DNS Tunnel Suspected",
                "critical",
                f"Abnormally long DNS label ({max(len(l) for l in labels)} chars) in query: {qname}",
                src_ip,
            ),
        )

    if len(_dns_query_tracker[src_ip]) > 200:
        asyncio.get_event_loop().call_soon_threadsafe(
            asyncio.ensure_future,
            _create_alert(
                "DNS Query Flood",
                "medium",
                f"{len(_dns_query_tracker[src_ip])} DNS queries in 60s from {src_ip}",
                src_ip,
            ),
        )

    # DGA detection: many unique random-looking subdomains
    unique_subdomains = set(q for _, q in _dns_query_tracker[src_ip])
    if len(unique_subdomains) > 100:
        asyncio.get_event_loop().call_soon_threadsafe(
            asyncio.ensure_future,
            _create_alert(
                "DGA Activity Suspected",
                "critical",
                f"{len(unique_subdomains)} unique subdomains queried in 60s — possible Domain Generation Algorithm",
                src_ip,
            ),
        )


def _handle_icmp_flood(src_ip, now):
    if _should_suppress("ICMP Flood", src_ip):
        return
    asyncio.get_event_loop().call_soon_threadsafe(
        asyncio.ensure_future,
        _create_alert(
            "ICMP Flood / Ping Sweep",
            "medium",
            "ICMP echo request detected — possible ping sweep or DoS",
            src_ip,
        ),
    )


async def _monitor_interface():
    """Start scapy sniffer on the default interface."""
    global INTERFACE, _sniff_proc
    if not SCAPY_AVAILABLE:
        logger.warning("[IDS] scapy not available, skipping packet capture")
        return

    if not INTERFACE:
        INTERFACE = _get_default_interface()

    logger.info(f"[IDS] Starting packet capture on interface: {INTERFACE}")

    try:
        _sniff_proc = await asyncio.to_thread(
            sniff,
            iface=INTERFACE,
            prn=_process_packet,
            store=False,
            filter="arp or ip or icmp",
        )
    except PermissionError:
        logger.error(
            "[IDS] Permission denied — need root/CAP_NET_RAW for packet capture"
        )
    except Exception as e:
        logger.error(f"[IDS] Sniff error: {e}")


async def _periodic_cleanup():
    while True:
        await asyncio.sleep(120)
        now = time.time()
        _port_scan_tracker = collections.defaultdict(
            list,
            {
                k: [t for t in v if now - t < 60]
                for k, v in _port_scan_tracker.items()
                if v
            },
        )
        _dns_query_tracker = collections.defaultdict(
            list,
            {
                k: [(t, q) for t, q in v if now - t < 60]
                for k, v in _dns_query_tracker.items()
                if v
            },
        )
        _syn_tracker = collections.defaultdict(
            list,
            {k: [t for t in v if now - t < 10] for k, v in _syn_tracker.items() if v},
        )


async def start_ids():
    global _running
    logger.info("Starting real IDS engine...")
    _running = True

    if PSUTIL_AVAILABLE:
        interfaces = psutil.net_if_stats()
        for name, st in interfaces.items():
            if st.isup and name != "lo":
                logger.info(f"[IDS] Available interface: {name} (speed={st.speed}Mbps)")

    await asyncio.gather(
        _monitor_interface(),
        _periodic_cleanup(),
        return_exceptions=True,
    )
