import asyncio
from backend.core.db import load_nodes_db
from backend.routers.nodes import _get_node_with_creds
from backend.core.session import session_manager

async def main():
    nodes = await load_nodes_db()
    for nid, node in nodes.items():
        if node.get("name") in ["Linux"]:
            creds = await _get_node_with_creds(nid, nodes)
            print(f"Restarting agent on {nid}...")
            pwd = creds.get("password", "")
            escaped_pwd = pwd.replace("'", "'\\''")
            cmd = f"echo '{escaped_pwd}' | sudo -S systemctl restart netrunner-agent; echo '{escaped_pwd}' | sudo -S journalctl -u netrunner-agent -n 20 --no-pager"
            try:
                res = await session_manager.run(nid, creds, [cmd])
                print(f"Result: {res}")
            except Exception as e:
                print(f"Error: {e}")

asyncio.run(main())
