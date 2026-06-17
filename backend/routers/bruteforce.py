from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict
import os
import aiofiles
import asyncio
import base64
import json
import re
import shlex
import ipaddress
from pathlib import Path
from ..core.session import session_manager
from ..core.vault import store_credentials
from .nodes import _get_node_with_creds, load_nodes

router = APIRouter(tags=["bruteforce"])

import time
DATA_DIR = Path("data")
WORDLISTS_DIR = DATA_DIR / "wordlists"
WORDLISTS_DIR.mkdir(parents=True, exist_ok=True)
SCRIPTS_DIR = Path("backend/scripts")


def _validate_host(host: str) -> bool:
    """Validate that host is a valid IP address or hostname (no shell metacharacters)."""
    # Try IP address first
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass
    # Hostname: alphanumeric, dots, hyphens, no shell metacharacters
    if not re.match(r'^[a-zA-Z0-9.-]+$', host):
        return False
    # Must not start/end with dot or hyphen
    if host.startswith('.') or host.endswith('.') or host.startswith('-') or host.endswith('-'):
        return False
    return True


def _validate_filename(filename: str) -> bool:
    """Validate filename is safe (alphanumeric, dots, hyphens, underscores only)."""
    if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        return False
    # Prevent path traversal
    if '..' in filename or filename.startswith('/') or filename.startswith('.'):
        return False
    return True


def _validate_service(service: str) -> bool:
    """Validate service name (alphanumeric, hyphens, underscores only)."""
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', service))


def _shell_quote(value: str) -> str:
    """Shell-quote a value for safe interpolation."""
    return shlex.quote(value)

# Keep track of running attacks
# format: { node_id: { "status": "running" | "success" | "failed", "message": "...", "service": "...", "task": Task } }
active_attacks: Dict[str, Dict] = {}

@router.post("/bruteforce/wordlists")
async def upload_wordlist(file: UploadFile = File(...)):
    if not file.filename.endswith(".txt"):
        raise HTTPException(400, "Only .txt wordlists are supported")
        
    file_path = WORDLISTS_DIR / file.filename
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
        
    return {"status": "ok", "filename": file.filename}

@router.get("/bruteforce/wordlists")
async def list_wordlists() -> List[str]:
    files = []
    for f in WORDLISTS_DIR.glob("*.txt"):
        files.append(f.name)
    return files

async def _run_attack_bg(nid: str, node: dict, service: str, payload: dict):
    # Upload the script and wordlist, then run it via the session manager
    script_content = (SCRIPTS_DIR / "bruteforcer.py").read_text()
    encoded_script = base64.b64encode(script_content.encode()).decode()
    remote_script = "/tmp/netrunner-bruteforcer.py"

    # Validate target_ip from node (prevent command injection)
    target_ip = node["host"]
    if not _validate_host(target_ip):
        active_attacks[nid] = {"status": "failed", "message": f"Invalid target host: {target_ip}"}
        return

    # Validate service name
    if not _validate_service(service):
        active_attacks[nid] = {"status": "failed", "message": f"Invalid service name: {service}"}
        return

    # Safe upload command (base64 encoded, no user input)
    cmd_upload = f"echo {encoded_script} | base64 -d > {_shell_quote(remote_script)} && chmod +x {_shell_quote(remote_script)}"

    attack_mode = payload.get("attack_mode", "wordlist")

    try:
        session = session_manager.get_session(nid)
        if not session:
            success, _ = await session_manager.open(nid, node, auto=True)
            if not success:
                active_attacks[nid] = {"status": "failed", "message": "Could not connect to node"}
                return
            session = session_manager.get_session(nid)

        if not hasattr(session, 'run_command'):
            active_attacks[nid] = {"status": "failed", "message": "Session does not support running commands"}
            return

        session.run_command(cmd_upload)

        if attack_mode == "wordlist":
            wordlist_name = payload.get("wordlist")
            if not wordlist_name or not _validate_filename(wordlist_name):
                active_attacks[nid] = {"status": "failed", "message": f"Invalid wordlist filename: {wordlist_name}"}
                return
            wordlist_path = WORDLISTS_DIR / wordlist_name
            if not wordlist_path.exists():
                active_attacks[nid] = {"status": "failed", "message": f"Wordlist {wordlist_name} not found"}
                return

            wordlist_content = wordlist_path.read_text(errors='ignore')
            encoded_wordlist = base64.b64encode(wordlist_content.encode()).decode()
            remote_wordlist = f"/tmp/{wordlist_name}"
            # Validate remote path is safe
            if not _validate_filename(wordlist_name):
                active_attacks[nid] = {"status": "failed", "message": f"Invalid wordlist filename: {wordlist_name}"}
                return
            cmd_upload_wl = f"echo {encoded_wordlist} | base64 -d > {_shell_quote(remote_wordlist)}"
            session.run_command(cmd_upload_wl)
            cmd_run = f"python3 {_shell_quote(remote_script)} --target {_shell_quote(target_ip)} --service {_shell_quote(service)} --wordlist {_shell_quote(remote_wordlist)}"
        else:
            algo_user = payload.get("algo_user", "root")
            algo_charset = payload.get("algo_charset", "aA1")
            algo_min = payload.get("algo_min", 1)
            algo_max = payload.get("algo_max", 4)

            # Validate algo parameters
            if not _validate_filename(algo_user):
                active_attacks[nid] = {"status": "failed", "message": f"Invalid algo_user: {algo_user}"}
                return
            if not re.match(r'^[a-zA-Z0-9]+$', str(algo_charset)):
                active_attacks[nid] = {"status": "failed", "message": f"Invalid algo_charset: {algo_charset}"}
                return
            if not isinstance(algo_min, int) or not isinstance(algo_max, int) or algo_min < 1 or algo_max > 10 or algo_min > algo_max:
                active_attacks[nid] = {"status": "failed", "message": f"Invalid algo_min/algo_max: {algo_min}/{algo_max}"}
                return

            cmd_run = f"python3 {_shell_quote(remote_script)} --target {_shell_quote(target_ip)} --service {_shell_quote(service)} --algo --algo-user {_shell_quote(algo_user)} --algo-charset {_shell_quote(algo_charset)} --algo-min {algo_min} --algo-max {algo_max}"

        # Launch in background
        log_file = f"/tmp/bruteforce_{nid}.log"
        # Validate nid is safe (alphanumeric only)
        if not re.match(r'^[a-zA-Z0-9_-]+$', nid):
            active_attacks[nid] = {"status": "failed", "message": f"Invalid node ID: {nid}"}
            return
        session.run_command(f"rm -f {_shell_quote(log_file)}")
        cmd_bg = f"nohup {cmd_run} > {_shell_quote(log_file)} 2>&1 & echo $!"
        pid = session.run_command(cmd_bg).strip()
        
        # Poll log
        active_attacks[nid]["progress"] = 0
        active_attacks[nid]["total"] = 0
        active_attacks[nid]["pid"] = pid
        
        found_creds = None
        last_msg = ""
        
        import asyncio
        from ..core.db import save_threat_event_db
        from ..core.cti import cti_queue
        
        # Emit an initial event that the attack has started
        start_event_id = f"evt_{int(time.time()*1000)}"
        start_event = {
            "id": start_event_id,
            "timestamp": time.time(),
            "source": {"ip": "127.0.0.1", "city": "Netrunner Console", "lat": 55.67, "lng": 12.56},
            "target": {"ip": target_ip, "city": node.get("name", "Target"), "lat": 55.68, "lng": 12.57},
            "type": f"Brute Force Attack Started ({service.upper()})",
            "severity": "high",
            "targeted": True,
            "node_id": nid
        }
        await cti_queue.put(start_event)
        await save_threat_event_db({
            "id": start_event_id,
            "timestamp": time.time(),
            "node_id": nid,
            "source_ip": "127.0.0.1",
            "target_ip": target_ip,
            "type": start_event["type"],
            "severity": "high"
        })
        
        while active_attacks.get(nid, {}).get("status") in ("running", "paused"):
            await asyncio.sleep(2)
            if active_attacks[nid]["status"] == "paused":
                continue
            log_out = session.run_command(f"tail -n 20 {_shell_quote(log_file)} 2>/dev/null")

            # Check for progress
            prog_matches = re.findall(r"\[PROGRESS\] (\d+)/(\d+)", log_out)
            if prog_matches:
                active_attacks[nid]["progress"] = int(prog_matches[-1][0])
                active_attacks[nid]["total"] = int(prog_matches[-1][1])

            # Check for success or error
            for line in log_out.split('\n'):
                line = line.strip()
                if line.startswith("{"):
                    try:
                        data = json.loads(line)
                        if "success" in data:
                            is_success = data.get("success")

                            # Emit event for completion/success
                            event_id = f"evt_{int(time.time()*1000)}"
                            event_type = f"Brute Force ({service.upper()}) " + ("SUCCESS" if is_success else "FAILED")
                            severity = "critical" if is_success else "medium"

                            event = {
                                "id": event_id,
                                "timestamp": data.get("timestamp", time.time()),
                                "source": {"ip": "127.0.0.1", "city": "Netrunner Console", "lat": 55.67, "lng": 12.56},
                                "target": {"ip": target_ip, "city": node.get("name", "Target"), "lat": 55.68, "lng": 12.57},
                                "type": event_type,
                                "severity": severity,
                                "targeted": True,
                                "node_id": nid
                            }
                            await cti_queue.put(event)
                            await save_threat_event_db({
                                "id": event_id,
                                "timestamp": data.get("timestamp", time.time()),
                                "node_id": nid,
                                "source_ip": "127.0.0.1",
                                "target_ip": target_ip,
                                "type": event_type,
                                "severity": severity
                            })

                            if is_success:
                                found_creds = {"username": data.get("username"), "password": data.get("password")}
                                break
                            elif data.get("error"):
                                last_msg = data.get("error")
                    except: pass

            if found_creds or "exhausted" in log_out or "failed" in log_out:
                break

            # Check if process is still alive - validate pid is numeric
            if pid and pid.isdigit():
                is_alive = session.run_command(f"ps -p {pid} >/dev/null 2>&1 && echo YES || echo NO")
                if "NO" in is_alive:
                    break
            else:
                break
    
        if active_attacks.get(nid, {}).get("status") == "cancelled":
            return
            
        if found_creds:
            await store_credentials(nid, found_creds["username"], found_creds["password"])
            active_attacks[nid] = {
                "status": "success",
                "message": f"Found valid credentials! User: {found_creds['username']}",
                "credentials": found_creds
            }
        else:
            active_attacks[nid] = {
                "status": "failed",
                "message": last_msg or "Dictionary exhausted without success."
            }
            
    except Exception as e:
        active_attacks[nid] = {"status": "failed", "message": f"Internal error: {e}"}

@router.post("/bruteforce/attack")
async def launch_attack(payload: dict):
    nid = payload.get("node_id")
    service = payload.get("service")
    wordlist = payload.get("wordlist")
    
    if not nid or not service:
        raise HTTPException(400, "Missing required fields")
        
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")
        
    node = await _get_node_with_creds(nid, nodes)
    
    # Start the attack in the background
    active_attacks[nid] = {
        "status": "running", 
        "service": service, 
        "wordlist": wordlist if payload.get("attack_mode") == "wordlist" else f"ALGO ({payload.get('algo_min')}-{payload.get('algo_max')} chars)", 
        "message": "Attack initiated..."
    }
    
    task = asyncio.create_task(_run_attack_bg(nid, node, service, payload))
    # We could store the task to allow cancellation later
    
    return {"status": "ok", "message": "Attack started in background"}

@router.get("/bruteforce/status")
async def get_attack_status():
    # Return the status of all active/recent attacks
    return active_attacks

@router.post("/bruteforce/stop")
async def stop_attack(payload: dict):
    nid = payload.get("node_id")
    if not nid or nid not in active_attacks:
        return {"status": "ok", "message": "No active attack found"}
    
    if active_attacks[nid].get("status") not in ("running", "paused"):
        return {"status": "ok", "message": "Attack is not active"}
        
    pid = active_attacks[nid].get("pid")
    session = session_manager.get_session(nid)
    
    active_attacks[nid]["status"] = "cancelled"
    active_attacks[nid]["message"] = "Attack stopped by user."
    
    if session and pid and pid.isdigit():
        try:
            # Kill the python wrapper
            session.run_command(f"kill -9 {_shell_quote(pid)} 2>/dev/null")
            # Try to kill any hydra docker containers running on the target node
            session.run_command("docker ps -q --filter ancestor=secsi/hydra | xargs -r docker stop 2>/dev/null")
        except:
            pass
            
    return {"status": "ok", "message": "Attack stopped"}

@router.post("/bruteforce/pause")
async def pause_attack(payload: dict):
    nid = payload.get("node_id")
    if not nid or nid not in active_attacks:
        return {"status": "ok", "message": "No active attack found"}
    if active_attacks[nid].get("status") != "running":
        return {"status": "ok", "message": "Attack is not running"}
    
    pid = active_attacks[nid].get("pid")
    session = session_manager.get_session(nid)
    active_attacks[nid]["status"] = "paused"
    active_attacks[nid]["message"] = "Attack paused."
    
    if session and pid and pid.isdigit():
        try:
            session.run_command(f"kill -STOP {_shell_quote(pid)} 2>/dev/null")
            session.run_command("docker ps -q --filter ancestor=secsi/hydra | xargs -r docker pause 2>/dev/null")
        except:
            pass
    return {"status": "ok", "message": "Attack paused"}

@router.post("/bruteforce/resume")
async def resume_attack(payload: dict):
    nid = payload.get("node_id")
    if not nid or nid not in active_attacks:
        return {"status": "ok", "message": "No active attack found"}
    if active_attacks[nid].get("status") != "paused":
        return {"status": "ok", "message": "Attack is not paused"}
    
    pid = active_attacks[nid].get("pid")
    session = session_manager.get_session(nid)
    active_attacks[nid]["status"] = "running"
    active_attacks[nid]["message"] = "Attack running..."
    
    if session and pid and pid.isdigit():
        try:
            session.run_command(f"kill -CONT {_shell_quote(pid)} 2>/dev/null")
            session.run_command("docker ps -q --filter ancestor=secsi/hydra | xargs -r docker unpause 2>/dev/null")
        except:
            pass
    return {"status": "ok", "message": "Attack resumed"}
