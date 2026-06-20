"""Network configuration command generators (ported + expanded from gns3-config)."""
from __future__ import annotations

import re
import shlex


def _split_csvish(value) -> list[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = re.split(r"[,\n]+", str(value or ""))
    out = []
    for item in raw:
        item = str(item).strip()
        if item and item not in out:
            out.append(item)
    return out


def _vid(value) -> int | None:
    s = str(value).strip()
    if not s.isdigit():
        return None
    n = int(s)
    return n if 1 <= n <= 4094 else None


def _safe_name(value: str, fallback: str = "config") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(value or fallback)).strip("_")
    return cleaned or fallback


def _get_any(d: dict, keys: list[str], default=None):
    if not isinstance(d, dict):
        return default
    for key in keys:
        value = d.get(key)
        if value is not None and value != "":
            return value
    normalized = {str(k).lower().replace("_", "").replace("-", ""): v for k, v in d.items()}
    for key in keys:
        value = normalized.get(key.lower().replace("_", "").replace("-", ""))
        if value is not None and value != "":
            return value
    return default


def gen_ip(iface: str, addrs: list[str], action: str = "add") -> list[str]:
    cmds = []
    for a in addrs:
        if a.strip() and '/' not in a:
            cmds.append(f"# WARNING: Address '{a}' has no CIDR prefix (e.g. /24). This may fail.")
    if action == "flush":
        cmds.append(f"ip addr flush dev {iface}")
        for a in addrs:
            cmds.append(f"ip addr add {a} dev {iface}")
        cmds.append(f"ip link set {iface} up")
    elif action == "add":
        for a in addrs:
            cmds.append(f"ip addr add {a} dev {iface}")
        cmds.append(f"ip link set {iface} up")
    elif action == "del":
        for a in addrs:
            cmds.append(f"ip addr del {a} dev {iface}")
    return cmds


def gen_interface(cfg: dict) -> list[str]:
    iface = (cfg.get("interface") or "eth0").strip() or "eth0"
    action = cfg.get("action", "add")
    
    if action == "delete_interface":
        return [
            f"# ── Delete Interface: {iface} ──────────────────────────",
            f"ip link set {iface} down 2>/dev/null || true",
            f"ip link del dev {iface} 2>/dev/null || true"
        ]
        
    cmds = [f"# ── Interface Setup: {iface} ──────────────────────────"]
    
    # Auto-create VLAN sub-interface if "." is in the name (e.g. eth0.100)
    if "." in iface:
        parts = iface.split(".", 1)
        if len(parts) == 2 and parts[1].isdigit():
            parent, vid = parts[0], parts[1]
            cmds.append(f"modprobe 8021q 2>/dev/null || true")
            cmds.append(f"ip link set {parent} up")
            cmds.append(f"ip link add link {parent} name {iface} type vlan id {vid} 2>/dev/null || true")
            cmds.append(f"ip link set {iface} up")
    
    # Static IPs
    addrs = _split_csvish(cfg.get("addresses"))
    if addrs:
        cmds.extend(gen_ip(iface, addrs, action))
    
    # DHCP
    if cfg.get("dhcp"):
        cmds.extend(gen_dhcp(iface, "renew"))
    
    # Explicit link state override or default up
    state = cfg.get("state")
    if state == "up":
        cmds.append(f"ip link set {iface} up")
    elif state == "down":
        cmds.append(f"ip link set {iface} down")
    elif not state or state == "none":
        if not addrs and not cfg.get("dhcp"):
            cmds.append(f"ip link set {iface} up")
        
    return cmds


def gen_routes(routes: list[dict], action: str = "add") -> list[str]:
    cmds = []
    for r in routes:
        dst = _get_any(r, ["dst", "destination", "dest", "prefix", "network"])
        if not dst:
            continue
        parts = ["ip route", action, str(dst)]
        via = _get_any(r, ["via", "gateway", "next_hop", "nexthop"])
        dev = _get_any(r, ["dev", "interface", "iface"])
        metric = _get_any(r, ["metric", "route_metric"])
        if via:    parts += ["via",    str(via)]
        if dev:    parts += ["dev",    str(dev)]
        if metric: parts += ["metric", str(metric)]
        cmds.append(" ".join(parts))
    return cmds


def gen_forwarding(ipv4: bool | None = None, ipv6: bool | None = None) -> list[str]:
    cmds = []
    if ipv4 is not None:
        cmds.append(f"sysctl -w net.ipv4.ip_forward={1 if ipv4 else 0}")
    if ipv6 is not None:
        cmds.append(f"sysctl -w net.ipv6.conf.all.forwarding={1 if ipv6 else 0}")
    return cmds


def gen_dhcp(iface: str, action: str = "renew") -> list[str]:
    iface = (iface or "eth0").strip() or "eth0"
    if action == "renew":
        return [
            f"udhcpc -i {iface} 2>/dev/null "
            f"|| dhclient {iface} 2>/dev/null "
            f"|| dhcpcd {iface} 2>/dev/null "
            f"|| echo '(no DHCP client found — install udhcpc, dhclient or dhcpcd)'"
        ]
    if action == "release":
        return [
            f"dhclient -r {iface} 2>/dev/null "
            f"|| udhcpc -R -i {iface} 2>/dev/null "
            f"|| dhcpcd -k {iface} 2>/dev/null "
            f"|| echo '(no DHCP client found)'"
        ]
    return []


def gen_dns(cfg: dict) -> list[str]:
    nameservers = _split_csvish(cfg.get("nameservers"))
    search      = _split_csvish(cfg.get("search"))
    records     = cfg.get("records") or []
    hostname    = str(cfg.get("hostname", "")).strip()
    domain      = str(cfg.get("domain", "")).strip()

    cmds = [
        "# ── DNS / resolver configuration ──────────────────────────",
        "rm -f /tmp/nr_resolv.conf",
        "echo '# Generated by Netrunner' > /tmp/nr_resolv.conf",
    ]
    if search:
        cmds.append(f"echo 'search {' '.join(search)}' >> /tmp/nr_resolv.conf")
    for ns in nameservers:
        cmds.append(f"echo 'nameserver {ns}' >> /tmp/nr_resolv.conf")
    if not nameservers:
        cmds.append("echo '# no nameservers defined yet' >> /tmp/nr_resolv.conf")
    cmds.extend([
        "cp /tmp/nr_resolv.conf /etc/resolv.conf",
        "rm -f /tmp/nr_resolv.conf",
    ])

    if hostname:
        fqdn = f"{hostname}.{domain}" if domain else hostname
        cmds.extend([
            f"echo {shlex.quote(hostname)} > /etc/hostname",
            f"hostname {shlex.quote(hostname)}",
            "sed -i '/# BEGIN NETRUNNER HOSTS/,/# END NETRUNNER HOSTS/d' /etc/hosts 2>/dev/null || true",
            "echo '# BEGIN NETRUNNER HOSTS' >> /etc/hosts",
            f"echo '127.0.1.1 {fqdn} {hostname}' >> /etc/hosts",
        ])
    else:
        cmds.extend([
            "sed -i '/# BEGIN NETRUNNER HOSTS/,/# END NETRUNNER HOSTS/d' /etc/hosts 2>/dev/null || true",
            "echo '# BEGIN NETRUNNER HOSTS' >> /etc/hosts",
        ])

    for record in records:
        name  = str(record.get("name",  "")).strip()
        value = str(record.get("value", "")).strip()
        if name and value:
            cmds.append(f"echo '{value} {name}' >> /etc/hosts")

    cmds.extend([
        "echo '# END NETRUNNER HOSTS' >> /etc/hosts",
        "echo 'DNS configuration updated'",
    ])
    return cmds


def gen_dhcp_server(cfg: dict) -> list[str]:
    iface       = str(cfg.get("interface", "eth1")).strip() or "eth1"
    range_start = str(cfg.get("range_start", "")).strip()
    range_end   = str(cfg.get("range_end", "")).strip()
    mask        = str(cfg.get("mask", "255.255.255.0")).strip() or "255.255.255.0"
    gateway     = str(cfg.get("gateway", "")).strip()
    lease       = str(cfg.get("lease", "12h")).strip() or "12h"
    domain      = str(cfg.get("domain", "")).strip()
    dns_servers = _split_csvish(cfg.get("dns"))
    static_hosts = cfg.get("static_hosts") or []

    cmds = [
        "# ── DHCP server (dnsmasq) ─────────────────────────────────",
        "mkdir -p /etc/dnsmasq.d",
        "rm -f /etc/dnsmasq.d/netrunner-dhcp.conf",
        "echo '# Generated by Netrunner' > /etc/dnsmasq.d/netrunner-dhcp.conf",
        f"echo 'interface={iface}' >> /etc/dnsmasq.d/netrunner-dhcp.conf",
        "echo 'bind-interfaces' >> /etc/dnsmasq.d/netrunner-dhcp.conf",
        "echo 'except-interface=lo' >> /etc/dnsmasq.d/netrunner-dhcp.conf",
        "echo 'dhcp-authoritative' >> /etc/dnsmasq.d/netrunner-dhcp.conf",
    ]
    if range_start and range_end:
        cmds.append(f"echo 'dhcp-range={range_start},{range_end},{mask},{lease}' >> /etc/dnsmasq.d/netrunner-dhcp.conf")
    if gateway:
        cmds.append(f"echo 'dhcp-option=option:router,{gateway}' >> /etc/dnsmasq.d/netrunner-dhcp.conf")
    if dns_servers:
        cmds.append(f"echo 'dhcp-option=option:dns-server,{','.join(dns_servers)}' >> /etc/dnsmasq.d/netrunner-dhcp.conf")
    if domain:
        cmds.extend([
            f"echo 'domain={domain}' >> /etc/dnsmasq.d/netrunner-dhcp.conf",
            f"echo 'local=/{domain}/' >> /etc/dnsmasq.d/netrunner-dhcp.conf",
        ])
    for lease_item in static_hosts:
        mac      = str(lease_item.get("mac",      "")).strip()
        ip       = str(lease_item.get("ip",       "")).strip()
        hostname = str(lease_item.get("hostname", "")).strip()
        if mac and ip:
            host_bits = [mac, ip]
            if hostname:
                host_bits.append(hostname)
            cmds.append(f"echo 'dhcp-host={','.join(host_bits)}' >> /etc/dnsmasq.d/netrunner-dhcp.conf")
    cmds.extend([
        "dnsmasq --test -C /etc/dnsmasq.d/netrunner-dhcp.conf 2>/dev/null || echo '(dnsmasq test failed or missing)'",
        "pkill dnsmasq 2>/dev/null || true",
        "dnsmasq --conf-file=/etc/dnsmasq.d/netrunner-dhcp.conf 2>/tmp/nr-dnsmasq.log || cat /tmp/nr-dnsmasq.log",
    ])
    return cmds


def gen_nat(cfg: dict) -> list[str]:
    outbound   = str(_get_any(cfg, ["outbound_iface", "out_interface", "wan_iface", "wan", "external_iface"], "eth0")).strip() or "eth0"
    inbound    = str(_get_any(cfg, ["inbound_iface", "in_interface", "lan_iface", "lan", "internal_iface"], "eth1")).strip() or "eth1"
    raw_source = _get_any(cfg, ["source_subnet", "inside_subnet", "inside_subnets", "source", "src"], "")
    source     = raw_source[0] if isinstance(raw_source, list) and raw_source else raw_source
    source     = str(source or "").strip()
    masquerade = bool(cfg.get("masquerade", True))
    forwards   = cfg.get("port_forwards") or cfg.get("forwards") or cfg.get("rules") or []

    cmds = [
        "# ── NAT / port forwarding via iptables ─────────────────────",
        "sysctl -w net.ipv4.ip_forward=1",
        "iptables -N NR_FORWARD 2>/dev/null || true",
        "iptables -F NR_FORWARD",
        "iptables -D FORWARD -j NR_FORWARD 2>/dev/null || true",
        "iptables -A FORWARD -j NR_FORWARD",
        "iptables -t nat -N NR_NAT 2>/dev/null || true",
        "iptables -t nat -F NR_NAT",
        "iptables -t nat -D PREROUTING -j NR_NAT 2>/dev/null || true",
        "iptables -t nat -D POSTROUTING -j NR_NAT 2>/dev/null || true",
        "iptables -t nat -A PREROUTING -j NR_NAT",
        "iptables -t nat -A POSTROUTING -j NR_NAT",
        "iptables -A NR_FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT",
    ]
    if source:
        cmds.append(f"iptables -A NR_FORWARD -i {inbound} -o {outbound} -s {source} -j ACCEPT")
    if masquerade:
        parts = ["iptables", "-t", "nat", "-A", "NR_NAT"]
        if source:
            parts += ["-s", source]
        parts += ["-o", outbound, "-j", "MASQUERADE"]
        cmds.append(" ".join(parts))
    for rule in forwards:
        proto       = str(rule.get("proto", "tcp")).strip() or "tcp"
        ext_port    = str(_get_any(rule, ["external_port", "ext_port", "port", "dport"], "")).strip()
        target_ip   = str(_get_any(rule, ["target_ip", "to_ip", "destination_ip", "host"], "")).strip()
        target_port = str(_get_any(rule, ["target_port", "to_port", "internal_port"], "")).strip() or ext_port
        if not (ext_port and target_ip):
            continue
        cmds.append(
            f"iptables -t nat -A NR_NAT -i {outbound} -p {proto} --dport {ext_port} "
            f"-j DNAT --to-destination {target_ip}:{target_port}"
        )
        cmds.append(
            f"iptables -A NR_FORWARD -i {outbound} -o {inbound} -p {proto} -d {target_ip} "
            f"--dport {target_port} -j ACCEPT"
        )
    cmds.extend([
        "iptables -S NR_FORWARD 2>/dev/null || true",
        "iptables -t nat -S NR_NAT 2>/dev/null || true",
    ])
    return cmds


def gen_reset_node() -> list[str]:
    return [
        "# ── Reset network configuration ─────────────────────────────",
        "sh -lc 'for dev in $(ip -o link show | awk -F\": \" \"{print \\$2}\" | cut -d@ -f1 | grep -v \"^lo$\"); do ip addr flush dev \"$dev\" 2>/dev/null || true; ip link set \"$dev\" down 2>/dev/null || true; ip link set \"$dev\" up 2>/dev/null || true; done'",
        "ip route flush table main 2>/dev/null || true",
        "ip -6 route flush table main 2>/dev/null || true",
        "sh -lc 'for dev in $(ip -o link show type wireguard 2>/dev/null | awk -F\": \" \"{print \\$2}\" | cut -d@ -f1); do wg-quick down \"$dev\" 2>/dev/null || ip link del \"$dev\" 2>/dev/null || true; done'",
        "sh -lc 'for dev in $(ip -o link show type vlan 2>/dev/null | awk -F\": \" \"{print \\$2}\" | cut -d@ -f1); do ip link del \"$dev\" 2>/dev/null || true; done'",
        "sh -lc 'for dev in $(ip -o link show type bridge 2>/dev/null | awk -F\": \" \"{print \\$2}\" | cut -d@ -f1); do [ \"$dev\" = \"docker0\" ] && continue; ip link set \"$dev\" down 2>/dev/null || true; ip link del \"$dev\" type bridge 2>/dev/null || true; done'",
        "sysctl -w net.ipv4.ip_forward=0 2>/dev/null || true",
        "sysctl -w net.ipv6.conf.all.forwarding=0 2>/dev/null || true",
        "nft flush ruleset 2>/dev/null || true",
        "iptables -F 2>/dev/null || true",
        "iptables -t nat -F 2>/dev/null || true",
        "iptables -t mangle -F 2>/dev/null || true",
        "iptables -X NR_FORWARD 2>/dev/null || true",
        "iptables -t nat -X NR_NAT 2>/dev/null || true",
        "iptables -P INPUT ACCEPT 2>/dev/null || true",
        "iptables -P FORWARD ACCEPT 2>/dev/null || true",
        "iptables -P OUTPUT ACCEPT 2>/dev/null || true",
        "ufw --force disable 2>/dev/null || true",
        "ufw --force reset 2>/dev/null || true",
        "pkill dnsmasq 2>/dev/null || true",
        "rm -f /etc/dnsmasq.d/netrunner-dhcp.conf /tmp/nr-dnsmasq.log 2>/dev/null || true",
        "printf '# resolver reset by Netrunner\\n' > /etc/resolv.conf",
        "sed -i '/# BEGIN NETRUNNER HOSTS/,/# END NETRUNNER HOSTS/d' /etc/hosts 2>/dev/null || true",
        "rm -f /etc/wireguard/*.conf 2>/dev/null || true",
        "echo 'Network configuration reset complete'",
    ]


def gen_vlan_router(iface: str, vlans: list[dict]) -> list[str]:
    iface = (iface or "eth0").strip() or "eth0"
    cmds = [
        f"# ── Router-on-a-stick on {iface} ───────────────────────────",
        "modprobe 8021q 2>/dev/null || true",
        f"ip link set {iface} up",
    ]
    seen = set()
    for v in vlans or []:
        vid = _vid(v.get("id"))
        if not vid or vid in seen:
            continue
        seen.add(vid)
        sub = f"{iface}.{vid}"
        action = v.get("action", "add")
        if action in ("del", "delete"):
            cmds.append(f"# Delete VLAN {vid}: {v.get('description', '')}")
            cmds.append(f"ip link set {sub} down 2>/dev/null || true")
            cmds.append(f"ip link del dev {sub} 2>/dev/null || true")
        else:
            if v.get("description"):
                cmds.append(f"# VLAN {vid}: {v['description']}")
            cmds.append(f"ip link add link {iface} name {sub} type vlan id {vid} 2>/dev/null || true")
            cmds.append(f"ip link set {sub} up")
            addr = (v.get("address") or "").strip()
            if addr:
                cmds.append(f"ip addr add {addr} dev {sub} 2>/dev/null || true")
    return cmds


def gen_vlan_switch(bridge: str, vlans: list[dict], ports: list[dict]) -> list[str]:
    bridge = (bridge or "br0").strip() or "br0"
    cmds = [
        f"# ── VLAN-aware switch on {bridge} ───────────────────────────",
        f"ip link add name {bridge} type bridge vlan_filtering 1 2>/dev/null || "
        f"ip link set {bridge} type bridge vlan_filtering 1",
        f"ip link set {bridge} up",
        f"bridge vlan del dev {bridge} vid 1 self 2>/dev/null || true",
    ]
    for v in vlans or []:
        vid = _vid(v.get("id"))
        if not vid:
            continue
        name = (v.get("name") or "").strip()
        cmds.append(f"# VLAN {vid}" + (f" ({name})" if name else ""))

    for p in ports or []:
        iface = (p.get("iface") or "").strip()
        if not iface:
            continue
        mode = p.get("mode", "access")
        cmds.append("")
        cmds.append(f"# Port {iface} — {mode}")
        cmds.append(f"ip link set {iface} master {bridge}")
        cmds.append(f"ip link set {iface} up")
        cmds.append(f"bridge vlan del dev {iface} vid 1 2>/dev/null || true")
        if mode == "access":
            vid = _vid(p.get("vlan"))
            if vid:
                cmds.append(f"bridge vlan add dev {iface} vid {vid} pvid untagged")
        else:
            allowed = []
            raw_allowed = p.get("allowed", [])
            if isinstance(raw_allowed, str):
                raw_allowed = [x for x in re.split(r"[,\s]+", raw_allowed) if x]
            for x in raw_allowed:
                vid = _vid(x)
                if vid and vid not in allowed:
                    allowed.append(vid)
            for vid in allowed:
                cmds.append(f"bridge vlan add dev {iface} vid {vid} tagged")
            pvid = _vid(p.get("pvid"))
            if pvid:
                cmds.append(f"bridge vlan add dev {iface} vid {pvid} pvid untagged")
    return cmds


def _get_robust(d: dict, keys: list[str]) -> any:
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d:
            val = d[k]
            if val is not None:
                if isinstance(val, (list, tuple)):
                    return ", ".join(str(x) for x in val)
                return val
    # Fallback to normalized keys (lowercase, no underscores or dashes)
    lower_dict = {str(k).lower().replace("_", "").replace("-", ""): v for k, v in d.items()}
    for k in keys:
        norm_k = k.lower().replace("_", "").replace("-", "")
        if norm_k in lower_dict:
            val = lower_dict[norm_k]
            if val is not None:
                if isinstance(val, (list, tuple)):
                    return ", ".join(str(x) for x in val)
                return val
    return None


def gen_wireguard(iface: str, cfg: dict) -> list[str]:
    action = cfg.get("action", "add")
    if action == "delete":
        return [
            f"# ── Delete WireGuard Interface & Keys: {iface} ───────────",
            f"wg-quick down {iface} 2>/dev/null || ip link del {iface} 2>/dev/null || true",
            f"rc-update del wg-quick.{iface} default 2>/dev/null || systemctl disable wg-quick@{iface} 2>/dev/null || true",
            f"rm -f /etc/wireguard/{iface}.conf /etc/wireguard/privatekey /etc/wireguard/publickey 2>/dev/null || true",
            f"echo 'WireGuard interface {iface} and keys deleted successfully'"
        ]

    private_key = _get_robust(cfg, ["private_key", "privateKey", "PrivateKey"])
    address = _get_robust(cfg, ["address", "addresses", "Address", "Addresses"])

    if not private_key:
        raise ValueError("WireGuard PrivateKey is required to generate/apply configuration.")
    if not address:
        raise ValueError("WireGuard IP Address (e.g. 10.0.0.1/24) is required.")

    lines = ["[Interface]"]
    for keys, lbl in [
        (["private_key", "privateKey", "PrivateKey"], "PrivateKey"),
        (["address", "addresses", "Address", "Addresses"], "Address"),
        (["listen_port", "listenPort", "ListenPort"], "ListenPort"),
        (["dns", "dns_servers", "dnsServers", "DNS"], "DNS"),
        (["mtu", "MTU"], "MTU"),
        (["post_up", "postUp", "PostUp"], "PostUp"),
        (["post_down", "postDown", "PostDown"], "PostDown"),
    ]:
        val = _get_robust(cfg, keys)
        if val is not None and str(val).strip() != "":
            lines.append(f"{lbl} = {val}")

    for peer in cfg.get("peers", []):
        pub_key = _get_robust(peer, ["public_key", "publicKey", "PublicKey"])
        if not pub_key:
            continue
        lines += ["", "[Peer]"]
        for keys, lbl in [
            (["public_key", "publicKey", "PublicKey"], "PublicKey"),
            (["preshared_key", "presharedKey", "PresharedKey"], "PresharedKey"),
            (["endpoint", "Endpoint"], "Endpoint"),
            (["allowed_ips", "allowedIPs", "AllowedIPs"], "AllowedIPs"),
            (["persistent_keepalive", "persistentKeepalive", "PersistentKeepalive"], "PersistentKeepalive"),
        ]:
            val = _get_robust(peer, keys)
            if val is not None and str(val).strip() != "":
                lines.append(f"{lbl} = {val}")
    conf = "\n".join(lines)

    return [
        "# ── Install WireGuard ───────────────────────────────────────",
        "apk add wireguard-tools 2>/dev/null || apt-get install -y wireguard-tools 2>/dev/null || yum install -y wireguard-tools 2>/dev/null || true",
        "",
        "# ── Keypair generation (run manually on device) ─────────────",
        "# wg genkey | tee /etc/wireguard/privatekey | wg pubkey > /etc/wireguard/publickey",
        "# cat /etc/wireguard/privatekey && cat /etc/wireguard/publickey",
        "",
        f"# ── Write /etc/wireguard/{iface}.conf ──────────────────────",
        f"mkdir -p /etc/wireguard\ncat > /etc/wireguard/{iface}.conf << 'EOF'\n{conf}\nEOF\nchmod 600 /etc/wireguard/{iface}.conf",
        "",
        "# ── Activate ────────────────────────────────────────────────",
        f"wg-quick down {iface} 2>/dev/null || ip link del {iface} 2>/dev/null || true",
        f"wg-quick up {iface}",
        "",
        "# ── Persist across reboots ──────────────────────────────────",
        f"rc-update add wg-quick.{iface} default 2>/dev/null || "
        f"systemctl enable wg-quick@{iface} 2>/dev/null || true",
    ]


def gen_persist_script(name: str, commands: list[str]) -> list[str]:
    script_name = _safe_name(name, "config")
    marker = f"__NETRUNNER_{script_name.upper()}_EOF__"
    script_path = f"/usr/local/sbin/netrunner-{script_name}.sh"
    openrc_path = f"/etc/local.d/netrunner-{script_name}.start"
    service_name = f"netrunner-{script_name}.service"
    service_path = f"/etc/systemd/system/{service_name}"
    body = ["#!/bin/sh", "# Generated by Netrunner", ""]
    body.extend(commands or [])

    body_str = "\n".join(body)
    service = "\n".join([
        "[Unit]",
        f"Description=Netrunner persistent config: {script_name}",
        "After=network-online.target",
        "Wants=network-online.target",
        "",
        "[Service]",
        "Type=oneshot",
        f"ExecStart={script_path}",
        "RemainAfterExit=yes",
        "",
        "[Install]",
        "WantedBy=multi-user.target",
    ])
    return [
        "# ── Install persistent boot script ──────────────────────────",
        f"mkdir -p /usr/local/sbin\ncat > {script_path} << '{marker}'\n{body_str}\n{marker}\nchmod +x {script_path}",
        (
            f"if command -v systemctl >/dev/null 2>&1; then\n"
            f"  cat > {service_path} << '{marker}_SERVICE'\n{service}\n{marker}_SERVICE\n"
            f"  systemctl daemon-reload\n"
            f"  systemctl enable {service_name}\n"
            f"elif command -v rc-update >/dev/null 2>&1; then\n"
            f"  mkdir -p /etc/local.d\n"
            f"  cp {script_path} {openrc_path}\n"
            f"  chmod +x {openrc_path}\n"
            f"  rc-update add local default\n"
            f"else\n"
            f"  echo 'No supported boot manager found: install {script_path} manually.'\n"
            f"fi"
        ),
        f"echo 'Persistent config installed: {script_path}'",
    ]


def gen_backup_commands(paths: dict) -> list[str]:
    def q(s): return shlex.quote(s)
    ip_addr   = paths["ip_addr"]
    ip_route  = paths["ip_route"]
    ip6_route = paths["ip6_route"]
    ipv4_fwd  = paths["ipv4_forward"]
    ipv6_fwd  = paths["ipv6_forward"]
    iptables  = paths["iptables"]
    nft       = paths["nft"]
    resolv    = paths["resolv"]
    hosts     = paths["hosts"]
    dnsmasq   = paths["dnsmasq"]
    wg_dir    = paths["wireguard"]
    backup_dir = paths["dir"]

    return [
        "# ── Backup current network state ────────────────────────────",
        f"rm -rf {q(backup_dir)}",
        f"mkdir -p {q(wg_dir)}",
        f"sh -lc {q('ip address save > ' + ip_addr + ' 2>/dev/null || :')}",
        f"sh -lc {q('ip route save > ' + ip_route + ' 2>/dev/null || :')}",
        f"sh -lc {q('ip -6 route save > ' + ip6_route + ' 2>/dev/null || :')}",
        f"sh -lc {q('sysctl -n net.ipv4.ip_forward > ' + ipv4_fwd + ' 2>/dev/null || echo 0 > ' + ipv4_fwd)}",
        f"sh -lc {q('sysctl -n net.ipv6.conf.all.forwarding > ' + ipv6_fwd + ' 2>/dev/null || echo 0 > ' + ipv6_fwd)}",
        f"sh -lc {q('iptables-save > ' + iptables + ' 2>/dev/null || :')}",
        f"sh -lc {q('nft list ruleset > ' + nft + ' 2>/dev/null || :')}",
        f"cp /etc/resolv.conf {q(resolv)} 2>/dev/null || true",
        f"cp /etc/hosts {q(hosts)} 2>/dev/null || true",
        f"cp /etc/dnsmasq.d/netrunner-dhcp.conf {q(dnsmasq)} 2>/dev/null || true",
        f"cp -r /etc/wireguard/. {q(wg_dir)}/ 2>/dev/null || true",
        "echo 'Backup created: " + backup_dir + "'",
    ]


def gen_restore_commands(paths: dict) -> list[str]:
    def q(s): return shlex.quote(s)
    ip_addr   = paths["ip_addr"]
    ip_route  = paths["ip_route"]
    ip6_route = paths["ip6_route"]
    ipv4_fwd  = paths["ipv4_forward"]
    ipv6_fwd  = paths["ipv6_forward"]
    iptables  = paths["iptables"]
    nft       = paths["nft"]
    resolv    = paths["resolv"]
    hosts     = paths["hosts"]
    dnsmasq   = paths["dnsmasq"]
    wg_dir    = paths["wireguard"]

    return [
        "# ── Restore network state from backup ───────────────────────",
        f"test -d {q(paths['dir'])} || (echo 'Backup not found' && false)",
        "ip route flush table main 2>/dev/null || true",
        "ip -6 route flush table main 2>/dev/null || true",
        "nft flush ruleset 2>/dev/null || true",
        "iptables -F 2>/dev/null || true; iptables -t nat -F 2>/dev/null || true",
        f"if [ -s {q(ip_addr)} ]; then ip address restore < {q(ip_addr)} 2>/dev/null || :; fi",
        f"if [ -s {q(ip_route)} ]; then ip route restore < {q(ip_route)} 2>/dev/null || :; fi",
        f"if [ -s {q(ip6_route)} ]; then ip -6 route restore < {q(ip6_route)} 2>/dev/null || :; fi",
        f"if [ -s {q(ipv4_fwd)} ]; then sysctl -w net.ipv4.ip_forward=$(cat {q(ipv4_fwd)}) 2>/dev/null || :; fi",
        f"if [ -s {q(ipv6_fwd)} ]; then sysctl -w net.ipv6.conf.all.forwarding=$(cat {q(ipv6_fwd)}) 2>/dev/null || :; fi",
        f"if [ -s {q(iptables)} ]; then iptables-restore < {q(iptables)} 2>/dev/null || :; fi",
        f"if [ -s {q(nft)} ]; then nft -f {q(nft)} 2>/dev/null || :; fi",
        f"if [ -f {q(resolv)} ]; then cp {q(resolv)} /etc/resolv.conf; fi",
        f"if [ -f {q(hosts)} ]; then cp {q(hosts)} /etc/hosts; fi",
        f"if [ -f {q(dnsmasq)} ]; then mkdir -p /etc/dnsmasq.d && cp {q(dnsmasq)} /etc/dnsmasq.d/netrunner-dhcp.conf; fi",
        f"if [ -d {q(wg_dir)} ]; then mkdir -p /etc/wireguard && cp -r {q(wg_dir)}/. /etc/wireguard/; fi",
        "echo 'Rollback complete'",
    ]


def gen_nmap(cfg: dict) -> list[str]:
    target = str(cfg.get("target", "127.0.0.1")).strip() or "127.0.0.1"
    scan_type = cfg.get("scan_type", "quick")
    
    # Base command
    nmap = ["nmap"]
    
    if scan_type == "quick":
        nmap += ["-F", "-T4"]
    elif scan_type == "service":
        nmap += ["-sV", "-T4"]
    elif scan_type == "os":
        nmap += ["-O", "-sV", "-T4"]
    elif scan_type == "stealth":
        nmap += ["-sS", "-T4"]
    elif scan_type == "ping":
        nmap += ["-sn"]
    elif scan_type == "full":
        nmap += ["-p-", "-sV", "-T4"]
    
    if cfg.get("dns_resolve") is False:
        nmap += ["-n"]
    
    if cfg.get("interface"):
        nmap += ["-e", cfg["interface"]]
        
    nmap.append(target)
    
    return [
        "# ── Nmap Network Scan ──────────────────────────────────────",
        " ".join(nmap)
    ]


def gen_iperf3(cfg: dict) -> list[str]:
    mode = cfg.get("mode", "client")
    cmds = ["# ── iperf3 Bandwidth Test ──────────────────────────────────"]
    if mode == "server":
        cmds.append("iperf3 -s -1") # Run once and exit
    else:
        server = str(cfg.get("server", "")).strip()
        if not server: raise ValueError("Server IP/Hostname required")
        args = ["iperf3", "-c", server, "-t", str(cfg.get("duration", 10))]
        if cfg.get("reverse"): args.append("-R")
        if cfg.get("udp"): args.append("-u")
        if cfg.get("bitrate"): args += ["-b", cfg["bitrate"]]
        cmds.append(" ".join(args))
    return cmds


def gen_mtr(cfg: dict) -> list[str]:
    target = str(cfg.get("target", "")).strip()
    if not target: raise ValueError("Target required")
    count = cfg.get("count", 5)
    return [
        "# ── MTR Traceroute ─────────────────────────────────────────",
        f"mtr -rw -c {count} {target}"
    ]


def gen_speedtest() -> list[str]:
    return [
        "# ── Speedtest-CLI ──────────────────────────────────────────",
        "speedtest-cli --simple || speedtest --simple"
    ]


def gen_dns_lookup(cfg: dict) -> list[str]:
    target = str(cfg.get("target", "")).strip()
    if not target: raise ValueError("Target required")
    qtype = cfg.get("query_type", "A")
    server = str(cfg.get("server", "")).strip()
    
    cmd = ["dig", qtype, target]
    if server: cmd.append(f"@{server}")
    cmd.append("+short")
    
    return [
        "# ── DNS Lookup (dig) ───────────────────────────────────────",
        " ".join(cmd)
    ]


def gen_wol(cfg: dict) -> list[str]:
    mac = str(cfg.get("mac", "")).strip()
    if not mac: raise ValueError("MAC address required")
    iface = str(cfg.get("interface", "")).strip()
    
    cmd = ["wakeonlan"]
    if iface: cmd += ["-i", iface]
    cmd.append(mac)
    
    return [
        "# ── Wake-on-LAN ────────────────────────────────────────────",
        " ".join(cmd)
    ]


def gen_arp_scan(cfg: dict) -> list[str]:
    iface = str(cfg.get("interface", "")).strip()
    target = str(cfg.get("target", "localnet")).strip()
    
    cmd = ["arp-scan"]
    if iface: cmd += ["-I", iface]
    cmd.append(target)
    
    return [
        "# ── Arp-scan ───────────────────────────────────────────────",
        " ".join(cmd)
    ]


def gen_pmf(cfg: dict) -> list[str]:
    """Generate Management Frame Protection (802.11w) configuration.

    Supports three backends tried in order:
      1. nmcli  (NetworkManager — most modern Linux distros)
      2. wpa_supplicant config file  (client / station mode)
      3. hostapd config file  (AP / hotspot mode)

    Config keys:
        ssid        – WiFi network name (required)
        password    – WPA2/WPA3 passphrase (required for secured networks)
        interface   – wireless interface, default "wlan0"
        mode        – "client" (default) or "ap"
        country     – two-letter country code, default "DK"
        hidden      – bool, whether the SSID is hidden
        ap_channel  – AP channel (only used in ap mode), default 6
    """
    ssid      = str(cfg.get("ssid", "")).strip()
    password  = str(cfg.get("password", "")).strip()
    iface     = str(cfg.get("interface", "wlan0")).strip() or "wlan0"
    mode      = str(cfg.get("mode", "client")).strip().lower()
    country   = str(cfg.get("country", "DK")).strip().upper()
    hidden    = bool(cfg.get("hidden", False))
    ap_channel = int(cfg.get("ap_channel", 6))

    if not ssid:
        raise ValueError("ssid is required for PMF configuration")

    scan_ssid = "scan_ssid=1\n" if hidden else ""
    marker = "__NETRUNNER_PMF_EOF__"

    # ── wpa_supplicant (client / station) ─────────────────────────
    wpa_conf = (
        f"country={country}\n"
        f"ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n"
        f"update_config=1\n\n"
        f"network={{\n"
        f'    ssid="{ssid}"\n'
        f"{scan_ssid}"
        + (f'    psk="{password}"\n' if password else "    key_mgmt=NONE\n")
        + f"    key_mgmt=WPA-PSK-SHA256 WPA-PSK\n"
        + f"    proto=RSN\n"
        + f"    pairwise=CCMP\n"
        + f"    group=CCMP\n"
        + f"    ieee80211w=2\n"
        + f"}}"
    )

    # ── hostapd (AP / hotspot) ────────────────────────────────────
    wpa_psk = password if password else ""
    hostapd_conf = (
        f"interface={iface}\n"
        f"driver=nl80211\n"
        f"ssid={ssid}\n"
        f"hw_mode=g\n"
        f"channel={ap_channel}\n"
        f"wmm_enabled=1\n"
        f"macaddr_acl=0\n"
        f"auth_algs=1\n"
        f"ignore_broadcast_ssid={'1' if hidden else '0'}\n\n"
        f"# WPA2/WPA3 with PMF Required (802.11w)\n"
        f"wpa=2\n"
        f"wpa_passphrase={wpa_psk}\n"
        f"wpa_key_mgmt=SAE\n"
        f"wpa_pairwise=CCMP\n"
        f"rsn_pairwise=CCMP\n"
        f"ieee80211w=2\n"
    )

    # ── nmcli commands (NetworkManager) ───────────────────────────
    # 802-11-wireless.pmf values: 1=disable, 2=optional, 3=required
    nmcli_cmds = [
        f"nmcli connection modify \"{ssid}\" 802-11-wireless.pmf 3",
        f"nmcli connection modify \"{ssid}\" 802-11-wireless.key-mgmt \"wpa-psk-sha256 wpa-psk\"",
    ]

    cmds = [
        "# ── Management Frame Protection (802.11w — PMF Required) ──",
        "# PMF protects against deauthentication/disassociation attacks.",
        "# Requires WPA2-CCMP or WPA3 (SAE). Older clients may not connect.",
        "",
    ]

    if mode == "ap":
        cmds += [
            "# ── hostapd AP configuration with PMF ──────────────────",
            f"mkdir -p /etc/hostapd",
            f"cat > /etc/hostapd/hostapd.conf << '{marker}'",
            hostapd_conf,
            marker,
            "",
            "# ── Enable and start hostapd ────────────────────────────",
            "systemctl unmask hostapd 2>/dev/null || true",
            "systemctl enable hostapd 2>/dev/null || true",
            "systemctl restart hostapd 2>/dev/null || "
            f"hostapd -B /etc/hostapd/hostapd.conf 2>/dev/null || true",
            "",
            "# ── Verify PMF is active ────────────────────────────────",
            f"iw dev {iface} info 2>/dev/null | grep -i 'pmf\\|mgmt' || "
            f"iwpriv {iface} get_pmf 2>/dev/null || "
            "echo 'Verify PMF manually: iw dev <iface> info'",
        ]
    else:
        nmcli_connect = (
            f"nmcli dev wifi connect \"{ssid}\""
            + (f" password \"{password}\"" if password else "")
            + f" 2>/dev/null && ("
            + " && ".join(nmcli_cmds)
            + f") && echo 'Connected via nmcli with PMF Required'"
        )
        wpa_file = (
            f"cat > /etc/wpa_supplicant/wpa_supplicant.conf << '{marker}'\n"
            f"{wpa_conf}\n"
            f"{marker}\n"
            f"wpa_cli -i {iface} reconfigure 2>/dev/null || "
            f"wpa_supplicant -B -i {iface} -c /etc/wpa_supplicant/wpa_supplicant.conf 2>/dev/null || true\n"
            f"sleep 3\n"
            f"ip addr show {iface} | grep 'inet '"
        )
        cmds += [
            "# ── Try nmcli first (NetworkManager) ───────────────────",
            f"{nmcli_connect} || (",
            "",
            "# ── Fallback: wpa_supplicant with PMF ──────────────────",
            wpa_file,
            ")",
            "",
            "# ── Verify PMF is active ────────────────────────────────",
            f"wpa_cli -i {iface} status 2>/dev/null | grep -i 'pmf\\|ieee80211w' || "
            f"iw dev {iface} info 2>/dev/null | grep -i 'pmf' || "
            "echo 'Verify PMF manually: wpa_cli status'",
        ]

    return cmds
