import asyncio
from backend.core.db import load_nodes_db
from backend.routers.nodes import _get_node_with_creds
async def main():
    nodes = await load_nodes_db()
    for nid, node in nodes.items():
        if node.get("name") == "Linux":
            creds = await _get_node_with_creds(nid, nodes)
            print(creds.get("password", ""))
asyncio.run(main())
