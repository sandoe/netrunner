"""Auto-detect device type by probing a node.

Returns one of: "gns3", "linux", "rpi", "unknown"
"""

from __future__ import annotations

import socket

from .session import SshClient, TelnetClient


async def detect_device_type(
    host: str, port: int, username: str = "root", password: str = ""
) -> str:
    """Probe the device and return its type.

    Strategy:
    1. Try SSH on the given port
       - Run `uname -a` + `cat /proc/cpuinfo | grep -i raspberry`
       - If RPi marker found → "rpi"
       - If Linux → "linux"
    2. Try telnet on the given port
       - If connects → "gns3"
    3. → "unknown"
    """
    # Try SSH
    try:
        from .session import session_manager

        node = {"host": host, "port": port, "username": username, "password": password}
        nid = f"detect_{host}_{port}"
        try:
            results, err = await session_manager.run(
                nid,
                node,
                [
                    "uname -a",
                    "cat /proc/cpuinfo 2>/dev/null | grep -i 'raspberry\\|bcm2'",
                ],
                timeout=5,
            )
            if not err and len(results) >= 2:
                uname = results[0]
                rpi_check = results[1]
                if rpi_check.strip():
                    return "rpi"
                if "linux" in uname.lower():
                    return "linux"
                return "unknown"
        finally:
            session_manager.close(nid)
    except Exception:
        pass

    # Try telnet
    try:
        sock = socket.create_connection((host, port), timeout=3)
        sock.close()
        return "gns3"
    except Exception:
        pass

    return "unknown"


async def detect_package_manager(run_fn) -> str:
    """Detect package manager by running probe commands via a callable."""
    for cmd, mgr in [
        ("command -v apt-get", "apt"),
        ("command -v yum", "yum"),
        ("command -v dnf", "dnf"),
        ("command -v pacman", "pacman"),
        ("command -v apk", "apk"),
        ("command -v zypper", "zypper"),
    ]:
        try:
            out = await run_fn(cmd)
            if out and out.strip() and "not found" not in out:
                return mgr
        except Exception:
            pass
    return "apt"
