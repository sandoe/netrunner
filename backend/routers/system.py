from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..core.state import global_state
from ..core.soar import soar_engine
from .auth import require_admin

router = APIRouter()

class StateUpdate(BaseModel):
    autopilot: bool | None = None
    chaos: bool | None = None

@router.get("/system/state")
async def get_state():
    return {
        "autopilot": global_state.autopilot,
        "chaos": global_state.chaos
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
