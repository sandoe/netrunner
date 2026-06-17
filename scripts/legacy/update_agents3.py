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
            cmd = f"""echo '{escaped_pwd}' | sudo -S bash -c '
              systemctl stop netrunner-agent
              ARCH=$(uname -m)
              if [ "$ARCH" = "x86_64" ]; then DL_ARCH="amd64"; elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then DL_ARCH="arm64"; else exit 1; fi
              rm -f /usr/local/bin/netrunner-agent
              curl -sL "http://192.168.1.17:8000/api/agent/download/$DL_ARCH" -o /usr/local/bin/netrunner-agent || wget -qO /usr/local/bin/netrunner-agent "http://192.168.1.17:8000/api/agent/download/$DL_ARCH"
              chmod +x /usr/local/bin/netrunner-agent
              systemctl start netrunner-agent
              systemctl start bluetooth
              bluetoothctl scan on &
              sleep 5
              kill %1 || true
            '"""
            try:
                res = await session_manager.run(nid, creds, [cmd])
                print(f"Node {node.get('name')} update:\\n{res[0][0]['output']}")
            except Exception as e:
                print(f"Error on {node.get('name')}: {e}")

asyncio.run(main())
