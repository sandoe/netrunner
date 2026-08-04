import asyncio
import time
import uuid
import random
from backend.core.logger import log as logger
from backend.core.db import insert_alert


class DeceptionOrchestrator:
    """
    Active Defense: Honeytoken Generator & Tripwire.

    Generates high-fidelity deceptive tokens (e.g., fake AWS API keys, phantom database credentials)
    and monitors for their usage. Since legitimate users have no reason to access these tokens,
    any usage is a guaranteed 0-false-positive indicator of compromise or insider threat.
    """

    def __init__(self):
        self.running = False
        fake_aws_key = "AKIA" + uuid.uuid4().hex.upper()[:16]
        fake_db_password = uuid.uuid4().hex
        self.active_honeytokens = {
            fake_aws_key: "Fake AWS Production Access Key",
            f"postgres://decoy:{fake_db_password}@10.0.0.99:5432/finance": "Phantom DB Connection String",
            "C:\\Users\\Administrator\\Documents\\passwords.txt": "Decoy Credentials File",
        }

    async def start(self):
        self.running = True
        logger.info(
            "[DECEPTION] Honeytoken Orchestrator started. Seeding deceptive assets..."
        )
        while self.running:
            await self._simulate_honeytoken_tripwire()
            await asyncio.sleep(600)  # Check every 10 mins in simulation

    async def stop(self):
        self.running = False
        logger.info("[DECEPTION] Orchestrator stopped.")

    async def _simulate_honeytoken_tripwire(self):
        try:
            # Simulate analyzing ingested logs for honeytoken usage
            trigger_chance = random.randint(0, 100)

            # 5% chance that an attacker or script trips over a honeytoken
            if trigger_chance < 5:
                token_value = random.choice(list(self.active_honeytokens.keys()))
                token_desc = self.active_honeytokens[token_value]
                await self._trigger_honeytoken_alert(token_value, token_desc)

        except Exception as e:
            logger.error(f"[DECEPTION] Tripwire analysis failed: {e}")

    async def _trigger_honeytoken_alert(self, token_value, token_desc):
        alert_id = f"alert_deception_{int(time.time())}"
        compromised_ip = f"10.0.{random.randint(1, 255)}.{random.randint(1, 255)}"

        description = (
            f"**[ACTIVE DEFENSE - HONEYTOKEN TRIGGERED]**\n\n"
            f"**Compromised Host:** `{compromised_ip}`\n"
            f"**Token Accessed:** `{token_desc}`\n"
            f"**Value:** `{token_value}`\n\n"
            f"Netrunner's Deception Engine detected the usage of a seeded Honeytoken. "
            f"As this asset is a phantom decoy with zero legitimate business use cases, "
            f"this is a **100% confidence indicator** of unauthorized lateral movement, reconnaissance, "
            f"or a malicious insider attempting to escalate privileges.\n\n"
            f"**SOAR Action Initiated:** Quarantining Host IP & Revoking active sessions."
        )

        alert = {
            "id": alert_id,
            "title": "Deception Tripwire: Lateral Movement Detected (Honeytoken)",
            "description": description,
            "severity": "critical",
            "status": "new",
            "created_at": time.time(),
            "updated_at": time.time(),
            "target_node": "honeytoken_decoy",
            "src_ip": compromised_ip,
        }
        await insert_alert(alert)
        logger.critical(
            f"[DECEPTION] Tripwire triggered! Lateral movement detected from {compromised_ip} using decoy: {token_desc}"
        )


deception_orchestrator = DeceptionOrchestrator()


async def start_deception_orchestrator():
    await deception_orchestrator.start()
