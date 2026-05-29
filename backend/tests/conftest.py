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
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
