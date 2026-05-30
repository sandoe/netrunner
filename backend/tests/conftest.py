import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Force SQLite to use in-memory database for testing BEFORE importing anything
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from backend.main import app
from backend.core.db import init_db, engine, Base

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    # Setup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Teardown
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def anon_client():
    """Unauthenticated client (for testing that auth is enforced)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def client():
    """Authenticated client — logs in as the demo admin and sets the bearer token."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        token = resp.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac
