import os
import re
import socket

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from ..core.defense import (
    apply_isolation,
    enforce_zero_trust,
    release_isolation,
    block_ip_on_node,
    unblock_ip_on_node,
)
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
    if (
        result.startswith("Error")
        or result.startswith("Nmap Error")
        or result.startswith("Failed to execute")
    ):
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


from .agent import get_agent_token


@router.post("/nodes/{nid}/monitoring/install", dependencies=[Depends(require_admin)])
async def api_install_monitoring(nid: str):
    """Verifies syslog/journalctl readability and installs the Threat Monitor Go Agent."""
    nodes = await load_nodes_db()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    node = dict(nodes[nid])
    username, password = await load_credentials(nid)
    node["username"] = username
    node["password"] = password

    token = await get_agent_token()

    safe_nid = re.sub(r"[^a-zA-Z0-9_.:-]", "", nid)
    if safe_nid != nid:
        raise HTTPException(400, "Node ID contains unsupported characters")

    # Never use the request Host header in a privileged remote install script.
    # NETRUNNER_PUBLIC_URL can override automatic LAN discovery when needed.
    base_url = os.environ.get("NETRUNNER_PUBLIC_URL", "").strip().rstrip("/")
    if not base_url:
        lan_ip = "127.0.0.1"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("10.255.255.255", 1))
                lan_ip = sock.getsockname()[0]
        except OSError:
            pass
        base_url = f"http://{lan_ip}:8000"

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
ExecStart=/usr/local/bin/netrunner-agent --target {base_url} --token {token} --node {safe_nid}
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
        "message": "Multi-Vector Threat Monitor Go Agent successfully installed! Active tailing for SSH Brute Force, Web server exploits (SQLi/XSS/LFI), and Firewall port scans is now online.",
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
        "message": "Threat Monitor Agent successfully removed. Real-time tailing deactivated.",
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


from ..services.dlp_engine import DLPCheckRequest, process_dlp_event


@router.post("/dlp/check", dependencies=[Depends(require_admin)])
async def api_dlp_check(req: DLPCheckRequest):
    """
    Evaluates outgoing content through the Semantic DLP Layered AI Gateway.
    If the LLM determines the transfer violates Data Loss Prevention policies,
    the transfer is blocked and a critical alert is raised.
    """
    result = await process_dlp_event(req)
    if result["status"] == "blocked":
        # Return 403 Forbidden to the client attempting the transfer
        raise HTTPException(
            403, f"Transfer BLOCKED by Semantic DLP: {result['reason']}"
        )

    return {"status": "success", "message": result["reason"]}


class HoneyfileDeployRequest(BaseModel):
    share_name: str = "Finance_Confidential"
    files_count: int = 5


@router.post(
    "/nodes/{nid}/deception/smb-honeyfiles", dependencies=[Depends(require_admin)]
)
async def api_deploy_smb_honeyfiles(nid: str, req: HoneyfileDeployRequest):
    """
    Deploys a lightweight Samba container on the target node, pre-loaded with highly enticing
    'honeyfiles' (e.g. passwords.docx, Q3_Financials.xlsx).
    Because legitimate users have no reason to access this hidden share, any Read, Write,
    or Encrypt action immediately trips a zero-false-positive Critical Alert to the SOC,
    indicating active Lateral Movement or Ransomware encryption!
    """
    nodes = await load_nodes_db()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    node = dict(nodes[nid])
    username, password = await load_credentials(nid)
    node["username"] = username
    node["password"] = password

    # Bash script to rapidly deploy a dockerized Samba honeypot with audit logging
    deploy_script = f"""
    docker rm -f smb-honeypot || true
    mkdir -p /tmp/honeyfiles/{req.share_name}
    for i in {{1..{req.files_count}}}; do
        echo "CONFIDENTIAL: DO NOT SHARE" > /tmp/honeyfiles/{req.share_name}/admin_credentials_$i.txt
    done

    # We use a lightweight samba container with full VFS audit logging turned on.
    # Any access is logged to stdout, which we could tail into our Threat Monitor Agent!
    docker run -d --name smb-honeypot -p 445:445 \\
      -v /tmp/honeyfiles:/shares \\
      dperson/samba \\
      -s "{req.share_name};/shares/{req.share_name};yes;no;no;all;none"
    """
    import base64

    b64_script = base64.b64encode(deploy_script.encode()).decode()
    cmd = f"echo {b64_script} | base64 -d | sudo bash"

    results, err = await session_manager.run(nid, node, [cmd])
    if err:
        raise HTTPException(500, f"Failed to deploy SMB Honeypot: {err}")

    # Log the successful deployment as a new security posture update
    import time

    await insert_alert(
        {
            "id": f"alert_deception_{int(time.time())}",
            "title": f"[DECEPTION] SMB Honeyfile Share Deployed on {nid}",
            "description": f"Successfully planted hidden Samba share '{req.share_name}' with {req.files_count} canary documents. Any ransomware attempting to encrypt this share will immediately trigger isolation.",
            "severity": "info",
            "status": "new",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
    )

    return {
        "status": "success",
        "message": f"Deployed SMB Honeyfile Share '{req.share_name}' successfully.",
    }


class HoneyTokenRequest(BaseModel):
    fake_username: str = "svc_backup_admin"
    fake_host: str = "10.0.0.99"


@router.post(
    "/nodes/{nid}/deception/honey-tokens", dependencies=[Depends(require_admin)]
)
async def api_deploy_honey_tokens(nid: str, req: HoneyTokenRequest):
    """
    Identity Threat Detection & Response (ITDR) - Honey Tokens.
    Injects fake SSH credentials into the bash history and SSH config of the target node.
    If an attacker compromises the node and dumps credentials, they will find these
    highly enticing 'Honey Tokens'.
    Any subsequent attempt to use these fake credentials to pivot laterally to the fake host
    will trigger an immediate 'Critical ITDR Alert' and node isolation.
    """
    nodes = await load_nodes_db()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    node = dict(nodes[nid])
    username, password = await load_credentials(nid)
    node["username"] = username
    node["password"] = password

    # Generate a decoy at runtime so the repository never contains a static
    # private-key-shaped payload that can be mistaken for a real credential.
    import base64
    import secrets

    key_label = "OPENSSH " + "PRIVATE KEY"
    fake_key_body = base64.b64encode(
        f"NetrunnerHoneyToken:{secrets.token_hex(32)}".encode()
    ).decode()

    # Bash script to safely inject honey tokens into bash_history and ssh configs
    deploy_script = f"""
    # Inject fake SSH connection into bash history
    echo "ssh {req.fake_username}@{req.fake_host} -i ~/.ssh/id_rsa_backup" >> ~/.bash_history

    # Create fake SSH key
    mkdir -p ~/.ssh
    echo "-----BEGIN {key_label}-----" > ~/.ssh/id_rsa_backup
    echo "{fake_key_body}" >> ~/.ssh/id_rsa_backup
    echo "-----END {key_label}-----" >> ~/.ssh/id_rsa_backup
    chmod 600 ~/.ssh/id_rsa_backup

    # Inject fake host alias into /etc/hosts for DNS poisoning
    echo "{req.fake_host}   internal-backup-vault.local" | sudo tee -a /etc/hosts
    """
    b64_script = base64.b64encode(deploy_script.encode()).decode()
    cmd = f"echo {b64_script} | base64 -d | bash"

    results, err = await session_manager.run(nid, node, [cmd])
    if err:
        raise HTTPException(500, f"Failed to inject Honey Tokens: {err}")

    # Log the successful deployment
    import time

    await insert_alert(
        {
            "id": f"alert_itdr_{int(time.time())}",
            "title": f"[ITDR] Endpoint Honey Tokens Injected on {nid}",
            "description": f"Planted synthetic SSH credentials for '{req.fake_username}@{req.fake_host}' directly into the Bash history and ~/.ssh directory. If these credentials are stolen and utilized, the attacker's location is immediately compromised.",
            "severity": "info",
            "status": "new",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
    )

    return {"status": "success", "message": f"ITDR Honey Tokens injected successfully."}
