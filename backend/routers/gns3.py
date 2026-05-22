"""GNS3 API integration for importing nodes and links."""
from __future__ import annotations

import httpx
import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from .settings import load_settings
from .nodes import load_nodes, save_nodes, NodeCreate
from .links import load_links, save_links, _add_link_if_new

router = APIRouter()

import configparser

def get_gns3_config():
    conf_path = Path.home() / ".config" / "GNS3" / "2.2" / "gns3_server.conf"
    if conf_path.exists():
        try:
            config = configparser.ConfigParser()
            config.read(conf_path)
            if "Server" in config:
                return config["Server"]
        except Exception:
            pass
    return None

async def _gns3_req(method: str, path: str, body: Optional[dict] = None):
    s = await load_settings()
    base = s.get("gns3_server_url", "http://127.0.0.1:3080").rstrip("/")
    
    server_conf = get_gns3_config()
    auth = None
    if server_conf:
        conf_user = server_conf.get("user", "")
        conf_pass = server_conf.get("password", "")
        conf_auth = server_conf.getboolean("auth", fallback=False)
        if conf_auth and conf_user and conf_pass:
            auth = (conf_user, conf_pass)
            
    candidates = []
    # Always include the local GNS3 server if config exists
    if server_conf:
        conf_host = server_conf.get("host", "127.0.0.1")
        conf_port = server_conf.get("port", "3080")
        local_base = f"http://{conf_host}:{conf_port}"
        candidates.append((local_base, auth))
        
    # Also include the configured URL from settings
    if base not in [c[0] for c in candidates]:
        candidates.append((base, auth))
        
    results = []
    success = False
    last_err = None
    
    for b_url, b_auth in candidates:
        async with httpx.AsyncClient() as client:
            try:
                url = f"{b_url}/v2{path}"
                res = await client.request(method, url, json=body, auth=b_auth, timeout=10.0)
                if res.status_code == 404:
                    continue
                res.raise_for_status()
                data = res.json()
                success = True
                if isinstance(data, list):
                    results.extend(data)
                else:
                    return data
            except Exception as e:
                last_err = e
                continue
                
    if success:
        if method == "GET" and isinstance(results, list):
            # De-duplicate lists by unique key
            seen = set()
            unique_results = []
            for item in results:
                key = item.get("project_id") or item.get("node_id") or item.get("name") or str(item)
                if key not in seen:
                    seen.add(key)
                    unique_results.append(item)
            return unique_results
        return results
        
    raise HTTPException(status_code=500, detail=f"GNS3 API error: {last_err}")

@router.get("/gns3/projects")
async def list_gns3_projects():
    return await _gns3_req("GET", "/projects")

@router.post("/gns3/sync/{project_id}")
async def sync_gns3_project(project_id: str):
    # 1. Get project nodes and links
    g_nodes = await _gns3_req("GET", f"/projects/{project_id}/nodes")
    g_links = await _gns3_req("GET", f"/projects/{project_id}/links")
    
    if g_nodes is None: raise HTTPException(status_code=404, detail="Project not found")

    nodes = await load_nodes()
    links = await load_links()
    
    # Map GNS3 node UUID to Netrunner ID
    uuid_map = {}
    
    # 2. Sync Nodes
    for gn in g_nodes:
        # Check if already exists by name/console
        found_id = None
        for nid, n in nodes.items():
            if n.get("name") == gn["name"]:
                found_id = nid
                break
        
        if not found_id:
            # Create new node
            new_id = f"gns3_{gn['node_id'][:8]}"
            nodes[new_id] = {
                "id": new_id,
                "name": gn["name"],
                "host": gn.get("console_host", "127.0.0.1"),
                "port": gn.get("console", 0),
                "transport": "telnet",
                "device_type": "gns3",
                "tags": ["gns3-imported"],
                "created": gn.get("created_at")
            }
            found_id = new_id
        
        uuid_map[gn["node_id"]] = found_id

    # 3. Sync Links
    new_links = 0
    for gl in g_links:
        # GNS3 links connect node UUIDs
        # link -> nodes -> [ {node_id, adapter_number, port_number}, ... ]
        g_node_ids = [n["node_id"] for n in gl["nodes"]]
        if len(g_node_ids) == 2:
            s_id = uuid_map.get(g_node_ids[0])
            t_id = uuid_map.get(g_node_ids[1])
            if s_id and t_id:
                if _add_link_if_new(links, s_id, t_id, "gns3-sync"):
                    new_links += 1

    await save_nodes(nodes)
    await save_links(links)
    
    return {"status": "success", "nodes": len(g_nodes), "links": new_links}

@router.get("/gns3/local-projects")
async def list_local_gns3_projects():
    s = await load_settings()
    base_path = Path(s.get("gns3_local_projects_path", "/home/aso/GNS3/projects"))
    
    if not base_path.exists():
        return []
    
    projects = []
    try:
        for p_dir in base_path.iterdir():
            if p_dir.is_dir():
                gns3_files = list(p_dir.glob("*.gns3"))
                if gns3_files:
                    projects.append({
                        "name": p_dir.name,
                        "path": str(gns3_files[0]),
                        "id": p_dir.name
                    })
    except:
        return []
    return projects

@router.post("/local-sync")
async def sync_local_gns3_project(payload: dict):
    path = payload.get("path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Project file not found")
        
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read .gns3 file: {e}")

    topology = data.get("topology", {})
    g_nodes = topology.get("nodes", [])
    g_links = topology.get("links", [])

    nodes = await load_nodes()
    links = await load_links()
    uuid_map = {}
    
    s = await load_settings()
    # Assume console is reachable via the configured server host
    remote_host = s.get("gns3_server_url", "http://192.168.122.121").replace("http://", "").split(":")[0]

    for gn in g_nodes:
        found_id = None
        for nid, n in nodes.items():
            if n.get("name") == gn["name"]:
                found_id = nid
                break
        
        if not found_id:
            new_id = f"local_{gn['node_id'][:8]}"
            nodes[new_id] = {
                "id": new_id,
                "name": gn["name"],
                "host": remote_host,
                "port": gn.get("console", 0),
                "transport": "telnet",
                "device_type": "gns3",
                "tags": ["local-gns3-import"],
                "created": None
            }
            found_id = new_id
        
        uuid_map[gn["node_id"]] = found_id

    new_links = 0
    for gl in g_links:
        g_node_ids = [n["node_id"] for n in gl["nodes"]]
        if len(g_node_ids) == 2:
            s_id = uuid_map.get(g_node_ids[0])
            t_id = uuid_map.get(g_node_ids[1])
            if s_id and t_id:
                if _add_link_if_new(links, s_id, t_id, "local-gns3-sync"):
                    new_links += 1

    await save_nodes(nodes)
    await save_links(links)
    return {"status": "success", "nodes": len(g_nodes), "links": new_links}
