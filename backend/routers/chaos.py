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
        
        # Simulate a noisy scan or CPU spike
        cmds = [
            "echo '[CHAOS MONKEY] Triggering simulated anomaly!' | logger",
            "nmap -F 127.0.0.1 > /dev/null 2>&1 &"
        ]
        from ..core.soar import soar_engine
        from datetime import datetime
        now = datetime.now()
        try:
            results, err = await session_manager.run(nid, node, cmds)
            if err:
                print(f"[Chaos] Node {nid} connection was closed intentionally or failed: {err}")
                continue
                
            log_msg = {
                "timestamp": now.isoformat(),
                "message": f"[RED TEAM CHAOS] Unleashed Port Scan (Nmap) on node {node.get('name', nid)} ({node.get('host')})",
                "ts": now.strftime("%H:%M:%S"),
                "msg": f"[RED TEAM CHAOS] Unleashed Port Scan (Nmap) on node {node.get('name', nid)} ({node.get('host')})"
            }
            
            # Immediately trigger an active response from AI Autopilot (Blue Team) if it is online
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
                    "ip": node.get("host"),
                    "city": "Internal Network Target",
                    "lat": 35.6762,
                    "lng": 139.6503
                },
                "type": "Port Scan (Nmap)",
                "severity": "critical"
            }
            asyncio.create_task(soar_engine.process_event(simulated_event))
            soar_engine.action_logs.insert(0, log_msg)
            if len(soar_engine.action_logs) > 50:
                soar_engine.action_logs.pop()
            
        except Exception as e:
            print(f"[Chaos] Error running chaos on {nid}: {e}")
            log_msg = {
                "timestamp": now.isoformat(),
                "message": f"[RED TEAM CHAOS] Scan probe failed on node {node.get('name', nid)} ({node.get('host')}): {str(e)}",
                "ts": now.strftime("%H:%M:%S"),
                "msg": f"[RED TEAM CHAOS] Scan probe failed on node {node.get('name', nid)} ({node.get('host')}): {str(e)}"
            }
            soar_engine.action_logs.insert(0, log_msg)
            if len(soar_engine.action_logs) > 50:
                soar_engine.action_logs.pop()

from pydantic import BaseModel
from fastapi import HTTPException
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

    # 2. Try to perform high-fidelity remote file append if node has active session & monitoring is on
    write_success = False
    if ssh_cmd and node.get("threat_monitoring") and req.node_id in session_manager.active_ids():
        try:
            node_ssh = dict(node)
            username, password = await load_credentials(req.node_id)
            node_ssh["username"] = username
            node_ssh["password"] = password
            
            results, err = await session_manager.run(req.node_id, node_ssh, [ssh_cmd])
            if not err and results:
                write_success = True
                print(f"[Attack Emulation] Successfully appended real log on remote node {req.node_id}")
        except Exception as e:
            print(f"[Attack Emulation] Remote log append failed or was skipped: {e}")

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
    
    # Log in Red Team Activity feed
    from ..core.soar import soar_engine
    log_msg = {
        "timestamp": now.isoformat(),
        "message": f"[RED TEAM MANUAL STRIKE] Launched {log_detail} from {req.attacker_ip} against {node_name} ({target_ip})",
        "ts": now.strftime("%H:%M:%S"),
        "msg": f"[RED TEAM MANUAL STRIKE] Launched {log_detail} from {req.attacker_ip} against {node_name} ({target_ip})"
    }
    soar_engine.action_logs.insert(0, log_msg)
    if len(soar_engine.action_logs) > 50:
        soar_engine.action_logs.pop()
        
    return {
        "status": "success",
        "message": f"Successfully emulated manual strike: {log_detail}!",
        "real_file_write": write_success
    }
