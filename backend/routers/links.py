"""Link CRUD and Discovery API endpoints."""
from __future__ import annotations

import json
import uuid
import re
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .nodes import load_nodes, _get_node_with_creds
from ..core.session import session_manager

router = APIRouter()

DATA_DIR = Path("data")
LINKS_FILE = DATA_DIR / "links.json"

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_links() -> dict:
    if LINKS_FILE.exists():
        try:
            return json.loads(LINKS_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_links(links: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LINKS_FILE.write_text(json.dumps(links, indent=2))


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class LinkCreate(BaseModel):
    source: str  # Node ID
    target: str  # Node ID
    auto_discovered: bool = False
    metadata: dict = {}

class Link(LinkCreate):
    id: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/links", response_model=List[Link])
async def get_links():
    links = load_links()
    return list(links.values())


@router.post("/links", response_model=Link)
async def create_link(link_in: LinkCreate):
    links = load_links()
    
    # Simple check for duplicates
    for l in links.values():
        if (l["source"] == link_in.source and l["target"] == link_in.target) or \
           (l["source"] == link_in.target and l["target"] == link_in.source):
            # Return existing if same pair
            return Link(id=l["id"], **l)

    link_id = str(uuid.uuid4())
    new_link = Link(id=link_id, **link_in.model_dump())
    links[link_id] = new_link.model_dump()
    save_links(links)
    return new_link


@router.delete("/links/{link_id}")
async def delete_link(link_id: str):
    links = load_links()
    if link_id not in links:
        raise HTTPException(status_code=404, detail="Link not found")
    
    del links[link_id]
    save_links(links)
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Discovery Logic
# ---------------------------------------------------------------------------

@router.post("/links/discover")
async def discover_links():
    nodes = load_nodes()
    links = load_links()
    active_ids = session_manager.active_ids()
    
    if not active_ids:
        return {"status": "error", "message": "No active sessions. Please connect nodes first."}

    new_links_count = 0
    unknown_neighbors = []
    
    # 1. Build a comprehensive IP map (Management IP + Interface IPs)
    ip_to_node = {}
    for nid, n in nodes.items():
        ip_to_node[n["host"]] = nid
        
        # Try to get more IPs if node is active
        try:
            node_creds = _get_node_with_creds(nid, nodes)
            # This is a bit slow but robust: fetch all IPs for this node
            ip_results, _ = session_manager.run(nid, node_creds, ["ip -4 addr show | grep inet | awk '{print $2}' | cut -d/ -f1"])
            if ip_results:
                for ip in ip_results[0].get("output", "").splitlines():
                    if ip.strip():
                        ip_to_node[ip.strip()] = nid
        except:
            pass

    for nid in active_ids:
        node_data = _get_node_with_creds(nid, nodes)
        
        cmds = [
            "ip -4 neigh show",
            "lldpcli show neighbors -f json 2>/dev/null || echo '{}'",
            "bridge vlan show 2>/dev/null || echo ''" # Helper for switches
        ]
        
        results, err = session_manager.run(nid, node_data, cmds)
        if not results:
            continue
            
        # Parse ARP
        neigh_output = results[0].get("output", "")
        for line in neigh_output.splitlines():
            parts = line.split()
            if not parts: continue
            neighbor_ip = parts[0]
            
            if neighbor_ip in ip_to_node:
                target_id = ip_to_node[neighbor_ip]
                if target_id != nid:
                    if _add_link_if_new(links, nid, target_id, "arp"):
                        new_links_count += 1
            elif neighbor_ip not in ("127.0.0.1", "::1"):
                unknown_neighbors.append({
                    "ip": neighbor_ip,
                    "source_node": nodes[nid]["name"],
                    "method": "arp"
                })

        # Parse LLDP
        lldp_raw = results[1].get("output", "{}")
        if lldp_raw.strip() and lldp_raw != "{}":
            try:
                lldp_data = json.loads(lldp_raw)
                # LLDP structure can be complex, recursively look for chassis names
                def find_neighbors(obj):
                    if isinstance(obj, dict):
                        if "chassis" in obj:
                            c = obj["chassis"]
                            if isinstance(c, list):
                                for item in c:
                                    name = item.get("name", [{}])[0].get("value")
                                    if name: yield name
                            elif isinstance(c, dict):
                                name = c.get("name", [{}])[0].get("value")
                                if name: yield name
                        for v in obj.values():
                            yield from find_neighbors(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            yield from find_neighbors(item)

                for remote_name in find_neighbors(lldp_data):
                    found_in_db = False
                    for t_id, t_node in nodes.items():
                        if t_node["name"].lower() == remote_name.lower() and t_id != nid:
                            found_in_db = True
                            if _add_link_if_new(links, nid, t_id, "lldp"):
                                new_links_count += 1
                    
                    if not found_in_db:
                        unknown_neighbors.append({
                            "name": remote_name,
                            "source_node": nodes[nid]["name"],
                            "method": "lldp"
                        })
            except:
                pass

    save_links(links)
    return {
        "status": "success", 
        "discovered": new_links_count, 
        "unknown_neighbors": unknown_neighbors
    }


def _add_link_if_new(links: dict, s: str, t: str, method: str) -> bool:
    for l in links.values():
        if (l["source"] == s and l["target"] == t) or \
           (l["source"] == t and l["target"] == s):
            return False
            
    lid = str(uuid.uuid4())
    links[lid] = {
        "id": lid,
        "source": s,
        "target": t,
        "auto_discovered": True,
        "metadata": {"method": method}
    }
    return True
