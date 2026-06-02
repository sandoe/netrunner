"""Netrunner MCP server.

Exposes node management, command execution, config preview, and
device detection as MCP tools for AI clients (Claude Desktop, Claude Code).

Run:
    python -m mcp_server.server                  # read-only tools
    python -m mcp_server.server --allow-execute  # also enables admin/destructive tools

Environment:
    NETRUNNER_API_BASE  — API base URL (default: http://127.0.0.1:8000)
    NETRUNNER_TIMEOUT   — HTTP timeout in seconds (default: 30)
    NETRUNNER_API_TOKEN — JWT token from /api/auth/login (optional)
    NETRUNNER_USERNAME  — login username if token is not provided (optional)
    NETRUNNER_PASSWORD  — login password if token is not provided (optional)
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
API_TOKEN = os.environ.get("NETRUNNER_API_TOKEN", "").strip()

mcp = FastMCP("netrunner")


def _auth_header() -> dict[str, str]:
    global API_TOKEN
    if API_TOKEN:
        return {"Authorization": f"Bearer {API_TOKEN}"}

    username = os.environ.get("NETRUNNER_USERNAME", "").strip()
    password = os.environ.get("NETRUNNER_PASSWORD", "").strip()
    if username and password:
        data = _api("POST", "/api/auth/login", {"username": username, "password": password}, auth=False)
        API_TOKEN = data.get("access_token", "")
        if API_TOKEN:
            return {"Authorization": f"Bearer {API_TOKEN}"}
    return {}


def _api(method: str, path: str, body: Any = None, auth: bool = True, extra_headers: dict[str, str] | None = None) -> Any:
    url = API_BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    if auth:
        headers.update(_auth_header())
    if extra_headers:
        headers.update(extra_headers)
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


def _query(params: dict[str, Any]) -> str:
    clean = {k: v for k, v in params.items() if v is not None}
    return "?" + urllib.parse.urlencode(clean) if clean else ""


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
def get_settings() -> dict:
    """Get Netrunner settings status, including AI provider/model, GNS3 URL, and database URL.

    API keys are returned only as masked/set flags by the backend.
    """
    return _api("GET", "/api/settings")


@mcp.tool()
def get_current_user() -> dict:
    """Get the authenticated Netrunner user represented by the configured token/login."""
    return _api("GET", "/api/auth/me")


@mcp.tool()
def list_auth_users() -> dict:
    """List Netrunner users. Requires an admin token/login."""
    return _api("GET", "/api/auth/users")


@mcp.tool()
def chat_with_ai(messages: list[dict], model: str | None = None) -> dict:
    """Send a chat request to Netrunner's configured AI provider.

    Uses the provider/model/API key configured in Settings unless `model` is provided.
    messages must be a list of {role, content}.
    """
    body: dict[str, Any] = {"messages": messages}
    if model:
        body["model"] = model
    return _api("POST", "/api/ai/chat", body)


@mcp.tool()
def get_node(node_id: str) -> dict:
    """Get details for a single node by ID."""
    data = _api("GET", "/api/nodes")
    node = (data or {}).get(node_id)
    if not node:
        raise ValueError(f"Node '{node_id}' not found")
    return node


@mcp.tool()
def get_internal_node_connection(node_id: str) -> dict:
    """Get internal terminal connection details for a node."""
    return _api("GET", f"/api/internal/node/{_q(node_id)}", auth=False)


@mcp.tool()
def get_terminal_websocket_url(node_id: str, token: str | None = None) -> dict:
    """Return the WebSocket URL for a node terminal session."""
    base = API_BASE.replace("https://", "wss://").replace("http://", "ws://")
    query = _query({"token": token})
    return {"url": f"{base}/ws/terminal/{_q(node_id)}{query}"}


@mcp.tool()
def list_node_connections() -> dict:
    """List connection state for all node sessions."""
    return _api("GET", "/api/nodes/connections")


@mcp.tool()
def list_node_reachability() -> dict:
    """Get latest reachability/latency state for all nodes."""
    return _api("GET", "/api/nodes/reachability")


@mcp.tool()
def list_node_vitals() -> dict:
    """Get latest CPU/RAM/network vitals for connected nodes."""
    return _api("GET", "/api/nodes/vitals")


@mcp.tool()
def get_node_metrics_history(node_id: str) -> dict:
    """Get rolling vitals history for a node."""
    return _api("GET", f"/api/nodes/{_q(node_id)}/metrics/history")


@mcp.tool()
def get_node_system_snapshot(node_id: str) -> dict:
    """Get process, CPU, memory, disk, and service snapshot for a node."""
    return _api("GET", f"/api/nodes/{_q(node_id)}/system/snapshot")


@mcp.tool()
def get_node_logs(node_id: str, lines: int = 120) -> dict:
    """Get recent system logs from a node."""
    return _api("GET", f"/api/nodes/{_q(node_id)}/system/logs{_query({'lines': lines})}")


@mcp.tool()
def get_node_services(node_id: str) -> dict:
    """List system services on a node."""
    return _api("GET", f"/api/nodes/{_q(node_id)}/system/services")


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
def list_events() -> dict:
    """List Netrunner event feed entries."""
    return _api("GET", "/api/events")


@mcp.tool()
def list_system_logs() -> dict:
    """List backend/system log events."""
    return _api("GET", "/api/system/logs")


@mcp.tool()
def get_system_state() -> dict:
    """Get global system state such as autopilot and chaos toggles."""
    return _api("GET", "/api/system/state")


@mcp.tool()
def list_links() -> list[dict]:
    """List topology links."""
    return _api("GET", "/api/links") or []


@mcp.tool()
def auto_discover_links() -> dict:
    """Read-only link auto-discovery pass. Returns unknown/new neighbor information."""
    return _api("GET", "/api/links/auto-discover")


@mcp.tool()
def list_gns3_projects() -> list[dict]:
    """List projects from the configured GNS3 server."""
    return _api("GET", "/api/gns3/projects") or []


@mcp.tool()
def list_local_gns3_projects() -> list[dict]:
    """List local GNS3 project folders configured in settings."""
    return _api("GET", "/api/gns3/local-projects") or []


@mcp.tool()
def list_threat_nodes() -> dict:
    """Get current simulated/live threat node state."""
    return _api("GET", "/api/threats/nodes")


@mcp.tool()
def get_threats_websocket_url(token: str | None = None) -> dict:
    """Return the WebSocket URL for live threat updates."""
    base = API_BASE.replace("https://", "wss://").replace("http://", "ws://")
    return {"url": f"{base}/ws/threats{_query({'token': token})}"}


@mcp.tool()
def list_threat_history() -> dict:
    """Get stored threat history."""
    return _api("GET", "/api/threats/history")


@mcp.tool()
def list_active_rules() -> dict:
    """List active detection/response rules."""
    return _api("GET", "/api/rules/active")


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
def generate_wireguard_keys() -> dict:
    """Generate a WireGuard private/public keypair."""
    return _api("GET", "/api/wireguard/generate-keys")


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


@mcp.tool()
def list_captures(node_id: str) -> dict:
    """List packet captures for a node."""
    return _api("GET", f"/api/nodes/{_q(node_id)}/capture")


@mcp.tool()
def get_capture_status(node_id: str, capture_id: str) -> dict:
    """Get capture status and size."""
    return _api("GET", f"/api/nodes/{_q(node_id)}/capture/{_q(capture_id)}/status")


@mcp.tool()
def analyze_capture(node_id: str, capture_id: str) -> dict:
    """Analyze a stored packet capture."""
    return _api("GET", f"/api/nodes/{_q(node_id)}/capture/{_q(capture_id)}/analyze")


@mcp.tool()
def get_capture_download_url(node_id: str, capture_id: str) -> dict:
    """Return the API URL for downloading a packet capture."""
    return {"url": f"{API_BASE}/api/nodes/{_q(node_id)}/capture/{_q(capture_id)}/download"}


@mcp.tool()
def get_export_download_url(filename: str) -> dict:
    """Return the API URL for downloading an exported node bundle."""
    return {"url": f"{API_BASE}/api/exports/{_q(filename)}"}


@mcp.tool()
def get_agent_download_url(arch: str) -> dict:
    """Return the API URL for downloading the Netrunner agent binary. arch must be amd64 or arm64."""
    if arch not in ("amd64", "arm64"):
        raise ValueError("arch must be amd64 or arm64")
    return {"url": f"{API_BASE}/api/agent/download/{_q(arch)}"}


@mcp.tool()
def get_telemetry_websocket_url(token: str | None = None) -> dict:
    """Return the WebSocket URL for live telemetry updates."""
    base = API_BASE.replace("https://", "wss://").replace("http://", "ws://")
    return {"url": f"{base}/ws/telemetry{_query({'token': token})}"}


@mcp.tool()
def list_wifi_beacons() -> dict:
    """List configured WiFi CSI beacon nodes."""
    return _api("GET", "/api/wifi/beacons")


@mcp.tool()
def list_wifi_telemetry() -> dict:
    """List current WiFi CSI beacon telemetry."""
    return _api("GET", "/api/wifi/telemetry")


@mcp.tool()
def list_wifi_recordings() -> dict:
    """List recorded WiFi CSI capture sessions."""
    return _api("GET", "/api/wifi/record/list")


@mcp.tool()
def get_esp32_beacon_version() -> dict:
    """Get ESP32 beacon firmware/script version metadata."""
    return _api("GET", "/api/wifi/esp32/version")


@mcp.tool()
def get_esp32_beacon_download_url() -> dict:
    """Return the API URL for downloading the ESP32 beacon script."""
    return {"url": f"{API_BASE}/api/wifi/esp32/download"}


@mcp.tool()
def get_wifi_recording_download_url(filename: str) -> dict:
    """Return the API URL for downloading a WiFi CSI recording."""
    return {"url": f"{API_BASE}/api/wifi/record/download/{_q(filename)}"}


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


def _api_request(method: str, path: str, body: dict | None = None) -> Any:
    """Call an arbitrary Netrunner API endpoint.

    DESTRUCTIVE if method/path is destructive. Use only when no dedicated MCP tool exists.
    `path` should include /api/... exactly as exposed by Netrunner.
    """
    return _api(method.upper(), path, body)


def _report_agent_event(agent_token: str, event_type: str, severity: str, source_ip: str) -> dict:
    """Report a threat event through the agent endpoint using the configured agent token."""
    return _api(
        "POST",
        "/api/agent/events",
        {"type": event_type, "severity": severity, "source_ip": source_ip},
        auth=False,
        extra_headers={"Authorization": f"Bearer {agent_token}"},
    )


def _create_auth_user(username: str, password: str, role: str = "analyst") -> dict:
    """Create a Netrunner user. Requires an admin token/login."""
    return _api("POST", "/api/auth/users", {"username": username, "password": password, "role": role})


def _delete_auth_user(username: str) -> dict:
    """Delete a Netrunner user. Requires an admin token/login."""
    return _api("DELETE", f"/api/auth/users/{_q(username)}")


def _create_node(node: dict) -> dict:
    """Create a node. Expected fields include id, name, host, port, transport, username, password, device_type."""
    return _api("POST", "/api/nodes", node)


def _update_node(node_id: str, updates: dict) -> dict:
    """Update a node by ID."""
    return _api("PUT", f"/api/nodes/{_q(node_id)}", updates)


def _delete_node(node_id: str) -> dict:
    """Delete a node by ID."""
    return _api("DELETE", f"/api/nodes/{_q(node_id)}")


def _reboot_node(node_id: str, method: str = "command") -> dict:
    """Reboot a node. method may be command or gns3."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/reboot", {"method": method})


def _node_service_action(node_id: str, name: str, action: str) -> dict:
    """Run a service action on a node, e.g. start, stop, restart, status."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/system/service", {"name": name, "action": action})


def _kill_node_process(node_id: str, pid: int, signal: str = "TERM") -> dict:
    """Send a signal to a process on a node."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/system/kill", {"pid": pid, "signal": signal})


def _install_node_tool(node_id: str, tool: str) -> dict:
    """Install a missing tool/package on a node through Netrunner helper logic."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/install", {"tool": tool})


def _backup_node(node_id: str, paths: dict | None = None) -> dict:
    """Create a backup bundle for a node."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/backup", paths or {})


def _rollback_node(node_id: str) -> dict:
    """Rollback a node using its latest Netrunner backup."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/rollback")


def _export_node(node_id: str, options: dict | None = None) -> dict:
    """Export node configuration, diagnostics, and optional captures."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/export", options or {})


def _gns3_node_api(node_id: str, method: str, path: str, body: dict | None = None) -> dict:
    """Call a GNS3 API path related to a node through Netrunner."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/gns3-api", {"method": method, "path": path, "body": body})


def _sync_gns3_project(project_id: str) -> dict:
    """Sync nodes/links from a GNS3 project."""
    return _api("POST", f"/api/gns3/sync/{_q(project_id)}")


def _sync_local_gns3_project(path: str) -> dict:
    """Sync a local GNS3 project path."""
    return _api("POST", "/api/local-sync", {"path": path})


def _create_link(source: str, target: str) -> dict:
    """Create a topology link."""
    return _api("POST", "/api/links", {"source": source, "target": target})


def _delete_link(link_id: str) -> dict:
    """Delete a topology link."""
    return _api("DELETE", f"/api/links/{_q(link_id)}")


def _discover_links() -> dict:
    """Run topology discovery and create discovered links where backend logic allows it."""
    return _api("POST", "/api/links/discover")


def _update_settings(settings: dict) -> dict:
    """Update Netrunner settings, including AI provider/key/model/base URL, GNS3 URL, or database URL."""
    return _api("POST", "/api/settings", settings)


def _test_database(url: str) -> dict:
    """Test a database connection URL."""
    return _api("POST", "/api/settings/test-db", {"url": url})


def _init_database(url: str) -> dict:
    """Initialize database tables for a database connection URL."""
    return _api("POST", "/api/settings/init-db", {"url": url})


def _restart_backend() -> dict:
    """Request backend restart. Requires an external watcher/start loop to bring it back."""
    return _api("POST", "/api/settings/restart")


def _update_system_state(state: dict) -> dict:
    """Update global system state, e.g. {'autopilot': true, 'chaos': false}."""
    return _api("POST", "/api/system/state", state)


def _clear_events() -> dict:
    """Clear event feed."""
    return _api("DELETE", "/api/events")


def _trigger_demo_storm() -> dict:
    """Trigger the demo storm event generator."""
    return _api("POST", "/api/demo/storm")


def _start_capture(node_id: str, interface: str, filter_expr: str = "", packet_limit: int = 0, capture_id: str | None = None) -> dict:
    """Start a packet capture on a node."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/capture/start", {
        "id": capture_id,
        "interface": interface,
        "filter": filter_expr,
        "packet_limit": packet_limit,
    })


def _stop_capture(node_id: str, capture_id: str) -> dict:
    """Stop a packet capture."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/capture/{_q(capture_id)}/stop")


def _delete_capture(node_id: str, capture_id: str) -> dict:
    """Delete a packet capture."""
    return _api("DELETE", f"/api/nodes/{_q(node_id)}/capture/{_q(capture_id)}")


def _inject_capture_packet(node_id: str, target_ip: str, port: int, protocol: str, payload: str) -> dict:
    """Inject/forge a packet from a node."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/capture/inject", {
        "target_ip": target_ip,
        "port": port,
        "protocol": protocol,
        "payload": payload,
    })


def _defense_scan(node_id: str) -> dict:
    """Run Nmap defense scan for a node."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/nmap")


def _isolate_node(node_id: str) -> dict:
    """Deploy node isolation firewall rules."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/isolate")


def _enforce_zero_trust(node_id: str) -> dict:
    """Enable zero-trust response for a node."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/defense/zero-trust")


def _install_monitoring(node_id: str) -> dict:
    """Install Netrunner monitoring agent on a node."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/monitoring/install")


def _remove_monitoring(node_id: str) -> dict:
    """Remove Netrunner monitoring agent from a node."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/monitoring/remove")


def _deploy_redteam(payload: dict) -> dict:
    """Deploy a redteam payload. Payload should match /api/redteam/deploy."""
    return _api("POST", "/api/redteam/deploy", payload)


def _trigger_chaos_attack(payload: dict) -> dict:
    """Trigger a manual chaos attack. Payload should match /api/chaos/attack."""
    return _api("POST", "/api/chaos/attack", payload)


def _deploy_deception(node_id: str, persona: str, port: int = 2222, aggressiveness: str = "medium") -> dict:
    """Deploy Mirage deception honeypot on a node."""
    return _api("POST", f"/api/nodes/{_q(node_id)}/deception/deploy", {
        "persona": persona,
        "port": port,
        "aggressiveness": aggressiveness,
    })


def _set_wifi_mode(simulation: bool, nodes: list[str] | None = None) -> dict:
    """Set WiFi CSI simulation/real-node mode."""
    return _api("POST", "/api/wifi/mode", {"simulation": simulation, "nodes": nodes or []})


def _start_wifi_recording() -> dict:
    """Start WiFi CSI recording."""
    return _api("POST", "/api/wifi/record/start")


def _stop_wifi_recording() -> dict:
    """Stop WiFi CSI recording."""
    return _api("POST", "/api/wifi/record/stop")


def _add_wifi_beacon(beacon: dict) -> dict:
    """Add/update a WiFi CSI beacon node."""
    return _api("POST", "/api/wifi/beacons", beacon)


def _delete_wifi_beacon(node_id: str) -> dict:
    """Delete a WiFi CSI beacon node."""
    return _api("DELETE", f"/api/wifi/beacons/{_q(node_id)}")


def _deploy_wifi_beacon(payload: dict) -> dict:
    """Deploy WiFi beacon agent to a node. Payload should match /api/wifi/deploy."""
    return _api("POST", "/api/wifi/deploy", payload)


def _stop_wifi_beacon(node_id: str) -> dict:
    """Stop WiFi beacon on a node."""
    return _api("POST", f"/api/wifi/beacons/{_q(node_id)}/stop")


def _delete_saved_config(filename: str) -> dict:
    """Delete a saved config file."""
    return _api("DELETE", f"/api/configs/{_q(filename)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Netrunner MCP server (stdio)")
    ap.add_argument("--allow-execute", action="store_true", help="Enable destructive execute_commands and apply_config tools")
    args = ap.parse_args()

    if args.allow_execute:
        mcp.tool(name="api_request")(_api_request)
        mcp.tool(name="execute_commands")(_execute_commands)
        mcp.tool(name="apply_config")(_apply_config)
        mcp.tool(name="report_agent_event")(_report_agent_event)
        mcp.tool(name="create_auth_user")(_create_auth_user)
        mcp.tool(name="delete_auth_user")(_delete_auth_user)
        mcp.tool(name="create_node")(_create_node)
        mcp.tool(name="update_node")(_update_node)
        mcp.tool(name="delete_node")(_delete_node)
        mcp.tool(name="reboot_node")(_reboot_node)
        mcp.tool(name="node_service_action")(_node_service_action)
        mcp.tool(name="kill_node_process")(_kill_node_process)
        mcp.tool(name="install_node_tool")(_install_node_tool)
        mcp.tool(name="backup_node")(_backup_node)
        mcp.tool(name="rollback_node")(_rollback_node)
        mcp.tool(name="export_node")(_export_node)
        mcp.tool(name="gns3_node_api")(_gns3_node_api)
        mcp.tool(name="sync_gns3_project")(_sync_gns3_project)
        mcp.tool(name="sync_local_gns3_project")(_sync_local_gns3_project)
        mcp.tool(name="create_link")(_create_link)
        mcp.tool(name="delete_link")(_delete_link)
        mcp.tool(name="discover_links")(_discover_links)
        mcp.tool(name="update_settings")(_update_settings)
        mcp.tool(name="test_database")(_test_database)
        mcp.tool(name="init_database")(_init_database)
        mcp.tool(name="restart_backend")(_restart_backend)
        mcp.tool(name="update_system_state")(_update_system_state)
        mcp.tool(name="clear_events")(_clear_events)
        mcp.tool(name="trigger_demo_storm")(_trigger_demo_storm)
        mcp.tool(name="start_capture")(_start_capture)
        mcp.tool(name="stop_capture")(_stop_capture)
        mcp.tool(name="delete_capture")(_delete_capture)
        mcp.tool(name="inject_capture_packet")(_inject_capture_packet)
        mcp.tool(name="defense_scan")(_defense_scan)
        mcp.tool(name="isolate_node")(_isolate_node)
        mcp.tool(name="enforce_zero_trust")(_enforce_zero_trust)
        mcp.tool(name="install_monitoring")(_install_monitoring)
        mcp.tool(name="remove_monitoring")(_remove_monitoring)
        mcp.tool(name="deploy_redteam")(_deploy_redteam)
        mcp.tool(name="trigger_chaos_attack")(_trigger_chaos_attack)
        mcp.tool(name="deploy_deception")(_deploy_deception)
        mcp.tool(name="set_wifi_mode")(_set_wifi_mode)
        mcp.tool(name="start_wifi_recording")(_start_wifi_recording)
        mcp.tool(name="stop_wifi_recording")(_stop_wifi_recording)
        mcp.tool(name="add_wifi_beacon")(_add_wifi_beacon)
        mcp.tool(name="delete_wifi_beacon")(_delete_wifi_beacon)
        mcp.tool(name="deploy_wifi_beacon")(_deploy_wifi_beacon)
        mcp.tool(name="stop_wifi_beacon")(_stop_wifi_beacon)
        mcp.tool(name="delete_saved_config")(_delete_saved_config)

    mcp.run()


if __name__ == "__main__":
    main()
