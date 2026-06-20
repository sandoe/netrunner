"""Kismet Wireless IDS integration.

Manages a local Kismet subprocess and exposes its REST API data
for the Netrunner backend. Handles subprocess lifecycle, REST proxying,
and real-time data streaming via asyncio queues.
"""
from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

KISMET_HOST = os.environ.get("KISMET_HOST", "127.0.0.1")
KISMET_PORT = int(os.environ.get("KISMET_PORT", "2501"))
KISMET_USER = os.environ.get("KISMET_USER", "admin")
KISMET_PASS = os.environ.get("KISMET_PASS", "kismet")

_base_url = f"http://{KISMET_HOST}:{KISMET_PORT}"

# Queue for broadcasting Kismet events to WebSocket clients
kismet_event_queue: asyncio.Queue = asyncio.Queue()

# ---------------------------------------------------------------------------
# REST helpers
# ---------------------------------------------------------------------------

def _auth_header() -> str:
    import base64
    creds = f"{KISMET_USER}:{KISMET_PASS}"
    return "Basic " + base64.b64encode(creds.encode()).decode()


def _kismet_get(path: str, timeout: float = 10.0) -> Any:
    """GET request to the Kismet REST API."""
    url = _base_url + path
    req = urllib.request.Request(url, headers={"Authorization": _auth_header()})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Kismet HTTP {e.code} on {path}: {msg}") from None
    except (urllib.error.URLError, ConnectionRefusedError, OSError) as e:
        raise RuntimeError(f"Cannot reach Kismet at {_base_url}: {e}") from None


def _kismet_post(path: str, body: dict | None = None, timeout: float = 10.0) -> Any:
    """POST request to the Kismet REST API."""
    url = _base_url + path
    data = json.dumps(body).encode() if body is not None else None
    headers: dict[str, str] = {"Authorization": _auth_header()}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Kismet HTTP {e.code} on {path}: {msg}") from None
    except (urllib.error.URLError, ConnectionRefusedError, OSError) as e:
        raise RuntimeError(f"Cannot reach Kismet at {_base_url}: {e}") from None


def kismet_is_running() -> bool:
    """Check if Kismet REST API is reachable."""
    try:
        _kismet_get("/system/user_status", timeout=3.0)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Kismet subprocess manager
# ---------------------------------------------------------------------------

class KismetManager:
    """Manages a Kismet subprocess and provides data accessors."""

    def __init__(self) -> None:
        self.process: subprocess.Popen | None = None
        self.interface: str = ""
        self.log_dir: str = ""
        self._last_networks: list[dict] = []
        self._last_clients: list[dict] = []
        self._last_alerts: list[dict] = []
        self._last_channels: dict = {}
        self._last_datasources: list[dict] = []

    # -- Lifecycle ----------------------------------------------------------

    def start(
        self,
        interface: str = "wlan0",
        http_port: int = 2501,
        log_dir: str | None = None,
    ) -> dict:
        """Start the Kismet subprocess."""
        if self.process and self.process.poll() is None:
            return {"status": "already_running", "pid": self.process.pid}

        self.interface = interface
        if log_dir:
            self.log_dir = log_dir
            os.makedirs(log_dir, exist_ok=True)

        cmd = [
            "kismet_server",
            "--no-ncurses",
            "--no-line-wrap",
            "--no-plugins",
            f"--httpd={KISMET_HOST}:{http_port}",
        ]

        # Add capture source
        cmd.extend(["-c", interface])

        if log_dir:
            cmd.extend(["--log_prefix", log_dir])

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "kismet_server not found. Install Kismet first: "
                "https://www.kismetwireless.net/download/"
            )

        # Wait for the REST API to become available
        self._wait_for_ready(http_port)
        return {"status": "started", "pid": self.process.pid, "interface": interface}

    def _wait_for_ready(self, port: int, timeout: float = 30.0) -> None:
        """Poll until the Kismet HTTP server responds."""
        start = time.time()
        while time.time() - start < timeout:
            if kismet_is_running():
                return
            time.sleep(0.5)
        # Kill if it didn't start
        self.stop()
        raise TimeoutError("Kismet server did not start within timeout")

    def stop(self) -> dict:
        """Gracefully stop the Kismet subprocess."""
        if not self.process or self.process.poll() is not None:
            self.process = None
            return {"status": "not_running"}

        try:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        except Exception as e:
            return {"status": "error", "error": str(e)}

        self.process = None
        return {"status": "stopped"}

    def status(self) -> dict:
        """Return current Kismet status."""
        running = self.process is not None and self.process.poll() is None
        api_reachable = kismet_is_running()
        return {
            "running": running,
            "api_reachable": api_reachable,
            "pid": self.process.pid if running else None,
            "interface": self.interface,
            "host": KISMET_HOST,
            "port": KISMET_PORT,
        }

    # -- Data accessors (cached) -------------------------------------------

    def get_networks(self, force: bool = False) -> list[dict]:
        """Fetch all 802.11 access points from Kismet."""
        if not kismet_is_running():
            return self._last_networks

        try:
            raw = _kismet_post(
                "/devices/views/phydot11_accesspoints/devices.json",
                {"fields": [
                    "kismet.device.base.macaddr",
                    "kismet.device.base.name",
                    "kismet.device.base.commonname",
                    "kismet.device.base.type",
                    "kismet.device.base.channel",
                    "kismet.device.base.frequency",
                    "kismet.device.base.signal",
                    "kismet.device.base.crypt",
                    "kismet.device.base.crypt_string",
                    "kismet.device.base.manuf",
                    "kismet.device.base.first_time",
                    "kismet.device.base.last_time",
                    "kismet.device.base.packets.total",
                    "kismet.device.base.num_alerts",
                    "kismet.device.base.key",
                    "kismet.device.base_datasize",
                ]},
            )
            devices = raw.get("devices", [])
            networks = []
            for d in devices:
                signal_info = d.get("kismet.device.base.signal", {})
                networks.append({
                    "mac": d.get("kismet.device.base.macaddr", ""),
                    "ssid": d.get("kismet.device.base.name", "")
                            or d.get("kismet.device.base.commonname", ""),
                    "channel": d.get("kismet.device.base.channel", ""),
                    "frequency": d.get("kismet.device.base.frequency", 0),
                    "signal_dbm": signal_info.get("last_signal", 0),
                    "signal_max": signal_info.get("max_signal", 0),
                    "crypt": d.get("kismet.device.base.crypt_string", ""),
                    "manufacturer": d.get("kismet.device.base.manuf", ""),
                    "first_seen": d.get("kismet.device.base.first_time", 0),
                    "last_seen": d.get("kismet.device.base.last_time", 0),
                    "packets": d.get("kismet.device.base.packets.total", 0),
                    "alerts": d.get("kismet.device.base.num_alerts", 0),
                    "key": d.get("kismet.device.base.key", ""),
                })
            self._last_networks = networks
            return networks
        except Exception:
            return self._last_networks

    def get_clients(self) -> list[dict]:
        """Fetch all Wi-Fi client devices from Kismet."""
        if not kismet_is_running():
            return self._last_clients

        try:
            raw = _kismet_post(
                "/devices/views/all_devices/devices.json",
                {"fields": [
                    "kismet.device.base.macaddr",
                    "kismet.device.base.name",
                    "kismet.device.base.type",
                    "kismet.device.base.channel",
                    "kismet.device.base.signal",
                    "kismet.device.base.manuf",
                    "kismet.device.base.first_time",
                    "kismet.device.base.last_time",
                    "kismet.device.base.packets.total",
                    "kismet.device.base.key",
                ]},
            )
            devices = raw.get("devices", [])
            clients = []
            for d in devices:
                dev_type = d.get("kismet.device.base.type", "")
                # Filter: only Wi-Fi client devices (not APs)
                if "Wi-Fi" in dev_type and "Client" in dev_type:
                    signal_info = d.get("kismet.device.base.signal", {})
                    clients.append({
                        "mac": d.get("kismet.device.base.macaddr", ""),
                        "name": d.get("kismet.device.base.name", ""),
                        "type": dev_type,
                        "channel": d.get("kismet.device.base.channel", ""),
                        "signal_dbm": signal_info.get("last_signal", 0),
                        "manufacturer": d.get("kismet.device.base.manuf", ""),
                        "first_seen": d.get("kismet.device.base.first_time", 0),
                        "last_seen": d.get("kismet.device.base.last_time", 0),
                        "packets": d.get("kismet.device.base.packets.total", 0),
                        "key": d.get("kismet.device.base.key", ""),
                    })
            self._last_clients = clients
            return clients
        except Exception:
            return self._last_clients

    def get_alerts(self, since_ts: float = 0) -> list[dict]:
        """Fetch alerts from Kismet."""
        if not kismet_is_running():
            return self._last_alerts

        try:
            if since_ts > 0:
                path = f"/alerts/last-time/{since_ts}/alerts.json"
                raw = _kismet_get(path)
            else:
                raw = _kismet_get("/alerts/all_alerts.json")

            alerts_raw = raw.get("alerts", raw) if isinstance(raw, dict) else raw
            if not isinstance(alerts_raw, list):
                alerts_raw = []

            alerts = []
            for a in alerts_raw:
                alerts.append({
                    "type": a.get("kismet.alert.type", ""),
                    "severity": a.get("kismet.alert.severity", 0),
                    "message": a.get("kismet.alert.message", ""),
                    "timestamp": a.get("kismet.alert.timestamp", 0),
                    "mac": a.get("kismet.alert.mac", ""),
                    "phy": a.get("kismet.alert.phyname", ""),
                    "json": a.get("kismet.alert.json", ""),
                })
            self._last_alerts = alerts
            return alerts
        except Exception:
            return self._last_alerts

    def get_channels(self) -> dict:
        """Fetch channel information from Kismet."""
        if not kismet_is_running():
            return self._last_channels

        try:
            raw = _kismet_get("/channels/channels.json")
            channels = {}
            for ch_name, ch_data in raw.items():
                if isinstance(ch_data, dict):
                    channels[ch_name] = {
                        "frequency": ch_data.get("frequency", 0),
                        "packets_total": ch_data.get("packets.total", 0),
                        "packets_data": ch_data.get("packets.data", 0),
                        "packets_crypt": ch_data.get("packets.crypt", 0),
                        "packets_mgmt": ch_data.get("packets.mgmt", 0),
                        "packets_error": ch_data.get("packets.error", 0),
                        "packets_retry": ch_data.get("packets.retry", 0),
                        "devices": ch_data.get("num_devices", 0),
                    }
            self._last_channels = channels
            return channels
        except Exception:
            return self._last_channels

    def get_datasources(self) -> list[dict]:
        """Fetch datasource information from Kismet."""
        if not kismet_is_running():
            return self._last_datasources

        try:
            raw = _kismet_get("/datasource/all_sources.json")
            sources_raw = raw.get("datasources", []) if isinstance(raw, dict) else []
            sources = []
            for s in sources_raw:
                sources.append({
                    "uuid": s.get("kismet.datasource.uuid", ""),
                    "name": s.get("kismet.datasource.name", ""),
                    "interface": s.get("kismet.datasource.interface", ""),
                    "type": s.get("kismet.datasource.type", ""),
                    "channel": s.get("kismet.datasource.channel", ""),
                    "hop_channels": s.get("kismet.datasource.hop_channels", []),
                    "running": s.get("kismet.datasource.running", False),
                    "error": s.get("kismet.datasource.error", ""),
                    "packets": s.get("kismet.datasource.packets.total", 0),
                })
            self._last_datasources = sources
            return sources
        except Exception:
            return self._last_datasources

    # -- Channel control ---------------------------------------------------

    def set_channel(self, source_uuid: str, channel: int) -> dict:
        """Lock a datasource to a specific channel."""
        try:
            _kismet_post(
                f"/datasource/by-uuid/{source_uuid}/set_channel.cmd",
                {"channel": str(channel)},
            )
            return {"status": "ok", "channel": channel}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def set_hop(self, source_uuid: str) -> dict:
        """Re-enable channel hopping on a datasource."""
        try:
            _kismet_post(f"/datasource/by-uuid/{source_uuid}/set_hop.cmd")
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def list_interfaces(self) -> list[dict]:
        """Probe for available wireless interfaces."""
        try:
            raw = _kismet_get("/datasource/list_interfaces.json")
            ifaces = raw.get("interfaces", []) if isinstance(raw, dict) else []
            return [
                {
                    "name": i.get("name", ""),
                    "driver": i.get("driver", ""),
                    "monitor_mode": i.get("monitor", False),
                }
                for i in ifaces
            ]
        except Exception:
            return []


# Singleton instance
kismet_manager = KismetManager()
