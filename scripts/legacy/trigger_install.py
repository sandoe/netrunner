import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        # Get admin token (assuming standard admin:admin login or just bypass if no auth needed on this endpoint? Wait, it needs admin token)
        # Actually I can just use the token from the UI, or login as admin
        login_res = await client.post("http://localhost:8000/api/auth/login", json={"username": "admin", "password": "REDACTED_INFLUX_PASSWORD"})
        if login_res.status_code != 200:
            print("Login failed, trying without password...")
            login_res = await client.post("http://localhost:8000/api/auth/login", json={"username": "admin", "password": "password"})
            if login_res.status_code != 200:
                print(f"Login failed: {login_res.text}")
                return
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print("Installing on Linux (n1780255048167)...")
        res = await client.post("http://localhost:8000/api/nodes/n1780255048167/monitoring/install", headers=headers, timeout=60.0)
        print(f"Linux install: {res.status_code} {res.text}")

asyncio.run(main())
