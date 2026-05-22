"""Node CRUD + execute + read + capture + backup API endpoints."""
from __future__ import annotations

import base64
import json
import re
import shlex
import time
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from ..core.session import session_manager
from ..core.vault import store_credentials, load_credentials, delete_credentials, has_credentials
from ..core.detect import detect_device_type, detect_package_manager
from ..core.db import load_nodes_db, save_node_db, delete_node_db

router = APIRouter()

DATA_DIR    = Path("data")
CONFIGS_DIR = DATA_DIR / "configs"
CAPTURES_DIR = DATA_DIR / "captures"
EXPORTS_DIR  = DATA_DIR / "exports"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

async def load_nodes() -> dict:
    return await load_nodes_db()


async def save_nodes(nodes: dict) -> None:
    for nid, n in nodes.items():
        await save_node_db(n)


async def _node_public(nid: str, node: dict) -> dict:
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
    }


async def _get_node_with_creds(nid: str, nodes: dict) -> dict:
    node = dict(nodes[nid])
    username, password = await load_credentials(nid)
    node["username"] = username or "root"
    node["password"] = password
    return node


def _safe_name(value: str, fallback: str = "file") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(value or fallback)).strip("_")
    return cleaned or fallback


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
    "wireguard":    ["wg show 2>/dev/null || wg 2>/dev/null || echo '(WireGuard not running)'"],
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
    "nmap-scan":    ["nmap -sV -F 127.0.0.1 2>/dev/null || nmap -F 127.0.0.1 2>/dev/null || echo '(nmap not installed)'"],

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
async def api_nodes():
    nodes = await load_nodes()
    return {nid: await _node_public(nid, n) for nid, n in nodes.items()}


@router.post("/nodes", status_code=201)
async def api_nodes_create(body: NodeCreate):
    nodes = await load_nodes()
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
    await store_credentials(nid, body.username, body.password)
    nodes[nid] = node
    await save_nodes(nodes)
    return await _node_public(nid, node)


@router.put("/nodes/{nid}")
async def api_node_update(nid: str, body: NodeUpdate):
    nodes = await load_nodes()
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
        old_user, old_pass = await load_credentials(nid)
        await store_credentials(
            nid,
            body.username if body.username is not None else old_user,
            body.password if body.password is not None else old_pass,
        )
        if body.username is not None:
            node["username"] = body.username
    await save_nodes(nodes)
    return await _node_public(nid, node)


@router.delete("/nodes/{nid}")
async def api_node_delete(nid: str):
    nodes = await load_nodes()
    nodes.pop(nid, None)
    await delete_node_db(nid)
    session_manager.close(nid)
    await delete_credentials(nid)
    return {"ok": True}


@router.get("/nodes/connections")
async def api_node_connections():
    active = set(session_manager.active_ids())
    nodes = await load_nodes()
    return {nid: {"connected": nid in active} for nid in nodes}


@router.post("/nodes/{nid}/connect")
async def api_node_connect(nid: str):
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    node = await _get_node_with_creds(nid, nodes)
    cl, err = await session_manager.open(nid, node)
    if err:
        raise HTTPException(500, err)
    return {"status": "connected"}


@router.post("/nodes/{nid}/disconnect")
async def api_node_disconnect(nid: str):
    session_manager.close(nid)
    return {"ok": True}


async def _discover_gns3_node_details(node: dict) -> tuple[Optional[str], Optional[str]]:
    """Attempt to discover GNS3 project_id and node_id for a GNS3 node by its console port and name."""
    from .gns3 import _gns3_req
    port = node.get("port")
    node_name = node.get("name", "").strip().lower()
    if not port:
        return None, None
    try:
        projects = await _gns3_req("GET", "/projects")
        if not projects:
            return None, None
        
        # Sort projects to prioritize "opened" status
        sorted_projects = sorted(
            projects, 
            key=lambda p: 0 if p.get("status") == "opened" else 1
        )
        
        best_match = None
        
        for proj in sorted_projects:
            proj_id = proj.get("project_id")
            if not proj_id:
                continue
            try:
                proj_nodes = await _gns3_req("GET", f"/projects/{proj_id}/nodes")
            except Exception:
                continue
            if not proj_nodes:
                continue
            for gn in proj_nodes:
                if gn.get("console") == port:
                    gn_name = gn.get("name", "").strip().lower()
                    if node_name and gn_name == node_name:
                        # Perfect match: port and name match
                        return proj_id, gn.get("node_id")
                    elif not best_match:
                        # Port matches, keep as fallback candidate
                        best_match = (proj_id, gn.get("node_id"))
        
        if best_match:
            return best_match
            
    except Exception as e:
        print(f"[GNS3 Discovery Error] {e}")
    return None, None


@router.post("/nodes/{nid}/reboot")
async def api_node_reboot(nid: str, body: Optional[dict] = None):
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    node = await _get_node_with_creds(nid, nodes)
    
    body = body or {}
    method = body.get("method", "command")
    
    if method == "gns3":
        # Check metadata for GNS3 IDs, otherwise perform dynamic auto-discovery
        gns3_meta = node.get("metadata", {}).get("gns3", {})
        project_id = gns3_meta.get("project_id")
        node_id = gns3_meta.get("node_id")
        
        force_rediscover = False
        if project_id and node_id:
            # Self-healing verification: test if project/node is active and accessible
            from .gns3 import _gns3_req
            try:
                await _gns3_req("GET", f"/projects/{project_id}/nodes/{node_id}")
            except Exception:
                force_rediscover = True
                
        if not project_id or not node_id or force_rediscover:
            new_project_id, new_node_id = await _discover_gns3_node_details(node)
            if new_project_id and new_node_id:
                project_id = new_project_id
                node_id = new_node_id
                if "metadata" not in nodes[nid]:
                    nodes[nid]["metadata"] = {}
                nodes[nid]["metadata"]["gns3"] = {
                    "project_id": project_id,
                    "node_id": node_id
                }
                await save_node_db(nodes[nid])
            elif not project_id or not node_id:
                raise HTTPException(
                    400, 
                    "Could not discover GNS3 project ID or node ID for this node. Ensure the node is active in GNS3."
                )
                
        # Send reload request via GNS3 API
        from .gns3 import _gns3_req
        try:
            res = await _gns3_req("POST", f"/projects/{project_id}/nodes/{node_id}/reload")
            # Force disconnect console immediately because it is rebooting
            session_manager.close(nid)
            return {
                "status": "success",
                "message": "GNS3 API reload initiated successfully.",
                "api_call": f"POST /projects/{project_id}/nodes/{node_id}/reload",
                "details": res
            }
        except Exception as e:
            raise HTTPException(500, f"GNS3 API reload failed: {e}")
            
    else: # method == "command"
        password = node.get("password", "")
        if password:
            escaped = password.replace("'", "'\\''")
            cmd = f"reboot -f || echo '{escaped}' | sudo -S reboot -f || sudo reboot -f || reboot || sudo reboot"
        else:
            cmd = "reboot -f || sudo reboot -f || reboot || sudo reboot"
            
        results, err = await session_manager.run(nid, node, [cmd])
        if err:
            raise HTTPException(500, f"Failed to execute reboot command: {err}")
            
        # Give the session a tiny moment to process and verify connection state
        # If still connected, command finished but connection did not drop (meaning it failed)
        if session_manager.is_connected(nid):
            output = ""
            if results:
                output = results[0].get("output") or results[0].get("error") or ""
            raise HTTPException(
                500,
                f"Reboot command failed: {output or 'Node finished command but connection was not severed.'}"
            )
            
        session_manager.close(nid)
        return {
            "status": "success",
            "message": "Console terminal reboot command accepted.",
            "api_call": "Terminal force-reboot command sent"
        }




class Gns3ApiRequest(BaseModel):
    method: str
    path: str
    body: Optional[dict] = None

Gns3ApiRequest.model_rebuild()

@router.post("/nodes/{nid}/gns3-api")
async def api_node_gns3_api(nid: str, payload: Gns3ApiRequest):
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")
    node = await _get_node_with_creds(nid, nodes)
    
    # 1. Discover or load GNS3 details
    gns3_meta = node.get("metadata", {}).get("gns3", {})
    project_id = gns3_meta.get("project_id")
    node_id = gns3_meta.get("node_id")
    
    force_rediscover = False
    if project_id and node_id:
        # Self-healing verification: test if project/node is active and accessible
        from .gns3 import _gns3_req
        try:
            await _gns3_req("GET", f"/projects/{project_id}/nodes/{node_id}")
        except Exception:
            force_rediscover = True
            
    if not project_id or not node_id or force_rediscover:
        new_project_id, new_node_id = await _discover_gns3_node_details(node)
        if new_project_id and new_node_id:
            project_id = new_project_id
            node_id = new_node_id
            if "metadata" not in nodes[nid]:
                nodes[nid]["metadata"] = {}
            nodes[nid]["metadata"]["gns3"] = {
                "project_id": project_id,
                "node_id": node_id
            }
            await save_node_db(nodes[nid])
        elif not project_id or not node_id:
            raise HTTPException(
                400,
                "Could not auto-discover GNS3 IDs. Ensure the node is currently running in a GNS3 project."
            )
            
    # 2. Format path placeholders: replace '{project_id}' and '{node_id}'
    formatted_path = payload.path.replace("{project_id}", project_id).replace("{node_id}", node_id)
    if not formatted_path.startswith("/"):
        formatted_path = "/" + formatted_path
        
    # 3. Call _gns3_req
    from .gns3 import _gns3_req
    try:
        res = await _gns3_req(payload.method.upper(), formatted_path, payload.body)
        return {
            "status": "success",
            "url": f"{payload.method.upper()} /v2{formatted_path}",
            "response": res
        }
    except Exception as e:
        raise HTTPException(500, f"GNS3 API call failed: {e}")



@router.post("/nodes/{nid}/detect")
async def api_node_detect(nid: str):
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    node = await _get_node_with_creds(nid, nodes)
    device_type = detect_device_type(
        node["host"], node["port"],
        node.get("username", "root"),
        node.get("password", ""),
    )
    nodes[nid]["device_type"] = device_type
    await save_node_db(nodes[nid])
    return {"device_type": device_type}


@router.get("/nodes/{nid}/read/{ctype}")
async def api_node_read(nid: str, ctype: str):
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    if ctype not in READ_CMDS:
        raise HTTPException(400, f"Unknown type '{ctype}'. Valid: {', '.join(READ_CMDS)}")
    node = await _get_node_with_creds(nid, nodes)
    results, err = await session_manager.run(nid, node, READ_CMDS[ctype])
    if err:
        raise HTTPException(500, err)
    return {"results": results}


@router.post("/nodes/{nid}/execute")
async def api_node_execute(nid: str, body: dict):
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    cmds = body.get("commands", [])
    if isinstance(cmds, str):
        cmds = [c for c in cmds.split("\n") if c.strip()]
    node = await _get_node_with_creds(nid, nodes)
    results, err = await session_manager.run(nid, node, cmds)
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
async def api_capture_list(nid: str):
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    prefix = f"{nid}:"
    items = [m for k, m in _captures.items() if k.startswith(prefix)]
    items.sort(key=lambda m: m.get("started", ""), reverse=True)
    return {"captures": items}


@router.delete("/nodes/{nid}/capture/{cap_id}")
async def api_capture_delete(nid: str, cap_id: str):
    nodes = await load_nodes()
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
        node = await _get_node_with_creds(nid, nodes)
        await session_manager.run(nid, node, [f"sh -lc {shlex.quote(cleanup)}"])
    except Exception:
        pass
    local = _capture_local_dir(nid) / f"{_safe_name(cap_id)}.pcap"
    if local.exists():
        try: local.unlink()
        except Exception: pass
    return {"ok": True}


@router.post("/nodes/{nid}/capture/start")
async def api_capture_start(nid: str, body: dict):
    nodes = await load_nodes()
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
    node = await _get_node_with_creds(nid, nodes)
    
    # Check if tcpdump is installed
    check_results, check_err = await session_manager.run(nid, node, ["command -v tcpdump || echo '__MISSING__'"])
    if check_err:
        raise HTTPException(500, check_err)
    if "__MISSING__" in (check_results[0].get("output", "") if check_results else ""):
        raise HTTPException(400, "tcpdump is not installed on this node. Please install it to use capture features.")

    results, err = await session_manager.run(nid, node, [remote])
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
async def api_capture_status(nid: str, cap_id: str):
    nodes = await load_nodes()
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
    node = await _get_node_with_creds(nid, nodes)
    results, err = await session_manager.run(nid, node, [f"sh -lc {shlex.quote(status_script)}"])
    if err:
        raise HTTPException(500, err)
    output = results[0].get("output", "") if results else ""
    state  = "running" if "STATE=running" in output else "stopped"
    size_m = re.search(r"SIZE=(\d+)", output)
    return {"capture": {**meta, "state": state, "size": int(size_m.group(1)) if size_m else 0}}


@router.post("/nodes/{nid}/capture/{cap_id}/stop")
async def api_capture_stop(nid: str, cap_id: str):
    nodes = await load_nodes()
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
    node = await _get_node_with_creds(nid, nodes)
    results, err = await session_manager.run(nid, node, [f"sh -lc {shlex.quote(stop_script)}"])
    if err:
        raise HTTPException(500, err)
    output = results[0].get("output", "") if results else ""
    size_m = re.search(r"SIZE=(\d+)", output)
    return {"ok": True, "size": int(size_m.group(1)) if size_m else 0}


@router.get("/nodes/{nid}/capture/{cap_id}/download")
async def api_capture_download(nid: str, cap_id: str):
    nodes = await load_nodes()
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
    node = await _get_node_with_creds(nid, nodes)
    results, err = await session_manager.run(nid, node, [f"sh -lc {shlex.quote(dl_script)}"])
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


@router.get("/nodes/{nid}/capture/{cap_id}/analyze")
async def api_capture_analyze(nid: str, cap_id: str):
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
        
    local_dir = _capture_local_dir(nid)
    fname = f"{_safe_name(cap_id)}.pcap"
    pcap_path = local_dir / fname
    
    # Auto-download if not present locally
    if not pcap_path.exists():
        meta = _captures.get(f"{nid}:{cap_id}")
        if not meta:
            raise HTTPException(404, "Capture not found and not downloaded locally")
        paths = meta["paths"]
        dl_script = (
            f"if [ ! -f {shlex.quote(paths['pcap'])} ]; then echo __MISSING__; "
            f"else base64 {shlex.quote(paths['pcap'])} 2>/dev/null || busybox base64 {shlex.quote(paths['pcap'])}; fi"
        )
        node = await _get_node_with_creds(nid, nodes)
        results, err = await session_manager.run(nid, node, [f"sh -lc {shlex.quote(dl_script)}"])
        if err:
            raise HTTPException(500, err)
        output = (results[0].get("output") or "").strip() if results else ""
        if "__MISSING__" in output:
            raise HTTPException(404, "Remote capture file not found")
        try:
            raw = base64.b64decode("".join(output.splitlines()))
            pcap_path.write_bytes(raw)
        except Exception as e:
            raise HTTPException(500, f"Failed to decode capture: {e}")

    try:
        from scapy.all import rdpcap, IP, TCP, UDP, ICMP, DNS
        import asyncio
        # rdpcap is synchronous and blocking, wrap in to_thread
        packets = await asyncio.to_thread(rdpcap, str(pcap_path))
    except Exception as e:
        raise HTTPException(500, f"Failed to parse pcap via scapy: {e}")

    src_ips = Counter()
    dst_ips = Counter()
    protocols = Counter()
    
    for pkt in packets:
        if IP in pkt:
            src_ips[pkt[IP].src] += 1
            dst_ips[pkt[IP].dst] += 1
            if TCP in pkt:
                protocols["TCP"] += 1
            elif UDP in pkt:
                if DNS in pkt:
                    protocols["DNS"] += 1
                else:
                    protocols["UDP"] += 1
            elif ICMP in pkt:
                protocols["ICMP"] += 1
            else:
                protocols["Other IP"] += 1
        else:
            protocols["Non-IP"] += 1

    return {
        "total_packets": len(packets),
        "top_sources": [{"ip": k, "count": v} for k, v in src_ips.most_common(5)],
        "top_destinations": [{"ip": k, "count": v} for k, v in dst_ips.most_common(5)],
        "protocols": [{"name": k, "count": v} for k, v in protocols.items()]
    }


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
async def api_node_backup(nid: str, body: dict = {}):
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    backup_id = _safe_name((body or {}).get("id") or f"bkp_{int(time.time())}", "backup")
    paths = _backup_paths(nid, backup_id)

    from ..generators.network import gen_backup_commands
    cmds  = gen_backup_commands(paths)
    node  = await _get_node_with_creds(nid, nodes)
    results, err = await session_manager.run(nid, node, cmds)
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
async def api_node_rollback(nid: str):
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Not found")
    meta = _backups.get(nid)
    if not meta:
        raise HTTPException(404, "No backup available for this node")
    paths = meta["paths"]

    from ..generators.network import gen_restore_commands
    restore_cmds = gen_restore_commands(paths)
    node = await _get_node_with_creds(nid, nodes)
    results, err = await session_manager.run(nid, node, restore_cmds)
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
async def api_node_export(nid: str, body: dict = {}):
    nodes = await load_nodes()
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
        node_full = await _get_node_with_creds(nid, nodes)
        for ctype in diag_types:
            if ctype not in READ_CMDS:
                diag_errors[ctype] = f"unknown type '{ctype}'"
                continue
            results, err = await session_manager.run(nid, node_full, READ_CMDS[ctype])
            if err:
                diag_errors[ctype] = err
                continue
            diagnostics[ctype] = "\n\n".join(
                (r.get("output") or r.get("error") or "") for r in (results or [])
            ).strip()

    summary = {
        "exported": datetime.now().isoformat(),
        "node": await _node_public(nid, node_meta),
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


@router.post("/nodes/{nid}/install")
async def api_node_install_tool(nid: str, body: dict):
    tool = body.get("tool")
    if not tool:
        raise HTTPException(400, "Missing tool name")
        
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")
        
    node = await _get_node_with_creds(nid, nodes)
    
    # Map common tools to package names if different
    package_map = {
        "nmap": "nmap",
        "nmap-scan": "nmap",
        "tcpdump": "tcpdump",
        "wireguard": "wireguard",
        "iperf3": "iperf3",
        "htop": "htop",
        "dhcp-server": "dnsmasq",
        "dns-service": "dnsmasq",
        "vlan-switch": "bridge-utils",
        "lldp": "lldpd",
        "mtr": "mtr",
        "speedtest": "speedtest-cli",
        "dns-lookup": "bind9-host", # or 'dnsutils' / 'bind-tools'
        "wol": "wakeonlan",
        "arp-scan": "arp-scan"
    }
    
    pkg = package_map.get(tool.lower(), tool.lower())
    
    # Detect package manager
    async def _run(c):
        res, err = await session_manager.run(nid, node, [c])
        if err: return ""
        return res[0].get("output", "") if res else ""

    mgr = await detect_package_manager(_run)
    
    commands = []
    if mgr == "apt":
        commands = [f"apt-get update", f"apt-get install -y {pkg}"]
    elif mgr == "apk":
        commands = [f"apk add {pkg}"]
    elif mgr == "yum" or mgr == "dnf":
        commands = [f"{mgr} install -y {pkg}"]
    elif mgr == "pacman":
        commands = [f"pacman -Sy --noconfirm {pkg}"]
    else:
        raise HTTPException(400, f"Unsupported package manager on this node (detected: {mgr})")

    results, err = await session_manager.run(nid, node, commands)
    if err:
        raise HTTPException(500, err)
        
    return {"status": "success", "results": results}


@router.get("/exports/{fname}")
def api_export_download(fname: str):
    fname = Path(fname).name
    p = EXPORTS_DIR / fname
    if not p.exists():
        raise HTTPException(404, "Not found")
    return FileResponse(p, filename=fname, media_type="application/zip")
