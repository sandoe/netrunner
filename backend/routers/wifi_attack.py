"""
Netrunner WiFi Attack Router — API endpoints for WiFi penetration testing.

⚠️  LEGAL NOTICE: These endpoints are for AUTHORIZED penetration testing only.
    Unauthorized access to computer networks is illegal. Always obtain
    written authorization before performing any security testing.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from .auth import require_admin
from ..core.wifi_attack import (
    scan_networks,
    deauth_attack,
    evil_twin_attack,
    capture_handshake,
    crack_handshake,
    probe_clients,
    get_active_attacks,
    get_wireless_interfaces,
)

router = APIRouter()


class DeauthRequest(BaseModel):
    interface: str
    target_bssid: str
    target_client: str = "ff:ff:ff:ff:ff:ff"
    count: int = 10
    interval: float = 0.1


class EvilTwinRequest(BaseModel):
    interface: str
    target_ssid: str
    target_bssid: str
    channel: int = 6
    duration: int = 60


class HandshakeCaptureRequest(BaseModel):
    interface: str
    target_bssid: str
    target_client: str = "ff:ff:ff:ff:ff:ff"
    duration: int = 30


class CrackRequest(BaseModel):
    capture_file: str
    wordlist: str = "/usr/share/wordlists/rockyou.txt"


class ProbeRequest(BaseModel):
    interface: str
    target_bssid: str
    duration: int = 10


@router.get("/wifi-attack/interfaces")
async def api_wifi_attack_interfaces():
    """List available wireless interfaces."""
    interfaces = get_wireless_interfaces()
    return {"interfaces": interfaces}


class ScanRequest(BaseModel):
    interface: str
    duration: int = 10


@router.post("/wifi-attack/scan", dependencies=[Depends(require_admin)])
async def api_wifi_attack_scan(req: ScanRequest):
    """Scan for nearby WiFi networks."""
    networks = await scan_networks(req.interface, req.duration)
    return {"networks": networks, "count": len(networks)}


@router.post("/wifi-attack/deauth", dependencies=[Depends(require_admin)])
async def api_wifi_attack_deauth(req: DeauthRequest):
    """
    Perform deauthentication attack on a target AP/client.

    ⚠️ Requires: Wireless interface in monitor mode
    ⚠️ Legal: Only against networks you own or have authorization to test
    """
    result = await deauth_attack(
        interface=req.interface,
        target_bssid=req.target_bssid,
        target_client=req.target_client,
        count=req.count,
        interval=req.interval,
    )
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Attack failed"))
    return result


@router.post("/wifi-attack/evil-twin", dependencies=[Depends(require_admin)])
async def api_wifi_attack_evil_twin(req: EvilTwinRequest):
    """
    Create an evil twin AP that mimics a target network.

    ⚠️ Requires: Wireless interface in monitor mode + hostapd
    ⚠️ Legal: Only against networks you own or have authorization to test
    """
    result = await evil_twin_attack(
        interface=req.interface,
        target_ssid=req.target_ssid,
        target_bssid=req.target_bssid,
        channel=req.channel,
        duration=req.duration,
    )
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Attack failed"))
    return result


@router.post("/wifi-attack/capture-handshake", dependencies=[Depends(require_admin)])
async def api_wifi_attack_capture_handshake(req: HandshakeCaptureRequest):
    """
    Capture WPA 4-way handshake for offline cracking.

    ⚠️ Requires: Wireless interface in monitor mode
    ⚠️ Legal: Only against networks you own or have authorization to test
    """
    result = await capture_handshake(
        interface=req.interface,
        target_bssid=req.target_bssid,
        target_client=req.target_client,
        duration=req.duration,
    )
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Capture failed"))
    return result


@router.post("/wifi-attack/crack", dependencies=[Depends(require_admin)])
async def api_wifi_attack_crack(req: CrackRequest):
    """
    Attempt to crack a captured WPA handshake using aircrack-ng.

    ⚠️ Requires: aircrack-ng installed
    ⚠️ Legal: Only against captures from networks you own or have authorization to test
    """
    result = await crack_handshake(
        capture_file=req.capture_file,
        wordlist=req.wordlist,
    )
    if not result["success"]:
        raise HTTPException(
            400, result.get("error", result.get("message", "Crack failed"))
        )
    return result


@router.post("/wifi-attack/probe-clients", dependencies=[Depends(require_admin)])
async def api_wifi_attack_probe_clients(req: ProbeRequest):
    """Probe for clients connected to a specific AP."""
    clients = await probe_clients(
        interface=req.interface,
        target_bssid=req.target_bssid,
        duration=req.duration,
    )
    return {"clients": clients, "count": len(clients)}


@router.get("/wifi-attack/active")
async def api_wifi_attack_active():
    """Get list of active/completed attacks."""
    attacks = get_active_attacks()
    return {"attacks": attacks, "count": len(attacks)}
