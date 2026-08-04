import subprocess
import time
import json
import sys
import os

LOG_FILE = "/tmp/netrunner-sniffer.log"


def main():
    print(f"Starting Netrunner Packet Sniffer... Logging to {LOG_FILE}")

    # Use tcpdump to capture DNS queries (port 53)
    cmd = ["tcpdump", "-l", "-n", "-i", "any", "port", "53"]

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
        )
        while True:
            line = process.stdout.readline()
            if not line:
                break

            line = line.strip()
            # Basic parsing of tcpdump DNS output
            # Example: 19:33:04.293 IP 192.168.1.10.53 > 192.168.1.50.45000: 1234 A? google.com.
            if " A? " in line or " AAAA? " in line:
                parts = line.split(" ")
                try:
                    ts = parts[0]
                    src = parts[2]
                    domain = parts[-1].rstrip(".")

                    entry = {
                        "timestamp": time.time(),
                        "time_str": ts,
                        "source": src,
                        "query": domain,
                    }

                    SERVER_URL = os.environ.get("ORCHESTRATOR_URL")
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
                except Exception:
                    pass
    except Exception as e:
        print(f"Failed to start sniffer: {e}")


if __name__ == "__main__":
    main()
