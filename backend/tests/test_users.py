import pytest
from httpx import AsyncClient

from backend.routers.auth import seed_default_users
from backend.core.db import delete_user_db, get_user_db


async def _token(client: AsyncClient, username, password):
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    return r.status_code, (
        r.json().get("access_token") if r.status_code == 200 else None
    )


@pytest.mark.asyncio
async def test_user_mgmt_requires_admin(client: AsyncClient, anon_client: AsyncClient):
    # anon cannot list/create
    assert (await anon_client.get("/api/auth/users")).status_code == 401
    # analyst (non-admin) cannot create users
    _, analyst_tok = await _token(anon_client, "analyst", "analyst")
    h = {"Authorization": f"Bearer {analyst_tok}"}
    resp = await anon_client.post(
        "/api/auth/users",
        headers=h,
        json={"username": "x", "password": "y", "role": "analyst"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_creates_user_who_can_login(client: AsyncClient):
    resp = await client.post(
        "/api/auth/users",
        json={"username": "neo", "password": "trinity", "role": "analyst"},
    )
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
    assert (
        await client.post(
            "/api/auth/users",
            json={"username": "neo", "password": "p", "role": "analyst"},
        )
    ).status_code == 409


@pytest.mark.asyncio
async def test_cannot_delete_self_or_last_admin(client: AsyncClient):
    # admin (the caller) cannot delete itself
    assert (await client.delete("/api/auth/users/admin")).status_code == 400


@pytest.mark.asyncio
async def test_default_admin_is_recreated_when_missing(client: AsyncClient):
    await client.post(
        "/api/auth/users",
        json={"username": "teacher", "password": "secret", "role": "admin"},
    )
    await delete_user_db("admin")

    assert await get_user_db("admin") is None

    await seed_default_users()

    code_ok, token = await _token(client, "admin", "admin")
    assert code_ok == 200
    assert token


@pytest.mark.asyncio
async def test_student_deployment_rejects_privileged_logins_and_existing_tokens(
    anon_client: AsyncClient, monkeypatch
):
    code_ok, admin_token = await _token(anon_client, "admin", "admin")
    assert code_ok == 200 and admin_token

    monkeypatch.setenv("NETRUNNER_DEPLOYMENT_MODE", "student")

    assert (await _token(anon_client, "admin", "admin"))[0] == 401
    assert (await _token(anon_client, "analyst", "analyst"))[0] == 401
    assert (await _token(anon_client, "student", "student"))[0] == 200

    response = await anon_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_student_deployment_does_not_recreate_privileged_accounts(
    client: AsyncClient, monkeypatch
):
    await delete_user_db("admin")
    await delete_user_db("analyst")
    monkeypatch.setenv("NETRUNNER_DEPLOYMENT_MODE", "student")

    await seed_default_users()

    assert await get_user_db("admin") is None
    assert await get_user_db("analyst") is None
    assert await get_user_db("student") is not None
