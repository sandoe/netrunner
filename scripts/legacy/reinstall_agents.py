import asyncio
from backend.core.db import load_nodes_db
from backend.core.vault import load_credentials
from backend.core.session import session_manager
from backend.routers.defense import install_script

async def main():
    nodes = await load_nodes_db()
    for nid, node in nodes.items():
        if node.get("threat_monitoring"):
            print(f"Reinstalling agent on {nid}...")
            username, password = await load_credentials(nid)
            node["username"] = username
            node["password"] = password
            
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
            
            res, err = await session_manager.run(nid, node, [cmd])
            print(f"Result for {nid}: {res}, Err: {err}")

asyncio.run(main())
