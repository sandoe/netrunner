from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
import time
import uuid
from ..core.db import (
    load_alerts_db,
    save_alert_db,
    get_alert_db,
    delete_alert_db,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertBase(BaseModel):
    title: str
    description: Optional[str] = None
    severity: str  # "low", "medium", "high", "critical"


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    status: Optional[str] = None
    assignee_id: Optional[str] = None


class AlertResponse(AlertBase):
    id: str
    status: str
    assignee_id: Optional[str] = None
    created_at: float
    updated_at: float


@router.get("", response_model=List[AlertResponse])
async def get_alerts(status: Optional[str] = None):
    return await load_alerts_db(status=status)


@router.post("", response_model=AlertResponse)
async def create_alert(alert_in: AlertCreate):
    now = time.time()
    alert_dict = {
        "id": f"alrt_{uuid.uuid4().hex[:8]}",
        "title": alert_in.title,
        "description": alert_in.description,
        "severity": alert_in.severity,
        "status": "new",
        "assignee_id": None,
        "created_at": now,
        "updated_at": now,
    }
    await save_alert_db(alert_dict)
    return alert_dict


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(alert_id: str, update_in: AlertUpdate):
    alert = await get_alert_db(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if update_in.status is not None:
        alert["status"] = update_in.status
    if update_in.assignee_id is not None:
        if update_in.assignee_id == "":  # Allow clearing assignee
            alert["assignee_id"] = None
        else:
            alert["assignee_id"] = update_in.assignee_id

    alert["updated_at"] = time.time()
    await save_alert_db(alert)
    return alert


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str):
    alert = await get_alert_db(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await delete_alert_db(alert_id)
    return {"message": "Alert deleted"}
