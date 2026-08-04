from mcp.server.fastmcp import FastMCP
import asyncio
from typing import List, Dict, Any
import json
import os

from sqlalchemy import select
from backend.core.db import get_db, NodeModel
from backend.core.session import session_manager
from backend.core.knowledge_graph import KnowledgeGraph

# Opret FastMCP instansen
mcp = FastMCP("Netrunner Platform")


@mcp.tool()
async def get_network_topology() -> str:
    """
    Henter den nuværende netværkstopologi fra Netrunner (IP'er, typer, status).
    Brug denne til at få et overblik over hvilke systemer, der eksisterer i netværket.
    """
    nodes_data = []
    try:
        async for db in get_db():
            result = await db.execute(select(NodeModel))
            nodes = result.scalars().all()
            for n in nodes:
                nodes_data.append(
                    {
                        "id": n.id,
                        "name": n.name,
                        "host": n.host,
                        "port": n.port,
                        "device_type": n.device_type,
                        "username": n.username,
                        "transport": n.transport,
                    }
                )
            break  # vi skal kun bruge 1 session

        return json.dumps(nodes_data, indent=2)
    except Exception as e:
        return f"Fejl under indhentning af topologi: {str(e)}"


@mcp.tool()
async def execute_node_command(node_id: str, commands: List[str]) -> str:
    """
    Kør SSH/Telnet kommandoer på en specifik netværks-node baseret på dens node_id.
    Brug denne til at undersøge en maskine, pinge en anden, eller ændre konfigurationen.
    """
    try:
        target_node = None
        async for db in get_db():
            result = await db.execute(select(NodeModel).where(NodeModel.id == node_id))
            target_node = result.scalar_one_or_none()
            break

        if not target_node:
            return f"Fejl: Kunne ikke finde en node med ID '{node_id}'."

        node_dict = {
            "id": target_node.id,
            "host": target_node.host,
            "port": target_node.port,
            "username": target_node.username,
            "transport": target_node.transport,
            "password": "",  # Netrunner's session manager currently doesn't store passwords in NodeModel
        }

        results, err = await session_manager.run(
            nid=node_id, node=node_dict, commands=commands
        )

        if err:
            return f"Fejl: {err}"

        output_str = ""
        for res in results:
            output_str += f"Kommando: {res.get('command')}\n"
            if res.get("output"):
                output_str += f"Output:\n{res.get('output')}\n"
            if res.get("error"):
                output_str += f"Fejl:\n{res.get('error')}\n"
            output_str += "-" * 20 + "\n"

        return output_str

    except Exception as e:
        return f"Fejl under eksekvering af kommando: {str(e)}"


@mcp.tool()
async def query_cyber_intelligence(cypher_query: str) -> str:
    """
    Kør en Cypher forespørgsel direkte mod Netrunner's Neo4j grafdatabase.
    Dette tillader Agenten at spørge ind til dyb semantisk hukommelse (Graphiti)
    eller relationer mellem netværks komponenter.
    """
    try:
        kg = KnowledgeGraph()
        results = kg.execute_cypher(cypher_query)
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Cypher Query Fejl: {str(e)}"


if __name__ == "__main__":
    # Start the stdio MCP server
    mcp.run()
