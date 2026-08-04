import pytest
from httpx import AsyncClient


async def _auth_headers(client: AsyncClient, username: str, password: str) -> dict:
    response = await client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_bluetooth_devices_require_authentication(anon_client: AsyncClient):
    response = await anon_client.get("/api/bluetooth/devices")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_student_can_read_bluetooth_devices(anon_client: AsyncClient):
    headers = await _auth_headers(anon_client, "student", "student")

    response = await anon_client.get("/api/bluetooth/devices", headers=headers)

    assert response.status_code == 200
    assert "devices" in response.json()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/bluetooth/jam/00:11:22:33:44:55",
        "/api/bluetooth/unjam/00:11:22:33:44:55",
        "/api/bluetooth/enumerate/00:11:22:33:44:55",
        "/api/bluetooth/pair/00:11:22:33:44:55",
    ],
)
async def test_student_cannot_run_bluetooth_actions(
    anon_client: AsyncClient,
    endpoint: str,
):
    headers = await _auth_headers(anon_client, "student", "student")

    response = await anon_client.post(endpoint, headers=headers)

    assert response.status_code == 403
