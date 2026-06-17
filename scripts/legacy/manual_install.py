import asyncio
from backend.core.db import load_nodes_db
from backend.routers.nodes import _get_node_with_creds
from backend.core.session import session_manager
import base64

async def main():
    nodes = await load_nodes_db()
    for nid, node in nodes.items():
        if node.get("name") in ["Linux"]:
            creds = await _get_node_with_creds(nid, nodes)
            print(f"Manually installing on {nid}...")
            
            script = """
            ARCH=$(uname -m)
            if [ "$ARCH" = "x86_64" ]; then
                DL_ARCH="amd64"
            elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
                DL_ARCH="arm64"
            else
                echo "Error: Unsupported architecture $ARCH"
                exit 1
            fi
            curl -sL "http://192.168.1.17:8000/api/agent/download/$DL_ARCH" -o /usr/local/bin/netrunner-agent || wget -qO /usr/local/bin/netrunner-agent "http://192.168.1.17:8000/api/agent/download/$DL_ARCH"
            if [ ! -s /usr/local/bin/netrunner-agent ]; then
                echo "Error: Failed to download agent binary. Check network connectivity."
                exit 1
            fi
            chmod +x /usr/local/bin/netrunner-agent
            systemctl daemon-reload
            systemctl enable netrunner-agent
            systemctl restart netrunner-agent
            echo "Installed successfully!"
            """
            
            b64_script = base64.b64encode(script.encode()).decode()
            pwd = creds.get("password", "")
            escaped_pwd = pwd.replace("'", "'\\''")
            cmd = f"echo '{escaped_pwd}' | sudo -S bash -c 'echo {b64_script} | base64 -d | bash'"
            
            try:
                res = await session_manager.run(nid, creds, [cmd])
                print(f"Result: {res}")
            except Exception as e:
                print(f"Error: {e}")

asyncio.run(main())
