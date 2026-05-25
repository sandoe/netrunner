"""Linux system management command generators.

Covers: systemd services, package management, user administration,
cron jobs, logging, sysctl, file operations, disk management.
"""
from __future__ import annotations

import shlex


def gen_service(name: str, action: str) -> list[str]:
    """Manage a systemd/OpenRC/SysV service."""
    valid = ("start", "stop", "restart", "reload", "enable", "disable", "status", "mask", "unmask")
    if action not in valid:
        raise ValueError(f"action must be one of {valid}")

    cmds = [f"# ── Service: {action} {name} ───────────────────────────────"]

    if action in ("enable", "disable", "mask", "unmask"):
        cmds += [
            f"systemctl {action} {name} 2>/dev/null && echo 'systemd: done' || "
            f"rc-update {'add' if action == 'enable' else 'del'} {name} default 2>/dev/null || "
            f"echo '(service manager not found)'"
        ]
    elif action == "status":
        cmds += [
            f"systemctl status {name} --no-pager 2>/dev/null || "
            f"service {name} status 2>/dev/null || "
            f"rc-service {name} status 2>/dev/null || "
            f"echo '(service {name} not found)'"
        ]
    else:
        cmds += [
            f"systemctl {action} {name} 2>/dev/null || "
            f"service {name} {action} 2>/dev/null || "
            f"rc-service {name} {action} 2>/dev/null || "
            f"echo '(service manager not found)'"
        ]
    return cmds


def gen_package(pkgs: list[str], action: str = "install", manager: str = "auto") -> list[str]:
    """Install, remove, or update packages."""
    if not pkgs:
        return ["echo '(no packages specified)'"]

    pkg_str = " ".join(shlex.quote(p) for p in pkgs)
    valid_actions = ("install", "remove", "purge", "update")
    if action not in valid_actions:
        raise ValueError(f"action must be one of {valid_actions}")

    cmds = [f"# ── Packages: {action} {pkg_str} ─────────────────────────"]

    if action == "update":
        return cmds + [
            "apt-get update -qq && apt-get upgrade -y 2>/dev/null || "
            "yum update -y 2>/dev/null || "
            "dnf update -y 2>/dev/null || "
            "pacman -Syu --noconfirm 2>/dev/null || "
            "apk upgrade 2>/dev/null || "
            "echo '(no package manager found)'"
        ]

    apt_action   = {"install": f"install -y {pkg_str}", "remove": f"remove -y {pkg_str}", "purge": f"purge -y {pkg_str}"}[action]
    yum_action   = {"install": f"install -y {pkg_str}", "remove": f"remove -y {pkg_str}", "purge": f"remove -y {pkg_str}"}[action]
    pacman_action= {"install": f"-S --noconfirm {pkg_str}", "remove": f"-R --noconfirm {pkg_str}", "purge": f"-Rns --noconfirm {pkg_str}"}[action]
    apk_action   = {"install": f"add {pkg_str}", "remove": f"del {pkg_str}", "purge": f"del {pkg_str}"}[action]

    if manager == "apt":
        cmds += [f"apt-get {apt_action}"]
    elif manager in ("yum", "dnf"):
        cmds += [f"{manager} {yum_action}"]
    elif manager == "pacman":
        cmds += [f"pacman {pacman_action}"]
    elif manager == "apk":
        cmds += [f"apk {apk_action}"]
    else:
        cmds += [
            f"apt-get {apt_action} 2>/dev/null || "
            f"yum {yum_action} 2>/dev/null || "
            f"dnf {yum_action} 2>/dev/null || "
            f"pacman {pacman_action} 2>/dev/null || "
            f"apk {apk_action} 2>/dev/null || "
            f"echo '(no package manager found)'"
        ]
    return cmds


def gen_user(cfg: dict) -> list[str]:
    """Create or modify a user account."""
    username = str(cfg.get("username", "")).strip()
    if not username:
        raise ValueError("username is required")

    action   = cfg.get("action", "create")
    password = str(cfg.get("password", "")).strip()
    groups   = [g.strip() for g in (cfg.get("groups") or []) if g.strip()]
    shell    = str(cfg.get("shell", "/bin/bash")).strip() or "/bin/bash"
    home     = str(cfg.get("home", "")).strip()
    comment  = str(cfg.get("comment", "")).strip()
    system   = bool(cfg.get("system", False))

    cmds = [f"# ── User: {action} {username} ────────────────────────────"]

    if action == "create":
        parts = ["useradd"]
        if system:
            parts.append("--system")
        parts += ["--create-home", "--shell", shell]
        if home:
            parts += ["--home-dir", home]
        if comment:
            parts += ["--comment", shlex.quote(comment)]
        if groups:
            parts += ["--groups", ",".join(groups)]
        parts.append(username)
        cmds.append(" ".join(parts))
        if password:
            cmds.append(f"echo {shlex.quote(username + ':' + password)} | chpasswd")
        cmds.append(f"id {username}")

    elif action == "modify":
        parts = ["usermod"]
        if shell:
            parts += ["--shell", shell]
        if home:
            parts += ["--home", home, "--move-home"]
        if comment:
            parts += ["--comment", shlex.quote(comment)]
        if groups:
            parts += ["--append", "--groups", ",".join(groups)]
        parts.append(username)
        cmds.append(" ".join(parts))
        if password:
            cmds.append(f"echo {shlex.quote(username + ':' + password)} | chpasswd")

    elif action == "delete":
        cmds += [
            f"userdel --remove {username} 2>/dev/null || userdel {username}",
        ]

    elif action == "passwd":
        if password:
            cmds.append(f"echo {shlex.quote(username + ':' + password)} | chpasswd")
        else:
            cmds.append(f"passwd --lock {username}")

    elif action == "sudo":
        cmds += [
            f"usermod --append --groups sudo {username} 2>/dev/null || "
            f"usermod --append --groups wheel {username} 2>/dev/null || "
            f"echo '{username} ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
        ]

    return cmds


def gen_cron(cfg: dict) -> list[str]:
    """Add, remove, or list cron jobs."""
    action   = cfg.get("action", "add")
    user     = str(cfg.get("user", "root")).strip() or "root"
    schedule = str(cfg.get("schedule", "")).strip()
    command  = str(cfg.get("command",  "")).strip()
    comment  = str(cfg.get("comment",  "")).strip()
    job_id   = str(cfg.get("id",       "")).strip()

    cmds = [f"# ── Cron: {action} ({user}) ──────────────────────────────"]

    if action == "list":
        cmds.append(f"crontab -l -u {user} 2>/dev/null || echo '(no crontab for {user})'")

    elif action == "add":
        if not (schedule and command):
            raise ValueError("schedule and command are required for cron add")
        line = f"{schedule} {command}"
        if comment:
            line = f"# {comment}\n{line}"
        if job_id:
            line = f"# ID:{job_id}\n{line}"
        cmds += [
            f"( crontab -l -u {user} 2>/dev/null; echo {shlex.quote(line)} ) | crontab -u {user} -",
            f"echo 'Cron job added for {user}'",
        ]

    elif action == "remove":
        if not (job_id or command):
            raise ValueError("id or command is required for cron remove")
        pattern = job_id if job_id else command
        cmds += [
            f"crontab -l -u {user} 2>/dev/null | grep -v {shlex.quote(pattern)} | crontab -u {user} -",
            f"echo 'Cron job removed for {user}'",
        ]

    elif action == "clear":
        cmds.append(f"crontab -r -u {user} 2>/dev/null || true; echo 'Crontab cleared for {user}'")

    return cmds


def gen_sysctl(params: list[dict], persist: bool = True) -> list[str]:
    """Set sysctl parameters, optionally persisting to /etc/sysctl.d/."""
    cmds = ["# ── sysctl parameters ───────────────────────────────────"]
    for p in params:
        key   = str(p.get("key",   "")).strip()
        value = str(p.get("value", "")).strip()
        if key and value:
            cmds.append(f"sysctl -w {key}={value}")

    if persist and params:
        conf_path = "/etc/sysctl.d/99-netrunner.conf"
        cmds.append(f"# ── Persist to {conf_path} ──")
        cmds.append(f"> {conf_path}")
        for p in params:
            key   = str(p.get("key",   "")).strip()
            value = str(p.get("value", "")).strip()
            if key and value:
                cmds.append(f"echo '{key}={value}' >> {conf_path}")
        cmds.append(f"sysctl --system 2>/dev/null || sysctl -p {conf_path}")
    return cmds


def gen_file_write(cfg: dict) -> list[str]:
    """Write a file with specified content, mode, and owner."""
    path    = str(cfg.get("path",    "")).strip()
    content = str(cfg.get("content", ""))
    mode    = str(cfg.get("mode",    "644")).strip() or "644"
    owner   = str(cfg.get("owner",   "")).strip()
    backup  = bool(cfg.get("backup", False))

    if not path:
        raise ValueError("path is required")

    marker = "__NETRUNNER_FILE_EOF__"
    cmds = [f"# ── Write file: {path} ─────────────────────────────────"]

    if backup:
        cmds.append(f"cp {shlex.quote(path)} {shlex.quote(path + '.netrunner_bak')} 2>/dev/null || true")

    parent = path.rsplit("/", 1)[0] if "/" in path else ""
    if parent:
        cmds.append(f"mkdir -p {shlex.quote(parent)}")

    cmds += [
        f"cat > {shlex.quote(path)} << '{marker}'\n{content}\n{marker}\nchmod {mode} {shlex.quote(path)}",
    ]
    if owner:
        cmds.append(f"chown {owner} {shlex.quote(path)}")
    cmds.append(f"echo 'File written: {path}'")
    return cmds


def gen_hostname(hostname: str, domain: str = "") -> list[str]:
    fqdn = f"{hostname}.{domain}" if domain else hostname
    return [
        "# ── Set hostname ────────────────────────────────────────────",
        f"hostnamectl set-hostname {shlex.quote(hostname)} 2>/dev/null || "
        f"echo {shlex.quote(hostname)} > /etc/hostname && hostname {shlex.quote(hostname)}",
        "sed -i '/127.0.1.1/d' /etc/hosts 2>/dev/null || true",
        f"echo '127.0.1.1 {fqdn} {hostname}' >> /etc/hosts",
        f"echo 'Hostname set to: {fqdn}'",
    ]


def gen_ssh_hardening(cfg: dict) -> list[str]:
    """Apply SSH daemon hardening settings."""
    port             = int(cfg.get("port", 22))
    root_login       = bool(cfg.get("permit_root_login", False))
    password_auth    = bool(cfg.get("password_auth", False))
    pubkey_auth      = bool(cfg.get("pubkey_auth", True))
    max_auth_tries   = int(cfg.get("max_auth_tries", 3))
    allowed_users    = cfg.get("allowed_users", [])

    root_val = "yes" if root_login else "prohibit-password"
    pw_val   = "yes" if password_auth else "no"
    pk_val   = "yes" if pubkey_auth else "no"

    cmds = [
        "# ── SSH daemon hardening ────────────────────────────────────",
        "cp /etc/ssh/sshd_config /etc/ssh/sshd_config.netrunner_bak 2>/dev/null || true",
        f"sed -i 's/^#*Port .*/Port {port}/' /etc/ssh/sshd_config",
        f"sed -i 's/^#*PermitRootLogin .*/PermitRootLogin {root_val}/' /etc/ssh/sshd_config",
        f"sed -i 's/^#*PasswordAuthentication .*/PasswordAuthentication {pw_val}/' /etc/ssh/sshd_config",
        f"sed -i 's/^#*PubkeyAuthentication .*/PubkeyAuthentication {pk_val}/' /etc/ssh/sshd_config",
        f"sed -i 's/^#*MaxAuthTries .*/MaxAuthTries {max_auth_tries}/' /etc/ssh/sshd_config",
        "grep -q '^Protocol ' /etc/ssh/sshd_config && sed -i 's/^Protocol .*/Protocol 2/' /etc/ssh/sshd_config || echo 'Protocol 2' >> /etc/ssh/sshd_config",
    ]
    if allowed_users:
        users = " ".join(allowed_users)
        cmds.append(f"grep -q '^AllowUsers' /etc/ssh/sshd_config && sed -i 's/^AllowUsers .*/AllowUsers {users}/' /etc/ssh/sshd_config || echo 'AllowUsers {users}' >> /etc/ssh/sshd_config")

    cmds += [
        "sshd -t && echo 'sshd config OK' || echo 'sshd config ERROR — check manually'",
        "systemctl reload sshd 2>/dev/null || service ssh reload 2>/dev/null || rc-service sshd reload 2>/dev/null || true",
    ]
    return cmds


def gen_authorized_key(cfg: dict) -> list[str]:
    """Add an SSH authorized key for a user."""
    user    = str(cfg.get("user",    "root")).strip() or "root"
    pub_key = str(cfg.get("pub_key", "")).strip()
    comment = str(cfg.get("comment", "")).strip()

    if not pub_key:
        raise ValueError("pub_key is required")

    home = f"/root" if user == "root" else f"/home/{user}"
    key_line = f"{pub_key}{' # ' + comment if comment else ''}"

    return [
        f"# ── Authorized key for {user} ────────────────────────────",
        f"mkdir -p {home}/.ssh",
        f"chmod 700 {home}/.ssh",
        f"touch {home}/.ssh/authorized_keys",
        f"chmod 600 {home}/.ssh/authorized_keys",
        f"grep -qF {shlex.quote(pub_key)} {home}/.ssh/authorized_keys || "
        f"echo {shlex.quote(key_line)} >> {home}/.ssh/authorized_keys",
        f"chown -R {user}:{user} {home}/.ssh 2>/dev/null || true",
        f"echo 'Key added for {user}'",
    ]


def gen_systemd_service_unit(cfg: dict) -> list[str]:
    """Create and enable a custom systemd service unit."""
    name        = str(cfg.get("name",        "")).strip()
    description = str(cfg.get("description", name)).strip()
    exec_start  = str(cfg.get("exec_start",  "")).strip()
    after       = str(cfg.get("after",       "network.target")).strip()
    restart     = str(cfg.get("restart",     "on-failure")).strip()
    user        = str(cfg.get("user",        "root")).strip()
    working_dir = str(cfg.get("working_dir", "")).strip()
    env_file    = str(cfg.get("env_file",    "")).strip()
    enable      = bool(cfg.get("enable",     True))

    if not (name and exec_start):
        raise ValueError("name and exec_start are required")

    unit_path = f"/etc/systemd/system/{name}.service"
    lines = [
        "[Unit]",
        f"Description={description}",
        f"After={after}",
        "",
        "[Service]",
        f"User={user}",
        f"ExecStart={exec_start}",
        f"Restart={restart}",
        "RestartSec=5",
    ]
    if working_dir:
        lines.append(f"WorkingDirectory={working_dir}")
    if env_file:
        lines.append(f"EnvironmentFile={env_file}")
    lines += ["", "[Install]", "WantedBy=multi-user.target"]

    marker = "__NETRUNNER_UNIT_EOF__"
    lines_str = "\n".join(lines)
    cmds = [
        f"# ── Systemd unit: {name} ────────────────────────────────",
        f"cat > {shlex.quote(unit_path)} << '{marker}'\n{lines_str}\n{marker}",
        "systemctl daemon-reload",
    ]
    if enable:
        cmds += [
            f"systemctl enable {name}",
            f"systemctl start {name}",
            f"systemctl status {name} --no-pager",
        ]
    return cmds


def gen_remote_desktop(cfg: dict) -> list[str]:
    """Install, configure, start, or uninstall RDP/VNC remote desktop servers or Remmina client."""
    action = str(cfg.get("action", "install")).strip()
    protocol = str(cfg.get("protocol", "rdp")).lower().strip()
    username = str(cfg.get("username", "root")).strip() or "root"
    password = str(cfg.get("password", "")).strip()
    desktop = str(cfg.get("desktop", "xfce")).lower().strip()
    resolution = str(cfg.get("resolution", "1280x720")).strip() or "1280x720"
    
    if protocol == "remmina":
        cmds = [f"# ── Remote Desktop Client: {action.upper()} REMMINA ───────────────────"]
        if action == "uninstall":
            cmds += [
                "# Purge packages",
                "apt-get purge -y remmina remmina-plugin-rdp remmina-plugin-vnc 2>/dev/null || true",
                "apk del remmina 2>/dev/null || true",
                "echo 'Remmina client uninstalled successfully.'"
            ]
        else:
            cmds += [
                "# Install Remmina client packages",
                "apt-get update -qq && apt-get install -y remmina remmina-plugin-rdp remmina-plugin-vnc dbus-x11 2>/dev/null || "
                "apk add remmina 2>/dev/null || "
                "echo 'Package installation complete/skipped'",
                "echo 'Remmina client configuration applied!'"
            ]
        return cmds

    # Default ports
    default_port = 3389 if protocol == "rdp" else 5901
    try:
        port = int(cfg.get("port", default_port))
    except (ValueError, TypeError):
        port = default_port

    cmds = [f"# ── Remote Desktop: {action.upper()} {protocol.upper()} on port {port} ───────────────────"]

    if action == "uninstall":
        # Firewall removal
        cmds += [
            f"ufw delete allow {port}/tcp 2>/dev/null || ufw delete allow {port} 2>/dev/null || true",
            f"iptables -D INPUT -p tcp --dport {port} -j ACCEPT 2>/dev/null || true"
        ]
        
        if protocol == "rdp":
            cmds += [
                "# Stop and disable services",
                "systemctl stop xrdp xrdp-sesman 2>/dev/null || true",
                "systemctl disable xrdp xrdp-sesman 2>/dev/null || true",
                "rc-service xrdp stop 2>/dev/null || true",
                "rc-update del xrdp default 2>/dev/null || true",
                "# Purge packages",
                "apt-get purge -y xrdp xorgxrdp 2>/dev/null || true",
                "apk del xrdp 2>/dev/null || true",
                "# Remove config files",
                "rm -rf /etc/xrdp",
                f"rm -f /home/{username}/.xsession /home/{username}/.xsessionrc /root/.xsession /root/.xsessionrc 2>/dev/null",
                "echo 'RDP uninstalled successfully.'"
            ]
        else:  # vnc
            display_num = max(1, port - 5900)
            home_dir = "/root" if username == "root" else f"/home/{username}"
            cmds += [
                "# Kill active VNC servers",
                f"su - {username} -c \"vncserver -kill :{display_num} 2>/dev/null\" || pkill Xvnc 2>/dev/null || true",
                "# Purge packages",
                "apt-get purge -y tightvncserver tigervnc-standalone-server 2>/dev/null || true",
                "apk del tigervnc 2>/dev/null || true",
                "# Remove VNC configurations",
                f"rm -rf {home_dir}/.vnc",
                "echo 'VNC uninstalled successfully.'"
            ]
        return cmds

    # --- INSTALL/CONFIGURE ACTION ---
    
    # 1. User Password setup (critical for remote login authentication)
    if password:
        cmds += [
            "# Setup user password for authentication",
            f"echo {shlex.quote(username + ':' + password)} | chpasswd"
        ]

    # 2. Desktop Environment selection & packages
    deb_desktop_pkgs = []
    apk_desktop_pkgs = []
    if desktop == "xfce":
        deb_desktop_pkgs = ["xfce4", "xfce4-goodies"]
        apk_desktop_pkgs = ["xfce4", "xfce4-terminal"]
    elif desktop == "lxde":
        deb_desktop_pkgs = ["lxde-core"]
        apk_desktop_pkgs = ["lxde-desktop"]

    # 3. Protocol packages & configuration
    home_dir = "/root" if username == "root" else f"/home/{username}"
    desktop_start_cmd = "startxfce4" if desktop == "xfce" else ("startlxde" if desktop == "lxde" else "xterm")

    if protocol == "rdp":
        # Installation
        deb_pkgs = ["xrdp", "xorgxrdp", "dbus-x11"] + deb_desktop_pkgs
        apk_pkgs = ["xrdp", "dbus"] + apk_desktop_pkgs
        
        deb_pkg_str = " ".join(deb_pkgs)
        apk_pkg_str = " ".join(apk_pkgs)
        
        cmds += [
            "# Install Remote Desktop packages",
            f"apt-get update -qq && apt-get install -y {deb_pkg_str} 2>/dev/null || "
            f"apk add {apk_pkg_str} 2>/dev/null || "
            f"echo 'Package installation complete/skipped'"
        ]
        
        # Configure Port
        cmds += [
            "# Configure RDP port",
            f"if [ -f /etc/xrdp/xrdp.ini ]; then sed -i 's/^port=3389/port={port}/' /etc/xrdp/xrdp.ini; fi"
        ]

        # Configure session startup for the user
        session_content = f"#!/bin/sh\nexport DISPLAY=:1\nexport DBUS_SESSION_BUS_ADDRESS=\nexec {desktop_start_cmd}"
        marker = "__NETRUNNER_RDP_EOF__"
        
        cmds += [
            "# Setup user .xsession file",
            f"mkdir -p {home_dir}",
            f"cat > {home_dir}/.xsession << '{marker}'\n{session_content}\n{marker}",
            f"cp {home_dir}/.xsession {home_dir}/.xsessionrc 2>/dev/null || true",
            f"chmod +x {home_dir}/.xsession {home_dir}/.xsessionrc 2>/dev/null || true",
            f"chown -R {username}:{username} {home_dir}/.xsession {home_dir}/.xsessionrc 2>/dev/null || true"
        ]

        # Start services
        cmds += [
            "# Start RDP services",
            "systemctl daemon-reload 2>/dev/null || true",
            "systemctl enable xrdp xrdp-sesman 2>/dev/null && systemctl restart xrdp xrdp-sesman 2>/dev/null || "
            "rc-update add xrdp default 2>/dev/null && rc-service xrdp restart 2>/dev/null || "
            "echo '(failed to start system xrdp service)'"
        ]

    else:  # protocol == "vnc"
        # Installation
        deb_pkgs = ["tightvncserver", "dbus-x11"] + deb_desktop_pkgs
        apk_pkgs = ["tigervnc", "dbus"] + apk_desktop_pkgs
        
        deb_pkg_str = " ".join(deb_pkgs)
        apk_pkg_str = " ".join(apk_pkgs)

        cmds += [
            "# Install VNC packages",
            f"apt-get update -qq && (apt-get install -y {deb_pkg_str} || apt-get install -y tigervnc-standalone-server dbus-x11 {deb_pkg_str}) 2>/dev/null || "
            f"apk add {apk_pkg_str} 2>/dev/null || "
            f"echo 'Package installation complete/skipped'"
        ]

        # VNC Passwd encryption & config directory setup
        if password:
            vnc_passwd_setup = (
                f"mkdir -p {home_dir}/.vnc && "
                f"chmod 700 {home_dir}/.vnc && "
                f"echo {shlex.quote(password)} | vncpasswd -f > {home_dir}/.vnc/passwd 2>/dev/null || "
                f"(echo {shlex.quote(password)}; echo {shlex.quote(password)}) | vncpasswd {home_dir}/.vnc/passwd 2>/dev/null && "
                f"chmod 600 {home_dir}/.vnc/passwd && "
                f"chown -R {username}:{username} {home_dir}/.vnc 2>/dev/null || true"
            )
        else:
            # Fallback password is "netrunner" if none given
            vnc_passwd_setup = (
                f"mkdir -p {home_dir}/.vnc && "
                f"chmod 700 {home_dir}/.vnc && "
                f"echo 'netrunner' | vncpasswd -f > {home_dir}/.vnc/passwd 2>/dev/null || "
                f"(echo 'netrunner'; echo 'netrunner') | vncpasswd {home_dir}/.vnc/passwd 2>/dev/null && "
                f"chmod 600 {home_dir}/.vnc/passwd && "
                f"chown -R {username}:{username} {home_dir}/.vnc 2>/dev/null || true"
            )

        # Startup file
        xstartup_content = (
            f"#!/bin/sh\n"
            f"unset SESSION_MANAGER\n"
            f"unset DBUS_SESSION_BUS_ADDRESS\n"
            f"xrdb $HOME/.Xresources 2>/dev/null\n"
            f"xsetroot -solid grey\n"
            f"dbus-launch --exit-with-session {desktop_start_cmd} &\n"
        )
        xstartup_marker = "__NETRUNNER_VNC_START__"

        cmds += [
            "# Setup VNC configurations",
            vnc_passwd_setup,
            f"cat > {home_dir}/.vnc/xstartup << '{xstartup_marker}'\n{xstartup_content}\n{xstartup_marker}",
            f"chmod +x {home_dir}/.vnc/xstartup",
            f"chown -R {username}:{username} {home_dir}/.vnc 2>/dev/null || true"
        ]

        # Run/daemonize VNC server on display mapping (display = port - 5900)
        display_num = max(1, port - 5900)
        
        cmds += [
            "# Start VNC server instance",
            f"su - {username} -c \"vncserver -kill :{display_num} 2>/dev/null || true\"",
            f"su - {username} -c \"vncserver :{display_num} -geometry {resolution} -localhost no 2>/dev/null || vncserver :{display_num} -geometry {resolution}\""
        ]

    # 4. Open connection ports in Firewall
    cmds += [
        "# Adjust Firewall rules to allow connections",
        f"ufw allow {port}/tcp 2>/dev/null || ufw allow {port} 2>/dev/null || true",
        f"iptables -I INPUT -p tcp --dport {port} -j ACCEPT 2>/dev/null || true"
    ]

    cmds.append("echo 'Remote Desktop configuration applied!'")
    return cmds

