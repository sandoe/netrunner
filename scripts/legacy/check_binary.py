import asyncio
from backend.core.db import load_nodes_db
from backend.routers.nodes import _get_node_with_creds
from backend.core.session import session_manager

async def main():
    nodes = await load_nodes_db()
    for nid, node in nodes.items():
        if node.get("name") in ["Linux"]:
            creds = await _get_node_with_creds(nid, nodes)
            pwd = creds.get("password", "")
            escaped_pwd = pwd.replace("'", "'\\''")
            cmd = f"echo '{escaped_pwd}' | sudo -S ls -la /usr/local/bin/netrunner-agent; echo '{escaped_pwd}' | sudo -S file /usr/local/bin/netrunner-agent"
            res = await session_manager.run(nid, creds, [cmd])
            print(f"Result: {res}")

asyncio.run(main())
