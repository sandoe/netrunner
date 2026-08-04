import pytest
from pathlib import Path
from httpx import AsyncClient

from backend.routers.auth import authenticate_ws, create_access_token


ROOT = Path(__file__).resolve().parents[2]


def test_protocol_runtime_is_packaged_in_production_image():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY protocols/ ./protocols/" in dockerfile
    assert (ROOT / "protocols" / "docker-compose.protocols.yml").is_file()


async def _headers(client: AsyncClient, username: str, password: str) -> dict:
    response = await client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_liveness_is_public_and_machine_readable(anon_client: AsyncClient):
    response = await anon_client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "netrunner",
        "version": "1.0.0",
    }


@pytest.mark.asyncio
async def test_previously_open_alert_api_now_requires_auth(anon_client: AsyncClient):
    assert (await anon_client.get("/alerts")).status_code == 401
    assert (
        await anon_client.post(
            "/alerts",
            json={"title": "test", "description": "test", "severity": "low"},
        )
    ).status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/layer2/arp-spoof"),
        ("POST", "/api/nodes/example/reboot"),
        ("POST", "/api/settings"),
        ("POST", "/alerts"),
        ("POST", "/integrations"),
        ("DELETE", "/api/network/routes"),
    ],
)
async def test_student_is_read_only_across_backend(
    anon_client: AsyncClient,
    method: str,
    path: str,
):
    headers = await _headers(anon_client, "student", "student")

    response = await anon_client.request(method, path, headers=headers, json={})

    assert response.status_code == 403
    assert response.json()["detail"] == "Student accounts are read-only"


@pytest.mark.asyncio
async def test_analyst_can_use_authenticated_write_api(anon_client: AsyncClient):
    headers = await _headers(anon_client, "analyst", "analyst")

    response = await anon_client.post(
        "/alerts",
        headers=headers,
        json={"title": "release test", "description": "test", "severity": "low"},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_internal_credentials_endpoint_requires_service_token(
    anon_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("NETRUNNER_INTERNAL_TOKEN", "internal-test-token")

    missing = await anon_client.get("/api/internal/node/missing")
    invalid = await anon_client.get(
        "/api/internal/node/missing",
        headers={"X-Netrunner-Internal-Token": "wrong"},
    )
    authenticated = await anon_client.get(
        "/api/internal/node/missing",
        headers={"X-Netrunner-Internal-Token": "internal-test-token"},
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert authenticated.status_code == 404


class _WebSocketStub:
    def __init__(self, token: str):
        self.query_params = {"token": token}
        self.accepted = False
        self.close_code = None

    async def accept(self):
        self.accepted = True

    async def close(self, code: int):
        self.close_code = code


@pytest.mark.asyncio
async def test_websocket_role_gate_denies_student_and_accepts_analyst():
    student = _WebSocketStub(
        create_access_token({"sub": "student", "role": "student"})
    )
    assert await authenticate_ws(
        student, allowed_roles=("admin", "analyst")
    ) is None
    assert student.accepted is True
    assert student.close_code == 4403

    analyst = _WebSocketStub(
        create_access_token({"sub": "analyst", "role": "analyst"})
    )
    user = await authenticate_ws(analyst, allowed_roles=("admin", "analyst"))
    assert user == {"username": "analyst", "role": "analyst"}
    assert analyst.accepted is False
