from fastapi import APIRouter, HTTPException
from ..core.db import load_nodes_db
from ..core.vault import load_credentials

router = APIRouter()

@router.get("/api/internal/node/{node_id}")
async def get_internal_node(node_id: str):
    """
    Internal endpoint for the Go Terminal Multiplexer to fetch node credentials.
    WARNING: In a real production environment, this should be secured via IPC,
    mTLS, or a secret token to prevent external access.
    """
    nodes = await load_nodes_db()
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found")

    node = nodes[node_id]
    transport = (node.get("transport") or "ssh").lower()

    # Load credentials from vault (telnet consoles, e.g. GNS3, often need none)
    username, password = await load_credentials(node_id)

    return {
        "id": node_id,
        "host": node.get("host"),
        "port": node.get("port") or (23 if transport == "telnet" else 22),
        "transport": transport,
        "username": username or node.get("username") or "root",
        "password": password or ""
    }
