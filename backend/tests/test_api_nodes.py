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
async def test_internal_node_creds_for_telnet(client: AsyncClient, anon_client: AsyncClient):
    # Create a telnet node (e.g. a GNS3 console)
    payload = {
        "name": "R1", "host": "127.0.0.1", "port": 5001,
        "transport": "telnet", "device_type": "gns3",
    }
    created = await client.post("/api/nodes", json=payload)
    assert created.status_code in (200, 201)
    node_id = created.json()["id"]

    # The mux fetches creds here (endpoint is open by design) — must be 200, not 500
    r = await anon_client.get(f"/api/internal/node/{node_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["transport"] == "telnet"
    assert body["port"] == 5001

    # Unknown node -> 404 (not 500)
    assert (await anon_client.get("/api/internal/node/nope")).status_code == 404

@pytest.mark.asyncio
async def test_edit_without_password_keeps_it(client: AsyncClient, anon_client: AsyncClient):
    created = await client.post("/api/nodes", json={
        "name": "sshbox", "host": "10.0.0.7", "port": 22,
        "transport": "ssh", "username": "root", "password": "keepme",
    })
    nid = created.json()["id"]

    # Edit host only — payload omits password (frontend drops blank password)
    r = await client.put(f"/api/nodes/{nid}", json={"host": "192.168.122.121"})
    assert r.status_code == 200

    creds = (await anon_client.get(f"/api/internal/node/{nid}")).json()
    assert creds["host"] == "192.168.122.121"
    assert creds["password"] == "keepme"   # password preserved

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
