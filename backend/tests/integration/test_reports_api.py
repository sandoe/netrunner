import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.routers.auth import get_current_user


@pytest.fixture(autouse=True)
def bypass_auth():
    app.dependency_overrides[get_current_user] = lambda: {
        "username": "admin",
        "role": "admin",
    }
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def test_get_reports_success():
    """Ensure GET /api/v1/reports returns HTTP 200 and JSON payload contains aggregated data."""
    response = client.get("/api/v1/reports")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert "nodes" in data, "Payload missing 'nodes'"
    assert "links" in data, "Payload missing 'links'"
    assert "alerts" in data, "Payload missing 'alerts'"
