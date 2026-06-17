import sys, os
sys.path.append('/home/aso/Dokumenter/github/netrunner/backend')
from core.session import SessionManager
import asyncio

async def main():
    manager = SessionManager()
    await manager.init_db()
    for node in manager.nodes.values():
        if node["name"] == "rpi":
            success, _ = await manager.open(node["id"], node)
            if success:
                session = manager.get_session(node["id"])
                session.run_command("pkill -9 -f netrunner-bruteforcer")
                session.run_command("pkill -9 hydra")
                print("Killed on rpi")

asyncio.run(main())
