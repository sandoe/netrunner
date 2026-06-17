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
    ai_provider: str = "openai"
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_model: str = "gpt-4o"
    openai_api_key: str = ""
    alienvault_api_key: str = ""
    gns3_server_url: str = "http://127.0.0.1"
    gns3_local_projects_path: str = "/home/aso/GNS3/projects"
    max_postgres_mb: float = 5000.0
    max_influxdb_mb: float = 10000.0
    max_logs_mb: float = 1000.0
    cors_origins: str = ""  # Comma-separated list of allowed origins, empty = localhost only

async def load_settings() -> dict:
    return await load_settings_db()

async def save_settings(settings: dict) -> None:
    for k, v in settings.items():
        await save_setting_db(k, str(v))

@router.get("/settings")
async def get_settings():
    s = await load_settings()
    # Mask the key for safety
    key = s.get("ai_api_key") or s.get("openai_api_key", "")
    masked = f"{key[:8]}..." if len(key) > 8 else key
    
    otx_key = s.get("alienvault_api_key", "")
    masked_otx = f"{otx_key[:8]}..." if len(otx_key) > 8 else otx_key
    
    from ..core.db import DATABASE_URL
    
    return {
        "ai_provider": s.get("ai_provider", "openai"),
        "ai_api_key_set": bool(key),
        "ai_masked_key": masked,
        "ai_base_url": s.get("ai_base_url", ""),
        "ai_model": s.get("ai_model", "gpt-4o"),
        "openai_api_key_set": bool(key),
        "masked_key": masked,
        "alienvault_api_key_set": bool(otx_key),
        "masked_alienvault_key": masked_otx,
        "gns3_server_url": s.get("gns3_server_url", "http://127.0.0.1:3080"),
        "database_url": DATABASE_URL,
        "max_postgres_mb": float(s.get("max_postgres_mb", 5000)),
        "max_influxdb_mb": float(s.get("max_influxdb_mb", 10000)),
        "max_logs_mb": float(s.get("max_logs_mb", 1000)),
        "cors_origins": s.get("cors_origins", "")
    }

@router.post("/settings")
async def update_settings(settings: dict):
    s = await load_settings()
    for key in ("ai_provider", "ai_base_url", "ai_model"):
        if key in settings:
            s[key] = settings[key]
            await save_setting_db(key, settings[key])

    if "ai_api_key" in settings:
        s["ai_api_key"] = settings["ai_api_key"]
        await save_setting_db("ai_api_key", settings["ai_api_key"])
        if (s.get("ai_provider") or "openai").lower() == "openai":
            os.environ["OPENAI_API_KEY"] = settings["ai_api_key"]

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

    for key in ("max_postgres_mb", "max_influxdb_mb", "max_logs_mb"):
        if key in settings:
            s[key] = settings[key]
            await save_setting_db(key, str(settings[key]))

    if "cors_origins" in settings:
        s["cors_origins"] = settings["cors_origins"]
        await save_setting_db("cors_origins", settings["cors_origins"])
        # Update env var for current process (requires restart to take full effect)
        os.environ["NETRUNNER_CORS_ORIGINS"] = settings["cors_origins"]

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

    restart_needed = "cors_origins" in settings
    return {"status": "ok", "restart_needed": restart_needed}

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
