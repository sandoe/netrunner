import pytest
from httpx import AsyncClient

from backend.core.db import load_beacon_nodes_db
from backend.core.vault import load_credentials


@pytest.mark.asyncio
async def test_beacons_require_auth(anon_client: AsyncClient):
    assert (await anon_client.get("/api/wifi/beacons")).status_code == 401
    assert (
        await anon_client.post("/api/wifi/deploy", json={"node_id": "x"})
    ).status_code == 401


@pytest.mark.asyncio
async def test_beacon_password_stored_in_vault_not_db(client: AsyncClient):
    payload = {
        "id": "beacon_test_1",
        "ip": "10.0.0.5",
        "username": "pi",
        "password": "s3cret-ssh-pw",
        "target_server_ip": "10.0.0.1",
    }
    resp = await client.post("/api/wifi/beacons", json=payload)
    assert resp.status_code == 200

    # The beacon row must NOT hold the plaintext password
    rows = await load_beacon_nodes_db()
    row = next(r for r in rows if r["id"] == "beacon_test_1")
    assert row["password"] == ""

    # ...but the vault must hold it (encrypted at rest)
    user, pw = await load_credentials("beacon:beacon_test_1")
    assert user == "pi" and pw == "s3cret-ssh-pw"

    # ...and the API must never return it to the client
    listing = (await client.get("/api/wifi/beacons")).json()["beacons"]
    assert all("password" not in b for b in listing)
