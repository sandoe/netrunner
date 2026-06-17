import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from ..core.cti import cti_engine
from ..core.soar import soar_engine
from .auth import get_current_user

router = APIRouter()

# Global list of connected clients for threat streaming
threat_clients = []

# Global background task handle
_threat_task = None

from ..core.cti import cti_engine, cti_queue

import logging
_log = logging.getLogger("threats")


def _supervise(coro, name):
    """Run a background coroutine and log if it dies, instead of failing silently."""
    async def runner():
        try:
            await coro
        except Exception as e:
            _log.error(f"[threats] {name} crashed: {e!r}")
    return asyncio.create_task(runner())


async def broadcast_threats():
    """Background task that reads from CTI engine and broadcasts to all connected websocket clients."""
    # Start the generator and monitored-nodes log tailer (supervised so a crash
    # is logged, not silently swallowed — which would kill the threat feed).
    _supervise(cti_engine.stream_threats(cti_queue), "stream_threats")
    # Optional log tailer — only if the engine implements it (it doesn't today;
    # calling a missing method here used to crash the whole broadcast loop and
    # silently kill the threat feed).
    if hasattr(cti_engine, "tail_monitored_nodes_logs"):
        _supervise(cti_engine.tail_monitored_nodes_logs(cti_queue), "tail_monitored_nodes_logs")
    _log.info("[threats] broadcast loop started")

    while True:
        try:
            event = await cti_queue.get()
            # Feed event to SOAR Autopilot (supervised)
            _supervise(soar_engine.process_event(event), "soar.process_event")

            if not threat_clients:
                continue

            message = json.dumps(event)
            disconnected = []
            for client in threat_clients:
                try:
                    await client.send_text(message)
                except Exception:
                    disconnected.append(client)

            for client in disconnected:
                if client in threat_clients:
                    threat_clients.remove(client)
        except Exception as e:
            _log.error(f"[threats] broadcast loop error: {e!r}")
            await asyncio.sleep(0.5)


@router.websocket("/ws/threats")
async def websocket_threats(websocket: WebSocket):
    from .auth import authenticate_ws
    if await authenticate_ws(websocket) is None:
        return
    await websocket.accept()
    threat_clients.append(websocket)
    try:
        while True:
            # Just keep connection open, client doesn't send anything
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in threat_clients:
            threat_clients.remove(websocket)


@router.get("/api/threats/nodes")
async def get_threat_nodes(user: dict = Depends(get_current_user)):
    from ..core.db import load_nodes_db
    from ..core.cti import get_ip_geolocation
    nodes = await load_nodes_db()
    result = []
    for nid, n in nodes.items():
        host = n.get("host")
        if host:
            geo = await get_ip_geolocation(host, default_name=n.get("name"))
            result.append({
                "id": nid,
                "name": n.get("name"),
                "ip": host,
                "lat": geo["lat"],
                "lng": geo["lng"]
            })
    return result


@router.get("/api/threats/history")
async def get_threat_history(limit: int = 100, user: dict = Depends(get_current_user)):
    """Retrieves historical threat events."""
    from ..core.db import load_threat_events_db
    events = await load_threat_events_db(limit=limit)
    return events
