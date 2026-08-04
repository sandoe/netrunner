from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import time

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from backend.core.db import get_db, engine
from backend.routers.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/database", tags=["Database Control Room"])


class QueryPayload(BaseModel):
    query: str
    target: str = "postgres"  # "postgres" or "influxdb"


class ExfiltratePayload(BaseModel):
    source_dsn: str  # e.g. postgresql+asyncpg://user:pass@host:port/db
    source_table: str
    target_table: str


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    """Get overall database health and size."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")

    stats = {
        "postgres": {
            "status": "offline",
            "tables": 0,
            "size": "Unknown",
            "engine": "unknown",
        },
        "influxdb": {"status": "offline", "buckets": 0},
    }

    # Check Postgres / SQLite
    try:
        from backend.core.db import DATABASE_URL

        if "sqlite" in DATABASE_URL:
            # SQLite queries
            result = await db.execute(
                text("SELECT count(*) FROM sqlite_master WHERE type='table'")
            )
            tables = result.scalar()

            # Get file size
            db_path = DATABASE_URL.split(":///")[1]
            import os

            size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0
            size = f"{size_bytes / (1024*1024):.2f} MB"

            stats["postgres"] = {
                "status": "online",
                "tables": tables,
                "size": size,
                "engine": "sqlite",
            }
        else:
            # Get number of tables
            result = await db.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
                )
            )
            tables = result.scalar()

            # Get DB size
            result = await db.execute(
                text("SELECT pg_size_pretty(pg_database_size(current_database()))")
            )
            size = result.scalar()

            stats["postgres"] = {
                "status": "online",
                "tables": tables,
                "size": size,
                "engine": "postgres",
            }
    except Exception as e:
        stats["postgres"]["error"] = str(e)

    # Check InfluxDB
    from backend.core.db import get_influx_client, INFLUXDB_BUCKET

    try:
        client = get_influx_client()
        ready = await client.ping()
        if ready:
            stats["influxdb"]["status"] = "online"
            stats["influxdb"]["buckets"] = 1  # We know 'traffic' bucket exists
    except Exception as e:
        stats["influxdb"]["error"] = str(e)

    # Append Storage usage and limits
    from backend.core.storage import get_storage_stats
    from backend.routers.settings import load_settings

    storage = get_storage_stats()
    sys_settings = await load_settings()
    stats["storage"] = {
        "postgres": {
            "used_mb": storage["postgres"]["size_mb"],
            "limit_mb": float(sys_settings.get("max_postgres_mb", 5000)),
        },
        "influxdb": {
            "used_mb": storage["influxdb"]["size_mb"],
            "limit_mb": float(sys_settings.get("max_influxdb_mb", 10000)),
        },
        "logs": {
            "used_mb": storage["logs"]["size_mb"],
            "limit_mb": float(sys_settings.get("max_logs_mb", 1000)),
        },
    }

    return stats


@router.get("/tables")
async def get_tables(
    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    """Get list of tables from the database."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    try:
        from backend.core.db import DATABASE_URL

        if "sqlite" in DATABASE_URL:
            result = await db.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            )
            tables = [row[0] for row in result.fetchall()]
        else:
            result = await db.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
            )
            tables = [row[0] for row in result.fetchall()]
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def execute_query(
    payload: QueryPayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Run a raw SQL or Flux query."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")

    if payload.target == "postgres":
        try:
            # Need to commit if it's a DML
            result = await db.execute(text(payload.query))
            await db.commit()

            # If it's a SELECT, return rows
            if payload.query.strip().lower().startswith("select"):
                rows = [dict(row._mapping) for row in result.fetchall()]
                return {"status": "ok", "rows": rows, "count": len(rows)}
            else:
                return {"status": "ok", "message": "Query executed successfully."}
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    elif payload.target == "influxdb":
        from backend.core.db import get_influx_client, INFLUXDB_ORG

        try:
            client = get_influx_client()
            query_api = client.query_api()
            result = await query_api.query(query=payload.query, org=INFLUXDB_ORG)

            rows = []
            for table in result:
                for record in table.records:
                    rows.append(record.values)
            return {"status": "ok", "rows": rows, "count": len(rows)}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    raise HTTPException(status_code=400, detail="Invalid target database")


@router.post("/exfiltrate")
async def run_exfiltration(
    payload: ExfiltratePayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Connect to a foreign database, dump its table, and save locally."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")

    try:
        ext_engine = create_async_engine(payload.source_dsn)

        async with ext_engine.connect() as ext_conn:
            # Dump data
            query = text(f"SELECT * FROM {payload.source_table}")
            result = await ext_conn.execute(query)
            rows = [dict(row._mapping) for row in result.fetchall()]

        if not rows:
            return {
                "status": "ok",
                "message": "Source table is empty",
                "rows_migrated": 0,
            }

        # Create target table dynamically if it doesn't exist
        columns = rows[0].keys()
        col_defs = ", ".join(
            [f"{c} TEXT" for c in columns]
        )  # Treat all as text for safety during exfiltration
        create_table = f"CREATE TABLE IF NOT EXISTS exfiltrated_{payload.target_table} (exfiltration_id SERIAL PRIMARY KEY, {col_defs})"

        await db.execute(text(create_table))

        # Insert rows
        for row in rows:
            cols = ", ".join(row.keys())
            # Simple parameterization
            placeholders = ", ".join([f":{k}" for k in row.keys()])
            insert_q = text(
                f"INSERT INTO exfiltrated_{payload.target_table} ({cols}) VALUES ({placeholders})"
            )
            await db.execute(insert_q, row)

        await db.commit()
        return {
            "status": "ok",
            "message": f"Successfully exfiltrated {len(rows)} rows.",
            "rows_migrated": len(rows),
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Exfiltration failed: {str(e)}")
