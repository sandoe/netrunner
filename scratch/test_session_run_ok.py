import asyncio
import sys
import json
from pathlib import Path

# Add project root to sys.path
project_root = str(Path("/home/aso/repos/projects/netrunner").resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.routers.nodes import load_nodes, _get_node_with_creds
from backend.core.session import session_manager

async def main():
    nodes = await load_nodes()
    nid = "n1779455331493"
    node = await _get_node_with_creds(nid, nodes)
    
    print("Opening session first...")
    success, err = await session_manager.open(nid, node)
    print(f"Open result: {success}, error: {err}")
    
    if success:
        print("Running command sequence through session_manager...")
        results, err = await session_manager.run(nid, node, ["ip addr show", "ip link show"])
        print("Error:", err)
        print("Results:")
        print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
