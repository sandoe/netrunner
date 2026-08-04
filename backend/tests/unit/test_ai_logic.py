import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from backend.routers.ai import TOOLS, deploy_agent_tool


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Override the conftest.py setup_db fixture because we don't need DB here."""
    pass


def test_tools_definition_is_correct():
    """Verify that the TOOLS array is correctly structured."""
    assert isinstance(TOOLS, list)
    assert len(TOOLS) > 0

    # Verify all expected tools are present
    expected_tool_names = [
        "list_nodes",
        "get_topology",
        "run_discovery",
        "create_link",
        "read_node",
        "deploy_agent",
        "generate_report",
        "run_playbook_tool",
    ]

    actual_tool_names = [t.get("function", {}).get("name") for t in TOOLS]

    for expected_name in expected_tool_names:
        assert expected_name in actual_tool_names

    # Pick a specific tool to verify structure
    deploy_agent = next(t for t in TOOLS if t["function"]["name"] == "deploy_agent")
    assert deploy_agent["type"] == "function"
    assert "description" in deploy_agent["function"]
    assert "node_id" in deploy_agent["function"]["parameters"]["required"]
    assert "agent_id" in deploy_agent["function"]["parameters"]["required"]


@pytest.mark.asyncio
async def test_deploy_agent_tool_mocked():
    """Test mocking the deploy_agent_tool function to return expected JSON."""
    with patch(
        "backend.routers.ai.deploy_agent_tool", new_callable=AsyncMock
    ) as mock_deploy:
        expected_json = {"status": "success", "message": "recon deployed to node_1."}
        mock_deploy.return_value = expected_json

        # Call the mocked function
        result = await mock_deploy("node_1", "recon")

        assert result == expected_json
        mock_deploy.assert_called_once_with("node_1", "recon")


@pytest.mark.asyncio
@patch("backend.routers.ai.session_manager.run", new_callable=AsyncMock)
@patch("backend.routers.nodes.load_nodes", new_callable=AsyncMock)
@patch("backend.routers.nodes._get_node_with_creds", new_callable=AsyncMock)
@patch("pathlib.Path.exists")
@patch("builtins.open")
async def test_deploy_agent_tool_internal(
    mock_open, mock_exists, mock_get_creds, mock_load_nodes, mock_session_run
):
    """Test the internal logic of deploy_agent_tool directly."""
    # Setup mocks
    mock_load_nodes.return_value = {"node_1": {"host": "192.168.1.10"}}
    mock_get_creds.return_value = {"host": "192.168.1.10"}
    mock_exists.return_value = True

    mock_file = MagicMock()
    mock_file.read.return_value = "print('Hello World')"
    mock_open.return_value.__enter__.return_value = mock_file

    # Mock successful session.run
    mock_session_run.return_value = (["ok", "ok"], None)

    # Use patch to inject AVAILABLE_AGENTS just for this test
    with patch.dict(
        "backend.routers.agents.AVAILABLE_AGENTS",
        {"recon": {"name": "Recon Agent", "script": "recon.py"}},
    ):
        result = await deploy_agent_tool("node_1", "recon")

        assert result == {
            "status": "success",
            "message": "Recon Agent deployed to node_1.",
        }
