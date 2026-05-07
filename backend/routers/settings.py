"""Settings API for managing global configuration like API keys."""
from __future__ import annotations

import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

DATA_DIR = Path("data")
SETTINGS_FILE = DATA_DIR / "settings.json"

class Settings(BaseModel):
    openai_api_key: str = ""
    gns3_server_url: str = "http://127.0.0.1"
    gns3_local_projects_path: str = "/home/aso/GNS3/projects"

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except:
            return {}
    return {}

def save_settings(settings: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))

@router.get("/settings")
async def get_settings():
    s = load_settings()
    # Mask the key for safety
    key = s.get("openai_api_key", "")
    masked = f"{key[:8]}..." if len(key) > 8 else key
    return {
        "openai_api_key_set": bool(key), 
        "masked_key": masked,
        "gns3_server_url": s.get("gns3_server_url", "http://127.0.0.1:3080")
    }

@router.post("/settings")
async def update_settings(settings: dict):
    s = load_settings()
    if "openai_api_key" in settings:
        s["openai_api_key"] = settings["openai_api_key"]
        os.environ["OPENAI_API_KEY"] = settings["openai_api_key"]
    if "gns3_server_url" in settings:
        s["gns3_server_url"] = settings["gns3_server_url"]
    
    save_settings(s)
    return {"status": "ok"}
