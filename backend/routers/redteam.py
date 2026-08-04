from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from .auth import require_non_student
import asyncio
from datetime import datetime

from ..core.db import load_nodes_db
from ..core.emulation import execute_emulation_payload
from ..generators.redteam import RedTeamGenerator

router = APIRouter()


class RedTeamDeployRequest(BaseModel):
    node_id: str
    tool_name: str
    target_ip: str = ""
    target_path: str = ""
    port: int = 8080


@router.post("/redteam/deploy")
async def api_redteam_deploy(req: RedTeamDeployRequest, user: dict = Depends(require_non_student)):
    nodes = await load_nodes_db()
    if req.node_id not in nodes:
        raise HTTPException(404, "Node not found")

    node = nodes[req.node_id]

    # 1. Determine which payload to build
    payload_script = ""
    log_desc = ""

    if req.tool_name == "scapy":
        if not req.target_ip:
            req.target_ip = "127.0.0.1"
        payload_script = RedTeamGenerator.generate_dns_spoof_payload(
            target_domain="example.com", spoofed_ip=req.target_ip
        )
        log_desc = f"DNS Spoofing (Scapy) -> {req.target_ip}"

    elif req.tool_name == "impacket":
        if not req.target_ip:
            req.target_ip = "127.0.0.1"
        payload_script = RedTeamGenerator.generate_smb_relay_script(
            target_ip=req.target_ip
        )
        log_desc = f"SMB Relay (Impacket) -> {req.target_ip}"

    elif req.tool_name == "volatility":
        payload_script = RedTeamGenerator.generate_memory_dump_script()
        log_desc = "Memory Dump (Volatility3)"

    elif req.tool_name == "yara":
        if not req.target_path:
            req.target_path = "/tmp"
        payload_script = RedTeamGenerator.generate_yara_scanner(
            target_path=req.target_path
        )
        log_desc = f"Malware Scan (YARA) -> {req.target_path}"

    elif req.tool_name == "mitmproxy":
        payload_script = RedTeamGenerator.generate_mitmproxy_script(port=req.port)
        log_desc = f"Mitmproxy (Port {req.port})"

    elif req.tool_name == "shodan":
        # Usually runs locally on the backend, but we can run it on the node or locally.
        # Running on the node gives perspective from that node's egress IP.
        if not req.target_ip:
            req.target_ip = node.get("host", "127.0.0.1")
        payload_script = RedTeamGenerator.generate_shodan_query(target_ip=req.target_ip)
        log_desc = f"OSINT Recon (Shodan) -> {req.target_ip}"

    else:
        raise HTTPException(400, "Unknown Red Team tool")

    return await execute_emulation_payload(
        nid=req.node_id,
        node=node,
        payload_script=payload_script,
        log_desc=log_desc,
        target_ip=req.target_ip,
        script_name="rt_payload.py",
        background=False,
    )
