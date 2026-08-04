from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import subprocess
import os
import re

from .auth import require_admin

router = APIRouter(prefix="/api/vpn", tags=["vpn"])

WG_CONF_PATH = "/etc/wireguard/wg0.conf"


class VpnClientCreate(BaseModel):
    name: str


def get_wg_status():
    try:
        res = subprocess.run(
            ["wg", "show", "wg0"], capture_output=True, text=True, check=True
        )
        return res.stdout
    except subprocess.CalledProcessError:
        return ""


def generate_keypair():
    try:
        priv = subprocess.run(
            ["wg", "genkey"], capture_output=True, text=True, check=True
        ).stdout.strip()
        pub = subprocess.run(
            ["wg", "pubkey"], input=priv, capture_output=True, text=True, check=True
        ).stdout.strip()
        return priv, pub
    except Exception as e:
        raise HTTPException(500, f"WireGuard not installed or working: {e}")


def get_next_ip(subnet="10.8.0"):
    if not os.path.exists(WG_CONF_PATH):
        return f"{subnet}.2"

    with open(WG_CONF_PATH, "r") as f:
        content = f.read()

    ips = re.findall(rf"{subnet}\.(\d+)/32", content)
    if not ips:
        return f"{subnet}.2"

    highest = max([int(x) for x in ips])
    return f"{subnet}.{highest + 1}"


def get_server_pubkey():
    try:
        res = subprocess.run(
            ["wg", "show", "wg0", "public-key"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except:
        return "UNKNOWN_SERVER_PUBKEY"


def get_server_endpoint():
    # Best effort to guess public IP if not configured
    try:
        import urllib.request

        ip = (
            urllib.request.urlopen("https://api.ipify.org", timeout=3)
            .read()
            .decode("utf8")
        )
        return f"{ip}:51820"
    except:
        return "YOUR_SERVER_IP:51820"


@router.get("/status", dependencies=[Depends(require_admin)])
async def api_vpn_status():
    status_text = get_wg_status()
    peers = []
    if status_text:
        current_peer = {}
        for line in status_text.splitlines():
            line = line.strip()
            if line.startswith("peer:"):
                if current_peer:
                    peers.append(current_peer)
                current_peer = {
                    "pubkey": line.split()[1],
                    "endpoint": "",
                    "allowed_ips": "",
                    "latest_handshake": "",
                }
            elif line.startswith("endpoint:"):
                current_peer["endpoint"] = line.split(":", 1)[1].strip()
            elif line.startswith("allowed ips:"):
                current_peer["allowed_ips"] = line.split(":", 1)[1].strip()
            elif line.startswith("latest handshake:"):
                current_peer["latest_handshake"] = line.split(":", 1)[1].strip()
        if current_peer:
            peers.append(current_peer)

    # Determine if it's active
    is_active = False
    try:
        subprocess.run(["ip", "link", "show", "wg0"], check=True, capture_output=True)
        is_active = True
    except:
        pass

    return {
        "status": "active" if is_active else "inactive",
        "peers": peers,
        "server_pubkey": get_server_pubkey(),
        "server_endpoint": get_server_endpoint(),
    }


@router.post("/clients", dependencies=[Depends(require_admin)])
async def api_vpn_create_client(body: VpnClientCreate):
    priv, pub = generate_keypair()
    ip = get_next_ip()

    if not os.path.exists(WG_CONF_PATH):
        os.makedirs(os.path.dirname(WG_CONF_PATH), exist_ok=True)
        server_priv, server_pub = generate_keypair()
        with open(WG_CONF_PATH, "w") as f:
            f.write(
                f"[Interface]\nAddress = 10.8.0.1/24\nListenPort = 51820\nPrivateKey = {server_priv}\n\n"
            )
        subprocess.run(["wg-quick", "up", "wg0"], capture_output=True)

    with open(WG_CONF_PATH, "a") as f:
        f.write(
            f"\n# Client: {body.name}\n[Peer]\nPublicKey = {pub}\nAllowedIPs = {ip}/32\n"
        )

    try:
        # Start wg0 if not started
        subprocess.run(["ip", "link", "show", "wg0"], check=True, capture_output=True)
    except:
        subprocess.run(["wg-quick", "up", "wg0"], capture_output=True)

    try:
        subprocess.run(
            ["wg", "set", "wg0", "peer", pub, "allowed-ips", f"{ip}/32"],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            500, f"Failed to apply wg rule: {e.stderr.decode() if e.stderr else str(e)}"
        )

    server_pub = get_server_pubkey()
    endpoint = get_server_endpoint()

    config_str = f"""[Interface]
PrivateKey = {priv}
Address = {ip}/24

[Peer]
PublicKey = {server_pub}
Endpoint = {endpoint}
AllowedIPs = 10.0.0.0/8, 192.168.0.0/16, 10.8.0.0/24
PersistentKeepalive = 25
"""

    return {"config": config_str, "name": body.name, "ip": ip, "pubkey": pub}


@router.delete("/clients/{pubkey:path}", dependencies=[Depends(require_admin)])
async def api_vpn_delete_client(pubkey: str):
    subprocess.run(
        ["wg", "set", "wg0", "peer", pubkey, "remove"], check=False, capture_output=True
    )

    if os.path.exists(WG_CONF_PATH):
        with open(WG_CONF_PATH, "r") as f:
            lines = f.readlines()

        new_lines = []
        skip = False
        for i, line in enumerate(lines):
            if line.strip() == "[Peer]":
                is_target = False
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].strip().startswith("[Peer]") or lines[
                        j
                    ].strip().startswith("[Interface]"):
                        break
                    if pubkey in lines[j]:
                        is_target = True
                        break
                if is_target:
                    skip = True
                    if len(new_lines) > 0 and new_lines[-1].strip().startswith(
                        "# Client:"
                    ):
                        new_lines.pop()
                    continue

            if skip:
                if line.strip() == "" or line.strip().startswith("["):
                    if line.strip() == "":
                        continue
                    else:
                        skip = False
                        new_lines.append(line)
            else:
                new_lines.append(line)

        with open(WG_CONF_PATH, "w") as f:
            f.writelines(new_lines)

    return {"message": "Client removed"}
