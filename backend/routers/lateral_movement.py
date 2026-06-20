"""
Netrunner Lateral Movement Router — API endpoints for SSH tunnels and pivoting.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from .auth import require_admin
from ..core.lateral_movement import (
    create_socks_proxy, create_local_forward, create_remote_forward,
    create_pivot_chain, close_tunnel, close_pivot_chain,
    list_active_tunnels, list_pivot_chains,
)
from ..core.db import load_nodes_db

router = APIRouter()


class SOCKSProxyRequest(BaseModel):
    node_id: str
    local_port: int = 1080
    remote_port: int = 22


class LocalForwardRequest(BaseModel):
    node_id: str
    local_port: int
    remote_host: str
    remote_port: int
    ssh_port: int = 22


class RemoteForwardRequest(BaseModel):
    node_id: str
    remote_port: int
    local_host: str = "127.0.0.1"
    local_port: int
    ssh_port: int = 22


class PivotHop(BaseModel):
    node_id: str
    host: str
    username: str
    password: str
    port: int = 22


class PivotChainRequest(BaseModel):
    name: str
    hops: list[PivotHop]


class CloseRequest(BaseModel):
    tunnel_id: str


@router.get("/lateral/tunnels")
async def api_lateral_tunnels():
    """List all active tunnels."""
    tunnels = list_active_tunnels()
    return {"tunnels": tunnels, "count": len(tunnels)}


@router.get("/lateral/pivots")
async def api_lateral_pivots():
    """List all pivot chains."""
    chains = list_pivot_chains()
    return {"chains": chains, "count": len(chains)}


@router.post("/lateral/socks-proxy", dependencies=[Depends(require_admin)])
async def api_lateral_socks_proxy(req: SOCKSProxyRequest):
    """
    Create a SOCKS proxy via SSH dynamic port forwarding.

    Usage: Configure browser/tools to use SOCKS5 proxy at 127.0.0.1:<local_port>
    """
    nodes = await load_nodes_db()
    if req.node_id not in nodes:
        raise HTTPException(404, "Node not found")

    node = nodes[req.node_id]
    host = node.get("host", "")
    username = "root"
    password = node.get("ssh_password", "")

    try:
        from ..core.vault import get_credential
        cred = await get_credential(req.node_id, "ssh")
        if cred:
            username = cred.get("username", username)
            password = cred.get("password", password)
    except Exception:
        pass

    if not password:
        raise HTTPException(400, "No SSH credentials available")

    result = await create_socks_proxy(
        node_id=req.node_id,
        host=host,
        username=username,
        password=password,
        local_port=req.local_port,
        remote_port=req.remote_port,
    )

    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed"))
    return result


@router.post("/lateral/local-forward", dependencies=[Depends(require_admin)])
async def api_lateral_local_forward(req: LocalForwardRequest):
    """
    Create a local port forward via SSH.

    Forwards traffic from local_port to remote_host:remote_port through the SSH server.
    """
    nodes = await load_nodes_db()
    if req.node_id not in nodes:
        raise HTTPException(404, "Node not found")

    node = nodes[req.node_id]
    host = node.get("host", "")
    username = "root"
    password = node.get("ssh_password", "")

    try:
        from ..core.vault import get_credential
        cred = await get_credential(req.node_id, "ssh")
        if cred:
            username = cred.get("username", username)
            password = cred.get("password", password)
    except Exception:
        pass

    if not password:
        raise HTTPException(400, "No SSH credentials available")

    result = await create_local_forward(
        node_id=req.node_id,
        host=host,
        username=username,
        password=password,
        local_port=req.local_port,
        remote_host=req.remote_host,
        remote_port=req.remote_port,
        ssh_port=req.ssh_port,
    )

    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed"))
    return result


@router.post("/lateral/remote-forward", dependencies=[Depends(require_admin)])
async def api_lateral_remote_forward(req: RemoteForwardRequest):
    """
    Create a remote port forward via SSH.

    Makes a port on the remote SSH server forward back to local_host:local_port.
    """
    nodes = await load_nodes_db()
    if req.node_id not in nodes:
        raise HTTPException(404, "Node not found")

    node = nodes[req.node_id]
    host = node.get("host", "")
    username = "root"
    password = node.get("ssh_password", "")

    try:
        from ..core.vault import get_credential
        cred = await get_credential(req.node_id, "ssh")
        if cred:
            username = cred.get("username", username)
            password = cred.get("password", password)
    except Exception:
        pass

    if not password:
        raise HTTPException(400, "No SSH credentials available")

    result = await create_remote_forward(
        node_id=req.node_id,
        host=host,
        username=username,
        password=password,
        remote_port=req.remote_port,
        local_host=req.local_host,
        local_port=req.local_port,
        ssh_port=req.ssh_port,
    )

    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed"))
    return result


@router.post("/lateral/pivot-chain", dependencies=[Depends(require_admin)])
async def api_lateral_pivot_chain(req: PivotChainRequest):
    """
    Create a multi-hop pivot chain through multiple compromised hosts.

    Chains SSH connections through multiple hops to reach deep internal networks.
    """
    hops = [
        {
            "node_id": h.node_id,
            "host": h.host,
            "username": h.username,
            "password": h.password,
            "port": h.port,
        }
        for h in req.hops
    ]

    result = await create_pivot_chain(name=req.name, hops=hops)
    return result


@router.post("/lateral/close", dependencies=[Depends(require_admin)])
async def api_lateral_close(req: CloseRequest):
    """Close an active tunnel."""
    result = await close_tunnel(req.tunnel_id)
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed"))
    return result


@router.post("/lateral/close-chain/{chain_id}", dependencies=[Depends(require_admin)])
async def api_lateral_close_chain(chain_id: str):
    """Close a pivot chain."""
    result = await close_pivot_chain(chain_id)
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed"))
    return result
