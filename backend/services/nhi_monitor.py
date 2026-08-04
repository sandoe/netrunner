import asyncio
import time
import random
from backend.core.logger import log as logger
from backend.core.db import insert_alert, AsyncSessionLocal, NHITokenModel
from sqlalchemy import select


class NHISecurityEngine:
    """
    Non-Human Identity (NHI) Threat Correlation & Revocation Engine.

    Monitors API keys, OAuth tokens, and Service Accounts for anomalous usage,
    such as a dormant token suddenly being used from an unknown IP address.
    """

    def __init__(self):
        self.running = False

    async def _seed_database(self):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(NHITokenModel))
            if not res.scalars().first():
                # Seed some dummy NHI tokens
                tokens = [
                    NHITokenModel(
                        id="nhi_github_ci_1",
                        owner="devops_svc",
                        service="GitHub",
                        scopes="repo,admin:org",
                        last_used_ip="10.0.0.50",
                        status="Active",
                        last_used_at=time.time() - 3600,
                    ),
                    NHITokenModel(
                        id="nhi_aws_s3_read",
                        owner="analytics_job",
                        service="AWS",
                        scopes="s3:GetObject",
                        last_used_ip="10.0.0.51",
                        status="Active",
                        last_used_at=time.time() - 86400,
                    ),
                    NHITokenModel(
                        id="nhi_legacy_slack_bot",
                        owner="marketing_team",
                        service="Slack",
                        scopes="chat:write",
                        last_used_ip="192.168.1.100",
                        status="Dormant",
                        last_used_at=time.time() - (120 * 86400),
                    ),  # 120 days ago
                ]
                session.add_all(tokens)
                await session.commit()
                logger.info("[NHI] Seeded initial Non-Human Identity inventory.")

    async def start(self):
        await self._seed_database()
        self.running = True
        logger.info("[NHI] Non-Human Identity Monitor started.")
        while self.running:
            await self._simulate_nhi_anomaly()
            await asyncio.sleep(720)  # Check every 12 mins in simulation

    async def stop(self):
        self.running = False
        logger.info("[NHI] Monitor stopped.")

    async def _simulate_nhi_anomaly(self):
        try:
            # 5% chance to simulate a dormant token being compromised
            if random.randint(0, 100) < 5:
                async with AsyncSessionLocal() as session:
                    res = await session.execute(
                        select(NHITokenModel).where(NHITokenModel.status == "Dormant")
                    )
                    dormant_token = res.scalars().first()

                    if dormant_token:
                        rogue_ip = f"185.199.108.{random.randint(1, 255)}"
                        await self._trigger_nhi_revocation_alert(
                            dormant_token, rogue_ip
                        )

        except Exception as e:
            logger.error(f"[NHI] Analysis failed: {e}")

    async def _trigger_nhi_revocation_alert(self, token: NHITokenModel, rogue_ip: str):
        alert_id = f"alert_nhi_{int(time.time())}"

        description = (
            f"**[NHI - DORMANT TOKEN COMPROMISE]**\n\n"
            f"**Token ID:** `{token.id}`\n"
            f"**Service:** `{token.service}` (Owner: `{token.owner}`)\n"
            f"**Scopes:** `{token.scopes}`\n"
            f"**Anomaly:** Token was completely **DORMANT** for over 90 days, but was just used to authenticate from an unknown external IP (`{rogue_ip}`).\n\n"
            f"**SOAR Action Initiated:** Executing automated OAuth Revocation playbook via `{token.service}` Admin API to immediately destroy token privileges."
        )

        alert = {
            "id": alert_id,
            "title": f"Compromised Machine Identity: {token.service} Token",
            "description": description,
            "severity": "critical",
            "status": "new",
            "created_at": time.time(),
            "updated_at": time.time(),
            "target_node": token.service,
            "src_ip": rogue_ip,
        }
        await insert_alert(alert)
        logger.critical(
            f"[NHI] Dormant token {token.id} used from rogue IP {rogue_ip}. Revocation initiated!"
        )


nhi_engine = NHISecurityEngine()


async def start_nhi_monitor():
    await nhi_engine.start()
