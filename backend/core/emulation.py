import asyncio
from datetime import datetime
from .session import session_manager
from .vault import load_credentials
from .soar import soar_engine

async def execute_emulation_payload(
    nid: str,
    node: dict,
    payload_script: str,
    log_desc: str,
    target_ip: str,
    script_name: str = "rt_payload.py",
    background: bool = False
) -> dict:
    """Executes a red team or chaos payload script on a remote node via SSH."""
    
    cmds = [
        f"cat << 'EOFRED' > /tmp/{script_name}\n{payload_script}\nEOFRED",
        f"python3 /tmp/{script_name}{' > /dev/null 2>&1 &' if background else ''}",
        f"rm -f /tmp/{script_name}"
    ]
    
    write_success = False
    output_text = "Emulation mode fallback executed (No active SSH session)."
    
    if nid in session_manager.active_ids():
        try:
            node_ssh = dict(node)
            username, password = await load_credentials(nid)
            node_ssh["username"] = username
            node_ssh["password"] = password
            
            results, err = await session_manager.run(nid, node_ssh, cmds)
            if not err and results:
                write_success = True
                if len(results) >= 2:
                    output_text = results[1].stdout or results[1].stderr or "Payload executed successfully (no output)."
                else:
                    output_text = "Payload executed."
        except Exception as e:
            output_text = f"Execution failed: {str(e)}"
            
    now = datetime.now()
    log_msg = {
        "timestamp": now.isoformat(),
        "message": f"[RED TEAM / CHAOS] Deployed {log_desc} on node {node.get('name', nid)}",
        "ts": now.strftime("%H:%M:%S"),
        "msg": f"[RED TEAM / CHAOS] Deployed {log_desc} on node {node.get('name', nid)}"
    }
    
    soar_engine.action_logs.insert(0, log_msg)
    if len(soar_engine.action_logs) > 50:
        soar_engine.action_logs.pop()
        
    return {
        "status": "success",
        "message": output_text,
        "real_file_write": write_success
    }

async def execute_manual_attack(
    nid: str,
    node: dict,
    ssh_cmd: str,
    alert_type: str,
    log_detail: str,
    attacker_ip: str,
    target_ip: str
) -> bool:
    """Executes a manual attack command and logs it to SOAR."""
    write_success = False
    if ssh_cmd and node.get("threat_monitoring") and nid in session_manager.active_ids():
        try:
            node_ssh = dict(node)
            username, password = await load_credentials(nid)
            node_ssh["username"] = username
            node_ssh["password"] = password
            
            results, err = await session_manager.run(nid, node_ssh, [ssh_cmd])
            if not err and results:
                write_success = True
        except Exception as e:
            pass

    now = datetime.now()
    log_msg = {
        "timestamp": now.isoformat(),
        "message": f"[RED TEAM MANUAL STRIKE] Launched {log_detail} from {attacker_ip} against {node.get('name', nid)} ({target_ip})",
        "ts": now.strftime("%H:%M:%S"),
        "msg": f"[RED TEAM MANUAL STRIKE] Launched {log_detail} from {attacker_ip} against {node.get('name', nid)} ({target_ip})"
    }
    soar_engine.action_logs.insert(0, log_msg)
    if len(soar_engine.action_logs) > 50:
        soar_engine.action_logs.pop()
        
    return write_success
