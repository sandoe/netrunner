import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from backend.services.node_service import NodeService

@pytest.fixture
def mock_db():
    with patch("backend.services.node_service.load_nodes_db", new_callable=AsyncMock) as mock_load, \
         patch("backend.services.node_service.save_node_db", new_callable=AsyncMock) as mock_save, \
         patch("backend.services.node_service.delete_node_db", new_callable=AsyncMock) as mock_delete:
        yield mock_load, mock_save, mock_delete

@pytest.fixture
def mock_vault():
    with patch("backend.services.node_service.store_credentials", new_callable=AsyncMock) as mock_store, \
         patch("backend.services.node_service.load_credentials", new_callable=AsyncMock) as mock_load, \
         patch("backend.services.node_service.delete_credentials", new_callable=AsyncMock) as mock_delete, \
         patch("backend.services.node_service.has_credentials", new_callable=AsyncMock) as mock_has:
        yield mock_store, mock_load, mock_delete, mock_has

@pytest.fixture
def mock_cti():
    with patch("backend.services.node_service.get_ip_geolocation", new_callable=AsyncMock) as mock_geo:
        yield mock_geo

@pytest.fixture
def mock_session():
    with patch("backend.services.node_service.session_manager") as mock_sm:
        yield mock_sm

@pytest.fixture
def mock_utils():
    with patch("backend.services.node_service.cleanup_docker_containers") as mock_cleanup, \
         patch("backend.services.node_service.subprocess.run") as mock_sub:
        yield mock_cleanup, mock_sub

@pytest.mark.asyncio
async def test_get_all_nodes(mock_db):
    mock_load, _, _ = mock_db
    mock_load.return_value = {"n1": {"name": "test1"}}
    nodes = await NodeService.get_all_nodes()
    assert nodes == {"n1": {"name": "test1"}}
    mock_load.assert_awaited_once()

@pytest.mark.asyncio
async def test_create_node(mock_db, mock_vault, mock_cti):
    mock_load, mock_save, _ = mock_db
    mock_store, _, _, _ = mock_vault
    mock_geo = mock_cti

    mock_load.return_value = {}
    mock_geo.return_value = {"lat": 10.0, "lng": 20.0, "name": "Test City"}

    node_data = {
        "name": "Router1",
        "host": "192.168.1.1",
        "port": 22,
        "username": "admin",
        "password": "password",
        "transport": "ssh",
        "device_type": "cisco",
        "tags": ["prod"]
    }

    nid, node = await NodeService.create_node(node_data)

    assert node["name"] == "Router1"
    assert node["host"] == "192.168.1.1"
    assert node["metadata"]["city"] == "Test City"

    mock_geo.assert_awaited_once_with("192.168.1.1", default_name="Router1")
    mock_save.assert_awaited_once()
    mock_store.assert_awaited_once_with(nid, "admin", "password")

@pytest.mark.asyncio
async def test_update_node(mock_db, mock_vault, mock_cti):
    mock_load, mock_save, _ = mock_db
    mock_store, mock_load_creds, _, _ = mock_vault
    mock_geo = mock_cti

    mock_load.return_value = {
        "n1": {
            "name": "Router1",
            "host": "192.168.1.1",
            "port": 22
        }
    }
    mock_geo.return_value = {"lat": 0, "lng": 0, "name": "New City"}
    mock_load_creds.return_value = ("admin", "oldpass")

    update_data = {
        "name": "Router2",
        "host": "192.168.1.2",
        "username": "root"
    }

    updated = await NodeService.update_node("n1", update_data)

    assert updated["name"] == "Router2"
    assert updated["host"] == "192.168.1.2"
    assert updated["username"] == "root"

    mock_geo.assert_awaited_once()
    mock_save.assert_awaited_once()
    mock_store.assert_awaited_once_with("n1", "root", "oldpass")

@pytest.mark.asyncio
async def test_delete_node(mock_db, mock_vault, mock_session):
    mock_load, _, mock_delete_db = mock_db
    _, _, mock_delete_creds, _ = mock_vault
    mock_sm = mock_session

    mock_load.return_value = {"n1": {"name": "test"}}

    await NodeService.delete_node("n1")

    mock_delete_db.assert_awaited_once_with("n1")
    mock_delete_creds.assert_awaited_once_with("n1")
    mock_sm.close.assert_called_once_with("n1")

@pytest.mark.asyncio
async def test_get_node_public(mock_vault):
    _, _, _, mock_has = mock_vault
    mock_has.return_value = True

    node = {
        "name": "R1",
        "host": "10.0.0.1"
    }

    public = await NodeService.get_node_public("n1", node)
    assert public["id"] == "n1"
    assert public["name"] == "R1"
    assert public["has_password"] is True
