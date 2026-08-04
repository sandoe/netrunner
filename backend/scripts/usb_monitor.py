import subprocess
import time
import json
import sys

LOG_FILE = "/tmp/netrunner-usb.log"


def main():
    print(f"Starting Netrunner USB Monitor... Logging to {LOG_FILE}")

    cmd = ["dmesg", "-w"]
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
        )
        while True:
            line = process.stdout.readline()
            if not line:
                break

            line = line.strip()
            if "usb" in line and "New USB device found" in line:
                entry = {
                    "timestamp": time.time(),
                    "event": "usb_connected",
                    "raw_log": line,
                }
                SERVER_URL = __import__("os").environ.get("ORCHESTRATOR_URL")
                if SERVER_URL:
                    try:
                        import urllib.request

                        req = urllib.request.Request(
                            f"{SERVER_URL.rstrip('/')}/api/telemetry",
                            data=json.dumps(entry).encode("utf-8"),
                            headers={"Content-Type": "application/json"},
                        )
                        urllib.request.urlopen(req, timeout=3)
                    except Exception:
                        pass
                with open(LOG_FILE, "a") as f:
                    f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"USB Monitor failed: {e}")


if __name__ == "__main__":
    main()
