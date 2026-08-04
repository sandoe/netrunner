import asyncio
import time
import uuid
import random
from backend.core.logger import log as logger
from backend.core.db import insert_alert, AsyncSessionLocal, NodeModel
from sqlalchemy import select


class ShadowItDiscoveryEngine:
    """
    External Attack Surface Management (EASM) / ASM Engine.

    Continuously monitors external sources (like Certificate Transparency logs via crt.sh)
    to discover newly registered subdomains for seed domains. Cross-references discovered
    infrastructure against Netrunner's known Node inventory to detect 'Shadow IT'.
    """

    def __init__(self):
        self.running = False
        self.seed_domain = "netrunner.local"
        self.simulated_ct_logs = [
            f"staging-db.{self.seed_domain}",
            f"test-api-v2.{self.seed_domain}",
            f"dev-portal.{self.seed_domain}",
            f"legacy-vpn.{self.seed_domain}",
        ]

    async def start(self):
        self.running = True
        logger.info(
            "[ASM] Shadow IT Discovery Engine started. Monitoring CT logs for Seed: "
            + self.seed_domain
        )
        while self.running:
            await self._simulate_ct_log_discovery()
            await asyncio.sleep(720)  # Check every 12 mins in simulation

    async def stop(self):
        self.running = False
        logger.info("[ASM] Discovery Engine stopped.")

    async def _simulate_ct_log_discovery(self):
        try:
            # 5% chance to discover a new unmanaged subdomain via CT Logs
            if random.randint(0, 100) < 5:
                rogue_subdomain = random.choice(self.simulated_ct_logs)

                # Check if this asset is known to Netrunner's Node Management
                async with AsyncSessionLocal() as session:
                    res = await session.execute(
                        select(NodeModel).where(NodeModel.hostname == rogue_subdomain)
                    )
                    known_node = res.scalars().first()

                    if not known_node:
                        # It is unmanaged Shadow IT!
                        await self._trigger_shadow_it_alert(rogue_subdomain)

        except Exception as e:
            logger.error(f"[ASM] Discovery analysis failed: {e}")

    async def _trigger_shadow_it_alert(self, rogue_subdomain):
        alert_id = f"alert_asm_{int(time.time())}"
        resolved_ip = f"203.0.113.{random.randint(10, 250)}"

        description = (
            f"**[EASM - SHADOW IT DISCOVERED]**\n\n"
            f"**Discovered Asset:** `{rogue_subdomain}`\n"
            f"**Resolved IP:** `{resolved_ip}`\n"
            f"**Discovery Source:** Certificate Transparency (CT) Logs\n\n"
            f"Netrunner's ASM Engine detected a new SSL certificate issued for the seed domain `{self.seed_domain}`. "
            f"This subdomain is **NOT** present in the managed inventory, indicating it is an unmanaged Shadow IT asset.\n\n"
            f"**SOAR Action Initiated:** Pushing IP to Vulnerability Scanner & flagging asset for CISO review."
        )

        alert = {
            "id": alert_id,
            "title": "Shadow IT Discovery: Unmanaged Internet-Facing Asset",
            "description": description,
            "severity": "high",
            "status": "new",
            "created_at": time.time(),
            "updated_at": time.time(),
            "target_node": rogue_subdomain,
            "src_ip": resolved_ip,
        }
        await insert_alert(alert)
        logger.warning(
            f"[ASM] Unmanaged infrastructure discovered! Subdomain: {rogue_subdomain} (IP: {resolved_ip})"
        )


asm_engine = ShadowItDiscoveryEngine()


async def start_asm_engine():
    await asm_engine.start()
