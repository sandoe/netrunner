import os
import secrets
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from ..core.db import load_settings_db, save_setting_db, load_nodes_db
from ..core.cti import cti_engine, cti_queue

router = APIRouter()


class AgentEvent(BaseModel):
    type: str
    severity: str
    source_ip: str


async def verify_agent_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    token = authorization.split(" ", 1)[1]
    expected = await get_agent_token()

    if not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Invalid agent token")
    return token


async def get_agent_token() -> str:
    """Return the stable deployment token used by all installed agents."""
    configured = os.environ.get("NETRUNNER_AGENT_TOKEN", "").strip()
    if configured:
        return configured

    settings = await load_settings_db()
    if "agent_token" not in settings:
        settings["agent_token"] = secrets.token_hex(16)
        await save_setting_db("agent_token", settings["agent_token"])
    return settings["agent_token"]


@router.post("/events")
async def receive_event(
    request: Request, event: AgentEvent, token: str = Depends(verify_agent_token)
):
    """Receives a threat event from the local Go agent."""
    from ..core.db import load_nodes_db, save_threat_event_db
    import time
    import random

    nodes = await load_nodes_db()

    # Identify which node sent this
    client_ip = request.client.host
    node_id = request.headers.get("X-Node-ID", "unknown")
    target_host = client_ip
    target_name = "Unknown Agent"

    if node_id != "unknown" and node_id in nodes:
        target_host = nodes[node_id].get("host", target_host)
        target_name = nodes[node_id].get("name", target_name)
    else:
        for nid, n in nodes.items():
            if n.get("host") == client_ip:
                node_id = nid
                target_host = n.get("host", target_host)
                target_name = n.get("name", target_name)
                break

        # Fallback to the first monitored node if not matched by IP
        if node_id == "unknown":
            monitored = [n for n in nodes.values() if n.get("threat_monitoring")]
            if monitored:
                target_host = monitored[0].get("host", target_host)
                target_name = monitored[0].get("name", target_name)
                node_id = monitored[0].get("id", node_id)

    # Generate a unique event ID
    event_id = f"evt_{int(time.time()*1000)}_{random.randint(1000, 9999)}"
    timestamp = time.time()

    # Inject to real-time map queue
    await cti_engine.inject_agent_event(
        queue=cti_queue,
        target_host=target_host,
        target_name=target_name,
        alert_type=event.type,
        severity=event.severity,
        attacker_ip=event.source_ip,
        node_id=node_id,
    )

    # Save to history database
    db_event = {
        "id": event_id,
        "timestamp": timestamp,
        "node_id": node_id,
        "source_ip": event.source_ip,
        "target_ip": target_host,
        "type": event.type,
        "severity": event.severity,
    }
    await save_threat_event_db(db_event)

    return {"status": "ok"}


class AgentBluetoothDevice(BaseModel):
    mac: str
    rssi: int
    name: str = "Unknown Device"


class AgentBluetoothReport(BaseModel):
    devices: list[AgentBluetoothDevice]


@router.post("/bluetooth")
async def receive_bluetooth(
    request: Request,
    report: AgentBluetoothReport,
    token: str = Depends(verify_agent_token),
):
    """Receives local Bluetooth scans from the Go agent."""
    from ..core.db import load_nodes_db
    from ..core.bluetooth import receive_agent_bluetooth_data

    nodes = await load_nodes_db()
    client_ip = request.client.host
    node_id = request.headers.get("X-Node-ID", "unknown")

    if node_id == "unknown" or node_id not in nodes:
        node_id = "unknown"
        for nid, n in nodes.items():
            if n.get("host") == client_ip:
                node_id = nid
                break

        if node_id == "unknown":
            monitored = [n for n in nodes.values() if n.get("threat_monitoring")]
            if monitored:
                node_id = monitored[0].get("id", node_id)

    # Process into the central bluetooth engine
    await receive_agent_bluetooth_data(node_id, report.devices)

    return {"status": "ok"}


class AgentUSBDevice(BaseModel):
    device: str
    name: str


class AgentUSBReport(BaseModel):
    devices: list[AgentUSBDevice]


@router.post("/usb")
async def receive_usb(
    request: Request, report: AgentUSBReport, token: str = Depends(verify_agent_token)
):
    """Receives local USB scans from the Go agent."""
    from ..core.db import load_nodes_db
    from .usb import receive_agent_usb_data

    nodes = await load_nodes_db()
    client_ip = request.client.host
    node_id = request.headers.get("X-Node-ID", "unknown")

    if node_id == "unknown" or node_id not in nodes:
        node_id = "unknown"
        for nid, n in nodes.items():
            if n.get("host") == client_ip:
                node_id = nid
                break

        if node_id == "unknown":
            monitored = [n for n in nodes.values() if n.get("threat_monitoring")]
            if monitored:
                node_id = monitored[0].get("id", node_id)

    # Process into the central usb cache
    await receive_agent_usb_data(node_id, [d.model_dump() for d in report.devices])

    return {"status": "ok"}


@router.get("/download/{arch}")
async def download_agent(arch: str):
    """Downloads the Go agent binary for the specified architecture."""
    if arch not in ("amd64", "arm64"):
        raise HTTPException(status_code=400, detail="Invalid architecture")

    # In Docker, we will place the binaries in /app/bin/
    # If running locally without Docker, fallback
    filepath = f"/app/bin/netrunner-agent-{arch}"
    if not os.path.exists(filepath):
        # Fallback to local test directory
        filepath = f"../agent/netrunner-agent-{arch}"
        if not os.path.exists(filepath):
            raise HTTPException(
                status_code=404,
                detail="Agent binary not found. Please build via Docker.",
            )

    return FileResponse(
        path=filepath,
        filename=f"netrunner-agent",
        media_type="application/octet-stream",
    )
