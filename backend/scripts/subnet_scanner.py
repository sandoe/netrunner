import os
import sys
import time
import json
import subprocess
import re

LOG_FILE = "/tmp/netrunner-scanner.json"

def get_arp_table():
    arp_devices = {}
    try:
        with open('/proc/net/arp', 'r') as f:
            lines = f.readlines()[1:]
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    ip = parts[0]
                    mac = parts[3]
                    if mac != "00:00:00:00:00:00":
                        arp_devices[ip] = mac
    except Exception:
        pass
    return arp_devices

def get_all_cidrs():
    cidrs = []
    try:
        output = subprocess.check_output("ip -o -f inet addr show", shell=True).decode()
        for line in output.split('\n'):
            if not line: continue
            parts = line.split()
            if len(parts) >= 4:
                iface = parts[1]
                ip_cidr = parts[3]
                if iface != "lo" and not iface.startswith("docker") and not iface.startswith("br-"):
                    cidrs.append(ip_cidr)
    except Exception:
        pass
    if not cidrs:
        cidrs.append("192.168.1.0/24")
    return list(set(cidrs))

def get_tailscale_devices():
    ts_devices = {}
    try:
        output = subprocess.check_output("tailscale status --json", shell=True, stderr=subprocess.DEVNULL).decode()
        data = json.loads(output)
        if "Peer" in data:
            for peer_key, peer_info in data["Peer"].items():
                ips = peer_info.get("TailscaleIPs", [])
                if ips:
                    ip = next((i for i in ips if "." in i), ips[0])
                    ts_devices[ip] = "TAILSCALE"
    except Exception:
        pass
    return ts_devices

def main():
    print(f"Starting Netrunner Subnet Scanner... Logging to {LOG_FILE}")
    while True:
        cidrs = get_all_cidrs()
        
        found_ips = set()
        
        # 1. Nmap fast ping sweep on all CIDRs
        try:
            if subprocess.run("which nmap", shell=True, stdout=subprocess.DEVNULL).returncode == 0:
                for cidr in cidrs:
                    try:
                        output = subprocess.check_output(f"nmap -sn -oG - {cidr}", shell=True, stderr=subprocess.DEVNULL).decode()
                        for line in output.split('\n'):
                            if "Status: Up" in line:
                                m = re.search(r"Host: ([\d\.]+)", line)
                                if m:
                                    found_ips.add(m.group(1))
                    except subprocess.CalledProcessError:
                        pass
            else:
                # Fallback to pure bash ping
                for cidr in cidrs:
                    if "/24" in cidr:
                        base_ip = ".".join(cidr.split('/')[0].split(".")[:3]) + "."
                        cmd = f"for i in {{1..254}}; do (ping -c 1 -W 1 {base_ip}$i >/dev/null 2>&1 &) ; done; sleep 1"
                        subprocess.run(cmd, shell=True, executable='/bin/bash')
        except Exception:
            pass

        # 2. Get ARP table for MAC addresses
        arp_devices = get_arp_table()
        for ip in arp_devices.keys():
            found_ips.add(ip)
            
        # 3. Get Tailscale devices explicitly
        ts_devices = get_tailscale_devices()
        for ip in ts_devices.keys():
            found_ips.add(ip)

        # 4. Compile final list
        devices = []
        for ip in found_ips:
            mac = arp_devices.get(ip)
            if not mac:
                mac = ts_devices.get(ip, "UNKNOWN")
            devices.append({"ip": ip, "mac": mac})

        # Save to file
        try:
            with open(LOG_FILE, "w") as f:
                json.dump({"timestamp": time.time(), "networks": cidrs, "devices": devices}, f)
        except Exception as e:
            print(f"Failed to write log: {e}")
        
        sys.stdout.flush()
        time.sleep(60) # Scan every 60 seconds

if __name__ == "__main__":
    main()
