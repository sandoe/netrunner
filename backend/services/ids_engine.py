import asyncio
import uuid
import time
import random
from backend.core.logger import log as logger
from backend.core.db import insert_alert, check_ip_threat_intel

ALERT_TYPES = [
    ("ARP Spoofing Detected", "Critical", "Multiple ARP replies detected for the same IP address."),
    ("Port Scanning", "High", "Rapid sequential port connection attempts detected."),
    ("Malware Callback", "Critical", "Traffic to known C2 server detected.")
]

async def start_ids():
    logger.info("Starting IDS engine...")
    while True:
        await asyncio.sleep(30)
        title, severity, desc = random.choice(ALERT_TYPES)
        ip = random.choice([
            "185.150.10.1", "192.168.1.100", "45.22.19.102", "10.0.0.5", "194.26.29.11", "220.101.44.5"
        ])
        
        intel = await check_ip_threat_intel(ip)
        if intel:
            title = f"[KNOWN THREAT] {title}"
            desc = f"{desc} | TiF Match: {intel['source']} ({intel['threat_type']})"
            severity = intel["severity"]

        alert = {
            "id": str(uuid.uuid4()),
            "title": f"{title} [{ip}]",
            "description": desc,
            "severity": severity.lower(),
            "status": "new",
            "assignee_id": None,
            "created_at": time.time(),
            "updated_at": time.time()
        }
        await insert_alert(alert)
        logger.info(f"IDS Alert generated: {title} ({severity}) for {ip}")
