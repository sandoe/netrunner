#!/usr/bin/env python3
"""
Netrunner Beacon  (deployed to the target node over SSH, runs as /tmp/netrunner_beacon.py)

Goal: be GENERIC. On startup it probes the node, tries to obtain *real* Wi-Fi CSI
from whatever hardware is present, and falls back to a synthetic stream if it
can't — always reporting honestly which path is active so the dashboard can show
REAL vs SIMULATED.

CSI source priority:
  1. Nexmon CSI  (Broadcom bcm43455c0 etc. — RPi 3B+/4 built-in Wi-Fi).
     Captures the UDP 5500 frames Nexmon emits and decodes the subcarriers.
  2. Intel iwlwifi debugfs  (detected and reported, extraction not implemented
     here — the raw format is card-specific; we report the capability instead).
  3. Synthetic fallback  (clearly labelled status=SYNTHETIC).

Derived metrics (motion / breathing / heart rate) are intentionally NOT computed
here — the server runs the real signal analysis on the amplitudes we send, so
the same analysis applies to real and synthetic streams alike.
"""

import socket
import time
import json
import random
import struct
import shutil
import subprocess
import glob

TARGET_IP = "{{TARGET_IP}}"
TARGET_PORT = {{TARGET_PORT}}
CSI_MODE = "{{CSI_MODE}}"        # AUTO | RAW_NEXMON | SYNTHETIC
SAMPLE_RATE = {{SAMPLE_RATE}}
NODE_ID = "{{NODE_ID}}"

NEXMON_UDP_PORT = 5500           # port Nexmon CSI broadcasts on
NUM_SUBCARRIERS = 64             # 20 MHz

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


# --------------------------------------------------------------------------- #
# Capability detection — what can this node actually do?
# --------------------------------------------------------------------------- #
def _run(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=5).decode(errors="ignore")
    except Exception:
        return ""


def detect_capabilities():
    caps = {
        "nexmon": False,
        "iwlwifi_csi": False,
        "monitor_mode": False,
        "tools": [],
        "interfaces": [],
        "wifi_chip": "unknown",
        "notes": [],
    }

    # Wi-Fi interfaces
    iw = _run(["iw", "dev"])
    for line in iw.splitlines():
        line = line.strip()
        if line.startswith("Interface "):
            caps["interfaces"].append(line.split(" ", 1)[1])
        if "type monitor" in line:
            caps["monitor_mode"] = True

    # Nexmon-related tooling
    for tool in ("nexutil", "makecsiparams", "tcpdump"):
        if shutil.which(tool):
            caps["tools"].append(tool)
    if "nexutil" in caps["tools"] or "makecsiparams" in caps["tools"]:
        caps["nexmon"] = True

    # dmesg / module hints for the chip
    dmesg = _run(["dmesg"]).lower()
    if "nexmon" in dmesg:
        caps["nexmon"] = True
        caps["notes"].append("nexmon firmware traces in dmesg")
    if "brcmfmac" in dmesg or glob.glob("/sys/module/brcmfmac"):
        caps["wifi_chip"] = "broadcom"
    if "bcm43455" in dmesg:
        caps["wifi_chip"] = "bcm43455c0"

    # Intel CSI debugfs
    intel_paths = glob.glob("/sys/kernel/debug/iwlwifi/*/iwlmvm/csi")
    if intel_paths:
        caps["iwlwifi_csi"] = True
        caps["wifi_chip"] = "intel"
        caps["notes"].append("Intel iwlwifi CSI debugfs present (extraction not implemented in beacon)")

    return caps


# --------------------------------------------------------------------------- #
# Nexmon CSI — capture + decode
# --------------------------------------------------------------------------- #
def try_setup_nexmon(caps):
    """Best-effort: ask Nexmon to start emitting CSI. Safe to fail."""
    if not caps["nexmon"]:
        return False
    iface = caps["interfaces"][0] if caps["interfaces"] else "wlan0"
    try:
        # Typical Nexmon CSI enable sequence (channel 36/80 is just a default;
        # adjust on the node if you need a specific channel).
        params = _run(["makecsiparams", "-c", "36/80", "-C", "1", "-N", "1"]).strip()
        if params:
            subprocess.run(["ifconfig", iface, "up"], stderr=subprocess.DEVNULL, timeout=5)
            subprocess.run(["nexutil", "-I" + iface, "-s500", "-b", "-l34", "-v" + params],
                           stderr=subprocess.DEVNULL, timeout=5)
            subprocess.run(["iw", "dev", iface, "interface", "add", "mon0", "type", "monitor"],
                           stderr=subprocess.DEVNULL, timeout=5)
            subprocess.run(["ifconfig", "mon0", "up"], stderr=subprocess.DEVNULL, timeout=5)
            return True
    except Exception:
        pass
    return False


def decode_nexmon_payload(data):
    """Decode a Nexmon CSI UDP payload (bcm43455c0, 20 MHz / 64 subcarriers).

    Layout: 2B magic, 1B rssi, 1B fc, 6B src mac, 2B seq, 2B core/spatial,
            2B chanspec, 2B chipver, then int16 (imag, real) pairs.
    Returns a list of subcarrier amplitudes, or None if it doesn't look valid.
    """
    header = 18
    if len(data) < header + NUM_SUBCARRIERS * 4:
        return None
    amps = []
    off = header
    for _ in range(NUM_SUBCARRIERS):
        imag, real = struct.unpack_from("<hh", data, off)
        off += 4
        amps.append(math_hypot(real, imag))
    # sanity: a valid CSI frame won't be all zeros
    if not any(a > 0 for a in amps):
        return None
    return amps


def math_hypot(a, b):
    return (a * a + b * b) ** 0.5


class NexmonCapture:
    def __init__(self):
        self.sock = None

    def open(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", NEXMON_UDP_PORT))
            s.setblocking(False)
            self.sock = s
            return True
        except Exception:
            self.sock = None
            return False

    def latest(self):
        """Drain the socket, return amplitudes from the most recent valid frame."""
        if not self.sock:
            return None
        amps = None
        for _ in range(64):  # drain backlog, keep newest
            try:
                data, _addr = self.sock.recvfrom(4096)
            except BlockingIOError:
                break
            except Exception:
                break
            decoded = decode_nexmon_payload(data)
            if decoded:
                amps = decoded
        return amps


# --------------------------------------------------------------------------- #
# Synthetic fallback
# --------------------------------------------------------------------------- #
def get_synthetic_amplitudes():
    amps = []
    base_noise = random.uniform(5.0, 15.0)
    for _ in range(NUM_SUBCARRIERS):
        amps.append(base_noise + random.uniform(-2.0, 2.0))
    if random.random() < 0.05:
        center = random.randint(10, 54)
        for i in range(NUM_SUBCARRIERS):
            dist = abs(i - center)
            if dist < 8:
                amps[i] += (8 - dist) * random.uniform(1.0, 3.0)
    return amps


# --------------------------------------------------------------------------- #
# Main loop
# --------------------------------------------------------------------------- #
def main():
    caps = detect_capabilities()

    nexmon = None
    want_real = CSI_MODE in ("AUTO", "RAW_NEXMON")
    if want_real and caps["nexmon"]:
        try_setup_nexmon(caps)
        nexmon = NexmonCapture()
        if not nexmon.open():
            nexmon = None

    print(f"Netrunner Beacon up. node={NODE_ID} target={TARGET_IP}:{TARGET_PORT} "
          f"mode={CSI_MODE} caps={json.dumps(caps)}")

    last_real_ts = 0.0
    while True:
        amps = None
        source = "synthetic"

        if nexmon is not None and CSI_MODE != "SYNTHETIC":
            real = nexmon.latest()
            if real:
                amps = real
                source = "nexmon"
                last_real_ts = time.time()

        if amps is None:
            if CSI_MODE == "RAW_NEXMON" and caps["nexmon"]:
                # caller forced hardware but none arrived yet
                status = "WAITING_NEXMON_CSI"
            elif caps["iwlwifi_csi"]:
                status = "IWLWIFI_DETECTED_FALLBACK_SYNTHETIC"
            elif caps["nexmon"]:
                status = "NEXMON_DETECTED_FALLBACK_SYNTHETIC"
            else:
                status = "NO_CSI_HARDWARE_SYNTHETIC"
            amps = get_synthetic_amplitudes()
            source = "synthetic"
        else:
            status = "REAL_CSI_STREAMING"

        payload = {
            "node_id": NODE_ID,
            "timestamp": time.time(),
            "amplitudes": amps,
            "csi_source": source,                 # "nexmon" | "synthetic"
            "capabilities": caps,                 # what this node supports
            "status": status,                     # honest, machine-readable
            "sample_rate": SAMPLE_RATE,
            "subcarriers": len(amps),
            # research-grade decoders are NOT real here:
            "decoders_simulated": True,
            "keystroke": "",
            "behavior": "",
            "radar_x": 0.5,
            "radar_y": 0.5,
            # motion / heart_rate / breathing_rate are computed server-side
            # from these amplitudes, so we don't fabricate them here.
        }

        sock.sendto(json.dumps(payload).encode(), (TARGET_IP, TARGET_PORT))
        time.sleep(1.0 / SAMPLE_RATE if SAMPLE_RATE > 0 else 0.1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Beacon terminated.")
