"""Config command preview endpoints — generate shell commands without running them."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..generators.network import (
    gen_ip, gen_interface, gen_routes, gen_forwarding, gen_dhcp, gen_dns, gen_dhcp_server,
    gen_nat, gen_reset_node, gen_vlan_router, gen_vlan_switch, gen_wireguard,
    gen_persist_script, gen_nmap, gen_iperf3, gen_mtr, gen_speedtest,
    gen_dns_lookup, gen_wol, gen_arp_scan,
)
from ..generators.firewall import gen_iptables, gen_ufw, gen_nftables
from ..generators.linux import (
    gen_service, gen_package, gen_user, gen_cron, gen_sysctl,
    gen_file_write, gen_hostname, gen_ssh_hardening, gen_authorized_key,
    gen_systemd_service_unit, gen_remote_desktop,
)
from ..generators.windows import (
    gen_win_ip, gen_win_route, gen_win_service,
    gen_win_feature, gen_win_hostname, gen_win_file,
)
from ..generators.docker import gen_docker
from ..generators.rpi import (
    gen_rpi_config_set, gen_rpi_config_section, gen_rpi_gpio,
    gen_rpi_gpio_read_all, gen_rpi_i2c, gen_rpi_i2c_enable, gen_rpi_spi,
    gen_rpi_camera, gen_rpi_overclock, gen_rpi_temperature,
    gen_rpi_wifi, gen_rpi_bluetooth, gen_rpi_watchdog, gen_rpi_info,
)

router = APIRouter()


@router.get("/wireguard/generate-keys")
def generate_wg_keys():
    try:
        from cryptography.hazmat.primitives.asymmetric import x25519
        import base64
        priv = x25519.X25519PrivateKey.generate()
        priv_bytes = priv.private_bytes_raw()
        priv_b64 = base64.b64encode(priv_bytes).decode("utf-8")
        
        pub = priv.public_key()
        pub_bytes = pub.public_bytes_raw()
        pub_b64 = base64.b64encode(pub_bytes).decode("utf-8")
        
        return {"private_key": priv_b64, "public_key": pub_b64}
    except Exception as e:
        raise HTTPException(500, f"Failed to generate keypair: {str(e)}")


@router.post("/preview")
def api_preview(body: dict):
    t   = body.get("type")
    cfg = body.get("data", {})

    try:
        # ── Network ────────────────────────────────────────────────
        if t == "ip":
            cmds = gen_ip(cfg.get("interface", "eth0"), cfg.get("addresses", []), cfg.get("action", "add"))
        elif t == "interface":
            cmds = gen_interface(cfg)
        elif t == "routes":
            cmds = gen_routes(cfg.get("routes", []), cfg.get("action", "add"))
        elif t == "forwarding":
            cmds = gen_forwarding(cfg.get("ipv4"), cfg.get("ipv6"))
        elif t == "dhcp":
            cmds = gen_dhcp(cfg.get("interface", "eth0"), cfg.get("action", "renew"))
        elif t == "dns":
            cmds = gen_dns(cfg)
        elif t == "dhcp-server":
            cmds = gen_dhcp_server(cfg)
        elif t == "nat":
            cmds = gen_nat(cfg)
        elif t == "reset-node":
            cmds = gen_reset_node()
        elif t == "vlan-router":
            cmds = gen_vlan_router(cfg.get("interface", "eth0"), cfg.get("vlans", []))
        elif t == "vlan-switch":
            cmds = gen_vlan_switch(cfg.get("bridge", "br0"), cfg.get("vlans", []), cfg.get("ports", []))
        elif t == "wireguard":
            cmds = gen_wireguard(cfg.get("interface", "wg0"), cfg)
        elif t == "nmap":
            cmds = gen_nmap(cfg)
        elif t == "iperf3":
            cmds = gen_iperf3(cfg)
        elif t == "mtr":
            cmds = gen_mtr(cfg)
        elif t == "speedtest":
            cmds = gen_speedtest()
        elif t == "dns-lookup":
            cmds = gen_dns_lookup(cfg)
        elif t == "wol":
            cmds = gen_wol(cfg)
        elif t == "arp-scan":
            cmds = gen_arp_scan(cfg)
        elif t == "persist":
            cmds = gen_persist_script(cfg.get("name", "config"), cfg.get("commands", []))

        # ── Firewall ───────────────────────────────────────────────
        elif t == "iptables":
            cmds = gen_iptables(cfg)
        elif t == "ufw":
            cmds = gen_ufw(cfg)
        elif t == "nftables":
            cmds = gen_nftables(cfg)

        # ── Linux ──────────────────────────────────────────────────
        elif t == "service":
            cmds = gen_service(cfg.get("name", ""), cfg.get("action", "status"))
        elif t == "package":
            cmds = gen_package(cfg.get("packages", []), cfg.get("action", "install"), cfg.get("manager", "auto"))
        elif t == "user":
            cmds = gen_user(cfg)
        elif t == "cron":
            cmds = gen_cron(cfg)
        elif t == "sysctl":
            cmds = gen_sysctl(cfg.get("params", []), cfg.get("persist", True))
        elif t == "file-write":
            cmds = gen_file_write(cfg)
        elif t == "hostname":
            cmds = gen_hostname(cfg.get("hostname", ""), cfg.get("domain", ""))
        elif t == "ssh-hardening":
            cmds = gen_ssh_hardening(cfg)
        elif t == "authorized-key":
            cmds = gen_authorized_key(cfg)
        elif t == "systemd-unit":
            cmds = gen_systemd_service_unit(cfg)
        elif t == "remote-desktop":
            cmds = gen_remote_desktop(cfg)

        # ── Windows ────────────────────────────────────────────────
        elif t == "win-ip":
            cmds = gen_win_ip(cfg)
        elif t == "win-route":
            cmds = gen_win_route(cfg)
        elif t == "win-service":
            cmds = gen_win_service(cfg)
        elif t == "win-feature":
            cmds = gen_win_feature(cfg)
        elif t == "win-hostname":
            cmds = gen_win_hostname(cfg)
        elif t == "win-file":
            cmds = gen_win_file(cfg)
        elif t == "docker":
            cmds = gen_docker(cfg)

        # ── Raspberry Pi ───────────────────────────────────────────
        elif t == "rpi-config-set":
            cmds = gen_rpi_config_set(cfg.get("key", ""), cfg.get("value", ""))
        elif t == "rpi-config-section":
            cmds = gen_rpi_config_section(cfg.get("entries", []), cfg.get("section", ""))
        elif t == "rpi-gpio":
            cmds = gen_rpi_gpio(cfg.get("pin", 0), cfg.get("mode", "in"), cfg.get("value"))
        elif t == "rpi-gpio-read-all":
            cmds = gen_rpi_gpio_read_all()
        elif t == "rpi-i2c":
            cmds = gen_rpi_i2c(cfg.get("action", "scan"), cfg.get("bus", 1), cfg.get("addr", ""), cfg.get("reg", ""), cfg.get("value", ""))
        elif t == "rpi-i2c-enable":
            cmds = gen_rpi_i2c_enable(cfg.get("bus", 1), cfg.get("enable", True))
        elif t == "rpi-spi":
            cmds = gen_rpi_spi(cfg.get("enable", True))
        elif t == "rpi-camera":
            cmds = gen_rpi_camera(cfg.get("enable", True), cfg.get("legacy", False))
        elif t == "rpi-overclock":
            cmds = gen_rpi_overclock(cfg)
        elif t == "rpi-temperature":
            cmds = gen_rpi_temperature()
        elif t == "rpi-wifi":
            cmds = gen_rpi_wifi(cfg)
        elif t == "rpi-bluetooth":
            cmds = gen_rpi_bluetooth(cfg.get("enable", True))
        elif t == "rpi-watchdog":
            cmds = gen_rpi_watchdog(cfg.get("timeout", 14), cfg.get("action", "enable"))
        elif t == "rpi-info":
            cmds = gen_rpi_info()

        else:
            raise HTTPException(400, f"Unknown preview type '{t}'")

    except ValueError as e:
        raise HTTPException(400, str(e))

    return {"commands": cmds}
