import time
import subprocess
import shlex
from datetime import datetime
from typing import Dict, Any, Tuple

from backend.core.vault import (
    store_credentials,
    load_credentials,
    delete_credentials,
    has_credentials,
)
from backend.core.db import load_nodes_db, save_node_db, delete_node_db
from backend.core.session import session_manager
from backend.core.cti import get_ip_geolocation
from backend.core.utils import cleanup_docker_containers

class NodeService:
    """Service handling business logic for nodes."""

    @staticmethod
    async def get_all_nodes() -> Dict[str, Any]:
        return await load_nodes_db()

    @staticmethod
    async def get_node_public(nid: str, node: dict) -> dict:
        return {
            "id": nid,
            "name": node.get("name"),
            "host": node.get("host"),
            "port": node.get("port"),
            "username": node.get("username"),
            "transport": node.get("transport", "telnet"),
            "device_type": node.get("device_type", "unknown"),
            "has_password": await has_credentials(nid),
            "created": node.get("created"),
            "tags": node.get("tags", []),
            "metadata": node.get("metadata", {}),
            "threat_monitoring": bool(node.get("threat_monitoring", False)),
        }

    @staticmethod
    async def get_node_with_creds(nid: str, nodes: dict = None) -> dict:
        if nodes is None:
            nodes = await NodeService.get_all_nodes()
        if nid not in nodes:
            raise ValueError("Node not found")
        node = dict(nodes[nid])
        username, password = await load_credentials(nid)
        node["username"] = username or "root"
        node["password"] = password
        return node

    @staticmethod
    async def create_node(node_data: dict) -> Tuple[str, dict]:
        nodes = await NodeService.get_all_nodes()
        nid = f"n{int(time.time() * 1000)}"

        geo = await get_ip_geolocation(node_data["host"], default_name=node_data["name"])

        node = {
            "id": nid,
            "name": node_data["name"],
            "host": node_data["host"].strip(" /"),
            "port": node_data["port"],
            "username": node_data["username"],
            "transport": node_data["transport"],
            "device_type": node_data.get("device_type", "unknown"),
            "tags": node_data.get("tags", []),
            "created": datetime.now().isoformat(),
            "metadata": {"lat": geo["lat"], "lng": geo["lng"], "city": geo["name"]},
        }
        await save_node_db(node)
        await store_credentials(nid, node_data["username"], node_data.get("password", ""))
        return nid, node

    @staticmethod
    async def update_node(nid: str, update_data: dict) -> dict:
        nodes = await NodeService.get_all_nodes()
        if nid not in nodes:
            raise ValueError("Node not found")
        node = nodes[nid]

        if update_data.get("name") is not None:
            node["name"] = update_data["name"]

        if update_data.get("host") is not None:
            if update_data["host"] != node.get("host"):
                geo = await get_ip_geolocation(
                    update_data["host"], default_name=node.get("name", "Unknown")
                )
                if "metadata" not in node:
                    node["metadata"] = {}
                node["metadata"]["lat"] = geo["lat"]
                node["metadata"]["lng"] = geo["lng"]
                node["metadata"]["city"] = geo["name"]
            node["host"] = update_data["host"].strip(" /")

        if update_data.get("port") is not None:
            node["port"] = update_data["port"]
        if update_data.get("transport") is not None:
            node["transport"] = update_data["transport"]
        if update_data.get("device_type") is not None:
            node["device_type"] = update_data["device_type"]
        if update_data.get("tags") is not None:
            node["tags"] = update_data["tags"]

        if update_data.get("username") is not None or update_data.get("password") is not None:
            old_user, old_pass = await load_credentials(nid)
            new_user = update_data["username"] if update_data.get("username") is not None else old_user
            new_pass = update_data["password"] if update_data.get("password") is not None else old_pass

            await store_credentials(nid, new_user, new_pass)
            if update_data.get("username") is not None:
                node["username"] = update_data["username"]

        await save_node_db(node)
        return node

    @staticmethod
    async def delete_node(nid: str) -> None:
        nodes = await NodeService.get_all_nodes()
        if nid not in nodes:
            raise ValueError("Node not found")
        await delete_node_db(nid)
        session_manager.close(nid)
        await delete_credentials(nid)

    @staticmethod
    async def nuke_all_nodes() -> None:
        nodes = await NodeService.get_all_nodes()
        for nid, node in list(nodes.items()):
            if node.get("transport") == "docker" and node.get("host"):
                subprocess.run(
                    f"docker rm -f {shlex.quote(node['host'])} 2>/dev/null || true",
                    shell=True,
                )
            await delete_node_db(nid)
            session_manager.close(nid)
            await delete_credentials(nid)

        cleanup_docker_containers()
