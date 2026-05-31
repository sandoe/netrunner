"""Infrastructure events / alerts.

Turns the live data we already collect (reachability transitions, CPU/RAM
thresholds) into a stream of operational events so the user is told when
something goes wrong instead of having to watch the dashboard.
"""
import itertools
import time
from collections import deque

# Newest first; bounded ring buffer.
events: deque = deque(maxlen=300)
_counter = itertools.count(1)


# Map attack-event keywords → MITRE ATT&CK techniques. Only applied to
# security events (kind demo/threat), never to infra alerts like node-down.
import re as _re
_ATTACK = [
    (r"recon|scan|sweep|enumerat|probe", "T1046", "Network Service Discovery", "discovery"),
    (r"brute|password spray|credential|login attempt", "T1110", "Brute Force", "credential-access"),
    (r"exploit|intrusion|unauthor|public-facing|rce", "T1190", "Exploit Public-Facing App", "initial-access"),
    (r"malware|implant|backdoor|payload|script", "T1059", "Command & Scripting", "execution"),
    (r"persist|cron|startup|scheduled task", "T1053", "Scheduled Task/Job", "persistence"),
    (r"privilege|sudo|escalat|root", "T1068", "Privilege Escalation", "privilege-escalation"),
    (r"evade|disable|tamper|clear log|obfuscat", "T1562", "Impair Defenses", "defense-evasion"),
    (r"dump|hash|keylog|harvest", "T1003", "Credential Dumping", "credential-access"),
    (r"lateral|pivot|remote service|psexec|smb", "T1021", "Remote Services", "lateral-movement"),
    (r"collect|stage|archive", "T1074", "Data Staged", "collection"),
    (r"exfil|leak|data theft|upload", "T1041", "Exfiltration Over C2", "exfiltration"),
    (r"dos|flood|uplink lost|offline|denial", "T1498", "Network Denial of Service", "impact"),
    (r"cpu spike|resource|hijack|mining|ransom", "T1496", "Resource Hijacking", "impact"),
    (r"c2|command and control|beacon|callback", "T1071", "Application Layer Protocol", "command-and-control"),
]


def _infer_technique(message: str):
    m = message.lower()
    for pat, tid, name, tactic in _ATTACK:
        if _re.search(pat, m):
            return {"id": tid, "name": name, "tactic": tactic}
    return None


def record_event(severity: str, node_id: str, node_name: str, kind: str, message: str) -> dict:
    """severity: info | warning | critical. Returns the event."""
    technique = _infer_technique(message) if kind in ("demo", "threat") else None
    ev = {
        "id": next(_counter),
        "ts": time.time(),
        "severity": severity,
        "node_id": node_id,
        "node_name": node_name,
        "kind": kind,          # reachability | cpu | ram | demo | threat ...
        "message": message,
        "technique": technique,
    }
    events.appendleft(ev)
    # Broadcast over the telemetry websocket (lazy import avoids a cycle).
    try:
        from .telemetry import telemetry_queue
        telemetry_queue.put_nowait({"type": "event", **ev})
    except Exception:
        pass
    return ev


def recent_events(limit: int = 150) -> list:
    return list(itertools.islice(events, 0, limit))


def clear_events() -> int:
    n = len(events)
    events.clear()
    return n
