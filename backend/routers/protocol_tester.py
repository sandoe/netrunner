from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from backend.services.dpi_engine import MockDPIEngine
import socket

router = APIRouter(prefix="/protocol-tester", tags=["Protocol Tester"])


class TrafficRequest(BaseModel):
    protocol: str
    target_ip: str
    target_port: int
    payload_hex: str


@router.post("/send")
async def send_traffic(req: TrafficRequest) -> Dict[str, Any]:
    try:
        payload = bytes.fromhex(req.payload_hex)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex payload")

    # Send traffic using raw socket / UDP or TCP
    try:
        if req.protocol in ("mqtt", "amqp", "modbus_tcp", "quic", "tcp"):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((req.target_ip, req.target_port))
            sock.sendall(payload)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)
            sock.sendto(payload, (req.target_ip, req.target_port))
        sock.close()
    except Exception as e:
        return {"status": "error", "message": f"Failed to send traffic: {str(e)}"}

    # Mock DPI Analysis
    detected_protocol = MockDPIEngine.analyze(payload)

    return {
        "status": "success",
        "message": "Traffic sent successfully",
        "dpi_analysis": detected_protocol,
        "sent_bytes": len(payload),
    }
