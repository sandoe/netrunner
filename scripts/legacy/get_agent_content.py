import asyncio
from backend.core.db import load_nodes_db
from backend.routers.nodes import _get_node_with_creds
from backend.core.session import session_manager

async def main():
    nodes = await load_nodes_db()
    for nid, node in nodes.items():
        if node.get("name") == "rpi":
            node_with_creds = await _get_node_with_creds(nid, nodes)
            res, err = await session_manager.run(nid, node_with_creds, ["cat /usr/local/bin/netrunner-agent"])
            print(f"RPI agent content: {res}")

asyncio.run(main())
