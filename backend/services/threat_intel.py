import asyncio
import uuid
import time
from ..core.db import insert_threat_intel

# Simulated malicious IPs from a mock "Threat Intelligence Feed"
MOCK_MALICIOUS_IPS = [
    {"ip": "185.150.10.1", "source": "AlienVault OTX", "threat_type": "Botnet C2", "severity": "critical"},
    {"ip": "45.22.19.102", "source": "MISP Feed", "threat_type": "Ransomware Node", "severity": "critical"},
    {"ip": "194.26.29.11", "source": "Spamhaus", "threat_type": "Scanner", "severity": "high"},
    {"ip": "220.101.44.5", "source": "CrowdStrike TiF", "threat_type": "APT Group", "severity": "critical"}
]

async def start_threat_intel_sync():
    """Simulates periodically syncing threat intelligence feeds."""
    while True:
        print("[Threat Intel] Syncing feeds from OSINT sources...")
        for intel in MOCK_MALICIOUS_IPS:
            entry = {
                "id": str(uuid.uuid4()),
                "ip": intel["ip"],
                "source": intel["source"],
                "threat_type": intel["threat_type"],
                "severity": intel["severity"],
                "timestamp": time.time()
            }
            await insert_threat_intel(entry)
        
        # Sleep for a long time since feeds don't update every second
        await asyncio.sleep(3600)
