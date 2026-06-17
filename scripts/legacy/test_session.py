import asyncio
from backend.core.db import load_nodes_db
from backend.core.session import session_manager

async def main():
    nodes = await load_nodes_db()
    for node_id, node in nodes.items():
        results, err = await session_manager.run(node_id, node, ["which pkill", "which lsof"])
        print(f"Node {node_id}: {results}")
        if err: print(f"Error: {err}")

asyncio.run(main())
