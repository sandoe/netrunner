import asyncio
from backend.core.db import load_nodes_db
from backend.routers.nodes import _get_node_with_creds
from backend.core.session import session_manager
from backend.routers.auth import get_admin_token
import base64
import socket

async def main():
    nodes = await load_nodes_db()
    
    # Calculate base_url
    lan_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        lan_ip = s.getsockname()[0]
        s.close()
    except:
        pass
    base_url = f"http://{lan_ip}:8000"
    token = get_admin_token()

    for nid, node in nodes.items():
        if node.get("threat_monitoring"):
            print(f"Reinstalling agent on {nid} ({node.get('name')})...")
            
            node_with_creds = await _get_node_with_creds(nid, nodes)
            script = f"""
    ARCH=$(uname -m)
    if [ "$ARCH" = "x86_64" ]; then
        DL_ARCH="amd64"
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        DL_ARCH="arm64"
    else
        echo "Error: Unsupported architecture $ARCH"
        exit 1
    fi

    echo "Downloading Netrunner Agent ($DL_ARCH) from {base_url}..."
    curl -sL "{base_url}/api/agent/download/$DL_ARCH" -o /usr/local/bin/netrunner-agent || wget -qO /usr/local/bin/netrunner-agent "{base_url}/api/agent/download/$DL_ARCH"

    if [ ! -s /usr/local/bin/netrunner-agent ]; then
        echo "Error: Failed to download agent binary. Check network connectivity."
        exit 1
    fi

    chmod +x /usr/local/bin/netrunner-agent

    cat << 'INNEREOF' > /etc/systemd/system/netrunner-agent.service
[Unit]
Description=Netrunner Threat Monitor Agent
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/netrunner-agent --target {base_url} --token {token} --node {nid}
Restart=always
RestartSec=5
INNEREOF

    systemctl daemon-reload
    systemctl restart netrunner-agent
            """
            b64_script = base64.b64encode(script.encode()).decode()
            cmd = f"echo {b64_script} | base64 -d | sudo bash"
            
            try:
                res, err = await session_manager.run(nid, node_with_creds, [cmd])
                print(f"Result for {nid}: {res}, Err: {err}")
            except Exception as e:
                print(f"Failed to connect to {nid}: {e}")

asyncio.run(main())
