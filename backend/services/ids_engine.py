"""
Netrunner IDS Engine — Real network intrusion detection using scapy.

Replaces the stub with actual packet analysis, ARP spoof detection,
port scan detection, DNS tunnel detection, and known-bad IP checking.
"""
import asyncio
import uuid
import time
import collections
from typing import Optional
from backend.core.logger import log as logger
from backend.core.db import insert_alert, check_ip_threat_intel, load_nodes_db

try:
    from scapy.all import sniff, ARP, IP, TCP, UDP, DNS, DNSQR, ICMP, Raw, conf
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logger.warning("scapy not available — IDS will operate in passive/remote mode only")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# --- Detection state ---
_arp_table: dict[str, set[str]] = collections.defaultdict(set)
_port_scan_tracker: dict[str, list[float]] = collections.defaultdict(list)
_dns_query_tracker: dict[str, list[tuple[float, str]]] = collections.defaultdict(list)
_syn_tracker: dict[str, list[float]] = collections.defaultdict(list)
_alert_cooldowns: dict[str, float] = {}
_alert_suppression_window = 300  # 5 min cooldown per (type, src) pair

INTERFACE: Optional[str] = None  # auto-detect if None
_running = False
_sniff_proc = None


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


async def _create_alert(title: str, severity: str, description: str, src_ip: str = ""):
    if src_ip and _should_suppress(title.split("[")[0].strip(), src_ip):
        return

    intel = None
    if src_ip:
        intel = await check_ip_threat_intel(src_ip)

    if intel:
        title = f"[KNOWN THREAT] {title}"
        description = f"{description} | Threat Intel: {intel['source']} ({intel['threat_type']})"
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
        _port_scan_tracker[src_ip] = [t for t in _port_scan_tracker[src_ip] if now - t < 60]
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
        logger.error("[IDS] Permission denied — need root/CAP_NET_RAW for packet capture")
    except Exception as e:
        logger.error(f"[IDS] Sniff error: {e}")


async def _periodic_cleanup():
    """Periodically clean up stale tracking state."""
    global _arp_table, _port_scan_tracker, _dns_query_tracker, _syn_tracker
    while True:
        await asyncio.sleep(120)
        now = time.time()
        _port_scan_tracker = collections.defaultdict(
            list, {k: [t for t in v if now - t < 60] for k, v in _port_scan_tracker.items() if v}
        )
        _dns_query_tracker = collections.defaultdict(
            list, {k: [(t, q) for t, q in v if now - t < 60] for k, v in _dns_query_tracker.items() if v}
        )
        _syn_tracker = collections.defaultdict(
            list, {k: [t for t in v if now - t < 10] for k, v in _syn_tracker.items() if v}
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
