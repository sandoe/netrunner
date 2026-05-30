import pytest
from httpx import AsyncClient


async def _token(client: AsyncClient, username, password):
    r = await client.post("/api/auth/login", json={"username": username, "password": password})
    return r.status_code, (r.json().get("access_token") if r.status_code == 200 else None)


@pytest.mark.asyncio
async def test_user_mgmt_requires_admin(client: AsyncClient, anon_client: AsyncClient):
    # anon cannot list/create
    assert (await anon_client.get("/api/auth/users")).status_code == 401
    # analyst (non-admin) cannot create users
    _, analyst_tok = await _token(anon_client, "analyst", "analyst")
    h = {"Authorization": f"Bearer {analyst_tok}"}
    resp = await anon_client.post("/api/auth/users", headers=h, json={"username": "x", "password": "y", "role": "analyst"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_creates_user_who_can_login(client: AsyncClient):
    resp = await client.post("/api/auth/users", json={"username": "neo", "password": "trinity", "role": "analyst"})
    assert resp.status_code == 200

    # listing must not leak hashes/salts
    listing = (await client.get("/api/auth/users")).json()["users"]
    neo = next(u for u in listing if u["username"] == "neo")
    assert neo["role"] == "analyst"
    assert "password_hash" not in neo and "salt" not in neo

    # the new user can log in; wrong password is rejected
    code_ok, tok = await _token(client, "neo", "trinity")
    assert code_ok == 200 and tok
    code_bad, _ = await _token(client, "neo", "wrong")
    assert code_bad == 401

    # duplicate creation is rejected
    assert (await client.post("/api/auth/users", json={"username": "neo", "password": "p", "role": "analyst"})).status_code == 409


@pytest.mark.asyncio
async def test_cannot_delete_self_or_last_admin(client: AsyncClient):
    # admin (the caller) cannot delete itself
    assert (await client.delete("/api/auth/users/admin")).status_code == 400
