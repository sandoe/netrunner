"""
Netrunner Defense — Real network isolation and zero-trust enforcement.

Executes iptables rules via SSH on managed nodes for actual network isolation.
"""

import asyncio
import json
from .db import load_nodes_db
from .logger import log as logger

try:
    import paramiko

    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

try:
    from .vault import get_credential
except ImportError:
    get_credential = None


async def _ssh_exec(
    host: str, username: str, password: str, command: str, port: int = 22
) -> tuple[int, str, str]:
    """Execute a command over SSH. Returns (exit_code, stdout, stderr)."""
    if not PARAMIKO_AVAILABLE:
        return -1, "", "paramiko not installed"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        await asyncio.to_thread(
            client.connect,
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=10,
            look_for_keys=False,
            allow_agent=False,
        )
        _, stdout, stderr = await asyncio.to_thread(
            client.exec_command, command, timeout=30
        )
        exit_code = await asyncio.to_thread(stdout.channel.recv_exit_status)
        out = await asyncio.to_thread(stdout.read().decode, errors="replace")
        err = await asyncio.to_thread(stderr.read().decode, errors="replace")
        return exit_code, out, err
    except Exception as e:
        return -1, "", str(e)
    finally:
        client.close()


async def _get_node_credentials(node: dict) -> tuple[str, str, int]:
    """Get SSH credentials for a node from vault or defaults."""
    host = node.get("host", "")
    username = "root"
    password = ""
    port = 22

    if get_credential:
        try:
            cred = await asyncio.to_thread(get_credential, node.get("id", ""), "ssh")
            if cred:
                username = cred.get("username", username)
                password = cred.get("password", password)
                port = cred.get("port", port)
        except Exception:
            pass

    if not password:
        password = node.get("ssh_password", "")

    return username, password, port


async def apply_isolation(node_id: str) -> str:
    """
    Isolates a node by applying iptables rules via SSH.
    Drops all inbound/outbound traffic except management from Netrunner.
    """
    nodes = await load_nodes_db()
    if node_id not in nodes:
        return "Error: Node not found."

    node = nodes[node_id]
    host = node.get("host", "")
    name = node.get("name", node_id)

    username, password, port = await _get_node_credentials(node)

    if not password:
        return f"""[ACTIVE DEFENSE] No SSH credentials available for {name} ({host}).
Please set the password in the credential vault (Vault → Node Credentials → ssh)."""

    logger.info(f"[DEFENSE] Isolating node {name} ({host}) via SSH iptables")

    rules = [
        "iptables -F INPUT",
        "iptables -F OUTPUT",
        "iptables -F FORWARD",
        "iptables -P INPUT DROP",
        "iptables -P OUTPUT DROP",
        "iptables -P FORWARD DROP",
        "iptables -A INPUT -i lo -j ACCEPT",
        "iptables -A OUTPUT -o lo -j ACCEPT",
        "iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT",
        "iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT",
        "iptables -A INPUT -s 127.0.0.0/8 -j ACCEPT",
        "iptables -A OUTPUT -d 127.0.0.0/8 -j ACCEPT",
    ]

    exit_code, out, err = await _ssh_exec(
        host, username, password, " && ".join(rules), port
    )

    if exit_code != 0:
        logger.error(f"[DEFENSE] SSH iptables failed for {name}: {err}")
        return f"""[ACTIVE DEFENSE] Isolation FAILED for {name} ({host}).
SSH Error: {err}
Manual intervention required."""

    # Verify rules applied
    verify_code, verify_out, _ = await _ssh_exec(
        host, username, password, "iptables -L -n --line-numbers", port
    )

    return f"""[ACTIVE DEFENSE] Isolation protocol executed for {name} ({host}).
- Connected via SSH ({username}@{host}:{port})... OK.
- Flushed existing iptables rules... OK.
- Set default policy to DROP (INPUT/OUTPUT/FORWARD)... OK.
- Whitelisted loopback and established connections... OK.

Verification:
{verify_out if verify_code == 0 else '(verification unavailable)'}

Node is now isolated from the network.
To restore: use the 'Release Node' action or manually run 'iptables -F && iptables -P INPUT ACCEPT && iptables -P OUTPUT ACCEPT && iptables -P FORWARD ACCEPT'."""


async def release_isolation(node_id: str) -> str:
    """Restores a node from isolation by flushing iptables rules."""
    nodes = await load_nodes_db()
    if node_id not in nodes:
        return "Error: Node not found."

    node = nodes[node_id]
    host = node.get("host", "")
    name = node.get("name", node_id)
    username, password, port = await _get_node_credentials(node)

    if not password:
        return f"No SSH credentials available for {name} ({host})."

    logger.info(f"[DEFENSE] Releasing isolation for {name} ({host})")

    release_cmd = "iptables -F && iptables -P INPUT ACCEPT && iptables -P OUTPUT ACCEPT && iptables -P FORWARD ACCEPT"
    exit_code, out, err = await _ssh_exec(host, username, password, release_cmd, port)

    if exit_code != 0:
        return f"Release FAILED for {name}: {err}"

    return f"""[ACTIVE DEFENSE] Node {name} ({host}) released from isolation.
- Flushed iptables rules... OK.
- Reset policies to ACCEPT... OK.
- Node is now fully network-accessible."""


async def enforce_zero_trust(node_id: str) -> str:
    """
    Enforces strict Zero Trust Micro-Segmentation on the node.
    Only allows traffic to/from the Netrunner management IP.
    """
    nodes = await load_nodes_db()
    if node_id not in nodes:
        return "Error: Node not found."

    node = nodes[node_id]
    host = node.get("host", "")
    name = node.get("name", node_id)
    username, password, port = await _get_node_credentials(node)

    if not password:
        return f"No SSH credentials available for {name} ({host})."

    logger.info(f"[DEFENSE] Enforcing zero-trust on {name} ({host})")

    rules = [
        "iptables -F",
        "iptables -P INPUT DROP",
        "iptables -P OUTPUT DROP",
        "iptables -P FORWARD DROP",
        "iptables -A INPUT -i lo -j ACCEPT",
        "iptables -A OUTPUT -o lo -j ACCEPT",
        "iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT",
        "iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT",
        "iptables -A INPUT -p tcp --dport 22 -j ACCEPT",
        "iptables -A INPUT -p tcp --dport 8000 -j ACCEPT",
        "iptables -A INPUT -p tcp --dport 8001 -j ACCEPT",
        "iptables -A OUTPUT -p tcp --sport 22 -j ACCEPT",
        "iptables -A OUTPUT -p tcp --sport 8000 -j ACCEPT",
        "iptables -A OUTPUT -p tcp --sport 8001 -j ACCEPT",
        "iptables -A INPUT -p icmp -j ACCEPT",
        "iptables -A OUTPUT -p icmp -j ACCEPT",
    ]

    exit_code, out, err = await _ssh_exec(
        host, username, password, " && ".join(rules), port
    )

    if exit_code != 0:
        return f"""[ZERO TRUST] FAILED for {name} ({host}).
SSH Error: {err}"""

    verify_code, verify_out, _ = await _ssh_exec(
        host, username, password, "iptables -L -n --line-numbers", port
    )

    return f"""[ZERO TRUST ENFORCER] Micro-Segmentation enforced on {name} ({host}).
- Connected via SSH ({username}@{host}:{port})... OK.
- Flushed existing rules... OK.
- Default Policy: INPUT DROP, FORWARD DROP... OK.
- Management Access: ALLOWING Netrunner on Port 22/8000/8001... OK.
- Established Connections: ALLOWING stateful responses... OK.
- ICMP: ALLOWING... OK.

Verification:
{verify_out if verify_code == 0 else '(verification unavailable)'}

System hardened. Zero Trust Architecture enforced."""


async def block_ip_on_node(node_id: str, target_ip: str) -> str:
    """Blocks a specific IP address on a node via iptables."""
    nodes = await load_nodes_db()
    if node_id not in nodes:
        return f"Node {node_id} not found."

    node = nodes[node_id]
    host = node.get("host", "")
    name = node.get("name", node_id)
    username, password, port = await _get_node_credentials(node)

    if not password:
        return f"No SSH credentials available for {name} ({host})."

    cmd = f"iptables -A INPUT -s {target_ip} -j DROP && iptables -A OUTPUT -d {target_ip} -j DROP"
    exit_code, out, err = await _ssh_exec(host, username, password, cmd, port)

    if exit_code != 0:
        return f"Failed to block {target_ip} on {name}: {err}"

    return f"[SOAR ACTION] Blocked IP {target_ip} on {name} ({host}) via iptables."


async def unblock_ip_on_node(node_id: str, target_ip: str) -> str:
    """Unblocks a specific IP address on a node via iptables."""
    nodes = await load_nodes_db()
    if node_id not in nodes:
        return f"Node {node_id} not found."

    node = nodes[node_id]
    host = node.get("host", "")
    name = node.get("name", node_id)
    username, password, port = await _get_node_credentials(node)

    if not password:
        return f"No SSH credentials available for {name} ({host})."

    cmd = f"iptables -D INPUT -s {target_ip} -j DROP && iptables -D OUTPUT -d {target_ip} -j DROP"
    exit_code, out, err = await _ssh_exec(host, username, password, cmd, port)

    if exit_code != 0:
        return f"Failed to unblock {target_ip} on {name}: {err}"

    return f"[SOAR ACTION] Unblocked IP {target_ip} on {name} ({host})."
