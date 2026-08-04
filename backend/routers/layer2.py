from fastapi import APIRouter
from pydantic import BaseModel
import asyncio
import random

router = APIRouter(prefix="/layer2", tags=["layer2"])


class ArpSpoofRequest(BaseModel):
    target_ip: str
    gateway_ip: str
    interface: str = "eth0"


class StpTakeoverRequest(BaseModel):
    interface: str = "eth0"
    bridge_priority: int = 0


class VlanHopRequest(BaseModel):
    interface: str = "eth0"
    target_vlan: int


class MacFloodRequest(BaseModel):
    interface: str = "eth0"
    packets: int = 10000


@router.post("/arp-spoof")
async def arp_spoof(req: ArpSpoofRequest):
    # Simulate ARP Spoofing execution
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"ARP poisoning started between {req.target_ip} and {req.gateway_ip} on {req.interface}",
    }


@router.post("/stp-takeover")
async def stp_takeover(req: StpTakeoverRequest):
    # Simulate STP BPDU generation
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"Broadcasting forged BPDUs with priority {req.bridge_priority} on {req.interface}",
    }


@router.post("/vlan-hop")
async def vlan_hop(req: VlanHopRequest):
    # Simulate Double Tagging or DTP spoofing
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"VLAN hopping sequence initiated targeting VLAN {req.target_vlan} on {req.interface}",
    }


@router.post("/mac-flood")
async def mac_flood(req: MacFloodRequest):
    # Simulate MAC flooding to fill CAM table
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"Sending {req.packets} random MAC frames on {req.interface} to overflow CAM table",
    }


@router.get("/cdp-sniff")
async def cdp_sniff():
    # Simulate reading CDP/LLDP packets
    await asyncio.sleep(1.5)
    devices = [
        {
            "type": "Cisco Catalyst 2960",
            "ip": "10.0.0.5",
            "port": "GigabitEthernet1/0/1",
            "vlan": "10",
        },
        {
            "type": "Cisco IP Phone 7940",
            "ip": "10.0.0.12",
            "port": "FastEthernet0/2",
            "vlan": "20",
        },
        {"type": "Juniper EX2300", "ip": "10.0.0.2", "port": "ge-0/0/0", "vlan": "1"},
    ]
    return {
        "status": "success",
        "devices": random.sample(devices, k=random.randint(1, 3)),
    }


class DhcpStarvationRequest(BaseModel):
    interface: str = "eth0"
    pool_size: int = 254


class RogueDhcpRequest(BaseModel):
    interface: str = "eth0"
    fake_gateway: str
    fake_dns: str
    offer_ip_range: str


class MacSpoofRequest(BaseModel):
    interface: str = "eth0"
    target_mac: str


class VtpBombRequest(BaseModel):
    interface: str = "eth0"
    vtp_domain: str
    vtp_password: str = ""
    revision_number: int = 2147483647


class NdpSpoofRequest(BaseModel):
    interface: str = "eth0"
    target_ipv6: str
    gateway_ipv6: str


@router.post("/dhcp-starve")
async def dhcp_starve(req: DhcpStarvationRequest):
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"DHCP Starvation initiated on {req.interface}. Flooding {req.pool_size} discover packets.",
    }


@router.post("/rogue-dhcp")
async def rogue_dhcp(req: RogueDhcpRequest):
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"Rogue DHCP active on {req.interface}. Injecting Gateway: {req.fake_gateway}, DNS: {req.fake_dns}",
    }


@router.post("/mac-spoof")
async def mac_spoof(req: MacSpoofRequest):
    await asyncio.sleep(0.5)
    return {
        "status": "success",
        "message": f"Interface {req.interface} MAC address spoofed to {req.target_mac}",
    }


@router.post("/vtp-bomb")
async def vtp_bomb(req: VtpBombRequest):
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"VTP Bomb injected on {req.interface} (Domain: {req.vtp_domain}, Rev: {req.revision_number})",
    }


@router.post("/ndp-spoof")
async def ndp_spoof(req: NdpSpoofRequest):
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"IPv6 NDP Spoofing started between {req.target_ipv6} and {req.gateway_ipv6} on {req.interface}",
    }
