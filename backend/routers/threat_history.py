from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from ..core.db import load_threat_events_db
from .auth import require_admin

router = APIRouter()

@router.get("/history", dependencies=[Depends(require_admin)])
async def get_threat_history(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves historical threat events."""
    events = await load_threat_events_db(limit=limit)
    return events
