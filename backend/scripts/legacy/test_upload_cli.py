import asyncio
from backend.core.session import session_manager
from backend.core.db import load_nodes_db
from backend.core.vault import load_credentials

async def main():
    nodes = await load_nodes_db()
    node = nodes["n1780913184722"]
    un, pw = await load_credentials("n1780913184722")
    node["username"] = un
    node["password"] = pw
    
    print("Uploading nr_mcu_cli.py...")
    success, err = await session_manager.upload_file("n1780913184722", node, "/app/backend/scripts/nr_mcu_cli.py", "/tmp/nr_scripts/nr_mcu_cli.py")
    print(f"Success: {success}, Error: {err}")

asyncio.run(main())
