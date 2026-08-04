"""Netrunner MCP (Model Context Protocol) Server."""

from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, List

from .gns3 import _gns3_req
from .nodes import load_nodes, save_nodes
from ..core.session import session_manager

mcp = FastMCP("Netrunner")


@mcp.tool()
async def gns3_list_projects() -> List[Dict[str, Any]]:
    """List all available GNS3 projects."""
    try:
        return await _gns3_req("GET", "/projects")
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
async def gns3_list_nodes(project_id: str) -> List[Dict[str, Any]]:
    """List all nodes in a specific GNS3 project."""
    try:
        return await _gns3_req("GET", f"/projects/{project_id}/nodes")
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
async def gns3_start_node(project_id: str, node_id: str) -> Dict[str, Any]:
    """Start a specific node in a GNS3 project."""
    try:
        res = await _gns3_req("POST", f"/projects/{project_id}/nodes/{node_id}/start")
        return {"status": "started", "node_id": node_id}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def gns3_stop_node(project_id: str, node_id: str) -> Dict[str, Any]:
    """Stop a specific node in a GNS3 project."""
    try:
        res = await _gns3_req("POST", f"/projects/{project_id}/nodes/{node_id}/stop")
        return {"status": "stopped", "node_id": node_id}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def netrunner_list_agents() -> Dict[str, Any]:
    """List all agents/nodes known to Netrunner."""
    try:
        nodes = await load_nodes()
        return nodes
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def netrunner_execute_command(node_id: str, command: str) -> Dict[str, Any]:
    """Execute a bash command on a connected Netrunner node (Linux/SSH)."""
    try:
        nodes = await load_nodes()
        if node_id not in nodes:
            return {"error": "Node not found"}
        out, err = await session_manager.run(node_id, nodes[node_id], [command])
        return {"output": out, "error": err}
        return {"stdout": out, "stderr": err, "exit_code": code}
    except Exception as e:
        return {"error": str(e)}


# The Starlette app can be mounted directly into FastAPI
mcp_app = mcp.sse_app()
