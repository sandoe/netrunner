import asyncio
from backend.core.db import load_nodes_db, save_node_db
from backend.routers.defense import _get_node_with_creds, install_script
from backend.core.session import session_manager

async def main():
    nodes = await load_nodes_db()
    for nid, node in nodes.items():
        if node.get("threat_monitoring"):
            print(f"Reinstalling agent on {nid}...")
            
            node_with_creds = await _get_node_with_creds(nid, nodes)
            
            # Use base_url logic from defense.py
            base_url = "http://localhost:8000"
            import socket
            lan_ip = "127.0.0.1"
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("10.255.255.255", 1))
                lan_ip = s.getsockname()[0]
                s.close()
            except:
                pass
            base_url = f"http://{lan_ip}:8000"
            
            # Fetch token
            from backend.core.auth import get_admin_token
            token = get_admin_token()
            
            script = install_script.format(base_url=base_url, token=token, nid=nid)
            import base64
            b64_script = base64.b64encode(script.encode()).decode()
            cmd = f"echo {b64_script} | base64 -d | sudo bash"
            
            res, err = await session_manager.run(nid, node_with_creds, [cmd])
            print(f"Result for {nid}: {res}, Err: {err}")

asyncio.run(main())
