import asyncio
import sys
from pathlib import Path

# Add backend to path so we can import modules
sys.path.append("/app/backend")

from core.db import save_node_db, load_nodes_db
from core.vault import store_credentials

async def main():
    nodes = await load_nodes_db()
    
    # 172.21.0.2 is netrunner-sw1
    # 172.21.0.3 is netrunner-sw2
    
    sw1 = {
        "id": "node-test-sw1",
        "name": "netrunner-sw1",  # Match docker container name
        "device_type": "switch",
        "host": "172.21.0.2",
        "port": 22,
        "transport": "ssh",
        "tags": ["test", "docker"]
    }
    
    sw2 = {
        "id": "node-test-sw2",
        "name": "netrunner-sw2",  # Match docker container name
        "device_type": "switch",
        "host": "172.21.0.3",
        "port": 22,
        "transport": "ssh",
        "tags": ["test", "docker"]
    }

    print("Saving node-test-sw1...")
    await save_node_db(sw1)
    await store_credentials("node-test-sw1", "root", "root")

    print("Saving node-test-sw2...")
    await save_node_db(sw2)
    await store_credentials("node-test-sw2", "root", "root")

    print("Nodes created.")

if __name__ == "__main__":
    asyncio.run(main())
