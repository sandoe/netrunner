"""WiFi Security configuration generators — WPA3-SAE, OWE, 802.1X/EAP-TLS."""

from __future__ import annotations


def gen_wpa3_sae(cfg: dict) -> list[str]:
    """Generate WPA3-SAE (Simultaneous Authentication of Equals) configuration.

    WPA3-SAE protects against offline dictionary attacks even with weak passwords.
    The handshake mathematically prevents replay of captured traffic.
    Forward Secrecy ensures past traffic cannot be decrypted even if the password
    is later compromised.

    Config keys:
        ssid        – WiFi network name (required)
        password    – WPA3 passphrase (required)
        interface   – wireless interface, default "wlan0"
        mode        – "client" (default) or "ap"
        country     – two-letter country code, default "DK"
        hidden      – bool, whether the SSID is hidden
        ap_channel  – AP channel (ap mode only), default 6
        sae_groups  – DH groups for SAE, default "19 20 21" (P-256, P-384, P-521)
    """
    ssid = str(cfg.get("ssid", "")).strip()
    password = str(cfg.get("password", "")).strip()
    iface = str(cfg.get("interface", "wlan0")).strip() or "wlan0"
    mode = str(cfg.get("mode", "client")).strip().lower()
    country = str(cfg.get("country", "DK")).strip().upper()
    hidden = bool(cfg.get("hidden", False))
    ap_channel = int(cfg.get("ap_channel", 6))
    sae_groups = str(cfg.get("sae_groups", "19 20 21")).strip()

    if not ssid:
        raise ValueError("ssid is required for WPA3-SAE configuration")
    if not password:
        raise ValueError("password is required for WPA3-SAE configuration")

    scan_ssid = "scan_ssid=1\n" if hidden else ""
    marker = "__NETRUNNER_WPA3_EOF__"

    # ── wpa_supplicant (client / station) ─────────────────────────
    wpa_conf = (
        f"country={country}\n"
        f"ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n"
        f"update_config=1\n\n"
        f"network={{\n"
        f'    ssid="{ssid}"\n'
        f"{scan_ssid}"
        f'    psk="{password}"\n'
        f"    key_mgmt=SAE\n"
        f"    proto=RSN\n"
        f"    pairwise=CCMP\n"
        f"    group=CCMP\n"
        f"    ieee80211w=2\n"
        f"    sae_pwe=2\n"
        f"    sae_groups={sae_groups}\n"
        f"}}"
    )

    # ── hostapd (AP / hotspot) ────────────────────────────────────
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
        f"# WPA3-SAE\n"
        f"wpa=2\n"
        f"wpa_passphrase={password}\n"
        f"wpa_key_mgmt=SAE\n"
        f"wpa_pairwise=CCMP\n"
        f"rsn_pairwise=CCMP\n"
        f"ieee80211w=2\n"
        f"sae_pwe=2\n"
        f"sae_groups={sae_groups}\n"
        f"sae_hunting_and_pecking=1\n"
    )

    # ── nmcli ─────────────────────────────────────────────────────
    nmcli_cmds = [
        f'nmcli connection modify "{ssid}" 802-11-wireless.key-mgmt "sae"',
        f'nmcli connection modify "{ssid}" 802-11-wireless.pmf 3',
        f'nmcli connection modify "{ssid}" wifi-sec.key-mgmt "sae"',
        f'nmcli connection modify "{ssid}" wifi-sec.pmf 3',
    ]

    cmds = [
        "# ── WPA3-SAE (Simultaneous Authentication of Equals) ──────",
        "# WPA3-SAE protects against offline dictionary attacks.",
        "# Forward Secrecy prevents decryption of past traffic.",
        "# Requires WPA3-capable hardware on both AP and client.",
        "",
    ]

    if mode == "ap":
        cmds += [
            "# ── hostapd AP configuration with WPA3-SAE ───────────",
            "mkdir -p /etc/hostapd",
            f"cat > /etc/hostapd/hostapd.conf << '{marker}'",
            hostapd_conf,
            marker,
            "",
            "# ── Enable and start hostapd ──────────────────────────",
            "systemctl unmask hostapd 2>/dev/null || true",
            "systemctl enable hostapd 2>/dev/null || true",
            "systemctl restart hostapd 2>/dev/null || "
            f"hostapd -B /etc/hostapd/hostapd.conf 2>/dev/null || true",
            "",
            "# ── Verify WPA3-SAE is active ─────────────────────────",
            f"iw dev {iface} info 2>/dev/null | grep -i 'wpa3\\|sae\\|pmf' || "
            f"hostapd_cli -i {iface} status 2>/dev/null | grep -i 'key_mgmt\\|sae' || "
            "echo 'Verify WPA3 manually: hostapd_cli status'",
        ]
    else:
        nmcli_connect = (
            f'nmcli dev wifi connect "{ssid}" password "{password}" 2>/dev/null && ('
            + " && ".join(nmcli_cmds)
            + ') && echo "Connected via nmcli with WPA3-SAE"'
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
            "# ── Try nmcli first (NetworkManager) ──────────────────",
            f"{nmcli_connect} || (",
            "",
            "# ── Fallback: wpa_supplicant with WPA3-SAE ───────────",
            wpa_file,
            ")",
            "",
            "# ── Verify WPA3-SAE is active ─────────────────────────",
            f"wpa_cli -i {iface} status 2>/dev/null | grep -i 'key_mgmt\\|sae\\|pmf' || "
            f"iw dev {iface} info 2>/dev/null | grep -i 'wpa3\\|sae' || "
            "echo 'Verify WPA3 manually: wpa_cli status'",
        ]

    return cmds


def gen_owe(cfg: dict) -> list[str]:
    """Generate OWE (Opportunistic Wireless Encryption) configuration.

    OWE provides encryption on open networks without requiring a password.
    Each client gets a unique encrypted session with the AP via Diffie-Hellman
    key exchange. Passive eavesdroppers cannot sniff traffic.

    Config keys:
        ssid        – WiFi network name (required)
        interface   – wireless interface, default "wlan0"
        mode        – "client" (default) or "ap"
        country     – two-letter country code, default "DK"
        ap_channel  – AP channel (ap mode only), default 6
        owe_groups  – DH groups for OWE, default "19 20" (P-256, P-384)
    """
    ssid = str(cfg.get("ssid", "")).strip()
    iface = str(cfg.get("interface", "wlan0")).strip() or "wlan0"
    mode = str(cfg.get("mode", "client")).strip().lower()
    country = str(cfg.get("country", "DK")).strip().upper()
    ap_channel = int(cfg.get("ap_channel", 6))
    owe_groups = str(cfg.get("owe_groups", "19 20")).strip()

    if not ssid:
        raise ValueError("ssid is required for OWE configuration")

    marker = "__NETRUNNER_OWE_EOF__"

    # ── wpa_supplicant (client / station) ─────────────────────────
    wpa_conf = (
        f"country={country}\n"
        f"ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n"
        f"update_config=1\n\n"
        f"network={{\n"
        f'    ssid="{ssid}"\n'
        f"    key_mgmt=OWE\n"
        f"    owe_groups={owe_groups}\n"
        f"}}"
    )

    # ── hostapd (AP / hotspot) ────────────────────────────────────
    hostapd_conf = (
        f"interface={iface}\n"
        f"driver=nl80211\n"
        f"ssid={ssid}\n"
        f"hw_mode=g\n"
        f"channel={ap_channel}\n"
        f"wmm_enabled=1\n"
        f"macaddr_acl=0\n"
        f"auth_algs=1\n\n"
        f"# OWE — Opportunistic Wireless Encryption\n"
        f"# Open network with per-client encryption.\n"
        f"# No password required — DH key exchange provides security.\n"
        f"wpa_key_mgmt=OWE\n"
        f"ieee80211w=2\n"
        f"owe_groups={owe_groups}\n"
    )

    # ── nmcli ─────────────────────────────────────────────────────
    nmcli_cmds = [
        f'nmcli connection modify "{ssid}" 802-11-wireless.key-mgmt "owe"',
        f'nmcli connection modify "{ssid}" 802-11-wireless.pmf 3',
    ]

    cmds = [
        "# ── OWE (Opportunistic Wireless Encryption) ─────────────",
        "# OWE encrypts open networks without a password.",
        "# Each client gets a unique encrypted session via DH exchange.",
        "# Passive eavesdroppers cannot sniff traffic.",
        "",
    ]

    if mode == "ap":
        cmds += [
            "# ── hostapd AP configuration with OWE ────────────────",
            "mkdir -p /etc/hostapd",
            f"cat > /etc/hostapd/hostapd.conf << '{marker}'",
            hostapd_conf,
            marker,
            "",
            "# ── Enable and start hostapd ──────────────────────────",
            "systemctl unmask hostapd 2>/dev/null || true",
            "systemctl enable hostapd 2>/dev/null || true",
            "systemctl restart hostapd 2>/dev/null || "
            f"hostapd -B /etc/hostapd/hostapd.conf 2>/dev/null || true",
            "",
            "# ── Verify OWE is active ──────────────────────────────",
            f"iw dev {iface} info 2>/dev/null | grep -i 'owe\\|pmf' || "
            f"hostapd_cli -i {iface} status 2>/dev/null | grep -i 'key_mgmt\\|owe' || "
            "echo 'Verify OWE manually: hostapd_cli status'",
        ]
    else:
        nmcli_connect = (
            f'nmcli dev wifi connect "{ssid}" 2>/dev/null && ('
            + " && ".join(nmcli_cmds)
            + ') && echo "Connected via nmcli with OWE"'
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
            "# ── Try nmcli first (NetworkManager) ──────────────────",
            f"{nmcli_connect} || (",
            "",
            "# ── Fallback: wpa_supplicant with OWE ────────────────",
            wpa_file,
            ")",
            "",
            "# ── Verify OWE is active ──────────────────────────────",
            f"wpa_cli -i {iface} status 2>/dev/null | grep -i 'key_mgmt\\|owe' || "
            f"iw dev {iface} info 2>/dev/null | grep -i 'owe' || "
            "echo 'Verify OWE manually: wpa_cli status'",
        ]

    return cmds


def gen_eaptls(cfg: dict) -> list[str]:
    """Generate 802.1X / EAP-TLS (Enterprise certificate authentication) configuration.

    Instead of a shared Pre-Shared Key (PSK), each device authenticates with
    its own certificate. This makes Evil Twin attacks nearly impossible since
    the attacker cannot replicate the hardware certificate.

    Config keys:
        ssid            – WiFi network name (required)
        interface       – wireless interface, default "wlan0"
        mode            – "client" (default) or "ap"
        country         – two-letter country code, default "DK"
        hidden          – bool, whether the SSID is hidden
        ap_channel      – AP channel (ap mode only), default 6
        server_cert     – path to RADIUS/server certificate (AP mode)
        server_key      – path to RADIUS/server private key (AP mode)
        ca_cert         – path to CA certificate (both modes)
        client_cert     – path to client certificate (client mode)
        client_key      – path to client private key (client mode)
        identity        – EAP identity string (client mode)
        bridge          – bridge interface for RADIUS (AP mode), default "br0"
    """
    ssid = str(cfg.get("ssid", "")).strip()
    iface = str(cfg.get("interface", "wlan0")).strip() or "wlan0"
    mode = str(cfg.get("mode", "client")).strip().lower()
    country = str(cfg.get("country", "DK")).strip().upper()
    hidden = bool(cfg.get("hidden", False))
    ap_channel = int(cfg.get("ap_channel", 6))
    server_cert = str(cfg.get("server_cert", "/etc/ssl/certs/hostapd.pem")).strip()
    server_key = str(cfg.get("server_key", "/etc/ssl/private/hostapd.key")).strip()
    ca_cert = str(cfg.get("ca_cert", "/etc/ssl/certs/ca.pem")).strip()
    client_cert = str(cfg.get("client_cert", "/etc/ssl/certs/client.pem")).strip()
    client_key = str(cfg.get("client_key", "/etc/ssl/private/client.key")).strip()
    identity = (
        str(cfg.get("identity, '')")).strip() or str(cfg.get("identity", "")).strip()
    )
    bridge = str(cfg.get("bridge", "br0")).strip() or "br0"

    if not ssid:
        raise ValueError("ssid is required for 802.1X/EAP-TLS configuration")

    scan_ssid = "scan_ssid=1\n" if hidden else ""
    marker = "__NETRUNNER_EAPTLS_EOF__"

    # ── wpa_supplicant (client / station) ─────────────────────────
    wpa_conf = (
        f"country={country}\n"
        f"ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n"
        f"update_config=1\n\n"
        f"network={{\n"
        f'    ssid="{ssid}"\n'
        f"{scan_ssid}"
        f"    key_mgmt=WPA-EAP\n"
        f"    eap=TLS\n"
        f'    identity="{identity}"\n'
        f'    ca_cert="{ca_cert}"\n'
        f'    client_cert="{client_cert}"\n'
        f'    private_key="{client_key}"\n'
        f"    eapol_flags=3\n"
        f"    paired_key_auth=1\n"
        f"}}"
    )

    # ── hostapd (AP / hotspot) ────────────────────────────────────
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
        f"# 802.1X / EAP-TLS Enterprise Authentication\n"
        f"ieee8021x=1\n"
        f"wpa_key_mgmt=WPA-EAP\n"
        f"wpa=2\n"
        f"wpa_pairwise=CCMP\n"
        f"rsn_pairwise=CCMP\n"
        f"ieee80211w=2\n\n"
        f"# RADIUS via internal EAP server\n"
        f"eap_server=1\n"
        f'eap_user_file="/etc/hostapd/eap_user"\n'
        f'ca_cert="{ca_cert}"\n'
        f'server_cert="{server_cert}"\n'
        f'server_private_key="{server_key}"\n'
        f"server_private_key_passwd=\n\n"
        f"# Optional: bridge to RADIUS server\n"
        f"# bridge={bridge}\n"
    )

    # ── FreeRADIUS reference config (AP mode only) ────────────────
    radius_conf = (
        f"# FreeRADIUS clients.conf — add this AP as a RADIUS client:\n"
        f"# client ap_host {{\n"
        f"#     ipaddr = 127.0.0.1\n"
        f"#     secret = {ssid.lower().replace(' ', '_')}_secret\n"
        f"# }}\n\n"
        f"# FreeRADIUS mods-enabled/eap — EAP-TLS config:\n"
        f"# eap {{\n"
        f"#     default_eap_type = tls\n"
        f"#     tls-config tls-common {{\n"
        f"#         private_key_file = {server_key}\n"
        f"#         certificate_file = {server_cert}\n"
        f"#         ca_file = {ca_cert}\n"
        f"#         dh_file = {{...}}\n"
        f"#     }}\n"
        f"# }}\n\n"
        f"# Add user certificate to /etc/freameradius/3.0/mods-config/files/authorize:\n"
        f"# {identity or 'username'} Cleartext-Password := \"\"\n"
        f"#     EAP-Response, EAP-Type-Identity = \"{identity or 'username'}\"\n"
    )

    # ── nmcli ─────────────────────────────────────────────────────
    nmcli_cmds = [
        f'nmcli connection modify "{ssid}" 802-1x.eap tls',
        f'nmcli connection modify "{ssid}" 802-1x.identity "{identity}"',
        f'nmcli connection modify "{ssid}" 802-1x.ca-cert "{ca_cert}"',
        f'nmcli connection modify "{ssid}" 802-1x.client-cert "{client_cert}"',
        f'nmcli connection modify "{ssid}" 802-1x.private-key "{client_key}"',
        f'nmcli connection modify "{ssid}" 802-11-wireless.pmf 3',
    ]

    cmds = [
        "# ── 802.1X / EAP-TLS (Enterprise Certificate Auth) ──────",
        "# Each device authenticates with its own certificate.",
        "# Prevents Evil Twin attacks — attacker cannot copy hardware certs.",
        "# Requires RADIUS server (FreeRADIUS) for AP mode.",
        "",
    ]

    if mode == "ap":
        cmds += [
            "# ── Install FreeRADIUS ────────────────────────────────",
            "apt-get install -y freeradius 2>/dev/null || "
            "yum install -y freeradius 2>/dev/null || true",
            "",
            "# ── hostapd AP configuration with 802.1X/EAP-TLS ─────",
            "mkdir -p /etc/hostapd",
            f"cat > /etc/hostapd/hostapd.conf << '{marker}'",
            hostapd_conf,
            marker,
            "",
            "# ── EAP users file ────────────────────────────────────",
            f"cat > /etc/hostapd/eap_user << '{marker}_EAP'",
            f'"{identity or "*"}\tTLS\t""\n',
            f'"{marker}_EAP',
            "",
            "# ── FreeRADIUS reference configuration ────────────────",
            radius_conf,
            "",
            "# ── Enable and start services ─────────────────────────",
            "systemctl unmask hostapd 2>/dev/null || true",
            "systemctl enable hostapd 2>/dev/null || true",
            "systemctl restart hostapd 2>/dev/null || "
            f"hostapd -B /etc/hostapd/hostapd.conf 2>/dev/null || true",
            "systemctl enable freeradius 2>/dev/null || true",
            "systemctl restart freeradius 2>/dev/null || true",
            "",
            "# ── Verify 802.1X is active ───────────────────────────",
            f"hostapd_cli -i {iface} status 2>/dev/null | grep -i 'eap\\|802.1x\\|key_mgmt' || "
            "echo 'Verify 802.1X manually: hostapd_cli status'",
        ]
    else:
        nmcli_connect = (
            f'nmcli dev wifi connect "{ssid}" 2>/dev/null && ('
            + " && ".join(nmcli_cmds)
            + ') && echo "Connected via nmcli with EAP-TLS"'
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
            "# ── Ensure certificates exist ─────────────────────────",
            f"ls -la {ca_cert} {client_cert} {client_key} 2>/dev/null || "
            "echo 'WARNING: Certificate files not found! Generate or copy them first.'",
            "",
            "# ── Try nmcli first (NetworkManager) ──────────────────",
            f"{nmcli_connect} || (",
            "",
            "# ── Fallback: wpa_supplicant with EAP-TLS ────────────",
            wpa_file,
            ")",
            "",
            "# ── Verify EAP-TLS is active ──────────────────────────",
            f"wpa_cli -i {iface} status 2>/dev/null | grep -i 'eap\\|key_mgmt\\|pmf' || "
            f"iw dev {iface} info 2>/dev/null | grep -i 'wpa' || "
            "echo 'Verify EAP-TLS manually: wpa_cli status'",
        ]

    return cmds
