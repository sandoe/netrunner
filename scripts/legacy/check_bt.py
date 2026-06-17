import asyncio
from backend.core.db import load_nodes_db
from backend.routers.nodes import _get_node_with_creds
from backend.core.session import session_manager

async def main():
    nodes = await load_nodes_db()
    for nid, node in nodes.items():
        if node.get("name") == "rpi":
            creds = await _get_node_with_creds(nid, nodes)
            print(f"Checking btmgmt on {nid} ({node.get('name')})...")
            try:
                res = await session_manager.run(nid, creds, ["sudo btmgmt find"])
                print(f"Result: {res}")
            except Exception as e:
                print(f"Error: {e}")

asyncio.run(main())
