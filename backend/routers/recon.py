import uuid
import xml.etree.ElementTree as ET
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from datetime import datetime

from .auth import get_current_user
from ..core.session import session_manager
from .nodes import load_nodes, save_nodes, _get_node_with_creds
from .links import load_links, save_links

router = APIRouter(tags=["recon"])

@router.post("/recon/{nid}/scan")
async def scan_network(nid: str, body: dict, user: dict = Depends(get_current_user)):
    target = body.get("target")
    profile = body.get("profile", "quick")
    sudo_pass = body.get("sudo_pass")

    if not target:
        raise HTTPException(400, "Missing target")

    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    node = await _get_node_with_creds(nid, nodes)
    if sudo_pass:
        node["password"] = sudo_pass
    from ..core.scanner import run_remote_nmap_xml
    try:
        result = await run_remote_nmap_xml(nid, node, target, profile, sudo_pass)
        return result
    except RuntimeError as e:
        raise HTTPException(500, str(e))



@router.post("/recon/{nid}/import")
async def import_recon_hosts(nid: str, body: dict, user: dict = Depends(get_current_user)):
    hosts = body.get("hosts", [])
    if not hosts:
        raise HTTPException(400, "No hosts provided")

    nodes = await load_nodes()
    links = await load_links()
    
    imported_count = 0
    
    for h in hosts:
        ip = h.get("ip")
        if not ip: continue
        
        # Check if already exists
        exists = False
        for node_id, node_data in nodes.items():
            if node_data.get("host") == ip:
                exists = True
                break
                
        if exists:
            continue
            
        # Determine device type
        os_str = h.get("os", "").lower()
        device_type = "unknown"
        if "linux" in os_str:
            device_type = "linux"
        elif "windows" in os_str:
            device_type = "windows"
        elif "mac" in os_str or "apple" in os_str:
            device_type = "unknown"
            
        name = ip
        if h.get("hostnames"):
            name = h.get("hostnames")[0]
            
        new_node_id = str(uuid.uuid4())
        nodes[new_node_id] = {
            "id": new_node_id,
            "name": name,
            "host": ip,
            "port": 22,
            "username": "root",
            "transport": "ssh",
            "device_type": device_type,
            "has_password": False,
            "created": datetime.utcnow().isoformat(),
            "tags": ["recon"],
            "metadata": {
                "mac": h.get("mac"),
                "os_guess": h.get("os"),
                "ports": h.get("ports")
            }
        }
        
        # Add link from the scanning node to the discovered node
        new_link_id = f"{nid}_{new_node_id}"
        links[new_link_id] = {
            "id": new_link_id,
            "source": nid,
            "target": new_node_id,
            "auto_discovered": True,
            "metadata": {
                "method": "nmap"
            }
        }
        imported_count += 1
        
    if imported_count > 0:
        await save_nodes(nodes)
        await save_links(links)
        
    return {"status": "success", "imported": imported_count}
