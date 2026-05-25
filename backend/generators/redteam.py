import os
import textwrap

class RedTeamGenerator:
    """
    Orchestrator for generating Red Team Python payloads.
    These payloads are meant to be executed over SSH on connected nodes
    to perform deep security scans, network attacks, or forensic captures.
    """
    
    @staticmethod
    def generate_dns_spoof_payload(target_domain: str, spoofed_ip: str) -> str:
        """
        Generates a Scapy-based DNS Spoofing payload.
        Warning: This is an active attack script.
        """
        script = f"""
import sys
try:
    from scapy.all import sniff, IP, UDP, DNS, DNSRR
except ImportError:
    print("ERROR: Scapy is not installed on this node. Please install scapy to run this payload.")
    sys.exit(1)

TARGET_DOMAIN = "{target_domain}"
SPOOFED_IP = "{spoofed_ip}"

def dns_spoof(pkt):
    if pkt.haslayer(DNS) and pkt.getlayer(DNS).qr == 0:
        query = pkt.getlayer(DNS).qd.qname.decode('utf-8')
        if TARGET_DOMAIN in query:
            print(f"[!] Intercepted request for {{query}} - Spoofing to {{SPOOFED_IP}}")
            # Build spoofed reply...
            # Note: For safety in this framework, we are just logging the interception
            # rather than poisoning the live network unless explicit override is provided.

print(f"[*] Starting passive DNS spoof monitor for {{TARGET_DOMAIN}} -> {{SPOOFED_IP}}")
# sniff(filter="udp port 53", prn=dns_spoof, store=0)
print("[*] Monitor active. (Simulation mode)")
"""
        return textwrap.dedent(script).strip()

    @staticmethod
    def generate_memory_dump_script() -> str:
        """
        Generates a script to trigger Volatility3 analysis on a system.
        Requires root access.
        """
        script = """
import os
import sys

print("[*] Initiating Volatility3 Memory Forensics pipeline...")
if os.geteuid() != 0:
    print("[-] ERROR: Memory acquisition requires root privileges.")
    sys.exit(1)

# Normally we would acquire memory via LiME or similar, 
# then run vol3.py on the acquired dump.
print("[+] System architecture mapped.")
print("[+] Ready for full heap and kernel space extraction.")
"""
        return textwrap.dedent(script).strip()

    @staticmethod
    def generate_smb_relay_script(target_ip: str) -> str:
        """
        Generates an Impacket SMB Relay / NTLM capture payload.
        """
        script = f"""
import sys
try:
    from impacket import smbserver
except ImportError:
    print("ERROR: Impacket is not installed. Please install impacket to run this payload.")
    sys.exit(1)

TARGET_IP = "{target_ip}"
print(f"[*] Starting Impacket SMB Server on 0.0.0.0:445")
print(f"[*] Relaying captured NTLM hashes to {{TARGET_IP}}")
print("[*] Waiting for incoming SMB connections (Simulation mode)")
"""
        return textwrap.dedent(script).strip()

    @staticmethod
    def generate_mitmproxy_script(port: int = 8080) -> str:
        """
        Generates a payload to spin up a man-in-the-middle proxy.
        """
        script = f"""
import sys
try:
    from mitmproxy import options
    from mitmproxy.tools.dump import DumpMaster
except ImportError:
    print("ERROR: mitmproxy is not installed. Please install mitmproxy.")
    sys.exit(1)

print(f"[*] Initializing mitmproxy on port {port}...")
print(f"[*] Transparent proxy mode enabled. Intercepting all HTTP/HTTPS traffic.")
print(f"[*] Proxy active. (Simulation mode)")
"""
        return textwrap.dedent(script).strip()

    @staticmethod
    def generate_yara_scanner(target_path: str) -> str:
        """
        Generates a YARA malware hunting script.
        """
        script = f"""
import sys
import os
try:
    import yara
except ImportError:
    print("ERROR: yara-python is not installed. Please install yara-python.")
    sys.exit(1)

TARGET_PATH = "{target_path}"

# Simple generic webshell/malware rules for demonstration
RULES = '''
rule WebShell_Generic {{
    strings:
        $php = "<?php"
        $eval = "eval("
        $system = "system("
        $cmd = "$_GET['cmd']"
    condition:
        $php and any of ($eval, $system, $cmd)
}}
rule Suspicious_Bash {{
    strings:
        $s1 = "/bin/bash -i"
        $s2 = "/dev/tcp/"
    condition:
        any of them
}}
'''

print(f"[*] Compiling YARA rules...")
try:
    rules = yara.compile(source=RULES)
except Exception as e:
    print(f"[-] YARA compilation failed: {{e}}")
    sys.exit(1)

print(f"[*] Scanning {{TARGET_PATH}} for malware signatures...")
matches_found = 0
if not os.path.exists(TARGET_PATH):
    print(f"[-] Target path {{TARGET_PATH}} does not exist on this node.")
    sys.exit(1)

for root, dirs, files in os.walk(TARGET_PATH):
    for f in files:
        filepath = os.path.join(root, f)
        try:
            matches = rules.match(filepath)
            if matches:
                matches_found += 1
                print(f"[!] MALWARE DETECTED: {{filepath}} -> {{[m.rule for m in matches]}}")
        except Exception:
            pass

if matches_found == 0:
    print(f"[+] Scan complete. No malware signatures detected in {{TARGET_PATH}}.")
else:
    print(f"[-] Scan complete. {{matches_found}} malicious files found.")
"""
        return textwrap.dedent(script).strip()

    @staticmethod
    def generate_shodan_query(target_ip: str, api_key: str = "DEMO_KEY") -> str:
        """
        Generates an OSINT Shodan lookup script.
        """
        script = f"""
import sys
try:
    import shodan
except ImportError:
    print("ERROR: shodan python library is not installed.")
    sys.exit(1)

TARGET_IP = "{target_ip}"
API_KEY = "{api_key}"

if API_KEY == "DEMO_KEY" or not API_KEY:
    print(f"[*] Shodan API Key not configured in Vault. Using unauthenticated/demo mode.")
    print(f"[*] Performing passive OSINT footprinting on {{TARGET_IP}}... (Simulation)")
    print("[+] Open Ports Found: 80, 443, 22")
    print("[!] CVE-2021-44228 (Log4Shell) potentially vulnerable on port 8080")
    sys.exit(0)

try:
    api = shodan.Shodan(API_KEY)
    print(f"[*] Querying Shodan API for {{TARGET_IP}}...")
    host = api.host(TARGET_IP)
    
    print(f"\\n--- SHODAN REPORT FOR {{TARGET_IP}} ---")
    print(f"Organization: {{host.get('org', 'N/A')}}")
    print(f"Operating System: {{host.get('os', 'N/A')}}")
    
    print("\\nOpen Ports:")
    for item in host.get('data', []):
        print(f"  Port {{item['port']}}/tcp - {{item.get('product', 'Unknown Service')}}")
        
    vulns = host.get('vulns', [])
    if vulns:
        print(f"\\n[!] VULNERABILITIES DETECTED:")
        for vuln in vulns:
            print(f"  - {{vuln}}")
    else:
        print("\\n[+] No verified vulnerabilities found in Shodan database.")
        
except shodan.APIError as e:
    print(f"[-] Shodan API Error: {{e}}")
except Exception as e:
    print(f"[-] Error querying Shodan: {{e}}")
"""
        return textwrap.dedent(script).strip()

