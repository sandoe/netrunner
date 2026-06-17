import asyncio
from backend.routers.defense import api_install_monitoring
from fastapi import Request
from unittest.mock import MagicMock

async def main():
    try:
        # Mock Request
        req = MagicMock(spec=Request)
        req.url.hostname = "192.168.1.17"
        
        print("Installing on Linux (n1780255048167)...")
        res = await api_install_monitoring("n1780255048167", req)
        print(f"Linux install: {res}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
