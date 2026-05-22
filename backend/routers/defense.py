from fastapi import APIRouter, HTTPException, Depends
from ..core.defense import run_nmap_scan, apply_isolation, enforce_zero_trust
from .auth import require_admin
from ..core.db import load_nodes_db, save_node_db
from ..core.vault import load_credentials
from ..core.session import session_manager

router = APIRouter()

@router.post("/nodes/{nid}/nmap", dependencies=[Depends(require_admin)])
async def api_defense_nmap(nid: str):
    """Executes a vulnerability scan (nmap) on the node."""
    result = await run_nmap_scan(nid)
    if result.startswith("Error"):
        raise HTTPException(400, result)
    return {"status": "success", "scan_results": result}

@router.post("/nodes/{nid}/isolate", dependencies=[Depends(require_admin)])
async def api_defense_isolate(nid: str):
    """Deploys iptables isolation rules to the node."""
    result = await apply_isolation(nid)
    if result.startswith("Error"):
        raise HTTPException(400, result)
    return {"status": "success", "isolation_log": result}

@router.post("/nodes/{nid}/defense/zero-trust", dependencies=[Depends(require_admin)])
async def api_zero_trust_node(nid: str):
    """Enforces Zero Trust Architecture on the node."""
    result = await enforce_zero_trust(nid)
    if result.startswith("Error"):
        raise HTTPException(400, result)
    return {"status": "success", "message": result}

@router.post("/nodes/{nid}/monitoring/install", dependencies=[Depends(require_admin)])
async def api_install_monitoring(nid: str):
    """Verifies syslog/journalctl readability and installs the Threat Monitor Agent."""
    nodes = await load_nodes_db()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")
        
    node = dict(nodes[nid])
    username, password = await load_credentials(nid)
    node["username"] = username
    node["password"] = password
    
    # Check if we can read logs
    test_cmd = (
        "tail -n 1 /var/log/auth.log 2>/dev/null || "
        "journalctl -n 1 --no-pager 2>/dev/null || "
        "echo '__UNREADABLE__'"
    )
    
    results, err = await session_manager.run(nid, node, [test_cmd])
    if err:
        raise HTTPException(500, f"Failed to connect to node: {err}")
        
    output = results[0].get("output", "") if results else ""
    if "__UNREADABLE__" in output or "Permission denied" in output:
        raise HTTPException(
            400, 
            "Permission Denied: SSH user cannot read /var/log/auth.log or run journalctl. "
            "Please ensure the SSH user is root or added to the 'adm' / 'systemd-journal' groups."
        )
        
    # Save the updated state
    node_db_format = dict(nodes[nid])
    node_db_format["threat_monitoring"] = True
    await save_node_db(node_db_format)
    
    return {
        "status": "success", 
        "message": "Multi-Vector Threat Monitor Agent successfully installed! Active tailing for SSH Brute Force, Web server exploits (SQLi/XSS/LFI), and Firewall port scans is now online."
    }

@router.post("/nodes/{nid}/monitoring/remove", dependencies=[Depends(require_admin)])
async def api_remove_monitoring(nid: str):
    """Uninstalls the Threat Monitor Agent from the node."""
    nodes = await load_nodes_db()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")
        
    # Save the updated state
    node_db_format = dict(nodes[nid])
    node_db_format["threat_monitoring"] = False
    await save_node_db(node_db_format)
    
    return {
        "status": "success", 
        "message": "Threat Monitor Agent successfully removed. Real-time tailing deactivated."
    }
