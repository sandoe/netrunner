"""Kismet Wireless IDS — FastAPI router.

Provides REST endpoints for managing a local Kismet instance and
querying its wireless detection data.
"""
from __future__ import annotations

import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .auth import get_current_user, authenticate_ws
from ..core.kismet import kismet_manager, kismet_event_queue

router = APIRouter(tags=["kismet"])

# ---------------------------------------------------------------------------
# Background broadcast task
# ---------------------------------------------------------------------------

_kismet_broadcast_task = None


async def broadcast_kismet():
    """Background task: poll Kismet data and push to WebSocket clients."""
    while True:
        try:
            if kismet_manager.process and kismet_manager.process.poll() is None:
                networks = kismet_manager.get_networks()
                alerts = kismet_manager.get_alerts()
                channels = kismet_manager.get_channels()

                payload = {
                    "type": "kismet_update",
                    "networks": networks,
                    "alerts": alerts,
                    "channels": channels,
                    "timestamp": asyncio.get_event_loop().time(),
                }

                if not kismet_event_queue.empty():
                    # Drain old events
                    while not kismet_event_queue.empty():
                        try:
                            kismet_event_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break

                await kismet_event_queue.put(payload)
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Kismet broadcast error: {e}")
            await asyncio.sleep(5)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

_ws_clients: set[WebSocket] = set()


@router.websocket("/ws/kismet")
async def websocket_kismet(websocket: WebSocket):
    """Real-time Kismet data stream via WebSocket."""
    if await authenticate_ws(websocket) is None:
        return
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        while True:
            # Keep connection alive; ignore client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        _ws_clients.discard(websocket)
    except Exception:
        _ws_clients.discard(websocket)


async def _broadcast_loop():
    """Push Kismet updates to all connected WebSocket clients."""
    while True:
        try:
            payload = await kismet_event_queue.get()
            dead: set[WebSocket] = set()
            for client in _ws_clients:
                try:
                    await client.send_json(payload)
                except Exception:
                    dead.add(client)
            _ws_clients.difference_update(dead)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Kismet broadcast loop error: {e}")
            await asyncio.sleep(1)


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------


class StartPayload(BaseModel):
    interface: str = "wlan0"
    http_port: int = 2501
    log_dir: str | None = None


class ChannelPayload(BaseModel):
    source_uuid: str
    channel: int | None = None  # None = re-enable hopping


@router.get("/api/kismet/status")
async def kismet_status(user: dict = Depends(get_current_user)):
    """Get current Kismet status."""
    return kismet_manager.status()


@router.post("/api/kismet/start")
async def kismet_start(payload: StartPayload, user: dict = Depends(get_current_user)):
    """Start the Kismet subprocess."""
    try:
        result = kismet_manager.start(
            interface=payload.interface,
            http_port=payload.http_port,
            log_dir=payload.log_dir,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except TimeoutError as e:
        raise HTTPException(504, str(e))


@router.post("/api/kismet/stop")
async def kismet_stop(user: dict = Depends(get_current_user)):
    """Stop the Kismet subprocess."""
    return kismet_manager.stop()


@router.get("/api/kismet/networks")
async def kismet_networks(user: dict = Depends(get_current_user)):
    """List all detected 802.11 access points."""
    return {"networks": kismet_manager.get_networks()}


@router.get("/api/kismet/clients")
async def kismet_clients(user: dict = Depends(get_current_user)):
    """List all detected Wi-Fi client devices."""
    return {"clients": kismet_manager.get_clients()}


@router.get("/api/kismet/alerts")
async def kismet_alerts(
    since: float = 0,
    user: dict = Depends(get_current_user),
):
    """List Kismet alerts (threats)."""
    return {"alerts": kismet_manager.get_alerts(since_ts=since)}


@router.get("/api/kismet/channels")
async def kismet_channels(user: dict = Depends(get_current_user)):
    """Get channel usage information."""
    return {"channels": kismet_manager.get_channels()}


@router.get("/api/kismet/datasources")
async def kismet_datasources(user: dict = Depends(get_current_user)):
    """List Kismet datasources (capture interfaces)."""
    return {"datasources": kismet_manager.get_datasources()}


@router.get("/api/kismet/interfaces")
async def kismet_interfaces(user: dict = Depends(get_current_user)):
    """Probe for available wireless interfaces on the system."""
    return {"interfaces": kismet_manager.list_interfaces()}


@router.post("/api/kismet/channel")
async def kismet_set_channel(
    payload: ChannelPayload,
    user: dict = Depends(get_current_user),
):
    """Set channel or re-enable channel hopping on a datasource."""
    if payload.channel is not None:
        return kismet_manager.set_channel(payload.source_uuid, payload.channel)
    return kismet_manager.set_hop(payload.source_uuid)


# ---------------------------------------------------------------------------
# WIPS — Rogue AP Detection
# ---------------------------------------------------------------------------

@router.get("/api/kismet/rogue-aps")
async def kismet_rogue_aps(user: dict = Depends(get_current_user)):
    """Detect potential rogue access points using WIPS heuristics.

    Flags APs that:
    - Share an SSID with known networks but have different BSSID/encryption
    - Use unusual channels or signal strengths for their SSID
    - Have no encryption on a SSID that normally requires it
    - Appear multiple times with different configurations (evil twin signs)
    """
    networks = kismet_manager.get_networks()
    if not networks:
        return {"rogues": [], "summary": {"total": 0, "suspicious": 0}}

    # Group networks by SSID
    ssid_groups: dict[str, list[dict]] = {}
    for net in networks:
        ssid = net.get("ssid", "")
        if not ssid:
            continue
        ssid_groups.setdefault(ssid, []).append(net)

    rogues = []

    for ssid, nets in ssid_groups.items():
        if len(nets) < 2:
            continue

        # Collect unique encryption types per SSID
        encryptions = set()
        bssids = set()
        channels = set()
        signals = []

        for net in nets:
            enc = net.get("encryption", "unknown")
            encryptions.add(enc.lower() if enc else "unknown")
            bssid = net.get("mac", "")
            if bssid:
                bssids.add(bssid)
            ch = net.get("channel")
            if ch:
                channels.add(int(ch) if isinstance(ch, (int, float, str)) and str(ch).isdigit() else ch)
            sig = net.get("signal")
            if sig and isinstance(sig, (int, float)):
                signals.append(sig)

        # ── Detection heuristics ──────────────────────────────────
        reasons = []

        # 1. Multiple BSSIDs with same SSID = possible evil twin
        if len(bssids) > 2:
            reasons.append(f"{len(bssids)} different BSSIDs broadcasting same SSID")

        # 2. Mixed encryption types = suspicious (e.g., one open + one WPA2)
        if len(encryptions) > 1:
            reasons.append(f"Mixed encryption: {', '.join(encryptions)}")

        # 3. Unencrypted AP for a SSID that also has encrypted APs
        has_open = any("none" in e or "open" in e for e in encryptions)
        has_secured = any("wpa" in e or "owe" in e or "sae" in e or "wep" in e for e in encryptions)
        if has_open and has_secured:
            reasons.append("Open (unencrypted) AP detected alongside encrypted APs — possible evil twin")

        # 4. Unusual signal strength (very strong = possible close rogue)
        if signals:
            avg_sig = sum(signals) / len(signals)
            max_sig = max(signals)
            if max_sig > -20 and len(signals) > 1:
                reasons.append(f"Abnormally strong signal ({max_sig} dBm) vs avg ({avg_sig:.0f} dBm)")

        # 5. Channel spread (APs on many different channels is unusual)
        if len(channels) > 4:
            reasons.append(f"APs spread across {len(channels)} different channels")

        if reasons:
            # Determine severity
            severity = "warning"
            if has_open and has_secured:
                severity = "critical"
            elif len(bssids) > 3:
                severity = "critical"

            rogues.append({
                "ssid": ssid,
                "severity": severity,
                "reasons": reasons,
                "bssids": list(bssids),
                "channels": list(channels),
                "encryption_types": list(encryptions),
                "ap_count": len(nets),
            })

    # Sort by severity (critical first)
    rogues.sort(key=lambda r: 0 if r["severity"] == "critical" else 1)

    return {
        "rogues": rogues,
        "summary": {
            "total": len(networks),
            "ssids_monitored": len(ssid_groups),
            "suspicious": len(rogues),
            "critical": sum(1 for r in rogues if r["severity"] == "critical"),
        },
    }
