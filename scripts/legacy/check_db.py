import asyncio
from backend.core.db import load_bluetooth_db
async def main():
    bt = await load_bluetooth_db()
    for mac, dev in bt.items():
        print(f"{mac}: {dev}")

asyncio.run(main())
