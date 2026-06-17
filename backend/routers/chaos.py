import asyncio
import random
from fastapi import APIRouter
from ..core.state import global_state
from ..core.db import load_nodes_db
from ..core.session import session_manager
from ..core.vault import load_credentials

router = APIRouter()
_chaos_task = None

async def chaos_loop():
    while True:
        await asyncio.sleep(20)
        if not global_state.chaos:
            continue
        
        active_ids = session_manager.active_ids()
        if not active_ids:
            continue
            
        nodes = await load_nodes_db()
        if not nodes:
            continue
            
        nid = random.choice(active_ids)
        node = nodes.get(nid)
        if not node:
            continue
            
        username, password = await load_credentials(nid)
        node["username"] = username
        node["password"] = password
        
        from ..generators.redteam import RedTeamGenerator
        from ..core.soar import soar_engine
        from datetime import datetime
        
        # Pick a random real attack payload to emulate
        attack_types = ["scapy", "yara", "shodan"]
        attack_choice = random.choice(attack_types)
        payload_script = ""
        log_desc = ""
        target_ip = node.get("host", "127.0.0.1")
        
        if attack_choice == "scapy":
            payload_script = RedTeamGenerator.generate_dns_spoof_payload(target_domain="netrunner.corp", spoofed_ip="10.99.99.99")
            log_desc = "DNS Spoofing Payload (Scapy)"
        elif attack_choice == "yara":
            payload_script = RedTeamGenerator.generate_yara_scanner(target_path="/tmp")
            log_desc = "Malware File Scanner (YARA)"
        elif attack_choice == "shodan":
            payload_script = RedTeamGenerator.generate_shodan_query(target_ip=target_ip)
            log_desc = f"OSINT Footprinting (Shodan) against {target_ip}"
            
        from ..core.emulation import execute_emulation_payload
        
        async def execute_chaos_wrapper(nid, node_data, script, desc, target):
            await execute_emulation_payload(
                nid=nid,
                node=node_data,
                payload_script=script,
                log_desc=desc,
                target_ip=target,
                script_name="chaos_rt.py",
                background=True
            )
            
            # Immediately trigger an active response from AI Autopilot (Blue Team)
            simulated_event = {
                "id": f"evt_chaos_{int(now.timestamp())}_{random.randint(1000, 9999)}",
                "timestamp": now.timestamp(),
                "source": {
                    "ip": "10.99.99.99",
                    "city": "Threat Emulation Source",
                    "lat": 37.7749,
                    "lng": -122.4194
                },
                "target": {
                    "ip": node_data.get("host"),
                    "city": "Internal Network Target",
                    "lat": 35.6762,
                    "lng": 139.6503
                },
                "type": desc,
                "severity": "critical"
            }
            await soar_engine.process_event(simulated_event)
                
        asyncio.create_task(execute_chaos_wrapper(nid, node, payload_script, log_desc, target_ip))

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from ..core.cti import cti_queue, get_ip_geolocation

class ManualAttackRequest(BaseModel):
    node_id: str
    attack_type: str  # ssh, sqli, xss, lfi, ufw
    attacker_ip: str = "203.0.113.5"
    username: str = "admin"
    port: int = 80
    path_query: str = "/"

@router.post("/chaos/attack")
async def api_trigger_manual_attack(req: ManualAttackRequest):
    nodes = await load_nodes_db()
    if req.node_id not in nodes:
        raise HTTPException(404, "Node not found")
        
    node = nodes[req.node_id]
    target_ip = node.get("host", "127.0.0.1")
    node_name = node.get("name", "Target Node")
    
    # 1. Resolve visual/alert descriptions based on attack type
    alert_type = "Generic Cyberthreat"
    severity = "medium"
    log_detail = ""
    ssh_cmd = None
    
    if req.attack_type == "ssh":
        alert_type = f"SSH Brute Force ({req.username})"
        severity = "high"
        log_detail = f"SSH brute-force attempt as user '{req.username}'"
        ssh_cmd = f"echo 'May 21 22:38:03 localhost sshd[12345]: Failed password for invalid user {req.username} from {req.attacker_ip} port 54321 ssh2' | sudo tee -a /var/log/auth.log || echo 'Auth log write failed'"
        
    elif req.attack_type == "sqli":
        alert_type = "SQL Injection Attempt"
        severity = "high"
        log_detail = f"SQL Injection probe on path {req.path_query}"
        ssh_cmd = f"echo '{req.attacker_ip} - - [21/May/2026:22:38:03 +0200] \"GET {req.path_query} HTTP/1.1\" 200 4522 \"-\" \"Mozilla/5.0\"' | sudo tee -a /var/log/nginx/access.log || sudo tee -a /var/log/apache2/access.log || echo 'Web log write failed'"
        
    elif req.attack_type == "xss":
        alert_type = "XSS Attack Attempt"
        severity = "medium"
        log_detail = f"Cross-Site Scripting (XSS) probe on path {req.path_query}"
        ssh_cmd = f"echo '{req.attacker_ip} - - [21/May/2026:22:38:05 +0200] \"GET {req.path_query} HTTP/1.1\" 200 120 \"-\" \"Mozilla/5.0\"' | sudo tee -a /var/log/nginx/access.log || sudo tee -a /var/log/apache2/access.log || echo 'Web log write failed'"
        
    elif req.attack_type == "lfi":
        alert_type = "Path Traversal Attempt"
        severity = "high"
        log_detail = f"Local File Inclusion (LFI) probe on path {req.path_query}"
        ssh_cmd = f"echo '{req.attacker_ip} - - [21/May/2026:22:38:10 +0200] \"GET {req.path_query} HTTP/1.1\" 404 80 \"-\" \"Mozilla/5.0\"' | sudo tee -a /var/log/nginx/access.log || sudo tee -a /var/log/apache2/access.log || echo 'Web log write failed'"
        
    elif req.attack_type == "ufw":
        alert_type = f"Port Scan (UFW Blocked Port {req.port})"
        severity = "medium"
        log_detail = f"Firewall scan probing blocked port {req.port}"
        ssh_cmd = f"echo 'May 21 22:38:03 localhost kernel: [UFW BLOCK] IN=eth0 OUT= MAC=01:02:03:04:05:06 SRC={req.attacker_ip} DST={target_ip} LEN=40 TOS=0x00 PREC=0x00 TTL=64 ID=12345 PROTO=TCP SPT=49201 DPT={req.port} WINDOW=512 RES=0x00 SYN URGP=0' | sudo tee -a /var/log/ufw.log || sudo tee -a /var/log/syslog || echo 'FW log write failed'"

    from ..core.emulation import execute_manual_attack
    
    # 2. Try to perform high-fidelity remote file append if node has active session & monitoring is on
    write_success = await execute_manual_attack(
        nid=req.node_id,
        node=node,
        ssh_cmd=ssh_cmd,
        alert_type=alert_type,
        log_detail=log_detail,
        attacker_ip=req.attacker_ip,
        target_ip=target_ip
    )

    # 3. Create high-fidelity CTI event so that it updates the WebGL Globe instantly!
    attacker_geo = await get_ip_geolocation(req.attacker_ip, default_name="Custom Attacker")
    target_geo = await get_ip_geolocation(target_ip, default_name=node_name)
    
    from datetime import datetime
    now = datetime.now()
    
    event = {
        "id": f"evt_manual_{int(now.timestamp())}_{random.randint(1000, 9999)}",
        "timestamp": now.timestamp(),
        "source": {
            "ip": req.attacker_ip,
            "city": f"{attacker_geo['name']} (IP: {req.attacker_ip})",
            "lat": attacker_geo["lat"] + (random.random() - 0.5) * 1.5,
            "lng": attacker_geo["lng"] + (random.random() - 0.5) * 1.5
        },
        "target": {
            "ip": target_ip,
            "city": f"{node_name} ({target_geo['name']})",
            "lat": target_geo["lat"] + (random.random() - 0.5) * 0.3,
            "lng": target_geo["lng"] + (random.random() - 0.5) * 0.3
        },
        "type": alert_type,
        "severity": severity,
        "targeted": True
    }
    
    # Broadcast to the real-time CTI websocket queue
    await cti_queue.put(event)
        
    return {
        "status": "success",
        "message": f"Successfully emulated manual strike: {log_detail}!",
        "real_file_write": write_success
    }

class ShapingPayload(BaseModel):
    latency_ms: int = 0
    jitter_ms: int = 0
    loss_percent: int = 0

from .auth import require_admin

@router.post("/nodes/{nid}/chaos/shaping", dependencies=[Depends(require_admin)])
async def api_apply_chaos_shaping(nid: str, payload: ShapingPayload):
    nodes = await load_nodes_db()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    node = dict(nodes[nid])
    username, password = await load_credentials(nid)
    node["username"] = username
    node["password"] = password

    # Clear existing rules first (ignore errors if none exist)
    clear_cmd = "sudo tc qdisc del dev eth0 root 2>/dev/null || true"
    
    # Build netem command
    netem_parts = ["sudo tc qdisc add dev eth0 root netem"]
    if payload.latency_ms > 0:
        netem_parts.append(f"delay {payload.latency_ms}ms {payload.jitter_ms}ms distribution normal")
    if payload.loss_percent > 0:
        netem_parts.append(f"loss {payload.loss_percent}%")
        
    if len(netem_parts) == 1:
        # If no values, just clear
        apply_cmd = "echo 'No chaos parameters, cleared rules.'"
    else:
        apply_cmd = " ".join(netem_parts)

    commands = [clear_cmd, apply_cmd]
    res, err = await session_manager.run(nid, node, commands)
    if err:
        raise HTTPException(500, f"Failed to apply Traffic Shaping: {err}")

    return {
        "status": "success",
        "message": f"Traffic shaping applied: Latency {payload.latency_ms}ms, Loss {payload.loss_percent}%"
    }

@router.post("/nodes/{nid}/chaos/shaping/reset", dependencies=[Depends(require_admin)])
async def api_reset_chaos_shaping(nid: str):
    nodes = await load_nodes_db()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    node = dict(nodes[nid])
    username, password = await load_credentials(nid)
    node["username"] = username
    node["password"] = password

    clear_cmd = "sudo tc qdisc del dev eth0 root 2>/dev/null || true"
    res, err = await session_manager.run(nid, node, [clear_cmd])
    if err:
        raise HTTPException(500, f"Failed to reset Traffic Shaping: {err}")

    return {
        "status": "success",
        "message": "Traffic shaping reset to normal. All tc rules removed."
    }
