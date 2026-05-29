import pytest
from httpx import AsyncClient

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
