from fastapi import APIRouter
from pydantic import BaseModel
import asyncio

router = APIRouter(prefix="/layer4", tags=["layer4"])


class SynFloodRequest(BaseModel):
    target_ip: str
    target_port: int


class UdpFloodRequest(BaseModel):
    target_ip: str
    target_port: int


class TcpRstRequest(BaseModel):
    target_ip: str
    target_port: int
    source_ip: str
    source_port: int


class AckFloodRequest(BaseModel):
    target_ip: str
    target_port: int


@router.post("/syn-flood")
async def syn_flood(req: SynFloodRequest):
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"TCP SYN Flood initiated against {req.target_ip}:{req.target_port}. Half-open connections are stacking up.",
    }


@router.post("/udp-flood")
async def udp_flood(req: UdpFloodRequest):
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"UDP Flood initiated against {req.target_ip}:{req.target_port}. Target is overwhelmed with ICMP unreachable responses.",
    }


@router.post("/tcp-rst")
async def tcp_rst(req: TcpRstRequest):
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"Forged TCP RST packet injected into session {req.source_ip}:{req.source_port} -> {req.target_ip}:{req.target_port}. Connection forcibly closed.",
    }


@router.post("/ack-flood")
async def ack_flood(req: AckFloodRequest):
    await asyncio.sleep(1)
    return {
        "status": "success",
        "message": f"TCP ACK Flood initiated against {req.target_ip}:{req.target_port}. Stateful firewall states are exhausting.",
    }
