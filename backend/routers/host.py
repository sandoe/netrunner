from fastapi import APIRouter
import psutil
import serial.tools.list_ports
import os
import time

router = APIRouter()

def get_disk_usage(path: str):
    try:
        usage = psutil.disk_usage(path)
        return {
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "percent": usage.percent
        }
    except Exception:
        return None

def _collect_host_metrics():
    # If /host is mounted, check it. Otherwise fallback to /
    disk_path = "/host" if os.path.exists("/host") else "/"
    
    # USB Serial devices
    ports = serial.tools.list_ports.comports()
    usb_devices = []
    for port in ports:
        if "USB" in port.device or "ACM" in port.device or port.vid is not None:
            usb_devices.append({
                "device": port.device,
                "name": port.name,
                "description": port.description,
                "hwid": port.hwid,
                "vid": hex(port.vid) if port.vid else None,
                "pid": hex(port.pid) if port.pid else None,
                "manufacturer": port.manufacturer,
                "product": port.product
            })

    net_io = psutil.net_io_counters()
    swap = psutil.swap_memory()
    
    try:
        load1, load5, load15 = os.getloadavg()
    except Exception:
        load1, load5, load15 = 0.0, 0.0, 0.0

    # Basic host metrics
    return {
        "uptime": int(time.time() - psutil.boot_time()),
        "cpu": {
            "percent": psutil.cpu_percent(interval=0.1),
            "cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "loadavg": [round(load1, 2), round(load5, 2), round(load15, 2)]
        },
        "memory": {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
            "percent": psutil.virtual_memory().percent,
            "swap_total_gb": round(swap.total / (1024**3), 2),
            "swap_used_gb": round(swap.used / (1024**3), 2),
            "swap_percent": swap.percent
        },
        "network": {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv
        },
        "disk": get_disk_usage(disk_path),
        "usb_devices": usb_devices
    }

@router.get("/system/host")
async def get_host_metrics():
    import asyncio
    return await asyncio.to_thread(_collect_host_metrics)

@router.post("/system/cleanup")
async def api_system_cleanup():
    from ..core.db import wipe_all_data_db, load_beacon_nodes_db
    from ..core.deployment import scrub_beacon_on_node
    import asyncio
    
    # 1. Fetch all deployed beacon nodes to wipe them
    nodes = await load_beacon_nodes_db()
    
    tasks = []
    for node in nodes:
        # We don't await sequentially to make it fast
        tasks.append(scrub_beacon_on_node(node["ip"], node["username"], node["password"]))
        
    if tasks:
        # Wait for all scrubs to complete, ignoring errors if hosts are dead
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
    # 2. Drop local database tables
    await wipe_all_data_db()
    
    return {"status": "success", "message": "Ghost Protocol complete. All traces scrubbed."}
