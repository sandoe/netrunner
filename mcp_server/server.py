"""Netrunner MCP server.

Exposes node management, command execution, config preview, and
device detection as MCP tools for AI clients (Claude Desktop, Claude Code).

Run:
    python -m mcp_server.server                  # read-only tools
    python -m mcp_server.server --allow-execute  # also enables execute_commands

Environment:
    NETRUNNER_API_BASE  — API base URL (default: http://127.0.0.1:8000)
    NETRUNNER_TIMEOUT   — HTTP timeout in seconds (default: 30)
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from mcp.server.fastmcp import FastMCP

API_BASE = os.environ.get("NETRUNNER_API_BASE", "http://127.0.0.1:8000").rstrip("/")
HTTP_TIMEOUT = float(os.environ.get("NETRUNNER_TIMEOUT", "30"))

mcp = FastMCP("netrunner")


def _api(method: str, path: str, body: Any = None) -> Any:
    url = API_BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} on {method} {path}: {msg}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Cannot reach Netrunner at {API_BASE} ({e.reason}). "
            "Is `python netrunner.py` running?"
        ) from None


def _q(s: str) -> str:
    return urllib.parse.quote(str(s), safe="")


# ---------------------------------------------------------------------------
# Read types available
# ---------------------------------------------------------------------------

NETWORK_READ_TYPES = (
    "ip", "routes", "interfaces", "neighbors", "sockets", "resolver",
    "nftables", "iptables", "ufw", "wireguard", "forwarding",
    "vlan-router", "vlan-switch", "dns-service", "dhcp-server", "nat",
)
LINUX_READ_TYPES = (
    "services", "packages", "users", "groups", "cron", "logs",
    "disk", "cpu", "memory", "processes", "os-info", "environment", "mounts",
)
RPI_READ_TYPES = (
    "rpi-config", "rpi-gpio", "rpi-temp", "rpi-i2c", "rpi-camera",
    "rpi-clocks", "rpi-voltage", "rpi-info",
)
ALL_READ_TYPES = NETWORK_READ_TYPES + LINUX_READ_TYPES + RPI_READ_TYPES


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_nodes() -> list[dict]:
    """List all nodes registered in Netrunner.

    Returns id, name, host, port, transport, device_type, tags per node.
    Use `id` as node_id for other tools.
    """
    data = _api("GET", "/api/nodes")
    return list((data or {}).values())


@mcp.tool()
def get_node(node_id: str) -> dict:
    """Get details for a single node by ID."""
    data = _api("GET", "/api/nodes")
    node = (data or {}).get(node_id)
    if not node:
        raise ValueError(f"Node '{node_id}' not found")
    return node


@mcp.tool()
def detect_device_type(node_id: str) -> dict:
    """Auto-detect device type for a node (gns3 / linux / rpi / unknown).

    Updates the node's device_type field in Netrunner.
    Returns {device_type: "..."}
    """
    return _api("POST", f"/api/nodes/{_q(node_id)}/detect")


@mcp.tool()
def connect_node(node_id: str) -> dict:
    """Open or refresh the telnet/SSH session to a node.

    Returns {status: "connected"} on success.
    """
    return _api("POST", f"/api/nodes/{_q(node_id)}/connect")


@mcp.tool()
def disconnect_node(node_id: str) -> dict:
    """Close the cached session for a node."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/disconnect")


@mcp.tool()
def read_node(node_id: str, read_type: str) -> str:
    """Read live state from a node.

    read_type must be one of:
    - Network: ip, routes, interfaces, neighbors, sockets, resolver,
               nftables, iptables, ufw, wireguard, forwarding,
               vlan-router, vlan-switch, dns-service, dhcp-server, nat
    - Linux:   services, packages, users, groups, cron, logs,
               disk, cpu, memory, processes, os-info, environment, mounts
    - RPi:     rpi-config, rpi-gpio, rpi-temp, rpi-i2c, rpi-camera,
               rpi-clocks, rpi-voltage, rpi-info

    Returns concatenated raw output.
    """
    if read_type not in ALL_READ_TYPES:
        raise ValueError(f"Unknown read_type '{read_type}'. Valid: {', '.join(ALL_READ_TYPES)}")
    data = _api("GET", f"/api/nodes/{_q(node_id)}/read/{_q(read_type)}")
    return "\n".join(r.get("output", "") for r in data.get("results", []) if r.get("output"))


@mcp.tool()
def ping_node(node_id: str, target: str, count: int = 3) -> str:
    """Ping `target` FROM the node identified by node_id.

    count is clamped to [1, 10]. Returns raw ping output.
    """
    count = max(1, min(10, int(count)))
    cmd = f"ping -c {count} {target}"
    data = _api("POST", f"/api/nodes/{_q(node_id)}/execute", {"commands": [cmd]})
    results = data.get("results", [])
    if not results:
        return ""
    r = results[0]
    return r.get("output") or r.get("error") or ""


@mcp.tool()
def preview_commands(config_type: str, payload: dict) -> list[str]:
    """Generate shell commands for a structured config WITHOUT running them.

    config_type supports all types exposed by /api/preview:
    Network: ip, routes, forwarding, dhcp, dns, dhcp-server, nat,
             reset-node, vlan-router, vlan-switch, wireguard, persist,
             iptables, ufw, nftables
    Linux:   service, package, user, cron, sysctl, file-write,
             hostname, ssh-hardening, authorized-key, systemd-unit
    RPi:     rpi-config-set, rpi-config-section, rpi-gpio, rpi-gpio-read-all,
             rpi-i2c, rpi-i2c-enable, rpi-spi, rpi-camera, rpi-overclock,
             rpi-temperature, rpi-wifi, rpi-bluetooth, rpi-watchdog, rpi-info

    Examples:
      type=ip:      {"interface": "eth0", "addresses": ["10.0.0.1/24"], "action": "add"}
      type=package: {"packages": ["vim", "curl"], "action": "install"}
      type=rpi-gpio:{"pin": 17, "mode": "out", "value": "1"}
    """
    data = _api("POST", "/api/preview", {"type": config_type, "data": payload})
    return data.get("commands", [])


@mcp.tool()
def list_saved_configs() -> list[dict]:
    """List all saved shell script configurations."""
    return _api("GET", "/api/configs") or []


@mcp.tool()
def get_saved_config(filename: str) -> str:
    """Get the content of a saved configuration script."""
    data = _api("GET", f"/api/configs/{_q(filename)}")
    return data.get("content", "")


@mcp.tool()
def save_config(name: str, content: str, config_type: str = "misc") -> dict:
    """Save a shell script configuration.

    Returns {name: "filename.sh"} of the saved file.
    """
    return _api("POST", "/api/configs", {"name": name, "content": content, "type": config_type})


def _execute_commands(node_id: str, commands: list[str]) -> list[dict]:
    """Run arbitrary shell commands on a node via its session.

    DESTRUCTIVE: commands execute with node credentials (typically root).
    Prefer preview_commands first. Returns list of {command, output, error}.
    """
    if isinstance(commands, str):
        commands = [c for c in commands.split("\n") if c.strip()]
    data = _api("POST", f"/api/nodes/{_q(node_id)}/execute", {"commands": list(commands)})
    return data.get("results", [])


def _apply_config(node_id: str, config_type: str, payload: dict) -> list[dict]:
    """Generate AND immediately apply a config to a node.

    Equivalent to: cmds = preview_commands(config_type, payload); execute_commands(node_id, cmds).
    Returns list of {command, output, error}.
    """
    cmds = preview_commands(config_type, payload)
    if not cmds:
        return []
    return _execute_commands(node_id, cmds)


def main() -> None:
    ap = argparse.ArgumentParser(description="Netrunner MCP server (stdio)")
    ap.add_argument("--allow-execute", action="store_true", help="Enable destructive execute_commands and apply_config tools")
    args = ap.parse_args()

    if args.allow_execute:
        mcp.tool(name="execute_commands")(_execute_commands)
        mcp.tool(name="apply_config")(_apply_config)

    mcp.run()


if __name__ == "__main__":
    main()
