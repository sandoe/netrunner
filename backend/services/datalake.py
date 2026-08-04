import os
import time
import asyncio
from pathlib import Path
import pandas as pd
import duckdb
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import AsyncSessionLocal, ThreatEventModel
from core.logger import log as logger

DATALAKE_DIR = Path("data/datalake")


def init_datalake():
    DATALAKE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Data Lake directory initialized.")


async def archive_old_events(hours: int = 24):
    """
    Archives threat_events older than `hours` to a Parquet file and deletes them from SQLite.
    """
    cutoff_time = time.time() - (hours * 3600)
    filename = DATALAKE_DIR / f"archive_{int(time.time())}.parquet"

    try:
        con = duckdb.connect(":memory:")
        con.execute("INSTALL sqlite; LOAD sqlite;")
        con.execute("ATTACH 'data/netrunner.db' AS sqlite_db (TYPE SQLITE);")

        # Check if there are events to archive
        count_res = con.execute(
            f"SELECT count(*) FROM sqlite_db.threat_events WHERE timestamp < {cutoff_time}"
        ).fetchone()
        if not count_res or count_res[0] == 0:
            return

        count = count_res[0]

        # Export natively directly from SQLite file to Parquet file
        con.execute(f"""
            COPY (
                SELECT * FROM sqlite_db.threat_events
                WHERE timestamp < {cutoff_time}
            ) TO '{filename}' (FORMAT PARQUET);
        """)
        logger.info(f"Archived {count} events to {filename} using DuckDB")

        async with AsyncSessionLocal() as session:
            delete_stmt = delete(ThreatEventModel).where(
                ThreatEventModel.timestamp < cutoff_time
            )
            await session.execute(delete_stmt)
            await session.commit()
            logger.info(f"Deleted {count} archived events from hot tier (SQLite).")
    except Exception as e:
        logger.error(f"DuckDB archiver error: {e}")


def query_datalake(query_sql: str) -> list[dict]:
    """
    Executes a SQL query against the Data Lake using DuckDB.
    Expected usage: SELECT * FROM read_parquet('data/datalake/*.parquet') ...
    """
    try:
        if not list(DATALAKE_DIR.glob("*.parquet")):
            return []  # No archives yet

        con = duckdb.connect(database=":memory:")

        # Replace a placeholder table name with the parquet reader if necessary
        # We'll assume the caller passes something like `FROM threat_events`
        # and we replace it with `FROM read_parquet('data/datalake/*.parquet')`
        query_sql = query_sql.replace(
            "FROM threat_events", f"FROM read_parquet('{DATALAKE_DIR}/*.parquet')"
        )

        result_df = con.execute(query_sql).df()
        return result_df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Data Lake Query Error: {e}")
        return []


async def datalake_archiver_loop():
    """Background task to archive events periodically."""
    init_datalake()
    while True:
        try:
            # For iteration demonstration, let's archive everything older than 1 hour (or less)
            await archive_old_events(hours=1)
        except Exception as e:
            logger.error(f"Error in datalake archiver: {e}")
        await asyncio.sleep(600)  # Run every 10 minutes


# Ensure initialization on import
init_datalake()
