import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..core.cti import cti_engine
from ..core.soar import soar_engine

router = APIRouter()

# Global list of connected clients for threat streaming
threat_clients = []

# Global background task handle
_threat_task = None

from ..core.cti import cti_engine, cti_queue

async def broadcast_threats():
    """Background task that reads from CTI engine and broadcasts to all connected websocket clients."""
    # Start the generator and monitored nodes log tailer in the background
    asyncio.create_task(cti_engine.stream_threats(cti_queue))
    asyncio.create_task(cti_engine.tail_monitored_nodes_logs(cti_queue))
    
    while True:
        event = await cti_queue.get()
        # Feed event to SOAR Autopilot
        asyncio.create_task(soar_engine.process_event(event))
        
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


@router.websocket("/ws/threats")
async def websocket_threats(websocket: WebSocket):
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
async def get_threat_nodes():
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

