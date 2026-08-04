import asyncio
from backend.core.logger import log as logger
from backend.services.ids_engine import _process_packet
from backend.core.db import AsyncSessionLocal, AlertModel
from sqlalchemy import select

try:
    from scapy.all import IP, TCP, UDP, DNS, DNSQR, send  # type: ignore
except ImportError:
    pass


async def inject_synthetic_telemetry():
    logger.info("[BAS] Starting synthetic telemetry injection for IDS validation...")
    dummy_ip = "198.51.100.99"  # TEST-NET-2 documentation IP

    # 1. Simulate Port Scan (Triggers unique port detection in ids_engine.py)
    for port in range(1, 30):
        pkt = IP(src=dummy_ip, dst="10.0.0.1") / TCP(dport=port, flags="S")
        _process_packet(pkt)

    # 2. Simulate DNS Tunnel (Triggers >50 char subdomain detection in ids_engine.py)
    long_subdomain = "a" * 60 + ".synthetic-test.local"
    dns_pkt = (
        IP(src=dummy_ip, dst="8.8.8.8")
        / UDP(dport=53)
        / DNS(qd=DNSQR(qname=long_subdomain))
    )
    _process_packet(dns_pkt)

    # Allow time for async DB insertion and AI triage tasks to complete
    await asyncio.sleep(3)

    # 3. Pipeline Validation Loop
    async with AsyncSessionLocal() as session:
        # Check Port Scan
        stmt1 = (
            select(AlertModel)
            .where(AlertModel.title.icontains("Port Scanning"))
            .where(AlertModel.title.icontains(dummy_ip))
        )
        if (await session.execute(stmt1)).scalars().first():
            logger.info("🟢 [BAS] SUCCESS: Port scan detection rule operational.")
        else:
            logger.error("🔴 [BAS] FAILURE: Port scan detection rule failed!")

        # Check DNS Tunnel
        stmt2 = (
            select(AlertModel)
            .where(AlertModel.title.icontains("DNS Tunnel"))
            .where(AlertModel.title.icontains(dummy_ip))
        )
        if (await session.execute(stmt2)).scalars().first():
            logger.info("🟢 [BAS] SUCCESS: DNS Tunnel detection rule operational.")
        else:
            logger.error("🔴 [BAS] FAILURE: DNS Tunnel detection rule failed!")


async def start_bas_simulation(interval: int = 3600):
    """Run the BAS simulation periodically to ensure continuous pipeline health."""
    while True:
        await inject_synthetic_telemetry()
        await asyncio.sleep(interval)
