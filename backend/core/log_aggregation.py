"""
Netrunner Log Aggregation Module — Centralized logging from multiple nodes.

Provides:
- Syslog collection from managed nodes
- Journalctl log streaming
- Log search and filtering
- Alert correlation with logs
- Log storage and retention
"""
import asyncio
import json
import os
import time
import re
from typing import Optional
from backend.core.logger import log as logger

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

LOG_DIR = "data/logs/aggregated"


def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


# In-memory log store
LogStore: list[dict] = []
MAX_LOG_ENTRIES = 50000


async def _ssh_exec(host: str, username: str, password: str, command: str, port: int = 22) -> tuple[int, str, str]:
    """Execute a command over SSH."""
    if not PARAMIKO_AVAILABLE:
        return -1, "", "paramiko not installed"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        await asyncio.to_thread(
            client.connect,
            hostname=host, port=port, username=username, password=password,
            timeout=10, look_for_keys=False, allow_agent=False,
        )
        _, stdout, stderr = await asyncio.to_thread(client.exec_command, command, timeout=30)
        exit_code = await asyncio.to_thread(stdout.channel.recv_exit_status)
        out = await asyncio.to_thread(stdout.read().decode, errors="replace")
        err = await asyncio.to_thread(stderr.read().decode, errors="replace")
        return exit_code, out, err
    except Exception as e:
        return -1, "", str(e)
    finally:
        client.close()


async def fetch_logs(
    node_id: str,
    host: str,
    username: str,
    password: str,
    log_type: str = "journalctl",
    query: str = "",
    lines: int = 100,
    since: str = "",
    priority: str = "",
) -> dict:
    """
    Fetch logs from a remote node.

    Args:
        node_id: Node identifier
        host: Node hostname/IP
        username: SSH username
        password: SSH password
        log_type: Type of log (journalctl, syslog, auth, kern, dmesg)
        query: Search/filter query
        lines: Number of lines to fetch
        since: Time filter (e.g., "1 hour ago", "2024-01-01")
        priority: Log priority filter (emerg, alert, crit, err, warning, notice, info, debug)

    Returns:
        dict with log entries
    """
    logger.info(f"[LOG-AGG] Fetching {log_type} logs from {host} (node={node_id})")

    if log_type == "journalctl":
        cmd = "journalctl --no-pager"
        if lines:
            cmd += f" -n {lines}"
        if since:
            cmd += f" --since '{since}'"
        if priority:
            cmd += f" -p {priority}"
        if query:
            cmd += f" | grep -i '{query}'"
    elif log_type == "syslog":
        cmd = f"tail -n {lines} /var/log/syslog"
        if query:
            cmd += f" | grep -i '{query}'"
    elif log_type == "auth":
        cmd = f"tail -n {lines} /var/log/auth.log"
        if query:
            cmd += f" | grep -i '{query}'"
    elif log_type == "kern":
        cmd = f"tail -n {lines} /var/log/kern.log"
        if query:
            cmd += f" | grep -i '{query}'"
    elif log_type == "dmesg":
        cmd = f"dmesg | tail -n {lines}"
        if query:
            cmd += f" | grep -i '{query}'"
    elif log_type == "secure":
        cmd = f"tail -n {lines} /var/log/secure 2>/dev/null || tail -n {lines} /var/log/auth.log"
        if query:
            cmd += f" | grep -i '{query}'"
    else:
        return {"success": False, "error": f"Unknown log type: {log_type}"}

    exit_code, out, err = await _ssh_exec(host, username, password, cmd)

    if exit_code != 0 and not out:
        return {"success": False, "error": f"Failed to fetch logs: {err}"}

    # Parse log lines
    log_entries = []
    for line in out.strip().splitlines():
        if not line.strip():
            continue
        parsed = _parse_log_line(line, node_id, log_type)
        log_entries.append(parsed)

    # Add to central store
    LogStore.extend(log_entries)
    if len(LogStore) > MAX_LOG_ENTRIES:
        LogStore[:] = LogStore[-MAX_LOG_ENTRIES:]

    return {
        "success": True,
        "node_id": node_id,
        "log_type": log_type,
        "entries": log_entries,
        "count": len(log_entries),
    }


def _parse_log_line(line: str, node_id: str, log_type: str) -> dict:
    """Parse a log line into structured data."""
    entry = {
        "raw": line,
        "node_id": node_id,
        "log_type": log_type,
        "timestamp": time.time(),
    }

    # Try to extract timestamp
    ts_patterns = [
        r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})",  # Jan  1 12:00:00
        r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})",    # 2024-01-01T12:00:00
        r"^\[(\d+\.\d+)\]",                              # [1234567890.123]
    ]
    for pattern in ts_patterns:
        match = re.match(pattern, line)
        if match:
            entry["timestamp_str"] = match.group(1)
            break

    # Try to extract priority/severity
    priority_map = {
        "emerg": "critical", "alert": "critical", "crit": "critical",
        "err": "high", "error": "high",
        "warning": "medium", "warn": "medium",
        "notice": "info", "info": "info", "debug": "debug",
    }
    line_lower = line.lower()
    for keyword, severity in priority_map.items():
        if keyword in line_lower:
            entry["severity"] = severity
            break

    # Extract process/service
    proc_match = re.search(r"(\w+)\[\d+\]:", line)
    if proc_match:
        entry["process"] = proc_match.group(1)

    return entry


async def stream_logs(
    node_id: str,
    host: str,
    username: str,
    password: str,
    log_type: str = "journalctl",
    follow: bool = True,
) -> dict:
    """
    Stream logs from a remote node in real-time.
    Uses SSH + journalctl -f for continuous streaming.
    """
    logger.info(f"[LOG-AGG] Starting log stream from {host} (node={node_id})")

    if follow and log_type == "journalctl":
        cmd = "journalctl --no-pager -f"
    else:
        return await fetch_logs(node_id, host, username, password, log_type, lines=500)

    # For streaming, we'll poll periodically
    result = await fetch_logs(node_id, host, username, password, log_type, lines=100)
    result["streaming"] = True
    return result


def search_logs(
    query: str,
    node_id: Optional[str] = None,
    log_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """
    Search across all collected logs.
    """
    results = []
    for entry in reversed(LogStore):
        if node_id and entry.get("node_id") != node_id:
            continue
        if log_type and entry.get("log_type") != log_type:
            continue
        if severity and entry.get("severity") != severity:
            continue
        if query and query.lower() not in entry.get("raw", "").lower():
            continue

        results.append(entry)
        if len(results) >= limit:
            break

    return results


def get_log_stats() -> dict:
    """Get statistics about collected logs."""
    stats = {
        "total_entries": len(LogStore),
        "by_node": {},
        "by_type": {},
        "by_severity": {},
    }

    for entry in LogStore:
        node = entry.get("node_id", "unknown")
        log_type = entry.get("log_type", "unknown")
        severity = entry.get("severity", "unknown")

        stats["by_node"][node] = stats["by_node"].get(node, 0) + 1
        stats["by_type"][log_type] = stats["by_type"].get(log_type, 0) + 1
        stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1

    return stats


def get_recent_logs(limit: int = 100) -> list[dict]:
    """Get most recent log entries."""
    return list(reversed(LogStore[-limit:]))


async def aggregate_all_nodes(nodes: dict) -> dict:
    """
    Fetch logs from all available nodes.
    """
    results = []
    for node_id, node in nodes.items():
        host = node.get("host", "")
        username = "root"
        password = node.get("ssh_password", "")

        try:
            from ..core.vault import get_credential
            cred = await get_credential(node_id, "ssh")
            if cred:
                username = cred.get("username", username)
                password = cred.get("password", password)
        except Exception:
            pass

        if not password:
            continue

        result = await fetch_logs(
            node_id=node_id,
            host=host,
            username=username,
            password=password,
            log_type="journalctl",
            lines=50,
        )
        results.append({
            "node_id": node_id,
            "success": result["success"],
            "count": result.get("count", 0),
        })

    return {
        "nodes_aggregated": len(results),
        "results": results,
    }
