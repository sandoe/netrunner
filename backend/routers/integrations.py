from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import time
import uuid

from ..core.db import (
    load_integrations_db,
    save_integration_db,
    update_integration_db,
    delete_integration_db,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("", response_model=List[Dict[str, Any]])
async def get_integrations():
    return await load_integrations_db()


@router.post("", response_model=Dict[str, Any])
async def create_integration(data: Dict[str, Any]):
    integration = {
        "id": str(uuid.uuid4()),
        "provider": data.get("provider", "webhook"),
        "name": data.get("name", "New Webhook"),
        "url": data.get("url", ""),
        "is_active": data.get("is_active", True),
        "created_at": time.time(),
    }
    await save_integration_db(integration)
    return integration


@router.patch("/{integration_id}", response_model=Dict[str, Any])
async def update_integration(integration_id: str, data: Dict[str, Any]):
    await update_integration_db(integration_id, data)
    return {"status": "ok"}


@router.delete("/{integration_id}", response_model=Dict[str, str])
async def delete_integration(integration_id: str):
    await delete_integration_db(integration_id)
    return {"status": "deleted"}


@router.post("/{integration_id}/test", response_model=Dict[str, str])
async def test_integration(integration_id: str):
    """Simulates sending a webhook payload to the integration."""
    integrations = await load_integrations_db()
    integration = next((i for i in integrations if i["id"] == integration_id), None)

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    # In a real system, we would make an HTTP request here using httpx
    # For now, we simulate a successful test
    print(
        f"[WEBHOOK SIMULATION] Sent payload to {integration['provider']} at {integration['url']}"
    )
    return {
        "status": "success",
        "message": f"Test payload sent to {integration['provider']}",
    }
