import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
project_root = str(Path("/home/aso/repos/projects/netrunner").resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.core.session import session_manager

async def test_collision_prevention():
    nid = "test_node_123"
    node = {
        "host": "127.0.0.1",
        "port": 9999,
        "transport": "telnet"
    }

    print("--- 1. WebSocket terminal starting: calling close(nid) ---")
    session_manager.close(nid)
    assert nid in session_manager._no_auto_open, "Node must be marked in _no_auto_open"
    print("Success: Node marked in _no_auto_open.")

    print("\n--- 2. Background telemetry runs: calling run() with auto=True ---")
    results, err = await session_manager.run(nid, node, ["show ip route"])
    print(f"Results: {results}, Error: {repr(err)}")
    assert "intentionally disconnected" in str(err), "Should fail with intentionally disconnected"
    print("Success: Connection collision avoided.")

    print("\n--- 3. WebSocket terminal closing: discarding from _no_auto_open ---")
    session_manager._no_auto_open.discard(nid)
    assert nid not in session_manager._no_auto_open, "Node must be removed from _no_auto_open"
    print("Success: Node removed from _no_auto_open.")

    print("\n--- 4. Subsequent background telemetry tries again ---")
    # This should attempt standard connection and fail with socket/connection error rather than "intentionally disconnected"
    results, err = await session_manager.run(nid, node, ["show ip route"])
    print(f"Results: {results}, Error: {repr(err)}")
    assert "intentionally disconnected" not in str(err), "Should not fail with intentionally disconnected anymore"
    print("Success: Standard connection flow resumed.")

if __name__ == "__main__":
    asyncio.run(test_collision_prevention())
