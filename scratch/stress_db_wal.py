import asyncio
import time
import sys
import os
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.core.db import save_node_db, load_nodes_db, Base, DATABASE_URL

# Re-create engine with NullPool and pragmas
custom_engine = create_async_engine(DATABASE_URL, poolclass=NullPool)

from sqlalchemy import event
@event.listens_for(custom_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

import backend.core.db
backend.core.db.engine = custom_engine
backend.core.db.AsyncSessionLocal = async_sessionmaker(custom_engine, expire_on_commit=False)

async def setup():
    async with custom_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def writer_task(task_id: int, num_writes: int):
    success = 0
    errors = 0
    for i in range(num_writes):
        node = {
            "id": f"node_{task_id}_{i}",
            "name": f"Node {task_id}-{i}",
            "host": "127.0.0.1",
            "port": 22,
            "username": "admin",
            "transport": "ssh",
            "device_type": "router",
            "created": str(time.time()),
            "tags": ["test"],
            "metadata": {"task": task_id, "iter": i},
            "threat_monitoring": False
        }
        try:
            await save_node_db(node)
            success += 1
        except Exception as e:
            errors += 1
    return success, errors

async def reader_task(task_id: int, num_reads: int):
    success = 0
    errors = 0
    for i in range(num_reads):
        try:
            await load_nodes_db()
            success += 1
        except Exception as e:
            errors += 1
    return success, errors

async def main():
    await setup()
    
    num_writers = 200
    num_readers = 100
    ops_per_task = 50
    
    print(f"Starting WAL stress test with {num_writers} writers and {num_readers} readers, {ops_per_task} ops each.")
    start_time = time.time()
    
    tasks = []
    for i in range(num_writers):
        tasks.append(writer_task(i, ops_per_task))
    for i in range(num_readers):
        tasks.append(reader_task(i + num_writers, ops_per_task))
        
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    total_success = sum(r[0] for r in results)
    total_errors = sum(r[1] for r in results)
    
    print(f"\nWAL Stress Test Results:")
    print(f"Time taken: {end_time - start_time:.2f} seconds")
    print(f"Total Successful Ops: {total_success}")
    print(f"Total Failed Ops: {total_errors}")

if __name__ == "__main__":
    asyncio.run(main())
