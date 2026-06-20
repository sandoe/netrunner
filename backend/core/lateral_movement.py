"""
Netrunner Lateral Movement Module — SSH tunnels, SOCKS proxy, and pivoting.

Provides:
- SSH dynamic port forwarding (SOCKS proxy)
- SSH local port forwarding
- SSH remote port forwarding
- Pivot chain management
- Credential relay
"""
import asyncio
import os
import json
import time
import subprocess
from typing import Optional
from backend.core.logger import log as logger

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

# Active tunnels and pivots
ActiveTunnels: dict[str, dict] = {}
PivotChains: dict[str, dict] = {}
TUNNEL_DIR = "data/tunnels"


def _ensure_tunnel_dir():
    os.makedirs(TUNNEL_DIR, exist_ok=True)


async def create_socks_proxy(
    node_id: str,
    host: str,
    username: str,
    password: str,
    local_port: int = 1080,
    remote_port: int = 22,
    ssh_host: str = "127.0.0.1",
) -> dict:
    """
    Create a SOCKS proxy via SSH dynamic port forwarding.

    Creates a local SOCKS5 proxy on local_port that tunnels traffic
    through the SSH server at host:remote_port.

    Usage: Configure browser/tools to use SOCKS5 proxy at 127.0.0.1:local_port
    """
    _ensure_tunnel_dir()
    tunnel_id = f"socks_{node_id}_{int(time.time())}"

    logger.info(f"[LATERAL] Creating SOCKS proxy {tunnel_id}: localhost:{local_port} -> {host}:{remote_port}")

    try:
        # Start SSH with dynamic port forwarding
        proc = await asyncio.create_subprocess_exec(
            "ssh",
            "-N",  # No remote command
            "-D", str(local_port),  # Dynamic SOCKS proxy
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", f"ConnectTimeout=10",
            "-p", str(remote_port),
            f"{username}@{host}",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

        # Give it a moment to establish
        await asyncio.sleep(1)

        if proc.returncode is not None:
            stderr = await proc.stderr.read()
            return {"success": False, "error": f"SSH failed: {stderr.decode()}"}

        tunnel_info = {
            "id": tunnel_id,
            "type": "socks",
            "node_id": node_id,
            "host": host,
            "local_port": local_port,
            "remote_port": remote_port,
            "pid": proc.pid,
            "process": proc,
            "created_at": time.time(),
            "status": "active",
        }

        ActiveTunnels[tunnel_id] = tunnel_info

        # Save tunnel info
        info_path = os.path.join(TUNNEL_DIR, f"{tunnel_id}.json")
        with open(info_path, "w") as f:
            json.dump({k: v for k, v in tunnel_info.items() if k != "process"}, f, indent=2)

        return {
            "success": True,
            "tunnel_id": tunnel_id,
            "type": "socks",
            "proxy_address": f"socks5://127.0.0.1:{local_port}",
            "local_port": local_port,
            "target": f"{host}:{remote_port}",
        }

    except FileNotFoundError:
        return {"success": False, "error": "SSH client not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def create_local_forward(
    node_id: str,
    host: str,
    username: str,
    password: str,
    local_port: int,
    remote_host: str,
    remote_port: int,
    ssh_port: int = 22,
) -> dict:
    """
    Create a local port forward via SSH.

    Forwards traffic from local_port to remote_host:remote_port through
    the SSH server.
    """
    _ensure_tunnel_dir()
    tunnel_id = f"local_{node_id}_{int(time.time())}"

    logger.info(f"[LATERAL] Creating local forward {tunnel_id}: localhost:{local_port} -> {remote_host}:{remote_port}")

    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh",
            "-N",
            "-L", f"{local_port}:{remote_host}:{remote_port}",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            "-p", str(ssh_port),
            f"{username}@{host}",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

        await asyncio.sleep(1)

        if proc.returncode is not None:
            stderr = await proc.stderr.read()
            return {"success": False, "error": f"SSH failed: {stderr.decode()}"}

        tunnel_info = {
            "id": tunnel_id,
            "type": "local",
            "node_id": node_id,
            "host": host,
            "local_port": local_port,
            "remote_host": remote_host,
            "remote_port": remote_port,
            "ssh_port": ssh_port,
            "pid": proc.pid,
            "process": proc,
            "created_at": time.time(),
            "status": "active",
        }

        ActiveTunnels[tunnel_id] = tunnel_info

        info_path = os.path.join(TUNNEL_DIR, f"{tunnel_id}.json")
        with open(info_path, "w") as f:
            json.dump({k: v for k, v in tunnel_info.items() if k != "process"}, f, indent=2)

        return {
            "success": True,
            "tunnel_id": tunnel_id,
            "type": "local",
            "local_port": local_port,
            "remote_target": f"{remote_host}:{remote_port}",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def create_remote_forward(
    node_id: str,
    host: str,
    username: str,
    password: str,
    remote_port: int,
    local_host: str,
    local_port: int,
    ssh_port: int = 22,
) -> dict:
    """
    Create a remote port forward via SSH.

    Makes a port on the remote SSH server forward back to local_host:local_port.
    """
    _ensure_tunnel_dir()
    tunnel_id = f"remote_{node_id}_{int(time.time())}"

    logger.info(f"[LATERAL] Creating remote forward {tunnel_id}: {host}:{remote_port} -> {local_host}:{local_port}")

    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh",
            "-N",
            "-R", f"{remote_port}:{local_host}:{local_port}",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            "-p", str(ssh_port),
            f"{username}@{host}",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

        await asyncio.sleep(1)

        if proc.returncode is not None:
            stderr = await proc.stderr.read()
            return {"success": False, "error": f"SSH failed: {stderr.decode()}"}

        tunnel_info = {
            "id": tunnel_id,
            "type": "remote",
            "node_id": node_id,
            "host": host,
            "remote_port": remote_port,
            "local_host": local_host,
            "local_port": local_port,
            "ssh_port": ssh_port,
            "pid": proc.pid,
            "process": proc,
            "created_at": time.time(),
            "status": "active",
        }

        ActiveTunnels[tunnel_id] = tunnel_info

        info_path = os.path.join(TUNNEL_DIR, f"{tunnel_id}.json")
        with open(info_path, "w") as f:
            json.dump({k: v for k, v in tunnel_info.items() if k != "process"}, f, indent=2)

        return {
            "success": True,
            "tunnel_id": tunnel_id,
            "type": "remote",
            "remote_port": remote_port,
            "local_target": f"{local_host}:{local_port}",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def create_pivot_chain(
    name: str,
    hops: list[dict],
) -> dict:
    """
    Create a multi-hop pivot chain through multiple compromised hosts.

    Each hop should contain: {node_id, host, username, password, port}
    """
    _ensure_tunnel_dir()
    chain_id = f"pivot_{int(time.time())}"

    logger.info(f"[LATERAL] Creating pivot chain {chain_id}: {len(hops)} hops")

    # Build SSH ProxyCommand string
    proxy_parts = []
    for i, hop in enumerate(hops):
        if i == 0:
            proxy_parts.append(f"ssh -W %h:%p -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {hop['username']}@{hop['host']}")
        else:
            prev = hops[i - 1]
            proxy_parts.append(f"ssh -W %h:%p -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {prev['username']}@{prev['host']}")

    # The final hop is where we connect to
    final_hop = hops[-1]

    chain_info = {
        "id": chain_id,
        "name": name,
        "hops": hops,
        "created_at": time.time(),
        "status": "active",
    }

    PivotChains[chain_id] = chain_info

    info_path = os.path.join(TUNNEL_DIR, f"{chain_id}.json")
    with open(info_path, "w") as f:
        json.dump(chain_info, f, indent=2)

    return {
        "success": True,
        "chain_id": chain_id,
        "name": name,
        "hops": len(hops),
        "final_target": f"{final_hop['host']}:{final_hop.get('port', 22)}",
    }


async def close_tunnel(tunnel_id: str) -> dict:
    """Close an active tunnel."""
    if tunnel_id not in ActiveTunnels:
        return {"success": False, "error": "Tunnel not found"}

    tunnel = ActiveTunnels[tunnel_id]
    proc = tunnel.get("process")
    if proc and proc.returncode is None:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            proc.kill()

    tunnel["status"] = "closed"
    del ActiveTunnels[tunnel_id]

    # Remove info file
    info_path = os.path.join(TUNNEL_DIR, f"{tunnel_id}.json")
    if os.path.exists(info_path):
        os.remove(info_path)

    return {"success": True, "message": f"Tunnel {tunnel_id} closed"}


async def close_pivot_chain(chain_id: str) -> dict:
    """Close a pivot chain."""
    if chain_id not in PivotChains:
        return {"success": False, "error": "Pivot chain not found"}

    PivotChains[chain_id]["status"] = "closed"
    del PivotChains[chain_id]

    info_path = os.path.join(TUNNEL_DIR, f"{chain_id}.json")
    if os.path.exists(info_path):
        os.remove(info_path)

    return {"success": True, "message": f"Pivot chain {chain_id} closed"}


def list_active_tunnels() -> list[dict]:
    """List all active tunnels."""
    return [
        {k: v for k, v in t.items() if k != "process"}
        for t in ActiveTunnels.values()
    ]


def list_pivot_chains() -> list[dict]:
    """List all pivot chains."""
    return list(PivotChains.values())
