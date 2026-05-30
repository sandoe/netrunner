import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..core.telemetry import telemetry_queue, telemetry_cache

router = APIRouter()

telemetry_clients = []
_telemetry_task = None

async def broadcast_telemetry():
    while True:
        try:
            event = await telemetry_queue.get()
            if not telemetry_clients:
                continue
                
            message = json.dumps(event)
            disconnected = []
            for client in telemetry_clients:
                try:
                    await client.send_text(message)
                except Exception:
                    disconnected.append(client)
                    
            for client in disconnected:
                if client in telemetry_clients:
                    telemetry_clients.remove(client)
        except Exception:
            await asyncio.sleep(1)

@router.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    telemetry_clients.append(websocket)
    try:
        # Send initial full cache so clients don't start at 0
        await websocket.send_text(json.dumps({"type": "init", "cache": telemetry_cache}))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in telemetry_clients:
            telemetry_clients.remove(websocket)
