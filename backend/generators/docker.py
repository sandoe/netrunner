"""Docker command generator — generate Docker commands for container operations."""
from __future__ import annotations
import re

def _split_csvish(val) -> list[str]:
    if not val:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str):
        parts = re.split(r"[,\s;]+", val)
        return [p.strip() for p in parts if p.strip()]
    return [str(val).strip()]

def gen_docker(cfg: dict) -> list[str]:
    """Generate shell commands for Docker container lifecycle operations."""
    action = cfg.get("action", "run").strip().lower()
    name = cfg.get("name", "").strip()
    image = cfg.get("image", "").strip()
    ports = cfg.get("ports", "")
    volumes = cfg.get("volumes", "")
    env = cfg.get("env", "")
    options = cfg.get("options", "").strip()

    if action == "prune":
        return [
            "# ── Docker System Prune: Clean up unused docker objects ──────────────────",
            "docker system prune -a --volumes -f",
            "echo 'Docker system prune executed successfully'"
        ]

    # All other actions (start, stop, restart, delete, run) require a container name/ID
    if not name:
        raise ValueError("Container name or ID is required.")

    if action == "start":
        return [
            f"# ── Docker Start: {name} ──────────────────────────────────────",
            f"docker start \"{name}\""
        ]
    elif action == "stop":
        return [
            f"# ── Docker Stop: {name} ───────────────────────────────────────",
            f"docker stop \"{name}\""
        ]
    elif action == "restart":
        return [
            f"# ── Docker Restart: {name} ────────────────────────────────────",
            f"docker restart \"{name}\""
        ]
    elif action == "delete" or action == "remove":
        return [
            f"# ── Docker Delete: {name} ─────────────────────────────────────",
            f"docker rm -f \"{name}\""
        ]
    elif action == "run":
        if not image:
            raise ValueError("Docker Image is required to run a new container.")
        
        # Build docker run command
        cmd = f"docker run -d --name \"{name}\""
        
        # Add port mappings
        if ports:
            port_list = _split_csvish(ports)
            for p in port_list:
                cmd += f" -p \"{p}\""
                
        # Add volume bindings
        if volumes:
            vol_list = _split_csvish(volumes)
            for v in vol_list:
                cmd += f" -v \"{v}\""
                
        # Add environment variables
        if env:
            env_list = _split_csvish(env)
            for e in env_list:
                cmd += f" -e \"{e}\""
                
        # Add custom options
        if options:
            cmd += f" {options}"
            
        # Add the image name at the end
        cmd += f" \"{image}\""
        
        return [
            f"# ── Docker Run Container: {name} ───────────────────────────────",
            f"# Ensure container is stopped/deleted if already exists",
            f"docker rm -f \"{name}\" 2>/dev/null || true",
            cmd
        ]
    elif action == "create-network":
        if not name:
            raise ValueError("Network name is required.")
        driver = cfg.get("driver", "bridge").strip()
        subnet = cfg.get("subnet", "").strip()
        gateway = cfg.get("gateway", "").strip()
        
        cmd = "docker network create"
        if driver:
            cmd += f" -d \"{driver}\""
        if subnet:
            cmd += f" --subnet \"{subnet}\""
        if gateway:
            cmd += f" --gateway \"{gateway}\""
        if options:
            cmd += f" {options}"
        cmd += f" \"{name}\""
        
        return [
            f"# ── Docker Create Network: {name} ──────────────────────────────",
            cmd
        ]
    elif action == "delete-network" or action == "remove-network":
        if not name:
            raise ValueError("Network name is required.")
        return [
            f"# ── Docker Delete Network: {name} ──────────────────────────────",
            f"docker network rm \"{name}\""
        ]
    elif action == "connect-network":
        if not name:
            raise ValueError("Network name is required.")
        container = cfg.get("container", "").strip()
        if not container:
            raise ValueError("Container name or ID is required for connect-network.")
        return [
            f"# ── Docker Connect Container to Network: {container} ➔ {name} ──",
            f"docker network connect \"{name}\" \"{container}\""
        ]
    elif action == "disconnect-network":
        if not name:
            raise ValueError("Network name is required.")
        container = cfg.get("container", "").strip()
        if not container:
            raise ValueError("Container name or ID is required for disconnect-network.")
        return [
            f"# ── Docker Disconnect Container from Network: {container} ➔ {name} ──",
            f"docker network disconnect \"{name}\" \"{container}\""
        ]
    elif action == "swarm-init":
        addr = cfg.get("advertiseAddr", "").strip()
        cmd = "docker swarm init"
        if addr:
            cmd += f" --advertise-addr \"{addr}\""
        if options:
            cmd += f" {options}"
        return [
            "# ── Docker Swarm Initialize Cluster ─────────────────────────────",
            cmd
        ]
    elif action == "swarm-join":
        token = cfg.get("token", "").strip()
        address = cfg.get("address", "").strip()
        if not token or not address:
            raise ValueError("Swarm join token and manager address (IP:Port) are required.")
        return [
            "# ── Docker Swarm Join Cluster ───────────────────────────────────",
            f"docker swarm join --token \"{token}\" \"{address}\""
        ]
    elif action == "swarm-leave":
        force_flag = " --force" if cfg.get("force", True) else ""
        return [
            "# ── Docker Swarm Leave Cluster ──────────────────────────────────",
            f"docker swarm leave{force_flag}"
        ]
    else:
        raise ValueError(f"Unknown Docker action '{action}'")
