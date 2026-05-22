import random
import time
import asyncio
import json
import urllib.request
from typing import Dict, Any, List

from .db import load_settings_db, load_nodes_db
from .state import global_state

# Simple list of random coordinates (latitude, longitude) for major cities globally
# This simulates geo-IP locations.
CITIES = [
    {"name": "Beijing", "lat": 39.9042, "lng": 116.4074},
    {"name": "Moscow", "lat": 55.7558, "lng": 37.6173},
    {"name": "New York", "lat": 40.7128, "lng": -74.0060},
    {"name": "London", "lat": 51.5074, "lng": -0.1278},
    {"name": "Tokyo", "lat": 35.6762, "lng": 139.6503},
    {"name": "Tehran", "lat": 35.6892, "lng": 51.3890},
    {"name": "Seoul", "lat": 37.5665, "lng": 126.9780},
    {"name": "Pyongyang", "lat": 39.0392, "lng": 125.7625},
    {"name": "San Francisco", "lat": 37.7749, "lng": -122.4194},
    {"name": "Frankfurt", "lat": 50.1109, "lng": 8.6821},
    {"name": "Amsterdam", "lat": 52.3676, "lng": 4.9041},
    {"name": "São Paulo", "lat": -23.5505, "lng": -46.6333}
]

THREAT_TYPES = [
    "DDoS Amplification",
    "SSH Brute Force",
    "SQL Injection Attempt",
    "Ransomware Beacon",
    "Zero-Day Exploit",
    "Port Scan (Nmap)",
    "IoT Botnet Activity"
]

GEOLOC_CACHE = {}

def is_private_ip(ip: str) -> bool:
    if ip in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        parts = [int(x) for x in ip.split('.')]
        if len(parts) != 4:
            return False
        if parts[0] == 10:
            return True
        if parts[0] == 172 and (16 <= parts[1] <= 31):
            return True
        if parts[0] == 192 and parts[1] == 168:
            return True
        return False
    except:
        return False

async def get_ip_geolocation(ip: str, default_name: str = "Unknown") -> dict:
    if not ip:
        return {"name": default_name, "lat": 55.6761, "lng": 12.5683}
        
    if is_private_ip(ip):
        # Local/private nodes (like RPI 192.168.1.29) are located in Denmark
        return {"name": "Denmark (Local)", "lat": 55.6761, "lng": 12.5683}
        
    if ip in GEOLOC_CACHE:
        return GEOLOC_CACHE[ip]
        
    # Known droplet IPs to avoid API latency
    if ip == "68.183.72.134":
        loc = {"name": "Frankfurt (Cloud)", "lat": 50.1169, "lng": 8.6837}
        GEOLOC_CACHE[ip] = loc
        return loc

    def _fetch():
        try:
            url = f"http://ip-api.com/json/{ip}"
            with urllib.request.urlopen(url, timeout=3) as resp:
                res = json.loads(resp.read().decode())
                if res.get("status") == "success":
                    return {
                        "name": f"{res.get('city')}, {res.get('country')}",
                        "lat": float(res.get("lat", 0.0)),
                        "lng": float(res.get("lon", 0.0))
                    }
        except:
            pass
        return None

    loc = await asyncio.to_thread(_fetch)
    if loc:
        GEOLOC_CACHE[ip] = loc
        return loc
        
    # Default fallback
    return {"name": "Denmark (Local)", "lat": 55.6761, "lng": 12.5683}

def generate_random_ip():
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

class CTIEngine:
    def __init__(self):
        self.otx_iocs = []
        self.otx_threat_names = []
        self.last_fetch = 0
        self.api_key = ""

    async def fetch_otx_pulses(self, api_key: str):
        """Fetches the latest subscribed pulses from AlienVault OTX."""
        def _do_fetch():
            req = urllib.request.Request("https://otx.alienvault.com/api/v1/pulses/subscribed?limit=20")
            req.add_header("X-OTX-API-KEY", api_key)
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    return json.loads(response.read())
            except Exception as e:
                print(f"[CTI] OTX Fetch Error: {e}")
                return None

        data = await asyncio.to_thread(_do_fetch)
        if not data or "results" not in data:
            return

        iocs = []
        names = []
        for pulse in data["results"]:
            names.append(pulse.get("name", "Unknown Threat"))
            for ind in pulse.get("indicators", []):
                if ind.get("type") == "IPv4":
                    iocs.append(ind.get("indicator"))
                    
        if iocs:
            self.otx_iocs = list(set(iocs))
        if names:
            self.otx_threat_names = list(set(names))
            
        print(f"[CTI] Loaded {len(self.otx_iocs)} IOCs from AlienVault OTX.")

    async def stream_threats(self, queue: asyncio.Queue):
        """Generates a continuous stream of simulated threat intelligence events."""
        while True:
            # Check settings periodically to see if API key was added
            if time.time() - self.last_fetch > 60:
                settings = await load_settings_db()
                key = settings.get("alienvault_api_key", "")
                self.api_key = key
                if self.api_key:
                    await self.fetch_otx_pulses(self.api_key)
                self.last_fetch = time.time()

            # We need an IP and a Threat Name. If we have OTX data, we use it, otherwise fallback to demo.
            is_otx = bool(self.api_key and self.otx_iocs)
            
            source_ip = random.choice(self.otx_iocs) if is_otx and self.otx_iocs else generate_random_ip()
            target_ip = generate_random_ip()

            # Target our actual nodes:
            # - 75% chance if Chaos Mode is active or ambient scans target registered nodes
            is_targeted = False
            targeted_node_name = "Global Infrastructure"
            try:
                nodes = await load_nodes_db()
                if nodes:
                    target_chance = 1.00 if global_state.chaos else 0.00
                    if random.random() < target_chance:
                        chosen_nid = random.choice(list(nodes.keys()))
                        chosen_node = nodes[chosen_nid]
                        if chosen_node.get("host"):
                            target_ip = chosen_node.get("host")
                            targeted_node_name = chosen_node.get("name", "Managed Server")
                            is_targeted = True
            except Exception as e:
                print(f"[CTI] Error targeting real node: {e}")
            
            threat_name = random.choice(self.otx_threat_names) if is_otx and self.otx_threat_names else random.choice(THREAT_TYPES)
            if is_otx:
                threat_name = f"[OTX] {threat_name}"
                
            source_city = random.choice(CITIES)
            source = {
                "ip": source_ip,
                "city": source_city["name"],
                "lat": source_city["lat"] + (random.random() - 0.5) * 2, # add slight jitter
                "lng": source_city["lng"] + (random.random() - 0.5) * 2
            }
            
            if is_targeted:
                geo = await get_ip_geolocation(target_ip, default_name=targeted_node_name)
                target = {
                    "ip": target_ip,
                    "city": f"{targeted_node_name} ({geo['name']})",
                    "lat": geo["lat"] + (random.random() - 0.5) * 0.5, # narrow jitter
                    "lng": geo["lng"] + (random.random() - 0.5) * 0.5
                }
            else:
                target_city = random.choice(CITIES)
                while target_city == source_city:
                    target_city = random.choice(CITIES)
                target = {
                    "ip": target_ip,
                    "city": target_city["name"],
                    "lat": target_city["lat"] + (random.random() - 0.5) * 2,
                    "lng": target_city["lng"] + (random.random() - 0.5) * 2
                }
                
            event = {
                "id": f"evt_{int(time.time()*1000)}_{random.randint(1000, 9999)}",
                "timestamp": time.time(),
                "source": source,
                "target": target,
                "type": threat_name,
                "severity": random.choices(["low", "medium", "high", "critical"], weights=[0.4, 0.3, 0.2, 0.1])[0],
                "targeted": is_targeted
            }
            
            await queue.put(event)
            
            # Wait a bit before generating the next threat
            await asyncio.sleep(random.uniform(0.5, 2.5))

    async def tail_monitored_nodes_logs(self, queue: asyncio.Queue):
        """Periodically polls log files of monitored nodes and posts real-time targeted alerts."""
        import re
        from .vault import load_credentials
        from .session import session_manager
        
        # Regex parsers for SSH, Web server logs, and Firewall logs
        ssh_re = re.compile(r"Failed (?:password|publickey) for (?:invalid user )?(\S+) from (\S+)")
        web_re = re.compile(r"^(\S+)\s+\S+\s+\S+\s+\[[^\]]+\]\s+\"(\S+)\s+(.*?)\s+HTTP/[^\"]+\"\s+(\d+)")
        ufw_re = re.compile(r"\[UFW BLOCK\].*?SRC=(\S+).*?DST=(\S+).*?DPT=(\d+)")

        # Web exploit payloads regex
        sql_pat = re.compile(r"(?i)(union\s+select|select\s+.*\s+from|insert\s+into|delete\s+from|drop\s+table|' or 1=1|--|%27%20or%201%3D1|%20union%20select)")
        path_pat = re.compile(r"(?i)(\.\./\.\.|/etc/passwd|/boot\.ini|win\.ini|%2e%2e%2f)")
        xss_pat = re.compile(r"(?i)(<script>|javascript:|%3Cscript%3E|onerror=|onload=)")

        seen_lines = {} # nid -> set of line hashes to avoid duplicate alerts

        # Combined tail / journalctl commands for multiple log sources
        ssh_cmd = (
            "tail -n 50 /var/log/auth.log 2>/dev/null | grep -E 'Failed password|Failed publickey' || "
            "journalctl -u ssh -n 50 --no-pager 2>/dev/null | grep -E 'Failed password|Failed publickey' || echo ''"
        )
        web_cmd = (
            "tail -n 50 /var/log/nginx/access.log 2>/dev/null || "
            "tail -n 50 /var/log/apache2/access.log 2>/dev/null || "
            "tail -n 50 /var/log/httpd/access_log 2>/dev/null || echo ''"
        )
        fw_cmd = (
            "tail -n 50 /var/log/ufw.log 2>/dev/null || "
            "tail -n 50 /var/log/syslog 2>/dev/null | grep -E '\\[UFW BLOCK\\]|IPTABLES' || echo ''"
        )

        cmds = [ssh_cmd, web_cmd, fw_cmd]

        while True:
            try:
                nodes = await load_nodes_db()
                monitored_nodes = {nid: n for nid, n in nodes.items() if n.get("threat_monitoring")}
                
                for nid, node in monitored_nodes.items():
                    if nid not in seen_lines:
                        seen_lines[nid] = set()

                    # Fetch SSH credentials for connection
                    username, password = await load_credentials(nid)
                    node_ssh = dict(node)
                    node_ssh["username"] = username
                    node_ssh["password"] = password

                    # Run resilient multi-vector log queries in a single batch
                    results, err = await session_manager.run(nid, node_ssh, cmds)
                    if err or not results:
                        continue

                    # Avoid spamming historical logs on first connection
                    is_first_poll = len(seen_lines[nid]) == 0

                    async def process_and_queue_alert(attacker_ip, alert_type, severity):
                        # Geolocate the source IP
                        attacker_geo = await get_ip_geolocation(attacker_ip, default_name="Global Attack Source")
                        # Geolocate the destination target node
                        target_host = node.get("host", "127.0.0.1")
                        target_geo = await get_ip_geolocation(target_host, default_name=node.get("name", "Target Node"))
                        
                        source = {
                            "ip": attacker_ip,
                            "city": f"{attacker_geo['name']} (IP: {attacker_ip})",
                            "lat": attacker_geo["lat"] + (random.random() - 0.5) * 1.5, # Jitter for visual overlapping
                            "lng": attacker_geo["lng"] + (random.random() - 0.5) * 1.5
                        }
                        
                        target = {
                            "ip": target_host,
                            "city": f"{node.get('name')} ({target_geo['name']})",
                            "lat": target_geo["lat"] + (random.random() - 0.5) * 0.3,
                            "lng": target_geo["lng"] + (random.random() - 0.5) * 0.3
                        }
                        
                        event = {
                            "id": f"evt_{int(time.time()*1000)}_{random.randint(1000, 9999)}",
                            "timestamp": time.time(),
                            "source": source,
                            "target": target,
                            "type": alert_type,
                            "severity": severity,
                            "targeted": True
                        }
                        
                        await queue.put(event)
                        # Stagger messages to keep websocket queue smooth
                        await asyncio.sleep(0.1)

                    # 1. Parse SSH output
                    ssh_output = results[0].get("output", "") if len(results) > 0 else ""
                    ssh_lines = [l.strip() for l in ssh_output.split("\n") if l.strip()]
                    for line in ssh_lines:
                        if line in seen_lines[nid]:
                            continue
                        seen_lines[nid].add(line)
                        if is_first_poll:
                            continue
                        m = ssh_re.search(line)
                        if m:
                            attacker_username = m.group(1)
                            attacker_ip = m.group(2)
                            await process_and_queue_alert(
                                attacker_ip=attacker_ip,
                                alert_type=f"SSH Brute Force ({attacker_username})",
                                severity="high"
                            )

                    # 2. Parse Web server access logs
                    web_output = results[1].get("output", "") if len(results) > 1 else ""
                    web_lines = [l.strip() for l in web_output.split("\n") if l.strip()]
                    for line in web_lines:
                        if line in seen_lines[nid]:
                            continue
                        seen_lines[nid].add(line)
                        if is_first_poll:
                            continue
                        m = web_re.search(line)
                        if m:
                            ip, method, path_query, status = m.groups()
                            alert_type = None
                            severity = "medium"
                            
                            if sql_pat.search(path_query):
                                alert_type = "SQL Injection Attempt"
                                severity = "high"
                            elif path_pat.search(path_query):
                                alert_type = "Path Traversal Attempt"
                                severity = "high"
                            elif xss_pat.search(path_query):
                                alert_type = "XSS Attack Attempt"
                                severity = "medium"
                                
                            if alert_type:
                                await process_and_queue_alert(
                                    attacker_ip=ip,
                                    alert_type=alert_type,
                                    severity=severity
                                )

                    # 3. Parse Firewall blocked logs
                    fw_output = results[2].get("output", "") if len(results) > 2 else ""
                    fw_lines = [l.strip() for l in fw_output.split("\n") if l.strip()]
                    for line in fw_lines:
                        if line in seen_lines[nid]:
                            continue
                        seen_lines[nid].add(line)
                        if is_first_poll:
                            continue
                        m = ufw_re.search(line)
                        if m:
                            src_ip, dst_ip, port = m.groups()
                            await process_and_queue_alert(
                                attacker_ip=src_ip,
                                alert_type=f"Port Scan (UFW Blocked Port {port})",
                                severity="medium"
                            )

                    # Cap memory usage of seen lines set
                    if len(seen_lines[nid]) > 1000:
                        seen_lines[nid] = set(list(seen_lines[nid])[-500:])

            except Exception as e:
                print(f"[CTI] Error in monitored nodes tailing loop: {e}")

            # Polling frequency
            await asyncio.sleep(6)

cti_engine = CTIEngine()
cti_queue = asyncio.Queue()



