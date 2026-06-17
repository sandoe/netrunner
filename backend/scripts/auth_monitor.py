import time
import json
import os
import sys

LOG_FILE = "/tmp/netrunner-auth.log"
AUTH_LOG = "/var/log/auth.log"

def main():
    print(f"Starting Netrunner Auth Monitor... Logging to {LOG_FILE}")
    
    if not os.path.exists(AUTH_LOG):
        print(f"Cannot find {AUTH_LOG}")
        time.sleep(30)
        return
        
    try:
        with open(AUTH_LOG, "r") as f:
            f.seek(0, 2) # Go to the end of the file
            while True:
                line = f.readline()
                if not line:
                    time.sleep(1)
                    continue
                
                if "Failed password" in line or "session opened for user root" in line or "sudo:" in line:
                    entry = {
                        "timestamp": time.time(),
                        "event": "auth_alert",
                        "raw_log": line.strip()
                    }
                    with open(LOG_FILE, "a") as out:
                        out.write(json.dumps(entry) + "\n")
    except PermissionError:
        print("Permission denied reading auth.log. Run as root.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
