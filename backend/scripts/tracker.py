import time
import json
import urllib.request
import os
import sys

LOG_FILE = "/tmp/netrunner-location.log"

def get_location():
    try:
        req = urllib.request.Request("http://ip-api.com/json", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get('status') == 'success':
                return {
                    'lat': data['lat'],
                    'lon': data['lon'],
                    'city': data.get('city', ''),
                    'isp': data.get('isp', '')
                }
            else:
                return {"error": data.get("message", "API Error")}
    except Exception as e:
        return {"error": str(e)}

def main():
    print(f"Starting Netrunner Geolocation Tracker... Logging to {LOG_FILE}")
    while True:
        loc = get_location()
        if loc:
            entry = {
                "timestamp": time.time(),
                "location": loc
            }
            try:
                with open(LOG_FILE, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception as e:
                print(f"Failed to write log: {e}")
        
        # Flush stdout to ensure logs are visible if run via nohup/systemd
        sys.stdout.flush()
        time.sleep(60) # Log every 60 seconds

if __name__ == "__main__":
    main()
