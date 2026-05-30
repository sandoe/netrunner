import os
import secrets
from fastapi import APIRouter, HTTPException, Depends, Header
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
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.split(" ")[1]
    settings = await load_settings_db()
    
    if "agent_token" not in settings:
        # Generate token if not exists
        settings["agent_token"] = secrets.token_hex(16)
        await save_setting_db("agent_token", settings["agent_token"])
        
    if token != settings["agent_token"]:
        raise HTTPException(status_code=401, detail="Invalid agent token")
    return token

@router.post("/events")
async def receive_event(event: AgentEvent, token: str = Depends(verify_agent_token)):
    """Receives a threat event from the local Go agent."""
    # Find a node that matches the token? For simplicity, we just broadcast as "Global Infrastructure" 
    # unless we pass the node ID from the agent.
    # To keep it simple, let's just pick any monitored node or a generic target.
    from ..core.db import load_nodes_db, save_threat_event_db
    import time
    import random
    
    nodes = await load_nodes_db()
    monitored = [n for n in nodes.values() if n.get("threat_monitoring")]
    target_host = "127.0.0.1"
    target_name = "Monitored Node"
    node_id = "unknown"
    
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
        attacker_ip=event.source_ip
    )

    # Save to history database
    db_event = {
        "id": event_id,
        "timestamp": timestamp,
        "node_id": node_id,
        "source_ip": event.source_ip,
        "target_ip": target_host,
        "type": event.type,
        "severity": event.severity
    }
    await save_threat_event_db(db_event)

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
            raise HTTPException(status_code=404, detail="Agent binary not found. Please build via Docker.")
            
    return FileResponse(path=filepath, filename=f"netrunner-agent", media_type="application/octet-stream")
