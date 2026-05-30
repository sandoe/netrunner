import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_nodes_require_auth(anon_client: AsyncClient):
    # Protected router must reject unauthenticated access
    assert (await anon_client.get("/api/nodes")).status_code == 401
    assert (await anon_client.post("/api/nodes", json={"name": "x"})).status_code == 401

@pytest.mark.asyncio
async def test_login_rejects_wrong_password(anon_client: AsyncClient):
    bad = await anon_client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert bad.status_code == 401
    ok = await anon_client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert ok.status_code == 200 and ok.json().get("access_token")

@pytest.mark.asyncio
async def test_get_nodes_empty(client: AsyncClient):
    response = await client.get("/api/nodes")
    assert response.status_code == 200
    assert response.json() == {}

@pytest.mark.asyncio
async def test_add_and_get_node(client: AsyncClient):
    # Add a node
    payload = {
        "id": "test_node_1",
        "name": "Test Server",
        "host": "192.168.1.100",
        "port": 22,
        "username": "root",
        "device_type": "linux",
        "tags": ["test", "server"]
    }
    
    post_response = await client.post("/api/nodes", json=payload)
    assert post_response.status_code == 200 or post_response.status_code == 201
    
    # Retrieve the node
    get_response = await client.get("/api/nodes")
    assert get_response.status_code == 200
    nodes = get_response.json()
    
    assert len(nodes) == 1
    node_id = list(nodes.keys())[0]
    node = nodes[node_id]
    assert node["name"] == "Test Server"
    assert node["host"] == "192.168.1.100"
    assert node["port"] == 22
    assert "test" in node["tags"]
