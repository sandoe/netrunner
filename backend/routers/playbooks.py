from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import uuid
import time
from ..core.db import (
    load_playbooks_db,
    save_playbook_db,
    update_playbook_db,
    delete_playbook_db,
    insert_audit_log
)

router = APIRouter(prefix="/playbooks", tags=["playbooks"])

class PlaybookCreate(BaseModel):
    name: str = Field(..., example="Auto-ban botnets")
    description: str | None = Field(None, example="Bans critical port scan alerts")
    is_active: bool = Field(True)
    conditions: str = Field("[]", example='[{"field": "severity", "operator": "==", "value": "critical"}]')
    actions: str = Field("[]", example='[{"type": "block_ip"}]')

class PlaybookUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    conditions: str | None = None
    actions: str | None = None

class PlaybookResponse(BaseModel):
    id: str
    name: str
    description: str | None
    is_active: bool
    conditions: str
    actions: str
    created_at: float
    updated_at: float

@router.get("/", response_model=List[PlaybookResponse])
async def list_playbooks():
    """Get all playbooks"""
    return await load_playbooks_db()

@router.post("/", response_model=PlaybookResponse)
async def create_playbook(data: PlaybookCreate):
    """Create a new playbook"""
    now = time.time()
    playbook_id = str(uuid.uuid4())
    doc = {
        "id": playbook_id,
        "name": data.name,
        "description": data.description,
        "is_active": data.is_active,
        "conditions": data.conditions,
        "actions": data.actions,
        "updated_at": now
    }
    await save_playbook_db(doc)
    
    await insert_audit_log({
        "id": str(uuid.uuid4()),
        "user_id": "system_admin", # Mock user since auth isn't fully injected here
        "action": "CREATE_PLAYBOOK",
        "resource": playbook_id,
        "details": f"Created playbook: {data.name}",
        "timestamp": now
    })
    
    return doc

@router.patch("/{playbook_id}", response_model=Dict[str, str])
async def update_playbook(playbook_id: str, data: PlaybookUpdate):
    """Update an existing playbook"""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        return {"status": "no changes"}
    
    await update_playbook_db(playbook_id, update_data)
    
    await insert_audit_log({
        "id": str(uuid.uuid4()),
        "user_id": "system_admin",
        "action": "UPDATE_PLAYBOOK",
        "resource": playbook_id,
        "details": f"Updated playbook fields: {list(update_data.keys())}",
        "timestamp": time.time()
    })
    
    return {"status": "updated"}

@router.delete("/{playbook_id}", response_model=Dict[str, str])
async def delete_playbook(playbook_id: str):
    """Delete a playbook"""
    await delete_playbook_db(playbook_id)
    return {"status": "deleted"}
