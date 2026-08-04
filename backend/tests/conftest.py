import os
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Force SQLite to use a local test database for testing BEFORE importing anything
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_netrunner.db"
os.environ["NETRUNNER_ADMIN_PASSWORD"] = "admin"
os.environ["NETRUNNER_ANALYST_PASSWORD"] = "analyst"
os.environ["NETRUNNER_STUDENT_PASSWORD"] = "student"
os.environ["NETRUNNER_DEPLOYMENT_MODE"] = "server"
os.environ["NETRUNNER_INTERNAL_TOKEN"] = "test-internal-token"

from backend.main import app # noqa: E402

app.state.limiter.enabled = False

from backend.core.db import engine, Base


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    print("Executing setup_db fixture...")
    # Setup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    # Seed default users (lifespan doesn't run under ASGITransport)
    from backend.routers.auth import seed_default_users
    import backend.core.db as db

    db._NODES_CACHE = None
    db._NODES_CACHE_TIME = 0.0
    await seed_default_users()
    yield
    # Teardown
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def anon_client():
    """Unauthenticated client (for testing that auth is enforced)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def client():
    """Authenticated client — logs in as the demo admin and sets the bearer token."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/auth/login", json={"username": "admin", "password": "admin"}
        )
        token = resp.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac
