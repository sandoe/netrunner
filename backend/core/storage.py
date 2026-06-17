import asyncio
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import time
import logging

from backend.routers.settings import load_settings, save_settings
from .events import record_event

DATA_DIR = Path("data")
POSTGRES_DIR = DATA_DIR / "postgres"
INFLUXDB_DIR = DATA_DIR / "influxdb2"
LOGS_DIR = DATA_DIR / "logs"

def get_dir_size_mb(path: Path) -> float:
    """Returns the total size of a directory in MB."""
    if not path.exists():
        return 0.0
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024)

async def _rotate_influxdb():
    from .db import get_influx_client, INFLUXDB_BUCKET, INFLUXDB_ORG
    client = get_influx_client()
    delete_api = client.delete_api()
    
    # Delete data older than 24 hours to free up space (simple auto-rotation)
    start = "1970-01-01T00:00:00Z"
    # End is 24 hours ago
    end = (datetime.utcnow() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        await delete_api.delete(start, end, "", bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG)
        record_event("warning", "system", "STORAGE", "Storage Limit", f"InfluxDB limit exceeded. Auto-rotated data older than 24h.")
    except Exception as e:
        logging.error(f"Failed to rotate InfluxDB: {e}")

async def _rotate_postgres():
    from .db import get_session
    from sqlalchemy import text
    try:
        async for session in get_session():
            # Delete 10,000 oldest events (example rotation)
            await session.execute(text("DELETE FROM events WHERE id IN (SELECT id FROM events ORDER BY created_at ASC LIMIT 10000)"))
            # Delete oldest settings history, etc.
            await session.commit()
            break
        record_event("warning", "system", "STORAGE", "Storage Limit", f"Postgres limit exceeded. Auto-rotated oldest events.")
    except Exception as e:
        logging.error(f"Failed to rotate Postgres: {e}")

async def _rotate_logs():
    if not LOGS_DIR.exists():
        return
    try:
        # Simple rotation: delete oldest files
        files = sorted(LOGS_DIR.glob("*.*"), key=os.path.getmtime)
        if files:
            for f in files[:len(files)//2 + 1]: # Delete half the files
                f.unlink()
        record_event("warning", "system", "STORAGE", "Storage Limit", f"Logs limit exceeded. Auto-rotated log files.")
    except Exception as e:
        logging.error(f"Failed to rotate logs: {e}")

async def check_storage_limits():
    """Background task to monitor sizes and enforce limits."""
    while True:
        try:
            settings = await load_settings()
            
            # Default limits
            max_pg_mb = float(settings.get("max_postgres_mb", 5000))
            max_if_mb = float(settings.get("max_influxdb_mb", 10000))
            max_lg_mb = float(settings.get("max_logs_mb", 1000))
            
            pg_size = get_dir_size_mb(POSTGRES_DIR)
            if_size = get_dir_size_mb(INFLUXDB_DIR)
            lg_size = get_dir_size_mb(LOGS_DIR)
            
            if pg_size > max_pg_mb:
                await _rotate_postgres()
                
            if if_size > max_if_mb:
                await _rotate_influxdb()
                
            if lg_size > max_lg_mb:
                await _rotate_logs()
                
        except Exception as e:
            logging.error(f"Storage monitor error: {e}")
            
        await asyncio.sleep(60) # Check every minute

def get_storage_stats() -> dict:
    return {
        "postgres": {"size_mb": get_dir_size_mb(POSTGRES_DIR)},
        "influxdb": {"size_mb": get_dir_size_mb(INFLUXDB_DIR)},
        "logs": {"size_mb": get_dir_size_mb(LOGS_DIR)}
    }
