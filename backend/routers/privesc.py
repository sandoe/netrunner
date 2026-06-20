"""
Netrunner Privilege Escalation Scanner Router — API endpoints for privesc detection.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from .auth import require_admin
from ..core.privesc import run_privesc_scan, list_scans, get_scan_detail
from ..core.db import load_nodes_db

router = APIRouter()


class PrivescScanRequest(BaseModel):
    node_id: str


@router.get("/privesc/scans")
async def api_privesc_scans():
    """List all privilege escalation scans."""
    scans = list_scans()
    return {"scans": scans, "count": len(scans)}


@router.get("/privesc/scans/{scan_id}")
async def api_privesc_scan_detail(scan_id: str):
    """Get detailed scan results."""
    result = get_scan_detail(scan_id)
    if not result:
        raise HTTPException(404, "Scan not found")
    return result


@router.post("/privesc/scan", dependencies=[Depends(require_admin)])
async def api_privesc_scan(req: PrivescScanRequest):
    """
    Run privilege escalation scan on a node.

    Detects SUID exploits, sudo misconfigs, writable files,
    docker group membership, and other privesc vectors.
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

    result = await run_privesc_scan(
        node_id=req.node_id,
        host=host,
        username=username,
        password=password,
    )

    return result
