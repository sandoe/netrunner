import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from ..core.db import load_nodes_db
from ..core.vault import load_credentials

router = APIRouter()


async def verify_internal_token(
    x_netrunner_internal_token: str | None = Header(default=None),
):
    expected = os.environ.get("NETRUNNER_INTERNAL_TOKEN", "").strip()
    if not expected:
        raise HTTPException(503, "Internal service authentication is not configured")
    if not x_netrunner_internal_token or not secrets.compare_digest(
        x_netrunner_internal_token, expected
    ):
        raise HTTPException(401, "Invalid internal service token")


@router.get(
    "/api/internal/node/{node_id}",
    dependencies=[Depends(verify_internal_token)],
)
async def get_internal_node(node_id: str):
    """
    Internal endpoint for the Go Terminal Multiplexer to fetch node credentials.
    This endpoint returns credentials only to the terminal multiplexer, which
    authenticates with the deployment's internal service token.
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
        "password": password or "",
    }
