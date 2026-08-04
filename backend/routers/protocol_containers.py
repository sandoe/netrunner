import os
import shutil
import subprocess
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

router = APIRouter(prefix="/protocol-containers", tags=["Protocol Containers"])

COMPOSE_FILE = "/app/protocols/docker-compose.protocols.yml"


def _compose_command() -> list[str]:
    """Support both the Docker Compose plugin and Debian's v1 binary."""
    plugin = subprocess.run(
        ["docker", "compose", "version"], capture_output=True, text=True
    )
    if plugin.returncode == 0:
        return ["docker", "compose"]
    legacy = shutil.which("docker-compose")
    if legacy:
        return [legacy]
    raise RuntimeError("Docker Compose is not installed in the application image")

class ContainerRequest(BaseModel):
    service: str
    target_ip: str = ""
    tags: str = ""

@router.get("/status")
async def get_status() -> Dict[str, Any]:
    try:
        # Run docker compose ps
        result = subprocess.run(
            [*_compose_command(), "-f", COMPOSE_FILE, "ps", "--format", "json"],
            capture_output=True,
            text=True
        )
        return {"status": "success", "containers": result.stdout}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/start")
async def start_container(req: ContainerRequest) -> Dict[str, Any]:
    try:
        env = os.environ.copy()
        if req.target_ip:
            env["TARGET_IP"] = req.target_ip
        if req.tags:
            env["OPC_TAGS"] = req.tags

        # Stop first to ensure clean state with new env vars
        subprocess.run([*_compose_command(), "-f", COMPOSE_FILE, "stop", req.service], capture_output=True)

        # Start
        result = subprocess.run(
            [*_compose_command(), "-f", COMPOSE_FILE, "up", "-d", req.service],
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise Exception(result.stderr)

        return {"status": "success", "message": f"Started {req.service}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/stop")
async def stop_container(req: ContainerRequest) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            [*_compose_command(), "-f", COMPOSE_FILE, "stop", req.service],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise Exception(result.stderr)

        return {"status": "success", "message": f"Stopped {req.service}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/logs/{service}")
async def get_logs(service: str) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            [*_compose_command(), "-f", COMPOSE_FILE, "logs", "--tail", "50", service],
            capture_output=True,
            text=True
        )
        return {"status": "success", "logs": result.stdout}
    except Exception as e:
        return {"status": "error", "message": str(e)}
