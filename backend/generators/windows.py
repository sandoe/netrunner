"""Windows PowerShell configuration generators — generate PowerShell commands for Windows node configurations."""
from __future__ import annotations
import re

def _split_csvish(val) -> list[str]:
    if not val:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str):
        parts = re.split(r"[,\s;]+", val)
        return [p.strip() for p in parts if p.strip()]
    return [str(val).strip()]

def gen_win_ip(cfg: dict) -> list[str]:
    """Configure Windows network interface IP addresses, gateway and DNS server settings."""
    iface = (cfg.get("interface") or "Ethernet").strip() or "Ethernet"
    dhcp = bool(cfg.get("dhcp", False))
    address = cfg.get("address", "").strip()
    gateway = cfg.get("gateway", "").strip()
    dns = cfg.get("dns", "").strip()

    cmds = [f"# ── Windows IP Setup: {iface} ──────────────────────────"]

    if dhcp:
        cmds += [
            f'Set-NetIPInterface -InterfaceAlias "{iface}" -Dhcp Enabled -ErrorAction SilentlyContinue',
            f'Set-DnsClientServerAddress -InterfaceAlias "{iface}" -ResetServerAddresses -ErrorAction SilentlyContinue'
        ]
        return cmds

    # Parse address and prefix
    # Standard formats: "192.168.1.100/24", "192.168.1.100/255.255.255.0", "192.168.1.100"
    ip = address
    prefix = 24
    if "/" in address:
        parts = address.split("/", 1)
        ip = parts[0].strip()
        mask = parts[1].strip()
        if mask.isdigit():
            prefix = int(mask)
        else:
            # Subnet mask to prefix length conversion (e.g. 255.255.255.0 -> 24)
            try:
                octets = [int(o) for o in mask.split(".")]
                binary_str = "".join(bin(o)[2:].zfill(8) for o in octets)
                prefix = binary_str.count("1")
            except Exception:
                prefix = 24

    if ip:
        # Clear existing non-link-local addresses to prevent conflicts
        cmds += [
            f'Remove-NetIPAddress -InterfaceAlias "{iface}" -Confirm:$false -ErrorAction SilentlyContinue',
            f'Remove-NetRoute -InterfaceAlias "{iface}" -Confirm:$false -ErrorAction SilentlyContinue',
            f'New-NetIPAddress -InterfaceAlias "{iface}" -IPAddress "{ip}" -PrefixLength {prefix}' + (f' -DefaultGateway "{gateway}"' if gateway else '') + ' -ErrorAction SilentlyContinue'
        ]

    # DNS configuration
    if dns:
        dns_servers = _split_csvish(dns)
        dns_list = ", ".join(f'"{d}"' for d in dns_servers)
        cmds.append(f'Set-DnsClientServerAddress -InterfaceAlias "{iface}" -ServerAddresses @({dns_list}) -ErrorAction SilentlyContinue')

    return cmds

def gen_win_route(cfg: dict) -> list[str]:
    """Manage persistent static routing entries on Windows."""
    destination = cfg.get("destination", "").strip()
    gateway = cfg.get("gateway", "").strip()
    iface = cfg.get("interface", "").strip()
    metric = cfg.get("metric")
    action = cfg.get("action", "add").strip().lower()

    if not destination:
        raise ValueError("destination is required for routing")

    cmds = [f"# ── Windows Route: {action.upper()} {destination} ──────────────────────────"]

    if action == "remove" or action == "del":
        cmds.append(f'Remove-NetRoute -DestinationPrefix "{destination}" -Confirm:$false -ErrorAction SilentlyContinue')
    else:
        # Action is add
        if not gateway:
            raise ValueError("gateway (NextHop) is required to add route")
        cmd = f'New-NetRoute -DestinationPrefix "{destination}" -NextHop "{gateway}"'
        if iface:
            cmd += f' -InterfaceAlias "{iface}"'
        if metric:
            cmd += f' -RouteMetric {metric}'
        cmd += ' -ErrorAction SilentlyContinue'
        cmds.append(cmd)

    return cmds

def gen_win_service(cfg: dict) -> list[str]:
    """Start, stop, restart or configure Windows system services."""
    name = cfg.get("name", "").strip()
    action = cfg.get("action", "status").strip().lower()

    if not name:
        raise ValueError("service name is required")

    cmds = [f"# ── Windows Service: {name} ({action.upper()}) ──────────────────────────"]

    if action == "start":
        cmds.append(f'Start-Service -Name "{name}" -ErrorAction SilentlyContinue')
    elif action == "stop":
        cmds.append(f'Stop-Service -Name "{name}" -Confirm:$false -ErrorAction SilentlyContinue')
    elif action == "restart":
        cmds.append(f'Restart-Service -Name "{name}" -ErrorAction SilentlyContinue')
    elif action == "enable":
        cmds.append(f'Set-Service -Name "{name}" -StartupType Automatic -ErrorAction SilentlyContinue')
    elif action == "disable":
        cmds.append(f'Set-Service -Name "{name}" -StartupType Disabled -ErrorAction SilentlyContinue')
    else: # status
        cmds.append(f'Get-Service -Name "{name}"')

    return cmds

def gen_win_feature(cfg: dict) -> list[str]:
    """Install or enable Windows Features or packages via winget."""
    name = cfg.get("name", "").strip()
    action = cfg.get("action", "install").strip().lower()
    manager = cfg.get("manager", "feature").strip().lower() # 'feature' or 'winget'

    if not name:
        raise ValueError("feature or package name is required")

    cmds = [f"# ── Windows Package/Feature: {action.upper()} {name} via {manager.upper()} ──────────────────────────"]

    if manager == "winget":
        if action == "uninstall" or action == "remove":
            cmds.append(f'winget uninstall --id "{name}" --silent --accept-source-agreements')
        else:
            cmds.append(f'winget install --id "{name}" --silent --accept-package-agreements --accept-source-agreements')
    else: # default to Windows Optional Features (DISM)
        if action == "uninstall" or action == "disable" or action == "remove":
            cmds.append(f'Disable-WindowsOptionalFeature -Online -FeatureName "{name}" -NoRestart -ErrorAction SilentlyContinue')
        else:
            cmds.append(f'Enable-WindowsOptionalFeature -Online -FeatureName "{name}" -All -NoRestart -ErrorAction SilentlyContinue')

    return cmds

def gen_win_hostname(cfg: dict) -> list[str]:
    """Rename computer hostname on Windows."""
    hostname = cfg.get("hostname", "").strip()
    if not hostname:
        raise ValueError("hostname is required")

    return [
        f"# ── Windows Hostname: Rename to {hostname} ──────────────────────────",
        f'Rename-Computer -NewName "{hostname}" -Force -ErrorAction SilentlyContinue',
        '# Note: A system reboot is required for hostname change to take effect.'
    ]

def gen_win_file(cfg: dict) -> list[str]:
    """Write text file on Windows using PowerShell Here-Strings."""
    path = cfg.get("path", "").strip()
    content = cfg.get("content", "")
    overwrite = bool(cfg.get("overwrite", True))

    if not path:
        raise ValueError("file path is required")

    cmds = [f"# ── Windows File Write: {path} ──────────────────────────"]

    # Escape Here-String end markers inside content to prevent syntax errors
    safe_content = content.replace("@'", "@\"").replace("'@", "\"@")

    cmds += [
        '$content = @\'',
        safe_content,
        '\'@',
        '# Ensure parent directory exists',
        f'$dir = Split-Path -Path "{path}"',
        'if ($dir -and -not (Test-Path -Path $dir)) {',
        '    New-Item -ItemType Directory -Force -Path $dir -ErrorAction SilentlyContinue',
        '}'
    ]

    if overwrite:
        cmds.append(f'$content | Out-File -FilePath "{path}" -Encoding utf8 -Force')
    else:
        cmds.append(f'if (-not (Test-Path -Path "{path}")) {{ $content | Out-File -FilePath "{path}" -Encoding utf8 }}')

    return cmds
