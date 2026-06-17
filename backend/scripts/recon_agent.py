#!/usr/bin/env python3
import time
import json
import urllib.request
import subprocess
import socket
import os

LOG_FILE = "/tmp/netrunner-recon.jsonl"

def get_wan_geo():
    try:
        req = urllib.request.Request("http://ip-api.com/json", headers={'User-Agent': 'NetrunnerRecon'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e)}

def get_arp_table():
    try:
        output = subprocess.check_output(["arp", "-a"], stderr=subprocess.DEVNULL).decode()
        lines = output.strip().split("\n")
        return [l for l in lines if l]
    except Exception:
        return []

def get_wifi_scan():
    try:
        # Prøver nmcli (NetworkManager) som ofte er tilgængeligt uden sudo på Linux
        output = subprocess.check_output(["nmcli", "-t", "-f", "SSID,BSSID,SIGNAL,SECURITY", "dev", "wifi"], stderr=subprocess.DEVNULL).decode()
        return output.strip().split("\n")
    except Exception:
        try:
            # Alternativ: iwlist
            output = subprocess.check_output(["iwlist", "scan"], stderr=subprocess.DEVNULL).decode()
            return output[:1000] # Truncate to avoid massive logs if not parsed
        except Exception:
            return "WiFi scan not available or requires root"

def get_active_connections():
    try:
        output = subprocess.check_output(["ss", "-tun"], stderr=subprocess.DEVNULL).decode()
        return [l for l in output.strip().split("\n") if "ESTAB" in l]
    except Exception:
        return []

def get_system_info():
    try:
        uptime = subprocess.check_output(["uptime", "-p"]).decode().strip()
        who = subprocess.check_output(["who"]).decode().strip()
        return {"uptime": uptime, "users": who.split("\n")}
    except Exception:
        return {}

def collect_recon():
    data = {
        "timestamp": time.time(),
        "hostname": socket.gethostname(),
        "geo": get_wan_geo(),
        "arp": get_arp_table(),
        "wifi": get_wifi_scan(),
        "connections": get_active_connections(),
        "sysinfo": get_system_info()
    }
    return data

def main():
    print(f"Starting Netrunner Recon Agent... Logging to {LOG_FILE}")
    while True:
        data = collect_recon()
        try:
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            print(f"Failed to write log: {e}")
        
        time.sleep(60)

if __name__ == "__main__":
    main()
