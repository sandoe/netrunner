"""Agent deployment and management endpoints."""

from __future__ import annotations

import base64
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from .auth import get_current_user, require_non_student
from ..core.session import session_manager
from .nodes import load_nodes, _get_node_with_creds
from ..core.vault import store_credentials

import asyncio
import json
from ..core.events import record_event

router = APIRouter(tags=["agents"])

# Map agent ID to the script file name and its log file location
AVAILABLE_AGENTS = {
    "recon": {
        "name": "Reconnaissance Agent",
        "description": "Intercepts Bluetooth & WiFi data for OSINT.",
        "script": "recon_agent.py",
        "log_file": "/tmp/netrunner-recon.jsonl",
    },
    "tracker": {
        "name": "Geolocation Tracker",
        "description": "Logs IP-based geographical coordinates.",
        "script": "tracker.py",
        "log_file": "/tmp/netrunner-location.log",
    },
    "scanner": {
        "name": "Subnet Scanner",
        "description": "Scans local LAN for devices via ARP and ping.",
        "script": "subnet_scanner.py",
        "log_file": "/tmp/netrunner-scanner.json",
    },
    "sniffer": {
        "name": "Network Sniffer",
        "description": "Captures DNS lookups on the network interface.",
        "script": "sniffer.py",
        "log_file": "/tmp/netrunner-sniffer.log",
    },
    "honeypot": {
        "name": "Honeypot Service",
        "description": "Opens fake FTP port to trap login attempts.",
        "script": "honeypot.py",
        "log_file": "/tmp/netrunner-honeypot.log",
    },
    "auth_monitor": {
        "name": "Intrusion Detection",
        "description": "Tails auth.log for failed SSH attempts.",
        "script": "auth_monitor.py",
        "log_file": "/tmp/netrunner-auth.log",
    },
    "usb_monitor": {
        "name": "USB Device Monitor",
        "description": "Monitors dmesg for newly connected USB devices.",
        "script": "usb_monitor.py",
        "log_file": "/tmp/netrunner-usb.log",
    },
}


@router.get("/nodes/{nid}/agents/status")
async def api_get_agents_status(nid: str, user: dict = Depends(get_current_user)):
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    node = await _get_node_with_creds(nid, nodes)

    # We will run a single compound command to check both installation and running status for all agents.
    cmds = []
    for agent_id, info in AVAILABLE_AGENTS.items():
        script_name = info["script"]
        cmds.append(
            f"ls /tmp/{script_name} >/dev/null 2>&1 && echo '{agent_id}_INSTALLED' || echo '{agent_id}_MISSING'"
        )
        cmds.append(
            f"ps aux | grep '{script_name}' | grep -v grep >/dev/null 2>&1 && echo '{agent_id}_RUNNING' || echo '{agent_id}_STOPPED'"
        )

    cmd_str = " ; ".join(cmds)
    results, err = await session_manager.run(nid, node, [cmd_str])

    if err and not results:
        raise HTTPException(500, f"Failed to check agent status: {err}")

    output = results[0].get("output", "") if results else ""

    status_list = []
    for agent_id, info in AVAILABLE_AGENTS.items():
        installed = f"{agent_id}_INSTALLED" in output
        running = f"{agent_id}_RUNNING" in output
        status_list.append(
            {
                "id": agent_id,
                "name": info["name"],
                "description": info["description"],
                "installed": installed,
                "running": running,
            }
        )

    return {"status": "success", "agents": status_list}


@router.post("/nodes/{nid}/agents/{agent_id}/install")
async def api_install_agent(
    nid: str, agent_id: str, user: dict = Depends(require_non_student)
):
    if agent_id not in AVAILABLE_AGENTS:
        raise HTTPException(404, "Unknown agent type")

    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    script_name = AVAILABLE_AGENTS[agent_id]["script"]
    script_path = Path(__file__).parent.parent / "scripts" / script_name

    if not script_path.exists():
        raise HTTPException(500, f"Agent script {script_name} not found on server")

    with open(script_path, "r", encoding="utf-8") as f:
        script_content = f.read()

    encoded_script = base64.b64encode(script_content.encode("utf-8")).decode("utf-8")
    remote_cmd = f"echo {encoded_script} | base64 -d > /tmp/{script_name}"

    node = await _get_node_with_creds(nid, nodes)
    results, err = await session_manager.run(nid, node, [remote_cmd])
    if err:
        raise HTTPException(500, f"Install failed: {err}")

    return {
        "status": "success",
        "message": f"{AVAILABLE_AGENTS[agent_id]['name']} installed successfully.",
    }


@router.post("/nodes/{nid}/agents/{agent_id}/start")
async def api_start_agent(
    nid: str, agent_id: str, user: dict = Depends(require_non_student)
):
    if agent_id not in AVAILABLE_AGENTS:
        raise HTTPException(404, "Unknown agent type")

    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    script_name = AVAILABLE_AGENTS[agent_id]["script"]
    remote_cmd = f"nohup python3 /tmp/{script_name} > /dev/null 2>&1 &"

    node = await _get_node_with_creds(nid, nodes)
    results, err = await session_manager.run(nid, node, [remote_cmd])
    if err:
        raise HTTPException(500, f"Failed to start agent: {err}")

    return {
        "status": "success",
        "message": f"{AVAILABLE_AGENTS[agent_id]['name']} started.",
    }


@router.post("/nodes/{nid}/agents/{agent_id}/stop")
async def api_stop_agent(
    nid: str, agent_id: str, user: dict = Depends(require_non_student)
):
    if agent_id not in AVAILABLE_AGENTS:
        raise HTTPException(404, "Unknown agent type")

    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    script_name = AVAILABLE_AGENTS[agent_id]["script"]
    remote_cmd = f"pkill -f {script_name}"

    node = await _get_node_with_creds(nid, nodes)
    results, err = await session_manager.run(nid, node, [remote_cmd])
    if err:
        raise HTTPException(500, f"Failed to stop agent: {err}")

    return {
        "status": "success",
        "message": f"{AVAILABLE_AGENTS[agent_id]['name']} stopped.",
    }


@router.delete("/nodes/{nid}/agents/{agent_id}")
async def api_remove_agent(
    nid: str, agent_id: str, user: dict = Depends(require_non_student)
):
    if agent_id not in AVAILABLE_AGENTS:
        raise HTTPException(404, "Unknown agent type")

    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    script_name = AVAILABLE_AGENTS[agent_id]["script"]
    log_file = AVAILABLE_AGENTS[agent_id]["log_file"]
    remote_cmd = f"pkill -f {script_name} ; rm -f /tmp/{script_name} ; rm -f {log_file}"

    node = await _get_node_with_creds(nid, nodes)
    results, err = await session_manager.run(nid, node, [remote_cmd])
    if err:
        raise HTTPException(500, f"Failed to remove agent: {err}")

    return {
        "status": "success",
        "message": f"{AVAILABLE_AGENTS[agent_id]['name']} removed.",
    }


@router.get("/nodes/{nid}/agents/{agent_id}/fetch")
async def api_fetch_agent_data(
    nid: str, agent_id: str, user: dict = Depends(get_current_user)
):
    if agent_id not in AVAILABLE_AGENTS:
        raise HTTPException(404, "Unknown agent type")

    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    log_file = AVAILABLE_AGENTS[agent_id]["log_file"]
    remote_cmd = f"cat {log_file} 2>/dev/null || echo ''"

    node = await _get_node_with_creds(nid, nodes)
    results, err = await session_manager.run(nid, node, [remote_cmd])
    if err:
        raise HTTPException(500, f"Failed to fetch agent data: {err}")

    output = results[0].get("output", "") if results else ""
    return {"status": "success", "data": output}


@router.post("/nodes/{nid}/agents/attack/vmware")
async def api_vmware_recon(nid: str, payload: dict, user: dict = Depends(require_non_student)):
    target_ip = payload.get("target")
    if not target_ip:
        raise HTTPException(400, "Target IP required")
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")
    node = await _get_node_with_creds(nid, nodes)
    script_path = Path(__file__).parent.parent / "scripts" / "vmware_recon.py"
    script_content = script_path.read_text()
    encoded_script = base64.b64encode(script_content.encode()).decode()
    remote_path = "/tmp/netrunner-vmware.py"
    cmd_upload = (
        f"echo {encoded_script} | base64 -d > {remote_path} && chmod +x {remote_path}"
    )
    cmd_run = f"nohup python3 {remote_path} --target {target_ip} > /dev/null 2>&1 &"
    await session_manager.run(nid, node, [cmd_upload, cmd_run])
    return {
        "status": "success",
        "message": f"VMware recon launched against {target_ip}",
    }


@router.post("/nodes/{nid}/agents/attack/docker")
async def api_docker_recon(nid: str, payload: dict, user: dict = Depends(require_non_student)):
    target_ip = payload.get("target")
    if not target_ip:
        raise HTTPException(400, "Target IP required")
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")
    node = await _get_node_with_creds(nid, nodes)
    script_path = Path(__file__).parent.parent / "scripts" / "docker_recon.py"
    script_content = script_path.read_text()
    encoded_script = base64.b64encode(script_content.encode()).decode()
    remote_path = "/tmp/netrunner-docker.py"
    cmd_upload = (
        f"echo {encoded_script} | base64 -d > {remote_path} && chmod +x {remote_path}"
    )
    cmd_run = f"nohup python3 {remote_path} --target {target_ip} > /dev/null 2>&1 &"
    await session_manager.run(nid, node, [cmd_upload, cmd_run])
    return {
        "status": "success",
        "message": f"Docker recon launched against {target_ip}",
    }
