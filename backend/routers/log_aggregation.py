"""
Netrunner Log Aggregation Router — API endpoints for centralized logging.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from .auth import require_admin
from ..core.log_aggregation import (
    fetch_logs, search_logs, get_log_stats, get_recent_logs,
    aggregate_all_nodes, LogStore,
)
from ..core.db import load_nodes_db

router = APIRouter()


class LogFetchRequest(BaseModel):
    node_id: str
    log_type: str = "journalctl"
    query: str = ""
    lines: int = 100
    since: str = ""
    priority: str = ""


class LogSearchRequest(BaseModel):
    query: str
    node_id: Optional[str] = None
    log_type: Optional[str] = None
    severity: Optional[str] = None
    limit: int = 100


@router.get("/logs/stats")
async def api_log_stats():
    """Get statistics about collected logs."""
    stats = get_log_stats()
    return stats


@router.get("/logs/recent")
async def api_log_recent(limit: int = 100):
    """Get most recent log entries."""
    entries = get_recent_logs(limit)
    return {"entries": entries, "count": len(entries)}


@router.post("/logs/fetch", dependencies=[Depends(require_admin)])
async def api_log_fetch(req: LogFetchRequest):
    """
    Fetch logs from a remote node.

    Log types: journalctl, syslog, auth, kern, dmesg, secure
    """
    nodes = await load_nodes_db()
    if req.node_id not in nodes:
        raise HTTPException(404, "Node not found")

    node = nodes[req.node_id]
    host = node.get("host", "")
    username = "root"
    password = node.get("ssh_password", "")

    try:
        from ..core.vault import get_credential
        cred = await get_credential(req.node_id, "ssh")
        if cred:
            username = cred.get("username", username)
            password = cred.get("password", password)
    except Exception:
        pass

    if not password:
        raise HTTPException(400, "No SSH credentials available")

    result = await fetch_logs(
        node_id=req.node_id,
        host=host,
        username=username,
        password=password,
        log_type=req.log_type,
        query=req.query,
        lines=req.lines,
        since=req.since,
        priority=req.priority,
    )

    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed to fetch logs"))
    return result


@router.post("/logs/search")
async def api_log_search(req: LogSearchRequest):
    """Search across all collected logs."""
    entries = search_logs(
        query=req.query,
        node_id=req.node_id,
        log_type=req.log_type,
        severity=req.severity,
        limit=req.limit,
    )
    return {"entries": entries, "count": len(entries)}


@router.get("/logs/{node_id}")
async def api_log_node(node_id: str, log_type: str = "journalctl", lines: int = 100):
    """Quick fetch logs for a specific node."""
    nodes = await load_nodes_db()
    if node_id not in nodes:
        raise HTTPException(404, "Node not found")

    node = nodes[node_id]
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
        raise HTTPException(400, "No SSH credentials available")

    result = await fetch_logs(
        node_id=node_id,
        host=host,
        username=username,
        password=password,
        log_type=log_type,
        lines=lines,
    )

    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed"))
    return result


@router.post("/logs/aggregate-all", dependencies=[Depends(require_admin)])
async def api_log_aggregate_all():
    """Fetch logs from all available nodes."""
    nodes = await load_nodes_db()
    result = await aggregate_all_nodes(nodes)
    return result


@router.get("/logs/types")
async def api_log_types():
    """List available log types."""
    types = [
        {"id": "journalctl", "name": "Systemd Journal", "description": "Systemd journal logs"},
        {"id": "syslog", "name": "Syslog", "description": "/var/log/syslog"},
        {"id": "auth", "name": "Auth Log", "description": "/var/log/auth.log"},
        {"id": "kern", "name": "Kernel Log", "description": "/var/log/kern.log"},
        {"id": "dmesg", "name": "Dmesg", "description": "Kernel ring buffer"},
        {"id": "secure", "name": "Secure Log", "description": "/var/log/secure (RHEL)"},
    ]
    return {"types": types}
