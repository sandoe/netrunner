import pytest
from unittest.mock import patch
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


@patch("backend.routers.graph.load_nodes_db")
@patch("backend.routers.graph.load_links_db")
def test_get_graph_success(mock_load_links_db, mock_load_nodes_db):
    """Ensure GET /api/v1/graph returns HTTP 200 with nodes and links arrays."""

    # Mock return values for nodes and links
    mock_load_nodes_db.return_value = {
        "node1": {"id": "node1", "name": "Node 1"},
        "node2": {"id": "node2", "name": "Node 2"},
    }

    mock_load_links_db.return_value = {
        "link1": {"id": "link1", "source": "node1", "target": "node2"}
    }

    response = client.get("/api/v1/graph")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert "nodes" in data, "Payload missing 'nodes'"
    assert "links" in data, "Payload missing 'links'"

    assert isinstance(data["nodes"], list)
    assert isinstance(data["links"], list)

    assert len(data["nodes"]) == 2
    assert len(data["links"]) == 1

    assert data["nodes"][0]["id"] == "node1"
    assert data["links"][0]["id"] == "link1"
