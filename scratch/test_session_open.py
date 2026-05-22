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
    
    print("Opening session...")
    success, err = await session_manager.open(nid, node)
    
    if success:
        session = session_manager.get_session(nid)
        
        out = session.run_command("echo 'hello # world'")
        print("Output for '#':", repr(out))

        out = session.run_command("echo 'hello > world'")
        print("Output for '>':", repr(out))

        out = session.run_command("echo 'hello $ world'")
        print("Output for '$':", repr(out))

if __name__ == "__main__":
    asyncio.run(main())
