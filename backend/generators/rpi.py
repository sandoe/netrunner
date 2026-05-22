"""Raspberry Pi specific command generators.

Covers: /boot/config.txt, GPIO, I2C/SPI, camera, overclocking,
temperature, watchdog, WiFi, Bluetooth, and more.
"""
from __future__ import annotations

import shlex


# /boot/config.txt lives here on Bookworm+, older distros use /boot/config.txt
CONFIG_TXT = "/boot/firmware/config.txt"
CONFIG_TXT_LEGACY = "/boot/config.txt"


def _config_path_cmd() -> str:
    return (
        f"[ -f {CONFIG_TXT} ] && CONFIG={CONFIG_TXT} || CONFIG={CONFIG_TXT_LEGACY}"
    )


def gen_rpi_config_set(key: str, value: str, comment: str = "") -> list[str]:
    """Set a /boot/config.txt parameter, or add it if missing."""
    cmds = [
        f"# ── RPi config: {key}={value} ───────────────────────────────",
        _config_path_cmd(),
        f"cp $CONFIG ${{CONFIG}}.netrunner_bak 2>/dev/null || true",
        f"grep -q '^{key}=' $CONFIG && "
        f"sed -i 's|^{key}=.*|{key}={value}|' $CONFIG || "
        f"echo '{key}={value}' >> $CONFIG",
        f"echo 'Set {key}={value} in $CONFIG'",
        "echo '(Reboot required for changes to take effect)'",
    ]
    return cmds


def gen_rpi_config_section(entries: list[dict], section: str = "") -> list[str]:
    """Write multiple config.txt entries, optionally inside a [section]."""
    if not entries:
        return ["echo '(no config entries)'"]

    cmds = [
        "# ── RPi config.txt bulk update ──────────────────────────────",
        _config_path_cmd(),
        "cp $CONFIG ${CONFIG}.netrunner_bak 2>/dev/null || true",
    ]

    if section:
        cmds.append(f"# Section: [{section}]")
        cmds.append(f"grep -q '^\\[{section}\\]' $CONFIG || echo '[{section}]' >> $CONFIG")

    for e in entries:
        key   = str(e.get("key",   "")).strip()
        value = str(e.get("value", "")).strip()
        if not (key and value):
            continue
        cmds.append(
            f"grep -q '^{key}=' $CONFIG && "
            f"sed -i 's|^{key}=.*|{key}={value}|' $CONFIG || "
            f"echo '{key}={value}' >> $CONFIG"
        )

    cmds += [
        "echo 'config.txt updated'",
        "echo '(Reboot required for changes to take effect)'",
    ]
    return cmds


def gen_rpi_gpio(pin: int, mode: str, value: str | None = None) -> list[str]:
    """Set GPIO pin mode (in/out/up/down/alt0..5) and optional value."""
    cmds = [f"# ── GPIO pin {pin}: mode={mode}" + (f" value={value}" if value is not None else "") + " ─"]
    if mode in ("in", "out"):
        cmds += [
            f"raspi-gpio set {pin} {mode.upper()} 2>/dev/null || "
            f"gpio mode {pin} {'in' if mode == 'in' else 'out'} 2>/dev/null || "
            f"( echo {pin} > /sys/class/gpio/export 2>/dev/null || true; "
            f"  echo {mode} > /sys/class/gpio/gpio{pin}/direction )",
        ]
        if value is not None and mode == "out":
            v = "1" if str(value) in ("1", "high", "on", "true") else "0"
            cmds += [
                f"raspi-gpio set {pin} {'dh' if v == '1' else 'dl'} 2>/dev/null || "
                f"gpio write {pin} {v} 2>/dev/null || "
                f"echo {v} > /sys/class/gpio/gpio{pin}/value",
            ]
    elif mode in ("up", "down", "tri"):
        pud = {"up": "PU", "down": "PD", "tri": "NP"}[mode]
        cmds.append(f"raspi-gpio set {pin} {pud} 2>/dev/null || gpio mode {pin} {mode} 2>/dev/null || true")
    elif mode.startswith("alt"):
        cmds.append(f"raspi-gpio set {pin} {mode.upper()} 2>/dev/null || gpio mode {pin} {mode} 2>/dev/null || true")

    cmds.append(f"raspi-gpio get {pin} 2>/dev/null || gpio read {pin} 2>/dev/null || cat /sys/class/gpio/gpio{pin}/value 2>/dev/null || true")
    return cmds


def gen_rpi_gpio_read_all() -> list[str]:
    return [
        "# ── GPIO: read all pins ─────────────────────────────────────",
        "raspi-gpio get 2>/dev/null || gpio readall 2>/dev/null || "
        "for i in $(seq 0 27); do echo -n \"GPIO $i: \"; cat /sys/class/gpio/gpio$i/value 2>/dev/null || echo 'unexported'; done",
    ]


def gen_rpi_i2c(action: str = "scan", bus: int = 1, addr: str = "", reg: str = "", value: str = "") -> list[str]:
    """I2C operations: scan, read, write."""
    cmds = [f"# ── I2C bus {bus}: {action} ─────────────────────────────"]

    if action == "scan":
        cmds += [
            f"i2cdetect -l 2>/dev/null",
            f"i2cdetect -y {bus} 2>/dev/null || echo '(i2cdetect not available — install i2c-tools)'",
        ]
    elif action == "read" and addr and reg:
        cmds.append(f"i2cget -y {bus} {addr} {reg} 2>/dev/null || echo '(i2cget failed)'")
    elif action == "write" and addr and reg and value:
        cmds.append(f"i2cset -y {bus} {addr} {reg} {value} 2>/dev/null || echo '(i2cset failed)'")
    elif action == "dump" and addr:
        cmds.append(f"i2cdump -y {bus} {addr} 2>/dev/null || echo '(i2cdump failed)'")

    return cmds


def gen_rpi_spi(enable: bool = True) -> list[str]:
    cmds = [
        f"# ── {'Enable' if enable else 'Disable'} SPI ───────────────────────────────────────",
        _config_path_cmd(),
    ]
    if enable:
        cmds += [
            "grep -q '^dtparam=spi=on' $CONFIG && echo 'SPI already enabled' || "
            "( sed -i 's/^dtparam=spi=.*//' $CONFIG; echo 'dtparam=spi=on' >> $CONFIG )",
            "modprobe spi-bcm2835 2>/dev/null || true",
            "ls /dev/spidev* 2>/dev/null || echo '(spidev not yet visible — reboot may be needed)'",
        ]
    else:
        cmds += [
            "sed -i 's/^dtparam=spi=on.*/dtparam=spi=off/' $CONFIG",
            "echo 'SPI disabled (reboot to take effect)'",
        ]
    return cmds


def gen_rpi_i2c_enable(bus: int = 1, enable: bool = True) -> list[str]:
    cmds = [
        f"# ── {'Enable' if enable else 'Disable'} I2C bus {bus} ─────────────────────────────",
        _config_path_cmd(),
    ]
    if enable:
        cmds += [
            "grep -q '^dtparam=i2c_arm=on' $CONFIG && echo 'I2C already enabled' || "
            "( sed -i 's/^dtparam=i2c_arm=.*//' $CONFIG; echo 'dtparam=i2c_arm=on' >> $CONFIG )",
            "modprobe i2c-bcm2835 2>/dev/null || modprobe i2c-dev 2>/dev/null || true",
            f"ls /dev/i2c-{bus} 2>/dev/null || echo '(i2c-{bus} not yet visible — reboot may be needed)'",
        ]
    else:
        cmds += [
            "sed -i 's/^dtparam=i2c_arm=on.*/dtparam=i2c_arm=off/' $CONFIG",
            "echo 'I2C disabled (reboot to take effect)'",
        ]
    return cmds


def gen_rpi_camera(enable: bool = True, legacy: bool = False) -> list[str]:
    cmds = [
        f"# ── {'Enable' if enable else 'Disable'} camera ─────────────────────────────────────",
        _config_path_cmd(),
    ]
    if enable:
        if legacy:
            cmds += [
                "grep -q '^start_x=1' $CONFIG && echo 'Legacy camera already enabled' || "
                "( sed -i '/^start_x=/d;/^gpu_mem=/d' $CONFIG; echo 'start_x=1' >> $CONFIG; echo 'gpu_mem=128' >> $CONFIG )",
                "echo 'Legacy camera enabled (gpu_mem=128, start_x=1)'",
            ]
        else:
            cmds += [
                "grep -q '^camera_auto_detect=1' $CONFIG || echo 'camera_auto_detect=1' >> $CONFIG",
                "vcgencmd get_camera 2>/dev/null || libcamera-hello --list-cameras 2>/dev/null || echo '(camera check tools not available)'",
            ]
    else:
        cmds += [
            "sed -i 's/^start_x=.*/start_x=0/' $CONFIG 2>/dev/null || true",
            "sed -i 's/^camera_auto_detect=.*/camera_auto_detect=0/' $CONFIG 2>/dev/null || true",
            "echo 'Camera disabled (reboot to take effect)'",
        ]
    return cmds


def gen_rpi_overclock(cfg: dict) -> list[str]:
    """Apply overclocking settings to config.txt."""
    arm_freq  = str(cfg.get("arm_freq",  "")).strip()
    gpu_freq  = str(cfg.get("gpu_freq",  "")).strip()
    over_volt = str(cfg.get("over_voltage", "")).strip()
    governor  = str(cfg.get("governor",  "performance")).strip()
    force_turbo = bool(cfg.get("force_turbo", False))

    cmds = [
        "# ── RPi overclocking ─────────────────────────────────────────",
        _config_path_cmd(),
        "cp $CONFIG ${CONFIG}.netrunner_bak 2>/dev/null || true",
    ]

    for key, val in [("arm_freq", arm_freq), ("gpu_freq", gpu_freq), ("over_voltage", over_volt)]:
        if val:
            cmds.append(
                f"grep -q '^{key}=' $CONFIG && sed -i 's|^{key}=.*|{key}={val}|' $CONFIG || echo '{key}={val}' >> $CONFIG"
            )

    if force_turbo:
        cmds.append("grep -q '^force_turbo=' $CONFIG && sed -i 's|^force_turbo=.*|force_turbo=1|' $CONFIG || echo 'force_turbo=1' >> $CONFIG")

    if governor:
        cmds += [
            f"echo {shlex.quote(governor)} | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null || true",
            f"echo 'CPU governor set to {governor}'",
        ]

    cmds.append("echo 'Overclock settings applied (reboot required)'")
    return cmds


def gen_rpi_temperature() -> list[str]:
    return [
        "# ── RPi temperature & throttle ──────────────────────────────",
        "vcgencmd measure_temp 2>/dev/null || cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{printf \"temp=%.1f'C\\n\", $1/1000}'",
        "vcgencmd get_throttled 2>/dev/null || true",
        "vcgencmd measure_volts core 2>/dev/null || true",
        "uptime",
    ]


def gen_rpi_wifi(cfg: dict) -> list[str]:
    """Configure WiFi using wpa_supplicant or nmcli."""
    ssid     = str(cfg.get("ssid",    "")).strip()
    password = str(cfg.get("password","")).strip()
    country  = str(cfg.get("country", "DK")).strip().upper()
    hidden   = bool(cfg.get("hidden", False))

    if not ssid:
        raise ValueError("ssid is required")

    # wpa_supplicant approach (works on most RPi distros)
    scan_ssid = "scan_ssid=1\n" if hidden else ""
    wpa_conf = (
        f'country={country}\n'
        f'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n'
        f'update_config=1\n\n'
        f'network={{\n'
        f'    ssid="{ssid}"\n'
        f'{scan_ssid}'
        + (f'    psk="{password}"\n' if password else '    key_mgmt=NONE\n')
        + f'}}'
    )

    marker = "__NETRUNNER_WPA_EOF__"
    cmds = [
        f"# ── WiFi: connect to {ssid} ─────────────────────────────────",
        "# Try nmcli first (NetworkManager), fall back to wpa_supplicant",
        f"nmcli dev wifi connect {shlex.quote(ssid)}" +
        (f" password {shlex.quote(password)}" if password else "") +
        f" 2>/dev/null && echo 'Connected via nmcli' || (\n"
        f"cat > /etc/wpa_supplicant/wpa_supplicant.conf << '{marker}'\n"
        f"{wpa_conf}\n"
        f"{marker}\n"
        f"wpa_cli -i wlan0 reconfigure 2>/dev/null || wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf 2>/dev/null || true\n"
        f"sleep 3\n"
        f"ip addr show wlan0 | grep 'inet '\n"
        f")"
    ]
    return cmds


def gen_rpi_bluetooth(enable: bool = True) -> list[str]:
    cmds = [f"# ── {'Enable' if enable else 'Disable'} Bluetooth ─────────────────────────────"]
    if enable:
        cmds += [
            "systemctl enable bluetooth 2>/dev/null && systemctl start bluetooth 2>/dev/null || "
            "rfkill unblock bluetooth 2>/dev/null || true",
            "bluetoothctl power on 2>/dev/null || true",
            "hciconfig hci0 up 2>/dev/null || true",
            "bluetoothctl show 2>/dev/null || hciconfig 2>/dev/null || echo '(bluetooth tools not available)'",
        ]
    else:
        cmds += [
            "systemctl stop bluetooth 2>/dev/null || true",
            "systemctl disable bluetooth 2>/dev/null || true",
            "rfkill block bluetooth 2>/dev/null || hciconfig hci0 down 2>/dev/null || true",
            "echo 'Bluetooth disabled'",
        ]
    return cmds


def gen_rpi_watchdog(timeout: int = 14, action: str = "enable") -> list[str]:
    cmds = [f"# ── RPi watchdog: {action} (timeout={timeout}s) ─────────────────"]
    if action == "enable":
        cmds += [
            _config_path_cmd(),
            "grep -q '^dtparam=watchdog=on' $CONFIG || echo 'dtparam=watchdog=on' >> $CONFIG",
            "modprobe bcm2835_wdt 2>/dev/null || true",
            "apt-get install -y watchdog 2>/dev/null || apk add watchdog 2>/dev/null || true",
            f"sed -i 's|^watchdog-timeout.*|watchdog-timeout = {timeout}|' /etc/watchdog.conf 2>/dev/null || "
            f"echo 'watchdog-timeout = {timeout}' >> /etc/watchdog.conf",
            "grep -q '^watchdog-device' /etc/watchdog.conf || echo 'watchdog-device = /dev/watchdog' >> /etc/watchdog.conf",
            "systemctl enable watchdog 2>/dev/null && systemctl start watchdog 2>/dev/null || "
            "service watchdog start 2>/dev/null || true",
            "echo 'Watchdog enabled'",
        ]
    else:
        cmds += [
            "systemctl stop watchdog 2>/dev/null || service watchdog stop 2>/dev/null || true",
            "systemctl disable watchdog 2>/dev/null || true",
            "echo 'Watchdog disabled'",
        ]
    return cmds


def gen_rpi_info() -> list[str]:
    """Gather RPi system information."""
    return [
        "# ── Raspberry Pi system info ────────────────────────────────",
        "uname -a",
        "cat /proc/cpuinfo | grep -E 'Model|Hardware|Revision|Serial'",
        "cat /etc/os-release 2>/dev/null | head -5",
        "vcgencmd measure_temp 2>/dev/null || cat /sys/class/thermal/thermal_zone0/temp | awk '{printf \"temp=%.1f C\\n\", $1/1000}' 2>/dev/null",
        "vcgencmd get_throttled 2>/dev/null || true",
        "vcgencmd measure_clock arm 2>/dev/null || true",
        "free -h",
        "df -h /",
        "ip -4 addr show | grep inet",
    ]
