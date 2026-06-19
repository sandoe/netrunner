import asyncio
import os
import json
import aiofiles
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ..core.telemetry import telemetry_cache
from ..core.state import telemetry_queue

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
    from .auth import authenticate_ws
    if await authenticate_ws(websocket) is None:
        return
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

class UIEvent(BaseModel):
    type: str
    timestamp: str
    path: str
    element: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

LOG_FILE = os.environ.get("UI_CONTEXT_LOG_PATH", "data/ui_context.log")

@router.post("/api/telemetry/ui")
async def log_ui_event(event: UIEvent):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        async with aiofiles.open(LOG_FILE, "a", encoding="utf-8") as f:
            log_entry = json.dumps({
                "timestamp": event.timestamp,
                "type": event.type,
                "path": event.path,
                "element": event.element,
                "data": event.data
            })
            await f.write(f"{log_entry}\n")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to log event")
