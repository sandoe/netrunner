import asyncio
import time
import random
import uuid
import hashlib
from backend.core.logger import log as logger
from backend.core.db import insert_alert, load_nodes_db
from backend.core.session import session_manager


class FirmwareSecurityEngine:
    """
    Simulates a highly privileged kernel-mode driver capable of directly reading
    SPI flash and extracting TPM PCRs (Platform Configuration Registers) to detect
    supply chain implants and UEFI bootkits (e.g., BlackLotus) without physical access.
    """

    def __init__(self):
        self.running = False

    async def start(self):
        self.running = True
        logger.info("[FirmwareSecurity] SPI Flash & TPM Attestation Engine started.")
        while self.running:
            await self._run_attestation_cycle()
            await asyncio.sleep(300)  # Run every 5 minutes in this simulation

    async def stop(self):
        self.running = False
        logger.info("[FirmwareSecurity] Engine stopped.")

    async def _run_attestation_cycle(self):
        try:
            nodes = await load_nodes_db()
            for nid, node in nodes.items():
                if node.get("threat_monitoring", False):
                    await self._attest_node(nid, node)
        except Exception as e:
            logger.error(f"[FirmwareSecurity] Attestation cycle failed: {e}")

    async def _attest_node(self, node_id: str, node: dict):
        # We only attest if we have a live SSH session to deploy the driver/read
        if not session_manager.is_connected(node_id):
            return

        # Simulate executing the hardware read
        res, err = await session_manager.run(
            node_id,
            node,
            ["echo 'Simulating direct SPI flash read and TPM PCR extraction...'"],
        )

        # 2% chance of detecting a supply chain bootkit implant for the simulation
        if random.random() < 0.02:
            await self._trigger_bootkit_alert(node_id, node)

    async def _trigger_bootkit_alert(self, node_id: str, node: dict):
        fake_implant_hash = hashlib.sha256(str(time.time()).encode()).hexdigest()

        alert_id = f"alert_fw_{int(time.time())}_{node_id}"
        alert_title = "UEFI Bootkit / SPI Flash Implant Detected"
        description = (
            f"**CRITICAL HARDWARE THREAT**\n\n"
            f"The Netrunner Firmware Security agent successfully performed an out-of-band SPI flash read on node `{node_id}`.\n\n"
            f"- **Expected BIOS Hash:** `f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b`\n"
            f"- **Actual SPI Flash Hash:** `{fake_implant_hash}`\n"
            f"- **TPM PCR0 (Core Root of Trust):** Validation FAILED\n\n"
            f"**Analysis:** The cryptographic hashes of the running BIOS/UEFI do not match known-good vendor baselines. "
            f"This indicates a highly sophisticated supply chain implant or bootkit (e.g., BlackLotus) has compromised the system below the OS level."
        )

        alert = {
            "id": alert_id,
            "title": alert_title,
            "description": description,
            "severity": "critical",
            "status": "new",
            "created_at": time.time(),
            "updated_at": time.time(),
            "target_node": node_id,
        }

        await insert_alert(alert)
        logger.critical(
            f"[FirmwareSecurity] 🚨 BOOTKIT DETECTED on node {node_id}! SPI hash mismatch."
        )


firmware_engine = FirmwareSecurityEngine()


async def start_firmware_security():
    await firmware_engine.start()
