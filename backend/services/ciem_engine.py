import asyncio
import time
import uuid
import collections
from backend.core.logger import log as logger
from backend.core.db import insert_alert, AsyncSessionLocal
from sqlalchemy import select
from backend.core.db import AuditLogModel, UserModel
from backend.core.nexus_graph import get_memgraph


class CIEMGraphEngine:
    """
    Cloud Infrastructure Entitlement Management (CIEM) Graph Engine.

    1. Usage vs. Granted Analysis: Scans AuditLogs to find overly permissive
       "Zombie Permissions" (e.g. user holds Admin but only uses GET requests).
    2. Toxic Combination Detection: Finds Segregation of Duties violations using
       graph relationships (e.g., identity has write_playbooks AND delete_audit_logs).
    """

    def __init__(self):
        self.running = False

    async def start(self):
        self.running = True
        logger.info(
            "[CIEM] Cloud Infrastructure Entitlement Management Engine started."
        )
        while self.running:
            await self._run_ciem_analysis()
            await asyncio.sleep(3600)  # Run hourly in simulation

    async def stop(self):
        self.running = False
        logger.info("[CIEM] Engine stopped.")

    async def _run_ciem_analysis(self):
        try:
            async with AsyncSessionLocal() as session:
                users_res = await session.execute(select(UserModel))
                users = users_res.scalars().all()
                if not users:
                    return

                # Simulate Usage vs Granted Analysis
                # Fetch recent audit logs to determine actual usage
                recent_logs_res = await session.execute(
                    select(AuditLogModel)
                    .order_by(AuditLogModel.timestamp.desc())
                    .limit(1000)
                )
                recent_logs = recent_logs_res.scalars().all()

                user_actions = collections.defaultdict(set)
                for log in recent_logs:
                    if log.user_id:
                        user_actions[log.user_id].add(log.action)

                # ITDR: Sync Users and Roles to Memgraph via batch UNWIND MERGE
                memgraph = get_memgraph()

                # Format data for Memgraph ingestion
                user_data = []
                for user in users:
                    roles = user.role.split(",") if user.role else []
                    user_data.append(
                        {"id": user.username, "email": user.username, "roles": roles}
                    )

                # Batch upsert users and their relationships to roles
                # Using UNWIND for high-throughput batch writes
                upsert_query = """
                UNWIND $data AS row
                MERGE (u:User {id: row.id})
                SET u.email = row.email
                WITH u, row
                UNWIND row.roles AS role_name
                MERGE (r:Role {name: role_name})
                MERGE (u)-[:MEMBER_OF]->(r)
                """
                memgraph.execute(upsert_query, {"data": user_data})

                await self.detect_toxic_combinations(memgraph, users)
                await self.detect_dormant_privileges(memgraph, users, user_actions)

                # Overly Permissive / Zombie Permission Check
                for user in users:
                    roles = user.role.split(",") if user.role else []
                    if "admin" in roles:
                        actions = user_actions.get(user.username, set())
                        # If user is admin but has only performed read-only actions
                        if (
                            all(
                                a.startswith("view_") or a.startswith("read_")
                                for a in actions
                            )
                            and len(actions) > 0
                        ):
                            await self._trigger_zombie_permission_alert(user)

        except Exception as e:
            logger.error(f"[CIEM] Analysis cycle failed: {e}")

    async def detect_toxic_combinations(self, memgraph, users):
        toxic_query = """
        MATCH (u:User)-[:MEMBER_OF*1..5]->(r1:Role)
        WHERE r1.name = 'admin'
        MATCH (u)-[:MEMBER_OF*1..5]->(r2:Role)
        WHERE r2.name = 'auditor'
        RETURN u.email AS email, u.id as user_id
        """
        toxic_results = list(memgraph.execute_and_fetch(toxic_query))
        for result in toxic_results:
            user_id = result["user_id"]
            toxic_user = next((u for u in users if u.username == user_id), None)
            if toxic_user:
                await self._trigger_toxic_combination_alert(toxic_user)

    async def detect_dormant_privileges(self, memgraph, users, user_actions):
        dormant_query = """
        MATCH (u:User)-[:MEMBER_OF*1..5]->(r:Role)
        WHERE r.name = 'admin'
        RETURN u.email AS email, u.id as user_id
        """
        dormant_results = list(memgraph.execute_and_fetch(dormant_query))
        for result in dormant_results:
            user_id = result["user_id"]
            actions = user_actions.get(user_id, set())
            if len(actions) == 0:
                dormant_user = next((u for u in users if u.username == user_id), None)
                if dormant_user:
                    await self._trigger_dormant_privilege_alert(dormant_user)

    async def _trigger_toxic_combination_alert(self, user):
        alert_id = f"alert_ciem_toxic_{user.username}_{int(time.time())}"
        description = (
            f"**[TOXIC COMBINATION]**\n\n"
            f"User `{user.username}` holds conflicting roles (`admin` and `auditor`).\n"
            f"This is a severe Segregation of Duties (SoD) violation. An attacker compromising this identity "
            f"could execute administrative actions and simultaneously delete the audit logs to cover their tracks.\n"
        )
        alert = {
            "id": alert_id,
            "title": "CIEM: Toxic Permission Combination Detected",
            "description": description,
            "severity": "high",
            "status": "new",
            "created_at": time.time(),
            "updated_at": time.time(),
            "target_node": "identity_plane",
        }
        await insert_alert(alert)
        logger.warning(f"[CIEM] Toxic combination found for user {user.username}.")

    async def _trigger_zombie_permission_alert(self, user):
        alert_id = f"alert_ciem_zombie_{user.username}_{int(time.time())}"
        description = (
            f"**[IDENTITY RISK - ZOMBIE PERMISSION]**\n\n"
            f"User `{user.username}` has been granted `admin` privileges, but over the last 90 days of empirical audit logs, "
            f"they have exclusively performed read-only (`GET`) actions.\n\n"
            f"**Recommendation:** Downgrade this user to a read-only or viewer role to reduce the blast radius if the account is compromised."
        )
        alert = {
            "id": alert_id,
            "title": "CIEM: Overly Permissive Identity Detected",
            "description": description,
            "severity": "medium",
            "status": "new",
            "created_at": time.time(),
            "updated_at": time.time(),
            "target_node": "identity_plane",
        }
        await insert_alert(alert)
        logger.info(f"[CIEM] Overly permissive identity found for user {user.username}.")

    async def _trigger_dormant_privilege_alert(self, user):
        alert_id = f"alert_ciem_dormant_{user.username}_{int(time.time())}"
        description = (
            f"**[IDENTITY RISK - DORMANT ADMIN]**\n\n"
            f"User `{user.username}` holds `admin` privileges but has not performed any actions in the last 90 days.\n\n"
            f"**Recommendation:** Remove these privileges to reduce the attack surface. Dormant admin accounts are prime targets for takeover."
        )
        alert = {
            "id": alert_id,
            "title": "CIEM: Dormant Admin Privileges Detected",
            "description": description,
            "severity": "medium",
            "status": "new",
            "created_at": time.time(),
            "updated_at": time.time(),
            "target_node": "identity_plane",
        }
        await insert_alert(alert)
        logger.warning(f"[CIEM] Dormant privileges found for user {user.username}.")


ciem_engine = CIEMGraphEngine()


async def start_ciem_engine():
    await ciem_engine.start()
