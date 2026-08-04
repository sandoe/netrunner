from fastapi import APIRouter
from pydantic import BaseModel
import asyncio

router = APIRouter(prefix="/layer3", tags=["layer3"])


class IcmpRedirectRequest(BaseModel):
    target_ip: str
    gateway_ip: str
    new_gateway_ip: str


class PingOfDeathRequest(BaseModel):
    target_ip: str


class IcmpTunnelRequest(BaseModel):
    server_ip: str


class IpFragmentationRequest(BaseModel):
    target_ip: str


class OspfRouteInjectRequest(BaseModel):
    interface: str
    fake_network: str


@router.post("/icmp-redirect")
async def icmp_redirect(req: IcmpRedirectRequest):
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"ICMP Redirect sent to {req.target_ip}. Traffic for {req.gateway_ip} redirected to {req.new_gateway_ip}.",
    }


@router.post("/ping-of-death")
async def ping_of_death(req: PingOfDeathRequest):
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"Ping of Death attack simulated against {req.target_ip}.",
    }


@router.post("/icmp-tunnel")
async def icmp_tunnel(req: IcmpTunnelRequest):
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"ICMP Tunnel established to server {req.server_ip}.",
    }


@router.post("/ip-fragmentation")
async def ip_fragmentation(req: IpFragmentationRequest):
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"IP Fragmentation attack simulated against {req.target_ip}.",
    }


@router.post("/ospf-route-inject")
async def ospf_route_inject(req: OspfRouteInjectRequest):
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"OSPF Route injected on {req.interface}. Fake network {req.fake_network} broadcasted.",
    }
