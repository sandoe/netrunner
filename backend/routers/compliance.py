"""
Netrunner Compliance Scanner Router — API endpoints for CIS/NIST scanning.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from .auth import require_admin
from ..core.compliance import run_compliance_scan, get_scan_history, get_scan_detail, get_frameworks
from ..core.db import load_nodes_db

router = APIRouter()


class ComplianceScanRequest(BaseModel):
    node_id: str
    framework: str = "CIS"


@router.get("/compliance/frameworks")
async def api_compliance_frameworks():
    """List available compliance frameworks."""
    frameworks = get_frameworks()
    return {"frameworks": frameworks}


@router.post("/compliance/scan", dependencies=[Depends(require_admin)])
async def api_compliance_scan(req: ComplianceScanRequest):
    """
    Run a compliance scan against a node.

    Frameworks:
    - CIS: CIS Benchmark checks
    - NIST-800-53: NIST 800-53 control mapping
    """
    nodes = await load_nodes_db()
    if req.node_id not in nodes:
        raise HTTPException(404, "Node not found")

    node = nodes[req.node_id]
    host = node.get("host", "")
    username = "root"
    password = node.get("ssh_password", "")

    # Try vault credentials
    try:
        from ..core.vault import get_credential
        cred = await get_credential(req.node_id, "ssh")
        if cred:
            username = cred.get("username", username)
            password = cred.get("password", password)
    except Exception:
        pass

    if not password:
        raise HTTPException(400, "No SSH credentials available for this node")

    result = await run_compliance_scan(
        node_id=req.node_id,
        host=host,
        username=username,
        password=password,
        framework=req.framework,
    )

    return result


@router.get("/compliance/scans")
async def api_compliance_scans():
    """List all compliance scan history."""
    scans = get_scan_history()
    return {"scans": scans, "count": len(scans)}


@router.get("/compliance/scans/{scan_id}")
async def api_compliance_scan_detail(scan_id: str):
    """Get detailed results of a specific scan."""
    result = get_scan_detail(scan_id)
    if not result:
        raise HTTPException(404, "Scan not found")
    return result


@router.get("/compliance/checks")
async def api_compliance_checks(framework: str = "CIS"):
    """List all compliance checks for a framework."""
    from ..core.compliance import CIS_CHECKS
    checks = [c for c in CIS_CHECKS if framework in c.get("frameworks", [])]
    return {"checks": checks, "count": len(checks), "framework": framework}
