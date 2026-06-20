from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from ..core.defense import apply_isolation, enforce_zero_trust, release_isolation, block_ip_on_node, unblock_ip_on_node
from ..core.scanner import run_local_nmap
from .auth import require_admin
from ..core.db import load_nodes_db, save_node_db
from ..core.vault import load_credentials
from ..core.session import session_manager
from .nodes import _get_node_with_creds

router = APIRouter()


class BlockIPRequest(BaseModel):
    ip: str

class SOARActionRequest(BaseModel):
    node_id: str
    ip: str = ""

@router.post("/nodes/{nid}/nmap", dependencies=[Depends(require_admin)])
async def api_defense_nmap(nid: str):
    """Executes a vulnerability scan (nmap) on the node."""
    nodes = await load_nodes_db()
    if nid not in nodes:
        raise HTTPException(404, "Node not found.")
    
    node = nodes[nid]
    host = node.get("host")
    if not host:
        raise HTTPException(400, "Node has no IP/Host.")

    result = await run_local_nmap(host)
    if result.startswith("Error") or result.startswith("Nmap Error") or result.startswith("Failed to execute"):
        raise HTTPException(400, result)
    return {"status": "success", "scan_results": result}

@router.post("/nodes/{nid}/isolate", dependencies=[Depends(require_admin)])
async def api_defense_isolate(nid: str):
    """Deploys iptables isolation rules to the node."""
    result = await apply_isolation(nid)
    if result.startswith("Error"):
        raise HTTPException(400, result)
    return {"status": "success", "isolation_log": result}

@router.post("/nodes/{nid}/defense/zero-trust", dependencies=[Depends(require_admin)])
async def api_zero_trust_node(nid: str):
    """Enforces Zero Trust Architecture on the node."""
    result = await enforce_zero_trust(nid)
    if result.startswith("Error"):
        raise HTTPException(400, result)
    return {"status": "success", "message": result}

from fastapi import Request
from ..core.db import load_settings_db

@router.post("/nodes/{nid}/monitoring/install", dependencies=[Depends(require_admin)])
async def api_install_monitoring(nid: str, request: Request):
    """Verifies syslog/journalctl readability and installs the Threat Monitor Go Agent."""
    nodes = await load_nodes_db()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")
        
    node = dict(nodes[nid])
    username, password = await load_credentials(nid)
    node["username"] = username
    node["password"] = password
    
    settings = await load_settings_db()
    token = settings.get("agent_token", "")
    if not token:
        import secrets
        token = secrets.token_hex(16)
        settings["agent_token"] = token
        from ..core.db import save_setting_db
        await save_setting_db("agent_token", token)

    base_url = str(request.base_url).rstrip("/")
    # Auto-correct localhost to the actual network IP if installing on a remote node
    if "localhost" in base_url or "127.0.0.1" in base_url:
        import socket
        lan_ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.255.255.255", 1))
            lan_ip = s.getsockname()[0]
            s.close()
        except Exception:
            pass
        base_url = base_url.replace("localhost", lan_ip).replace("127.0.0.1", lan_ip)

    # Detect architecture and install
    install_script = f"""
    ARCH=$(uname -m)
    if [ "$ARCH" = "x86_64" ]; then
        DL_ARCH="amd64"
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        DL_ARCH="arm64"
    else
        echo "Error: Unsupported architecture $ARCH"
        exit 1
    fi

    echo "Downloading Netrunner Agent ($DL_ARCH) from {base_url}..."
    curl -sL "{base_url}/api/agent/download/$DL_ARCH" -o /usr/local/bin/netrunner-agent || wget -qO /usr/local/bin/netrunner-agent "{base_url}/api/agent/download/$DL_ARCH"
    
    if [ ! -s /usr/local/bin/netrunner-agent ]; then
        echo "Error: Failed to download agent binary. Check network connectivity."
        exit 1
    fi

    chmod +x /usr/local/bin/netrunner-agent

    cat << 'EOF' > /etc/systemd/system/netrunner-agent.service
[Unit]
Description=Netrunner Threat Monitor Agent
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/netrunner-agent --target {base_url} --token {token} --node {nid}
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable netrunner-agent
    systemctl restart netrunner-agent
    echo "Agent successfully installed and started."
    """

    # We need to run this script as root (sudo if necessary)
    # The session_manager.run wraps commands automatically if we need, but let's just pass it.
    # To run a multiline script reliably over SSH via single command execution,
    # we can base64 encode it and pipe to bash.
    import base64
    b64_script = base64.b64encode(install_script.encode()).decode()
    
    pwd = node.get("password", "")
    if pwd:
        escaped_pwd = pwd.replace("'", "'\\''")
        cmd = f"echo '{escaped_pwd}' | sudo -S bash -c 'echo {b64_script} | base64 -d | bash'"
    else:
        cmd = f"echo {b64_script} | base64 -d | sudo bash"
    
    results, err = await session_manager.run(nid, node, [cmd])
    if err:
        raise HTTPException(500, f"Failed to connect to node: {err}")
        
    output = results[0].get("output", "") if results else ""
    if "Error" in output:
        raise HTTPException(400, f"Agent installation failed: {output}")
        
    # Save the updated state
    node_db_format = dict(nodes[nid])
    node_db_format["threat_monitoring"] = True
    await save_node_db(node_db_format)
    
    return {
        "status": "success", 
        "message": "Multi-Vector Threat Monitor Go Agent successfully installed! Active tailing for SSH Brute Force, Web server exploits (SQLi/XSS/LFI), and Firewall port scans is now online."
    }

@router.get("/nodes/{nid}/monitoring/status")
async def api_monitoring_status(nid: str):
    """Checks if the agent is actively running on the target node."""
    nodes = await load_nodes_db()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")
        
    node = await _get_node_with_creds(nid, nodes)
    
    cmd = "systemctl is-active netrunner-agent || pgrep -f netrunner-agent >/dev/null && echo 'active' || echo 'inactive'"
    results, err = await session_manager.run(nid, node, [cmd])
    if err:
        return {"status": "error", "active": nodes[nid].get("threat_monitoring", False)}
        
    output = results[0].get("output", "").strip() if results else ""
    is_active = "active" in output
    
    # Update DB automatically if there's a mismatch
    if nodes[nid].get("threat_monitoring") != is_active:
        node_db_format = dict(nodes[nid])
        node_db_format["threat_monitoring"] = is_active
        from ..core.db import save_node_db
        await save_node_db(node_db_format)
        
    return {"status": "success", "active": is_active}

@router.post("/nodes/{nid}/monitoring/remove", dependencies=[Depends(require_admin)])
async def api_remove_monitoring(nid: str):
    """Uninstalls the Threat Monitor Agent from the node."""
    nodes = await load_nodes_db()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")
        
    node = dict(nodes[nid])
    username, password = await load_credentials(nid)
    node["username"] = username
    node["password"] = password

    remove_script = """
    systemctl stop netrunner-agent || true
    systemctl disable netrunner-agent || true
    rm -f /etc/systemd/system/netrunner-agent.service
    systemctl daemon-reload
    rm -f /usr/local/bin/netrunner-agent
    echo "Agent removed."
    """
    import base64
    b64_script = base64.b64encode(remove_script.encode()).decode()
    cmd = f"echo {b64_script} | base64 -d | sudo bash"

    await session_manager.run(nid, node, [cmd])

    # Save the updated state
    node_db_format = dict(nodes[nid])
    node_db_format["threat_monitoring"] = False
    await save_node_db(node_db_format)
    
    return {
        "status": "success", 
        "message": "Threat Monitor Agent successfully removed. Real-time tailing deactivated."
    }


@router.post("/nodes/{nid}/release", dependencies=[Depends(require_admin)])
async def api_defense_release(nid: str):
    """Releases a node from isolation by flushing iptables rules."""
    result = await release_isolation(nid)
    if result.startswith("Error") or result.startswith("No SSH"):
        raise HTTPException(400, result)
    return {"status": "success", "release_log": result}


@router.post("/nodes/{nid}/block-ip", dependencies=[Depends(require_admin)])
async def api_defense_block_ip(nid: str, req: BlockIPRequest):
    """Blocks a specific IP address on a node via iptables."""
    result = await block_ip_on_node(nid, req.ip)
    if "Failed" in result or "Error" in result:
        raise HTTPException(400, result)
    return {"status": "success", "message": result}


@router.post("/nodes/{nid}/unblock-ip", dependencies=[Depends(require_admin)])
async def api_defense_unblock_ip(nid: str, req: BlockIPRequest):
    """Unblocks a specific IP address on a node via iptables."""
    result = await unblock_ip_on_node(nid, req.ip)
    if "Failed" in result or "Error" in result:
        raise HTTPException(400, result)
    return {"status": "success", "message": result}
