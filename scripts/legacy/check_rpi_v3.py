import asyncio
from backend.core.db import load_nodes_db
from backend.routers.nodes import _get_node_with_creds
from backend.core.session import session_manager

async def main():
    nodes = await load_nodes_db()
    for nid, node in nodes.items():
        if node.get("name") == "rpi":
            node_with_creds = await _get_node_with_creds(nid, nodes)
            res, err = await session_manager.run(nid, node_with_creds, ["strings /usr/local/bin/netrunner-agent | grep X-Node-ID || echo 'MISSING'"])
            print(f"RPI binary check: {res}")
            res, err = await session_manager.run(nid, node_with_creds, ["systemctl status netrunner-agent --no-pager | grep -i error || echo 'NO_ERRORS'"])
            print(f"RPI service errors: {res}")
            res, err = await session_manager.run(nid, node_with_creds, ["journalctl -u netrunner-agent --no-pager -n 20"])
            print(f"RPI agent logs: {res}")

asyncio.run(main())
