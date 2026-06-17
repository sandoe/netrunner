import asyncio
from backend.core.db import load_nodes_db
from backend.routers.nodes import _get_node_with_creds
from backend.core.session import session_manager

async def main():
    nodes = await load_nodes_db()
    for nid, node in nodes.items():
        if node.get("name") in ["Linux", "rpi"]:
            creds = await _get_node_with_creds(nid, nodes)
            pwd = creds.get("password", "")
            escaped_pwd = pwd.replace("'", "'\\''")
            cmd = f"echo '{escaped_pwd}' | sudo -S rfkill unblock bluetooth; echo '{escaped_pwd}' | sudo -S hciconfig hci0 down; echo '{escaped_pwd}' | sudo -S hciconfig hci0 up"
            try:
                res = await session_manager.run(nid, creds, [cmd])
                print(f"Node {node.get('name')} BT Reset:\\n{res[0][0]['output']}")
            except Exception as e:
                print(f"Error on {node.get('name')}: {e}")

asyncio.run(main())
