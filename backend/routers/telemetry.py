import asyncio
import os
import json
import aiofiles
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ..core.telemetry import telemetry_cache
from ..core.state import telemetry_queue
from .auth import get_current_user

router = APIRouter()

telemetry_clients = []
_telemetry_task: Optional[asyncio.Task] = None
_poll_task: Optional[asyncio.Task] = None
_reach_task: Optional[asyncio.Task] = None


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
        await websocket.send_text(
            json.dumps({"type": "init", "cache": telemetry_cache})
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in telemetry_clients:
            telemetry_clients.remove(websocket)


import struct
import hashlib
import math

nexus_clients = []
_nexus_task: Optional[asyncio.Task] = None


def hash_node_id(node_id: str) -> int:
    return int(hashlib.md5(node_id.encode()).hexdigest()[:16], 16)


async def broadcast_nexus():
    t = 0.0
    while True:
        try:
            if not nexus_clients:
                await asyncio.sleep(1)
                continue

            t += 0.05
            from ..core.db import load_nodes_db

            nodes = await load_nodes_db()
            payloads = []
            for nid in nodes.keys():
                nid_bytes = nid.encode("utf-8")
                if len(nid_bytes) > 36:
                    nid_bytes = nid_bytes[:36]
                else:
                    nid_bytes = nid_bytes.ljust(36, b"\0")

                # Mock 3D coordinates for the simulation branch
                x = math.sin(t + hash(nid) % 100) * 100
                y = math.cos(t + hash(nid) % 100) * 100
                z = math.sin(t * 0.5 + hash(nid) % 100) * 100
                status = 1
                payloads.append(struct.pack("!36sfffB", nid_bytes, x, y, z, status))

            if payloads:
                msg = b"".join(payloads)
                disconnected = []
                for client in nexus_clients:
                    try:
                        await client.send_bytes(msg)
                    except Exception:
                        disconnected.append(client)

                for client in disconnected:
                    if client in nexus_clients:
                        nexus_clients.remove(client)
        except Exception:
            pass
        await asyncio.sleep(1 / 60.0)


@router.websocket("/ws/nexus")
async def websocket_nexus(websocket: WebSocket):
    from .auth import authenticate_ws

    if await authenticate_ws(websocket) is None:
        return
    await websocket.accept()
    nexus_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in nexus_clients:
            nexus_clients.remove(websocket)


class UIEvent(BaseModel):
    type: str
    timestamp: str
    path: str
    element: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


LOG_FILE = os.environ.get("UI_CONTEXT_LOG_PATH", "data/ui_context.log")


@router.post("/api/telemetry/ui")
async def log_ui_event(event: UIEvent, user: dict = Depends(get_current_user)):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        async with aiofiles.open(LOG_FILE, "a", encoding="utf-8") as f:
            log_entry = json.dumps(
                {
                    "timestamp": event.timestamp,
                    "type": event.type,
                    "path": event.path,
                    "element": event.element,
                    "data": event.data,
                }
            )
            await f.write(f"{log_entry}\n")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to log event")
