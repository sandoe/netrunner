import asyncio
import time
import sys
import os

# add backend path to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.core.db import save_node_db, load_nodes_db, engine, Base

async def setup():
    async with engine.begin() as conn:
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
            print(f"Error in task {task_id} write {i}: {e}")
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
            print(f"Error in task {task_id} read {i}: {e}")
    return success, errors

async def main():
    await setup()
    
    num_writers = 20
    num_readers = 20
    ops_per_task = 50
    
    print(f"Starting stress test with {num_writers} writers and {num_readers} readers, {ops_per_task} ops each.")
    
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
    
    print(f"\nStress Test Results:")
    print(f"Time taken: {end_time - start_time:.2f} seconds")
    print(f"Total Successful Ops: {total_success}")
    print(f"Total Failed Ops: {total_errors}")

if __name__ == "__main__":
    asyncio.run(main())
