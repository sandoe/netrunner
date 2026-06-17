import subprocess
import time
import json
import sys

LOG_FILE = "/tmp/netrunner-usb.log"

def main():
    print(f"Starting Netrunner USB Monitor... Logging to {LOG_FILE}")
    
    cmd = ["dmesg", "-w"]
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        while True:
            line = process.stdout.readline()
            if not line:
                break
            
            line = line.strip()
            if "usb" in line and "New USB device found" in line:
                entry = {
                    "timestamp": time.time(),
                    "event": "usb_connected",
                    "raw_log": line
                }
                with open(LOG_FILE, "a") as f:
                    f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"USB Monitor failed: {e}")

if __name__ == "__main__":
    main()
