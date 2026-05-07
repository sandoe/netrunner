"""Node CRUD + execute + read + capture + backup API endpoints."""
from __future__ import annotations

import base64
import json
import re
import shlex
import time
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from ..core.session import session_manager
from ..core.vault import store_credentials, load_credentials, delete_credentials, has_credentials
from ..core.detect import detect_device_type

router = APIRouter()

DATA_DIR    = Path("data")
NODES_FILE  = DATA_DIR / "nodes.json"
CONFIGS_DIR = DATA_DIR / "configs"
CAPTURES_DIR = DATA_DIR / "captures"
EXPORTS_DIR  = DATA_DIR / "exports"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_nodes() -> dict:
    if NODES_FILE.exists():
        try:
            return json.loads(NODES_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_nodes(nodes: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    NODES_FILE.write_text(json.dumps(nodes, indent=2))


def _safe_name(value: str, fallback: str = "file") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(value or fallback)).strip("_")
    return cleaned or fallback


def _node_public(nid: str, node: dict) -> dict:
    return {
        "id": nid,
        "name": node.get("name"),
        "host": node.get("host"),
        "port": node.get("port"),
        "username": node.get("username"),
        "transport": node.get("transport", "telnet"),
        "device_type": node.get("device_type", "unknown"),
        "has_password": has_credentials(nid),
        "created": node.get("created"),
        "tags": node.get("tags", []),
    }


def _get_node_with_creds(nid: str, nodes: dict) -> dict:
    node = dict(nodes[nid])
    username, password = load_credentials(nid)
    node["username"] = username
    node["password"] = password
    return node


# ---------------------------------------------------------------------------
# Read command registry
# ---------------------------------------------------------------------------

READ_CMDS: dict[str, list[str]] = {
    # Network
    "ip":           ["ip addr show"],
    "routes":       ["ip route show", "ip -6 route show 2>/dev/null"],
    "interfaces":   ["ip link show"],
    "neighbors":    ["ip neigh show 2>/dev/null || echo '(neighbor table unavailable)'"],
    "sockets":      ["ss -tulpn 2>/dev/null || netstat -tulpn 2>/dev/null || echo '(ss/netstat unavailable)'"],
    "resolver":     ["cat /etc/resolv.conf 2>/dev/null || echo '(resolv.conf unavailable)'"],
    "nftables":     ["nft list ruleset 2>/dev/null || echo '(nftables empty or not available)'"],
    "iptables":     ["iptables-save 2>/dev/null || iptables -S 2>/dev/null || echo '(iptables not available)'"],
    "ufw":          ["ufw status verbose 2>/dev/null || echo '(ufw not available)'"],
    "wireguard":    ["wg show all 2>/dev/null || echo '(WireGuard not running)'"],
    "forwarding":   ["sysctl net.ipv4.ip_forward net.ipv6.conf.all.forwarding 2>/dev/null || echo '(sysctl unavailable)'"],
    "vlan-router":  ["ip -d link show type vlan 2>/dev/null || echo '(no VLAN sub-interfaces)'"],
    "vlan-switch":  [
        "ip -d link show type bridge 2>/dev/null || echo '(no bridges)'",
        "bridge vlan show 2>/dev/null || echo '(bridge vlan unavailable)'",
    ],
    "dns-service":  [
        "cat /etc/resolv.conf 2>/dev/null || echo '(resolv.conf unavailable)'",
        "sed -n '/# BEGIN NETRUNNER HOSTS/,/# END NETRUNNER HOSTS/p' /etc/hosts 2>/dev/null",
    ],
    "dhcp-server":  [
        "cat /etc/dnsmasq.d/netrunner-dhcp.conf 2>/dev/null || echo '(dnsmasq config not found)'",
        "cat /var/lib/misc/dnsmasq.leases 2>/dev/null || echo '(no DHCP leases yet)'",
    ],
    "nat":          [
        "iptables -S NR_FORWARD 2>/dev/null || echo '(no NR_FORWARD chain yet)'",
        "iptables -t nat -S NR_NAT 2>/dev/null || echo '(no NR_NAT chain yet)'",
    ],
    "if-stats":     ["ip -s link show"],
    "wifi-scan":    ["nmcli -t -f SSID,SIGNAL,SECURITY dev wifi list 2>/dev/null || iwlist scan 2>/dev/null | grep -E 'ESSID|Signal|Encryption' || echo '(WiFi tools not available)'"],
    "nmap-scan":    ["nmap -F 127.0.0.1 2>/dev/null || echo '(nmap not installed)'"],

    # Linux system
    "services":     ["systemctl list-units --type=service --state=running --no-pager 2>/dev/null || service --status-all 2>/dev/null || rc-status 2>/dev/null"],
    "packages":     ["dpkg -l 2>/dev/null | tail -n +6 | head -50 || rpm -qa 2>/dev/null | head -50 || apk list --installed 2>/dev/null | head -50"],
    "users":        ["cat /etc/passwd", "who 2>/dev/null || w 2>/dev/null || true"],
    "groups":       ["cat /etc/group"],
    "cron":         ["crontab -l 2>/dev/null || echo '(no crontab for root)'", "ls -la /etc/cron* 2>/dev/null || true"],
    "logs":         ["journalctl -n 80 --no-pager 2>/dev/null || tail -n 80 /var/log/syslog 2>/dev/null || tail -n 80 /var/log/messages 2>/dev/null"],
    "disk":         ["df -h", "lsblk 2>/dev/null || fdisk -l 2>/dev/null | head -30"],
    "cpu":          ["lscpu 2>/dev/null || cat /proc/cpuinfo | head -30", "uptime"],
    "memory":       ["free -h", "cat /proc/meminfo | head -10"],
    "processes":    ["ps aux --sort=-%cpu 2>/dev/null | head -25 || ps aux | head -25"],
    "os-info":      ["uname -a", "cat /etc/os-release 2>/dev/null || cat /etc/issue 2>/dev/null"],
    "environment":  ["env | sort"],
    "mounts":       ["mount | grep -v 'tmpfs\\|devpts\\|cgroup\\|sysfs\\|proc'", "cat /etc/fstab 2>/dev/null"],

    # Raspberry Pi
    "rpi-config":   [f"cat /boot/firmware/config.txt 2>/dev/null || cat /boot/config.txt 2>/dev/null || echo '(config.txt not found)'"],
    "rpi-gpio":     ["raspi-gpio get 2>/dev/null || gpio readall 2>/dev/null || echo '(gpio tools not available — install raspi-gpio or wiringpi)'"],
    "rpi-temp":     [
        "vcgencmd measure_temp 2>/dev/null || cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{printf \"temp=%.1f C\\n\", $1/1000}'",
        "vcgencmd get_throttled 2>/dev/null || true",
    ],
    "rpi-i2c":      ["i2cdetect -l 2>/dev/null", "i2cdetect -y 1 2>/dev/null || echo '(I2C bus 1 not available)'"],
    "rpi-spi":      ["ls /dev/spidev* 2>/dev/null || echo '(SPI not enabled)'", "lsmod | grep spi"],
    "rpi-camera":   ["vcgencmd get_camera 2>/dev/null || libcamera-hello --list-cameras 2>/dev/null || echo '(camera tools not available)'"],
    "rpi-clocks":   [
        "vcgencmd measure_clock arm 2>/dev/null || true",
        "vcgencmd measure_clock core 2>/dev/null || true",
        "vcgencmd measure_clock v3d 2>/dev/null || true",
    ],
    "rpi-voltage":  [
        "vcgencmd measure_volts core 2>/dev/null || true",
        "vcgencmd measure_volts sdram_c 2>/dev/null || true",
    ],
    "rpi-info":     [
        "uname -a",
        "cat /proc/cpuinfo | grep -E 'Model|Hardware|Revision|Serial'",
        "vcgencmd measure_temp 2>/dev/null || cat /sys/class/thermal/thermal_zone0/temp | awk '{printf \"temp=%.1f C\\n\", $1/1000}' 2>/dev/null",
        "vcgencmd get_throttled 2>/dev/null || true",
        "free -h",
        "df -h /",
        "ip -4 addr show | grep inet",
    ],
}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class NodeCreate(BaseModel):
    name: str
    host: str
    port: int = 22
    username: str = "root"
    password: str = ""
    transport: str = "ssh"
    device_type: str = "unknown"
    tags: list[str] = []

    @field_validator("transport")
    @classmethod
    def transport_valid(cls, v):
        if v not in ("telnet", "ssh"):
            raise ValueError("transport must be 'telnet' or 'ssh'")
        return v

    @field_validator("port")
    @classmethod
    def port_valid(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("port must be 1-65535")
        return v


class NodeUpdate(NodeCreate):
    name: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    transport: str | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/nodes")
def api_nodes():
    nodes = load_nodes()
    return {nid: _node_public(nid, n) for nid, n in nodes.items()}


@router.post("/nodes", status_code=201)
def api_nodes_create(body: NodeCreate):
    nodes = load_nodes()
    nid   = f"n{int(time.time() * 1000)}"
    node  = {
        "id":          nid,
        "name":        body.name,
        "host":        body.host,
        "port":        body.port,
        "username":    body.username,
        "transport":   body.transport,
        "device_type": body.device_type,
        "tags":        body.tags,
        "created":     datetime.now().isoformat(),
    }
    store_credentials(nid, body.username, body.password)
    nodes[nid] = node
    save_nodes(nodes)
    return _node_public(nid, node)


@router.put("/nodes/{nid}")
def api_node_update(nid: str, body: NodeUpdate):
    nodes = load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    node = nodes[nid]
    if body.name        is not None: node["name"]        = body.name
    if body.host        is not None: node["host"]        = body.host
    if body.port        is not None: node["port"]        = body.port
    if body.transport   is not None: node["transport"]   = body.transport
    if body.device_type is not None: node["device_type"] = body.device_type
    if body.tags        is not None: node["tags"]        = body.tags
    if body.username is not None or body.password is not None:
        old_user, old_pass = load_credentials(nid)
        store_credentials(
            nid,
            body.username if body.username is not None else old_user,
            body.password if body.password is not None else old_pass,
        )
        if body.username is not None:
            node["username"] = body.username
    save_nodes(nodes)
    return _node_public(nid, node)


@router.delete("/nodes/{nid}")
def api_node_delete(nid: str):
    nodes = load_nodes()
    nodes.pop(nid, None)
    save_nodes(nodes)
    session_manager.close(nid)
    delete_credentials(nid)
    return {"ok": True}


@router.get("/nodes/connections")
def api_node_connections():
    active = set(session_manager.active_ids())
    nodes = load_nodes()
    return {nid: {"connected": nid in active} for nid in nodes}


@router.post("/nodes/{nid}/connect")
def api_node_connect(nid: str):
    nodes = load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    node = _get_node_with_creds(nid, nodes)
    cl, err = session_manager.open(nid, node)
    if err:
        raise HTTPException(500, err)
    return {"status": "connected"}


@router.post("/nodes/{nid}/disconnect")
def api_node_disconnect(nid: str):
    session_manager.close(nid)
    return {"ok": True}


@router.post("/nodes/{nid}/detect")
def api_node_detect(nid: str):
    nodes = load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    node = _get_node_with_creds(nid, nodes)
    device_type = detect_device_type(
        node["host"], node["port"],
        node.get("username", "root"),
        node.get("password", ""),
    )
    nodes[nid]["device_type"] = device_type
    save_nodes(nodes)
    return {"device_type": device_type}


@router.get("/nodes/{nid}/read/{ctype}")
def api_node_read(nid: str, ctype: str):
    nodes = load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    if ctype not in READ_CMDS:
        raise HTTPException(400, f"Unknown type '{ctype}'. Valid: {', '.join(READ_CMDS)}")
    node = _get_node_with_creds(nid, nodes)
    results, err = session_manager.run(nid, node, READ_CMDS[ctype])
    if err:
        raise HTTPException(500, err)
    return {"results": results}


@router.post("/nodes/{nid}/execute")
def api_node_execute(nid: str, body: dict):
    nodes = load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    cmds = body.get("commands", [])
    if isinstance(cmds, str):
        cmds = [c for c in cmds.split("\n") if c.strip()]
    node = _get_node_with_creds(nid, nodes)
    results, err = session_manager.run(nid, node, cmds)
    if err:
        raise HTTPException(500, err)
    return {"results": results}


# ---------------------------------------------------------------------------
# Captures
# ---------------------------------------------------------------------------

_captures: dict[str, dict] = {}
_backups:  dict[str, dict] = {}


def _cap_paths(nid: str, cap_id: str) -> dict:
    base = f"/tmp/nrcap_{_safe_name(nid)}_{_safe_name(cap_id)}"
    return {"pcap": f"{base}.pcap", "pid": f"{base}.pid", "log": f"{base}.log"}


def _capture_local_dir(nid: str) -> Path:
    path = CAPTURES_DIR / _safe_name(nid, "node")
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.get("/nodes/{nid}/capture")
def api_capture_list(nid: str):
    nodes = load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    prefix = f"{nid}:"
    items = [m for k, m in _captures.items() if k.startswith(prefix)]
    items.sort(key=lambda m: m.get("started", ""), reverse=True)
    return {"captures": items}


@router.delete("/nodes/{nid}/capture/{cap_id}")
def api_capture_delete(nid: str, cap_id: str):
    nodes = load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    key = f"{nid}:{cap_id}"
    meta = _captures.pop(key, None)
    if not meta:
        raise HTTPException(404, "Capture not found")
    paths = meta["paths"]
    cleanup = (
        f"PID=$(cat {shlex.quote(paths['pid'])} 2>/dev/null || echo ''); "
        f"if [ -n \"$PID\" ]; then kill \"$PID\" 2>/dev/null || true; fi; "
        f"rm -f {shlex.quote(paths['pcap'])} {shlex.quote(paths['pid'])} {shlex.quote(paths['log'])}"
    )
    try:
        node = _get_node_with_creds(nid, nodes)
        session_manager.run(nid, node, [f"sh -lc {shlex.quote(cleanup)}"])
    except Exception:
        pass
    local = _capture_local_dir(nid) / f"{_safe_name(cap_id)}.pcap"
    if local.exists():
        try: local.unlink()
        except Exception: pass
    return {"ok": True}


@router.post("/nodes/{nid}/capture/start")
def api_capture_start(nid: str, body: dict):
    nodes = load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")

    cap_id       = _safe_name(body.get("id") or f"cap_{int(time.time())}", "capture")
    iface        = (body.get("interface") or "eth0").strip() or "eth0"
    packet_limit = max(0, int(body.get("packet_limit", 0) or 0))
    filter_expr  = (body.get("filter") or "").strip()

    paths = _cap_paths(nid, cap_id)
    tcpdump = ["tcpdump", "-i", iface, "-U", "-n", "-s0", "-w", paths["pcap"]]
    if packet_limit:
        tcpdump += ["-c", str(packet_limit)]
    if filter_expr:
        tcpdump += shlex.split(filter_expr)

    shell_join = lambda p: " ".join(shlex.quote(str(x)) for x in p)
    start_cmd = (
        f"nohup {shell_join(tcpdump)} > {shlex.quote(paths['log'])} 2>&1 & "
        f"echo $! > {shlex.quote(paths['pid'])}"
    )
    remote = (
        f"rm -f {shlex.quote(paths['pcap'])} {shlex.quote(paths['pid'])} {shlex.quote(paths['log'])}; "
        f"sh -lc {shlex.quote(start_cmd)}; "
        f"sleep 1; cat {shlex.quote(paths['pid'])} 2>/dev/null || echo 0"
    )
    node = _get_node_with_creds(nid, nodes)
    
    # Check if tcpdump is installed
    check_results, check_err = session_manager.run(nid, node, ["command -v tcpdump || echo '__MISSING__'"])
    if check_err:
        raise HTTPException(500, check_err)
    if "__MISSING__" in (check_results[0].get("output", "") if check_results else ""):
        raise HTTPException(400, "tcpdump is not installed on this node. Please install it to use capture features.")

    results, err = session_manager.run(nid, node, [remote])
    if err:
        raise HTTPException(500, err)

    output = (results[0].get("output", "") if results else "")
    pid_match = re.search(r"(\d+)", output)
    meta = {
        "id": cap_id, "interface": iface, "filter": filter_expr,
        "packet_limit": packet_limit, "started": datetime.now().isoformat(),
        "paths": paths, "pid": pid_match.group(1) if pid_match else "",
    }
    _captures[f"{nid}:{cap_id}"] = meta
    return {"ok": True, "capture": meta}


@router.get("/nodes/{nid}/capture/{cap_id}/status")
def api_capture_status(nid: str, cap_id: str):
    nodes = load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    meta = _captures.get(f"{nid}:{cap_id}")
    if not meta:
        raise HTTPException(404, "Capture not found")

    paths = meta["paths"]
    status_script = (
        f"PID=$(cat {shlex.quote(paths['pid'])} 2>/dev/null || echo ''); "
        f"if [ -n \"$PID\" ] && kill -0 \"$PID\" 2>/dev/null; then echo STATE=running; else echo STATE=stopped; fi; "
        f"echo PID=$PID; "
        f"SIZE=$(wc -c < {shlex.quote(paths['pcap'])} 2>/dev/null || echo 0); echo SIZE=$SIZE; "
        f"tail -n 10 {shlex.quote(paths['log'])} 2>/dev/null || true"
    )
    node = _get_node_with_creds(nid, nodes)
    results, err = session_manager.run(nid, node, [f"sh -lc {shlex.quote(status_script)}"])
    if err:
        raise HTTPException(500, err)
    output = results[0].get("output", "") if results else ""
    state  = "running" if "STATE=running" in output else "stopped"
    size_m = re.search(r"SIZE=(\d+)", output)
    return {"capture": {**meta, "state": state, "size": int(size_m.group(1)) if size_m else 0}}


@router.post("/nodes/{nid}/capture/{cap_id}/stop")
def api_capture_stop(nid: str, cap_id: str):
    nodes = load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    meta = _captures.get(f"{nid}:{cap_id}")
    if not meta:
        raise HTTPException(404, "Capture not found")
    paths = meta["paths"]
    stop_script = (
        f"PID=$(cat {shlex.quote(paths['pid'])} 2>/dev/null || echo ''); "
        f"if [ -n \"$PID\" ]; then kill \"$PID\" 2>/dev/null || true; sleep 1; fi; "
        f"SIZE=$(wc -c < {shlex.quote(paths['pcap'])} 2>/dev/null || echo 0); echo SIZE=$SIZE"
    )
    node = _get_node_with_creds(nid, nodes)
    results, err = session_manager.run(nid, node, [f"sh -lc {shlex.quote(stop_script)}"])
    if err:
        raise HTTPException(500, err)
    output = results[0].get("output", "") if results else ""
    size_m = re.search(r"SIZE=(\d+)", output)
    return {"ok": True, "size": int(size_m.group(1)) if size_m else 0}


@router.get("/nodes/{nid}/capture/{cap_id}/download")
def api_capture_download(nid: str, cap_id: str):
    nodes = load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    meta = _captures.get(f"{nid}:{cap_id}")
    if not meta:
        raise HTTPException(404, "Capture not found")
    paths = meta["paths"]
    dl_script = (
        f"if [ ! -f {shlex.quote(paths['pcap'])} ]; then echo __MISSING__; "
        f"else base64 {shlex.quote(paths['pcap'])} 2>/dev/null || busybox base64 {shlex.quote(paths['pcap'])}; fi"
    )
    node = _get_node_with_creds(nid, nodes)
    results, err = session_manager.run(nid, node, [f"sh -lc {shlex.quote(dl_script)}"])
    if err:
        raise HTTPException(500, err)
    output = (results[0].get("output") or "").strip() if results else ""
    if "__MISSING__" in output:
        raise HTTPException(404, "Remote capture file not found")
    try:
        raw = base64.b64decode("".join(output.splitlines()))
    except Exception as e:
        raise HTTPException(500, f"Failed to decode capture: {e}")

    local_dir = _capture_local_dir(nid)
    fname = f"{_safe_name(cap_id)}.pcap"
    (local_dir / fname).write_bytes(raw)
    return FileResponse(local_dir / fname, filename=fname, media_type="application/octet-stream")


# ---------------------------------------------------------------------------
# Backup / rollback
# ---------------------------------------------------------------------------

def _backup_paths(nid: str, backup_id: str) -> dict:
    base = f"/tmp/nrbackup_{_safe_name(nid)}_{_safe_name(backup_id)}"
    return {
        "dir": base, "ip_addr": f"{base}/ip.addr",
        "ip_route": f"{base}/ip.route", "ip6_route": f"{base}/ip6.route",
        "ipv4_forward": f"{base}/ipv4_forward", "ipv6_forward": f"{base}/ipv6_forward",
        "iptables": f"{base}/iptables.save", "nft": f"{base}/nft.rules",
        "resolv": f"{base}/resolv.conf", "hosts": f"{base}/hosts",
        "dnsmasq": f"{base}/netrunner-dhcp.conf", "wireguard": f"{base}/wireguard",
    }


@router.post("/nodes/{nid}/backup")
def api_node_backup(nid: str, body: dict = {}):
    nodes = load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    backup_id = _safe_name((body or {}).get("id") or f"bkp_{int(time.time())}", "backup")
    paths = _backup_paths(nid, backup_id)

    from ..generators.network import gen_backup_commands
    cmds  = gen_backup_commands(paths)
    node  = _get_node_with_creds(nid, nodes)
    results, err = session_manager.run(nid, node, cmds)
    if err:
        raise HTTPException(500, err)

    # Build restore commands inline (simplified)
    meta = {
        "id": backup_id, "created": datetime.now().isoformat(),
        "paths": paths, "results": results,
    }
    _backups[nid] = meta
    return {"ok": True, "backup": {k: v for k, v in meta.items() if k != "results"}}


@router.post("/nodes/{nid}/rollback")
def api_node_rollback(nid: str):
    nodes = load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    meta = _backups.get(nid)
    if not meta:
        raise HTTPException(404, "No backup available for this node")
    paths = meta["paths"]

    from ..generators.network import gen_restore_commands
    restore_cmds = gen_restore_commands(paths)
    node = _get_node_with_creds(nid, nodes)
    results, err = session_manager.run(nid, node, restore_cmds)
    if err:
        raise HTTPException(500, err)
    return {"ok": True, "backup": {"id": meta["id"], "created": meta["created"]}, "results": results}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

DEFAULT_EXPORT_DIAGNOSTICS = [
    "ip", "routes", "interfaces", "neighbors", "sockets", "resolver",
    "forwarding", "iptables", "nftables", "ufw", "wireguard", "dns-service",
    "dhcp-server", "vlan-switch", "vlan-router",
]


@router.post("/nodes/{nid}/export")
def api_node_export(nid: str, body: dict = {}):
    nodes = load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    body = body or {}
    node_meta = nodes[nid]
    export_name = f"{_safe_name(node_meta.get('name', nid))}_export_{int(time.time())}.zip"
    export_path = EXPORTS_DIR / export_name
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    diag_types     = body.get("live_diagnostics")
    if diag_types is None:
        diag_types = DEFAULT_EXPORT_DIAGNOSTICS
    include_caps   = body.get("include_captures", True)

    diagnostics: dict[str, str] = {}
    diag_errors:  dict[str, str] = {}
    if diag_types:
        node_full = _get_node_with_creds(nid, nodes)
        for ctype in diag_types:
            if ctype not in READ_CMDS:
                diag_errors[ctype] = f"unknown type '{ctype}'"
                continue
            results, err = session_manager.run(nid, node_full, READ_CMDS[ctype])
            if err:
                diag_errors[ctype] = err
                continue
            diagnostics[ctype] = "\n\n".join(
                (r.get("output") or r.get("error") or "") for r in (results or [])
            ).strip()

    summary = {
        "exported": datetime.now().isoformat(),
        "node": _node_public(nid, node_meta),
        "diagnostic_types": list(diagnostics.keys()),
        "diagnostic_errors": diag_errors,
    }

    with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("summary.json", json.dumps(summary, indent=2))
        for ctype, output in diagnostics.items():
            zf.writestr(f"diagnostics/{_safe_name(ctype)}.txt", output)
        for cfg in body.get("saved_configs", []):
            if cfg.get("name") and cfg.get("content") is not None:
                zf.writestr(f"configs/{Path(cfg['name']).name}", cfg["content"])
        if include_caps:
            cap_dir = _capture_local_dir(nid)
            for pcap in cap_dir.glob("*.pcap"):
                zf.write(pcap, f"captures/{pcap.name}")

    return {
        "name": export_name,
        "diagnostic_types": list(diagnostics.keys()),
        "diagnostic_errors": diag_errors,
    }


@router.get("/exports/{fname}")
def api_export_download(fname: str):
    fname = Path(fname).name
    p = EXPORTS_DIR / fname
    if not p.exists():
        raise HTTPException(404, "Not found")
    return FileResponse(p, filename=fname, media_type="application/zip")
