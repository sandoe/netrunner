from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from backend.core.wifi_csi import csi_queue, mesh_queue
from pydantic import BaseModel
from typing import List
import backend.core.wifi_csi as wifi_core
import asyncio
import os
import glob
from backend.core.db import load_beacon_nodes_db, save_beacon_node_db, delete_beacon_node_db

router = APIRouter()

connected_clients = set()

@router.websocket("/ws/csi")
async def websocket_csi(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            # Vi læser bare passivt fra klienten for at holde forbindelsen i live
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
    except Exception as e:
        print(f"CSI WS error: {e}")
        try:
            connected_clients.remove(websocket)
        except KeyError:
            pass

class WifiModePayload(BaseModel):
    simulation: bool
    nodes: List[str]

@router.post("/api/wifi/mode")
async def set_wifi_mode(payload: WifiModePayload):
    wifi_core.is_simulation = payload.simulation
    wifi_core.real_nodes = payload.nodes
    return {"status": "ok", "simulation": payload.simulation, "nodes": payload.nodes}

@router.post("/api/wifi/record/start")
async def start_recording():
    filename = wifi_core.recorder.start_recording()
    return {"status": "recording_started", "filename": filename}

@router.post("/api/wifi/record/stop")
async def stop_recording():
    filename = wifi_core.recorder.stop_recording()
    return {"status": "recording_stopped", "filename": filename}

@router.get("/api/wifi/esp32/version")
async def esp32_get_version():
    # In a real app, this version could be stored in the DB or read from a manifest file.
    # For now, we bump this manually when we want the ESP32 to update.
    return {"version": "1.0.1"}

@router.get("/api/wifi/esp32/download")
async def esp32_download_main():
    path = os.path.join("agent", "esp32", "main.py")
    if os.path.exists(path):
        return FileResponse(path, media_type='text/plain', filename="main.py")
    return {"error": "Update file not found"}

@router.get("/api/wifi/record/list")
async def list_recordings():
    files = glob.glob("data/captures/csi_capture_*.jsonl")
    results = []
    for f in sorted(files, reverse=True):
        stat = os.stat(f)
        results.append({
            "filename": os.path.basename(f),
            "size": stat.st_size,
            "created": stat.st_mtime
        })
    return {"captures": results}

@router.get("/api/wifi/record/download/{filename}")
async def download_recording(filename: str):
    path = os.path.join("data", "captures", filename)
    if os.path.exists(path):
        return FileResponse(path, media_type='application/jsonl', filename=filename)
    return {"error": "File not found"}

class BeaconNodePayload(BaseModel):
    id: str
    ip: str
    username: str
    password: str
    target_server_ip: str = ""
    csi_mode: str = "AUTO"
    sample_rate: int = 30
    udp_port: int = 8001

@router.get("/api/wifi/beacons")
async def get_beacons():
    nodes = await load_beacon_nodes_db()
    return {"beacons": nodes}

@router.post("/api/wifi/beacons")
async def save_beacon(payload: BeaconNodePayload):
    await save_beacon_node_db(payload.model_dump())
    return {"status": "ok"}

@router.delete("/api/wifi/beacons/{node_id}")
async def delete_beacon(node_id: str):
    await delete_beacon_node_db(node_id)
    return {"status": "ok"}

class DeployPayload(BaseModel):
    node_id: str

from backend.core.deployment import deploy_beacon_to_node, stop_beacon_on_node

@router.post("/api/wifi/deploy")
async def deploy_beacon(payload: DeployPayload):
    # Find node from DB
    nodes = await load_beacon_nodes_db()
    node = next((n for n in nodes if n["id"] == payload.node_id), None)
    if not node:
        return {"error": "Node not found"}
        
    try:
        msg = await deploy_beacon_to_node(
            ip=node["ip"],
            username=node["username"],
            password=node["password"],
            target_server_ip=node.get("target_server_ip", "127.0.0.1"),
            csi_mode=node.get("csi_mode", "AUTO"),
            sample_rate=node.get("sample_rate", 30),
            udp_port=node.get("udp_port", 8001),
            node_id=node["id"]
        )
        return {"status": "deployed", "message": msg}
    except Exception as e:
        return {"error": str(e)}

@router.post("/api/wifi/beacons/{node_id}/stop")
async def stop_beacon(node_id: str):
    nodes = await load_beacon_nodes_db()
    node = next((n for n in nodes if n["id"] == node_id), None)
    if not node:
        return {"error": "Node not found"}
        
    try:
        msg = await stop_beacon_on_node(
            ip=node["ip"],
            username=node["username"],
            password=node["password"]
        )
        return {"status": "stopped", "message": msg}
    except Exception as e:
        return {"error": str(e)}

async def broadcast_csi():
    """Background task to broadcast CSI updates to all connected WS clients."""
    while True:
        try:
            payload = await csi_queue.get()
            if connected_clients:
                dead_clients = set()
                for client in connected_clients:
                    try:
                        await client.send_json(payload)
                    except Exception:
                        dead_clients.add(client)
                
                for dead in dead_clients:
                    connected_clients.remove(dead)
        except Exception as e:
            print(f"Error in broadcast_csi: {e}")
            await asyncio.sleep(1)

async def broadcast_mesh():
    """Background task to broadcast Mesh updates to all connected WS clients."""
    while True:
        try:
            payload = await mesh_queue.get()
            payload["type"] = "mesh"
            if connected_clients:
                dead_clients = set()
                for client in connected_clients:
                    try:
                        await client.send_json(payload)
                    except Exception:
                        dead_clients.add(client)
                
                for dead in dead_clients:
                    connected_clients.remove(dead)
        except Exception as e:
            print(f"Error in broadcast_mesh: {e}")
            await asyncio.sleep(1)
