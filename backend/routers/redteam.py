from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
import asyncio
from datetime import datetime

from ..core.db import load_nodes_db
from ..core.session import session_manager
from ..core.vault import load_credentials
from ..core.soar import soar_engine
from ..generators.redteam import RedTeamGenerator

router = APIRouter()

class RedTeamDeployRequest(BaseModel):
    node_id: str
    tool_name: str
    target_ip: str = ""
    target_path: str = ""
    port: int = 8080

@router.post("/redteam/deploy")
async def api_redteam_deploy(req: RedTeamDeployRequest):
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
        payload_script = RedTeamGenerator.generate_dns_spoof_payload(target_domain="example.com", spoofed_ip=req.target_ip)
        log_desc = f"DNS Spoofing (Scapy) -> {req.target_ip}"
        
    elif req.tool_name == "impacket":
        if not req.target_ip:
            req.target_ip = "127.0.0.1"
        payload_script = RedTeamGenerator.generate_smb_relay_script(target_ip=req.target_ip)
        log_desc = f"SMB Relay (Impacket) -> {req.target_ip}"
        
    elif req.tool_name == "volatility":
        payload_script = RedTeamGenerator.generate_memory_dump_script()
        log_desc = "Memory Dump (Volatility3)"
        
    elif req.tool_name == "yara":
        if not req.target_path:
            req.target_path = "/tmp"
        payload_script = RedTeamGenerator.generate_yara_scanner(target_path=req.target_path)
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

    # 2. Run the payload on the node
    # Note: For long-running scripts like mitmproxy or smbserver, we normally background them.
    # Here we write it to a file and execute it, or pass it directly.
    # To avoid hanging the UI, we run it in background and pipe output if it's a daemon,
    # or just run it inline if it returns quickly (like YARA or Shodan).
    
    cmds = [
        f"cat << 'EOFRED' > /tmp/rt_payload.py\n{payload_script}\nEOFRED",
        "python3 /tmp/rt_payload.py",
        "rm -f /tmp/rt_payload.py"
    ]
    
    write_success = False
    output_text = "Emulation mode fallback executed (No active SSH session)."
    
    if req.node_id in session_manager.active_ids():
        try:
            node_ssh = dict(node)
            username, password = await load_credentials(req.node_id)
            node_ssh["username"] = username
            node_ssh["password"] = password
            
            results, err = await session_manager.run(req.node_id, node_ssh, cmds)
            if not err and results:
                write_success = True
                # Get output of python script (the second command)
                if len(results) >= 2:
                    output_text = results[1].stdout or results[1].stderr or "Payload executed successfully (no output)."
                else:
                    output_text = "Payload executed."
        except Exception as e:
            output_text = f"Execution failed: {str(e)}"
    
    # 3. Log into SOAR Activity Feed
    now = datetime.now()
    log_msg = {
        "timestamp": now.isoformat(),
        "message": f"[RED TEAM ARSENAL] Deployed {log_desc} on node {node.get('name', req.node_id)}",
        "ts": now.strftime("%H:%M:%S"),
        "msg": f"[RED TEAM ARSENAL] Deployed {log_desc} on node {node.get('name', req.node_id)}"
    }
    soar_engine.action_logs.insert(0, log_msg)
    if len(soar_engine.action_logs) > 50:
        soar_engine.action_logs.pop()
        
    return {
        "status": "success",
        "message": output_text,
        "real_file_write": write_success
    }
