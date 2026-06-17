import asyncio
from backend.core.db import load_devices_db

async def main():
    devices = await load_devices_db()
    for d in devices:
        print(d.get("mac"), d.get("name"), d.get("nodes"))

asyncio.run(main())
