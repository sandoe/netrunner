import asyncio
from backend.core.db import load_nodes_db
from backend.routers.nodes import _get_node_with_creds
import subprocess

async def main():
    nodes = await load_nodes_db()
    for nid, node in nodes.items():
        if node.get("name") == "Linux":
            creds = await _get_node_with_creds(nid, nodes)
            pwd = creds.get("password", "")
            cmd = f"""echo '{pwd}' | sudo -S bash -c '
              systemctl stop netrunner-agent
              cp netrunner-agent-test /usr/local/bin/netrunner-agent
              chmod +x /usr/local/bin/netrunner-agent
              systemctl start netrunner-agent
              systemctl status netrunner-agent
            '"""
            subprocess.run(cmd, shell=True)

asyncio.run(main())
