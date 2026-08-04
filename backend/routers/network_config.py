import subprocess
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class RouteRequest(BaseModel):
    dest: str
    gateway: Optional[str] = None
    dev: Optional[str] = None
    metric: Optional[int] = None


class VlanRequest(BaseModel):
    parent: str
    vlan_id: int
    ip_address: Optional[str] = None


@router.get("/interfaces")
def get_interfaces():
    try:
        # Run ip -j link and ip -j addr
        link_res = subprocess.run(
            ["ip", "-j", "link"], capture_output=True, text=True, check=True
        )
        links = json.loads(link_res.stdout)

        addr_res = subprocess.run(
            ["ip", "-j", "addr"], capture_output=True, text=True, check=True
        )
        addrs = json.loads(addr_res.stdout)

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {e}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"JSON parse error: {e}")

    # Build a lookup for addresses
    addr_lookup = {}
    for addr_info in addrs:
        ifname = addr_info.get("ifname")
        ipv4 = []
        ipv6 = []
        for info in addr_info.get("addr_info", []):
            if info.get("family") == "inet":
                ipv4.append(f"{info.get('local')}/{info.get('prefixlen')}")
            elif info.get("family") == "inet6":
                ipv6.append(f"{info.get('local')}/{info.get('prefixlen')}")
        addr_lookup[ifname] = {"ipv4": ipv4, "ipv6": ipv6}

    # Combine the information
    interfaces = []
    for link in links:
        ifname = link.get("ifname")
        mac = link.get("address")
        mtu = link.get("mtu")
        state = link.get("operstate")

        ipv4 = addr_lookup.get(ifname, {}).get("ipv4", [])
        ipv6 = addr_lookup.get(ifname, {}).get("ipv6", [])

        interfaces.append(
            {
                "name": ifname,
                "mac": mac,
                "mtu": mtu,
                "state": state,
                "ipv4": ipv4,
                "ipv6": ipv6,
            }
        )

    return interfaces


@router.get("/routes")
def get_routes():
    try:
        res = subprocess.run(
            ["ip", "-j", "route"], capture_output=True, text=True, check=True
        )
        routes = json.loads(res.stdout)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {e.stderr or e}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"JSON parse error: {e}")

    parsed_routes = []
    for r in routes:
        parsed_routes.append(
            {
                "dest": r.get("dst"),
                "gateway": r.get("gateway"),
                "dev": r.get("dev"),
                "metric": r.get("metric"),
                "scope": r.get("scope"),
            }
        )
    return parsed_routes


@router.post("/routes")
def add_route(req: RouteRequest):
    cmd = ["ip", "route", "add", req.dest]
    if req.gateway:
        cmd.extend(["via", req.gateway])
    if req.dev:
        cmd.extend(["dev", req.dev])
    if req.metric is not None:
        cmd.extend(["metric", str(req.metric)])

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        raise HTTPException(status_code=400, detail=f"Failed to add route: {err}")
    return {"status": "success", "message": "Route added"}


@router.delete("/routes")
def delete_route(req: RouteRequest):
    cmd = ["ip", "route", "del", req.dest]
    if req.gateway:
        cmd.extend(["via", req.gateway])
    if req.dev:
        cmd.extend(["dev", req.dev])
    if req.metric is not None:
        cmd.extend(["metric", str(req.metric)])

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        raise HTTPException(status_code=400, detail=f"Failed to delete route: {err}")
    return {"status": "success", "message": "Route deleted"}


@router.post("/vlans")
def add_vlan(req: VlanRequest):
    iface_name = f"{req.parent}.{req.vlan_id}"
    try:
        # ip link add link eth0 name eth0.10 type vlan id 10
        subprocess.run(
            [
                "ip",
                "link",
                "add",
                "link",
                req.parent,
                "name",
                iface_name,
                "type",
                "vlan",
                "id",
                str(req.vlan_id),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        # ip link set dev eth0.10 up
        subprocess.run(
            ["ip", "link", "set", "dev", iface_name, "up"],
            capture_output=True,
            text=True,
            check=True,
        )
        if req.ip_address:
            # ip addr add 192.168.10.1/24 dev eth0.10
            subprocess.run(
                ["ip", "addr", "add", req.ip_address, "dev", iface_name],
                capture_output=True,
                text=True,
                check=True,
            )
    except subprocess.CalledProcessError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        raise HTTPException(status_code=400, detail=f"Failed to create VLAN: {err}")
    return {"status": "success", "message": "VLAN created"}


@router.delete("/vlans/{iface_name}")
def delete_vlan(iface_name: str):
    try:
        subprocess.run(
            ["ip", "link", "del", "dev", iface_name],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        raise HTTPException(status_code=400, detail=f"Failed to delete VLAN: {err}")
    return {"status": "success", "message": "VLAN deleted"}
