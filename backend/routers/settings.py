"""Settings API for managing global configuration like API keys."""
from __future__ import annotations

import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core.db import load_settings_db, save_setting_db

router = APIRouter()

class Settings(BaseModel):
    openai_api_key: str = ""
    alienvault_api_key: str = ""
    gns3_server_url: str = "http://127.0.0.1"
    gns3_local_projects_path: str = "/home/aso/GNS3/projects"

async def load_settings() -> dict:
    return await load_settings_db()

async def save_settings(settings: dict) -> None:
    for k, v in settings.items():
        await save_setting_db(k, str(v))

@router.get("/settings")
async def get_settings():
    s = await load_settings()
    # Mask the key for safety
    key = s.get("openai_api_key", "")
    masked = f"{key[:8]}..." if len(key) > 8 else key
    
    otx_key = s.get("alienvault_api_key", "")
    masked_otx = f"{otx_key[:8]}..." if len(otx_key) > 8 else otx_key
    
    from ..core.db import DATABASE_URL
    
    return {
        "openai_api_key_set": bool(key), 
        "masked_key": masked,
        "alienvault_api_key_set": bool(otx_key),
        "masked_alienvault_key": masked_otx,
        "gns3_server_url": s.get("gns3_server_url", "http://127.0.0.1:3080"),
        "database_url": DATABASE_URL
    }

@router.post("/settings")
async def update_settings(settings: dict):
    s = await load_settings()
    if "openai_api_key" in settings:
        s["openai_api_key"] = settings["openai_api_key"]
        await save_setting_db("openai_api_key", settings["openai_api_key"])
        os.environ["OPENAI_API_KEY"] = settings["openai_api_key"]
        
    if "alienvault_api_key" in settings:
        s["alienvault_api_key"] = settings["alienvault_api_key"]
        await save_setting_db("alienvault_api_key", settings["alienvault_api_key"])
    
    if "gns3_server_url" in settings:
        s["gns3_server_url"] = settings["gns3_server_url"]
        await save_setting_db("gns3_server_url", settings["gns3_server_url"])

    if "database_url" in settings:
        new_db_url = settings["database_url"]
        # Update .env file
        env_path = Path(".env")
        lines = []
        if env_path.exists():
            lines = env_path.read_text().splitlines()
        
        found = False
        new_lines = []
        for line in lines:
            if line.startswith("DATABASE_URL="):
                new_lines.append(f"DATABASE_URL={new_db_url}")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f"DATABASE_URL={new_db_url}")
            
        env_path.write_text("\n".join(new_lines) + "\n")
    
    return {"status": "ok"}

@router.post("/settings/test-db")
async def test_db_connection(body: dict):
    url = body.get("url")
    if not url:
        raise HTTPException(400, "Missing URL")
    
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    try:
        # Create a temporary engine to test
        temp_engine = create_async_engine(url)
        async with temp_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await temp_engine.dispose()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/settings/init-db")
async def api_init_db(body: dict):
    url = body.get("url")
    if not url: raise HTTPException(400, "Missing URL")
    
    from sqlalchemy.ext.asyncio import create_async_engine
    from ..core.db import Base
    try:
        # Create directories if SQLite
        if url.startswith("sqlite"):
            db_path = url.split(":///")[1]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
        temp_engine = create_async_engine(url)
        async with temp_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await temp_engine.dispose()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/settings/restart")
async def restart_server():
    """Trigger a server restart by exiting the process.
    Requires the server to be run with a watcher or a loop in start.sh.
    """
    import os
    import signal
    
    # Give the response time to reach the client
    def _kill():
        import time
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGTERM)
        
    import threading
    threading.Thread(target=_kill).start()
    
    return {"status": "restarting"}
