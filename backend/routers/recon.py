import uuid
import xml.etree.ElementTree as ET
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from datetime import datetime

from .auth import get_current_user, require_non_student
from ..core.session import session_manager
from .nodes import load_nodes, save_nodes, _get_node_with_creds
from .links import load_links, save_links

router = APIRouter(tags=["recon"])


@router.post("/recon/{nid}/scan")
async def scan_network(nid: str, body: dict, user: dict = Depends(require_non_student)):
    target = body.get("target")
    profile = body.get("profile", "quick")
    sudo_pass = body.get("sudo_pass")

    if not target:
        raise HTTPException(400, "Missing target")

    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    node = await _get_node_with_creds(nid, nodes)
    if sudo_pass:
        node["password"] = sudo_pass
    from ..core.scanner import run_remote_nmap_xml

    try:
        result = await run_remote_nmap_xml(nid, node, target, profile, sudo_pass)
        return result
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.post("/recon/{nid}/import")
async def import_recon_hosts(
    nid: str, body: dict, user: dict = Depends(require_non_student)
):
    hosts = body.get("hosts", [])
    if not hosts:
        raise HTTPException(400, "No hosts provided")

    nodes = await load_nodes()
    links = await load_links()

    imported_count = 0

    for h in hosts:
        ip = h.get("ip")
        if not ip:
            continue

        # Check if already exists
        exists = False
        for node_id, node_data in nodes.items():
            if node_data.get("host") == ip:
                exists = True
                break

        if exists:
            continue

        # Determine device type
        os_str = h.get("os", "").lower()
        device_type = "unknown"
        if "linux" in os_str:
            device_type = "linux"
        elif "windows" in os_str:
            device_type = "windows"
        elif "mac" in os_str or "apple" in os_str:
            device_type = "unknown"

        name = ip
        if h.get("hostnames"):
            name = h.get("hostnames")[0]

        new_node_id = str(uuid.uuid4())
        nodes[new_node_id] = {
            "id": new_node_id,
            "name": name,
            "host": ip,
            "port": 22,
            "username": "root",
            "transport": "ssh",
            "device_type": device_type,
            "has_password": False,
            "created": datetime.utcnow().isoformat(),
            "tags": ["recon"],
            "metadata": {
                "mac": h.get("mac"),
                "os_guess": h.get("os"),
                "ports": h.get("ports"),
            },
        }

        # Add link from the scanning node to the discovered node
        new_link_id = f"{nid}_{new_node_id}"
        links[new_link_id] = {
            "id": new_link_id,
            "source": nid,
            "target": new_node_id,
            "auto_discovered": True,
            "metadata": {"method": "nmap"},
        }
        imported_count += 1

    if imported_count > 0:
        await save_nodes(nodes)
        await save_links(links)

    return {"status": "success", "imported": imported_count}


@router.post("/recon/{nid}/report")
async def generate_recon_report(
    nid: str, body: dict, user: dict = Depends(get_current_user)
):
    """Generate a customizable recon report from the perspective of the node."""
    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    node = nodes[nid]

    modules = body.get("modules", ["network"])
    if not modules:
        modules = ["network"]

    script_parts = ['echo "=== RECON_REPORT_START ==="']

    for mod in modules:
        if mod == "network":
            script_parts.append('echo "--- INTERFACES ---"')
            script_parts.append("ip -br addr show 2>/dev/null || ifconfig 2>/dev/null")
            script_parts.append('echo "--- NEIGHBORS (ARP/NDP) ---"')
            script_parts.append("ip -br neigh show 2>/dev/null || arp -an 2>/dev/null")
            script_parts.append('echo "--- ROUTES ---"')
            script_parts.append("ip route show 2>/dev/null || route -n 2>/dev/null")
            script_parts.append('echo "--- HOPS (Traceroute 8.8.8.8) ---"')
            script_parts.append(
                'tracepath -m 15 8.8.8.8 2>/dev/null || traceroute -m 15 8.8.8.8 2>/dev/null || echo "Traceroute/tracepath not available"'
            )
        elif mod == "docker":
            script_parts.append('echo "--- DOCKER CONTAINERS ---"')
            script_parts.append(
                'docker ps -a 2>/dev/null || sudo -n docker ps -a 2>/dev/null || echo "(Docker not available)"'
            )
            script_parts.append('echo "--- DOCKER NETWORKS ---"')
            script_parts.append(
                "docker network ls 2>/dev/null || sudo -n docker network ls 2>/dev/null || true"
            )
            script_parts.append('echo "--- DOCKER IMAGES ---"')
            script_parts.append(
                "docker images 2>/dev/null || sudo -n docker images 2>/dev/null || true"
            )
        elif mod == "services":
            script_parts.append('echo "--- RUNNING SERVICES ---"')
            script_parts.append(
                'systemctl list-units --type=service --state=running --no-pager 2>/dev/null || service --status-all 2>/dev/null || rc-status 2>/dev/null || echo "(Service manager not found)"'
            )
        elif mod == "system":
            script_parts.append('echo "--- SYSTEM INFO ---"')
            script_parts.append("uname -a 2>/dev/null")
            script_parts.append('echo "--- MEMORY ---"')
            script_parts.append("free -h 2>/dev/null || cat /proc/meminfo | head -10")
            script_parts.append('echo "--- DISK ---"')
            script_parts.append("df -h 2>/dev/null || lsblk 2>/dev/null")
            script_parts.append('echo "--- CPU ---"')
            script_parts.append("lscpu 2>/dev/null || cat /proc/cpuinfo | head -20")
        elif mod == "vulnerabilities":
            script_parts.append('echo "--- VULNERABILITY INDICATORS ---"')
            script_parts.append('echo "--- SUDOERS ---"')
            script_parts.append(
                'cat /etc/sudoers 2>/dev/null || sudo -n cat /etc/sudoers 2>/dev/null || echo "(Access denied)"'
            )
            script_parts.append('echo "--- PASSWD ---"')
            script_parts.append("cat /etc/passwd 2>/dev/null")
            script_parts.append('echo "--- CRON JOBS ---"')
            script_parts.append(
                'crontab -l 2>/dev/null || sudo -n crontab -l 2>/dev/null || echo "(No cron)"'
            )
            script_parts.append("ls -la /etc/cron* 2>/dev/null || true")

    script_parts.append('echo "=== RECON_REPORT_END ==="')
    script = "\n".join(script_parts)

    # We need the node credentials if available
    target_node = await _get_node_with_creds(nid, nodes)

    # Run command (with auto-reconnect)
    res, err = await session_manager.run(nid, target_node, [script], timeout=120.0)

    if err:
        raise HTTPException(500, f"Failed to connect or run report: {err}")
    if not res:
        raise HTTPException(500, "Empty response from node")

    cmd_err = res[0].get("error")
    if cmd_err:
        raise HTTPException(500, f"Command execution failed: {cmd_err}")

    output = res[0].get("output", "")

    return {"status": "success", "report": output}
