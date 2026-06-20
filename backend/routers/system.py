import subprocess
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import asyncio
from ..core.state import global_state
from ..core.soar import soar_engine
from .auth import require_admin

router = APIRouter()

@router.post("/system/nuke-test-dockers", dependencies=[Depends(require_admin)])
async def nuke_test_dockers():
    try:
        cmd = "docker rm -f $(docker ps -a -q -f name=test-sw -f name=netrunner-sw) 2>/dev/null || true"
        subprocess.run(cmd, shell=True, check=False)
        return {"ok": True, "message": "Test docker containers nuked"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

async def check_port(host: str, port: int) -> bool:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=0.5)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False

class StateUpdate(BaseModel):
    autopilot: bool | None = None
    chaos: bool | None = None

@router.get("/system/state")
async def get_state():
    services = {
        "postgres": await check_port("127.0.0.1", 5432),
        "redis": await check_port("127.0.0.1", 6379),
        "influxdb": await check_port("127.0.0.1", 8086),
        "mux": await check_port("127.0.0.1", 8081)
    }
    return {
        "autopilot": global_state.autopilot,
        "chaos": global_state.chaos,
        "services": services
    }

@router.post("/system/state", dependencies=[Depends(require_admin)])
async def update_state(body: StateUpdate):
    if body.autopilot is not None:
        global_state.autopilot = body.autopilot
    if body.chaos is not None:
        global_state.chaos = body.chaos
    return {
        "autopilot": global_state.autopilot,
        "chaos": global_state.chaos
    }

@router.get("/system/logs")
async def get_logs():
    return {"logs": soar_engine.action_logs}
