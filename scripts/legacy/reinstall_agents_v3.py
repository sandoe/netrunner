import asyncio
from backend.core.db import load_nodes_db
from backend.routers.nodes import _get_node_with_creds
from backend.routers.defense import install_script
from backend.core.session import session_manager
from backend.core.auth import get_admin_token
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
            script = install_script.format(base_url=base_url, token=token, nid=nid)
            b64_script = base64.b64encode(script.encode()).decode()
            cmd = f"echo {b64_script} | base64 -d | sudo bash"
            
            try:
                res, err = await session_manager.run(nid, node_with_creds, [cmd])
                print(f"Result for {nid}: {res}, Err: {err}")
            except Exception as e:
                print(f"Failed to connect to {nid}: {e}")

asyncio.run(main())
