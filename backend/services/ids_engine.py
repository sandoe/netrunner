import asyncio
import uuid
import time
import random
from backend.core.logger import log as logger
from backend.core.db import insert_alert

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
        alert = {
            "id": str(uuid.uuid4()),
            "title": title,
            "description": desc,
            "severity": severity.lower(),
            "status": "new",
            "assignee_id": None,
            "created_at": time.time(),
            "updated_at": time.time()
        }
        await insert_alert(alert)
        logger.info(f"IDS Alert generated: {title} ({severity})")
