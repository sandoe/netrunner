from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import uuid
import time
from ..core.db import (
    load_playbooks_db,
    save_playbook_db,
    update_playbook_db,
    delete_playbook_db,
    insert_audit_log,
    load_pending_executions_db,
    update_pending_execution_db,
    update_alert_status,
)
from .auth import get_current_user, require_non_student

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


class ExecutionMode(str, Enum):
    AUTONOMOUS = "autonomous"
    APPROVAL_REQUIRED = "approval_required"


class PlaybookCreate(BaseModel):
    name: str = Field(..., example="Auto-ban botnets")
    description: str | None = Field(None, example="Bans critical port scan alerts")
    is_active: bool = Field(True)
    execution_mode: ExecutionMode = Field(default=ExecutionMode.AUTONOMOUS)
    conditions: str = Field(
        "[]", example='[{"field": "severity", "operator": "==", "value": "critical"}]'
    )
    actions: str = Field("[]", example='[{"type": "block_ip"}]')


class PlaybookUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    execution_mode: ExecutionMode | None = None
    conditions: str | None = None
    actions: str | None = None


class PlaybookResponse(BaseModel):
    id: str
    name: str
    description: str | None
    is_active: bool
    execution_mode: str
    conditions: str
    actions: str
    created_at: float
    updated_at: float


@router.get("/", response_model=List[PlaybookResponse])
async def list_playbooks(user: dict = Depends(get_current_user)):
    """Get all playbooks"""
    return await load_playbooks_db()


@router.post("/", response_model=PlaybookResponse)
async def create_playbook(data: PlaybookCreate, user: dict = Depends(require_non_student)):
    """Create a new playbook"""
    now = time.time()
    playbook_id = str(uuid.uuid4())
    doc = {
        "id": playbook_id,
        "name": data.name,
        "description": data.description,
        "is_active": data.is_active,
        "execution_mode": data.execution_mode.value,
        "conditions": data.conditions,
        "actions": data.actions,
        "created_at": now,
        "updated_at": now,
    }
    await save_playbook_db(doc)

    await insert_audit_log(
        {
            "id": str(uuid.uuid4()),
            "user_id": user["username"],  # Actual logged-in user's username
            "action": "CREATE_PLAYBOOK",
            "resource": playbook_id,
            "details": f"Created playbook: {data.name}",
            "timestamp": now,
        }
    )

    return doc


@router.patch("/{playbook_id}", response_model=Dict[str, str])
async def update_playbook(playbook_id: str, data: PlaybookUpdate, user: dict = Depends(require_non_student)):
    """Update an existing playbook"""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        return {"status": "no changes"}

    await update_playbook_db(playbook_id, update_data)

    await insert_audit_log(
        {
            "id": str(uuid.uuid4()),
            "user_id": user["username"],
            "action": "UPDATE_PLAYBOOK",
            "resource": playbook_id,
            "details": f"Updated playbook fields: {list(update_data.keys())}",
            "timestamp": time.time(),
        }
    )

    return {"status": "updated"}


@router.delete("/{playbook_id}", response_model=Dict[str, str])
async def delete_playbook(playbook_id: str, user: dict = Depends(require_non_student)):
    """Delete a playbook"""
    await delete_playbook_db(playbook_id)
    return {"status": "deleted"}


@router.get("/executions/pending")
async def list_pending_executions(user: dict = Depends(get_current_user)):
    """List playbook runs waiting for human authorization."""
    return await load_pending_executions_db()


@router.post("/executions/{execution_id}/approve")
async def approve_execution(execution_id: str, user: dict = Depends(require_non_student)):
    """Unblock and execute the pending actions."""
    from ..services.soar_playbooks import execute_actions
    import json

    execution = await update_pending_execution_db(execution_id, "approved")
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    await update_alert_status(execution["alert_id"], "mitigated")

    # Execute actions asynchronously
    import asyncio

    try:
        actions = json.loads(execution["actions"])
        asyncio.create_task(execute_actions(actions, execution["alert_id"]))
    except Exception as e:
        pass

    return {"status": "approved", "execution_id": execution_id}


@router.post("/executions/{execution_id}/reject")
async def reject_execution(execution_id: str, user: dict = Depends(require_non_student)):
    """Cancel the execution and log the rejection."""
    execution = await update_pending_execution_db(execution_id, "rejected")
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    await update_alert_status(execution["alert_id"], "new")

    return {"status": "rejected", "execution_id": execution_id}


@router.post("/simulate/{drill_name}")
async def simulate_drill(drill_name: str, user: dict = Depends(require_non_student)):
    """
    Blue Team Simulator: Generates mock telemetry or fake logs for DPI and SOAR engines to detect.
    """
    valid_drills = ["syn-flood", "malware-beacon", "brute-force"]
    if drill_name not in valid_drills:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid drill name. Supported drills: {', '.join(valid_drills)}",
        )

    mock_alert_id = str(uuid.uuid4())
    mock_alert = {
        "id": mock_alert_id,
        "title": f"Simulated {drill_name.replace('-', ' ').title()} Attack",
        "description": f"Mock telemetry generated for {drill_name} drill. Target IP: 192.168.1.100",
        "severity": "high",
        "status": "new",
        "created_at": time.time(),
        "updated_at": time.time(),
    }

    from ..core.db import save_alert_db

    await save_alert_db(mock_alert)

    return {
        "status": "success",
        "message": f"Mock simulation for '{drill_name}' was triggered successfully.",
        "alert_id": mock_alert_id,
    }
