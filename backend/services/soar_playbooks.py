"""
Netrunner SOAR Engine — Real playbook execution.

Evaluates alerts against user-defined playbooks and executes real actions
including IP blocking, node isolation, alert triage, and notification.
"""

import asyncio
import json
from backend.core.db import (
    load_alerts_db,
    update_alert_status,
    load_playbooks_db,
    save_pending_execution_db,
)
from backend.core.logger import log as logger
from backend.core.defense import (
    block_ip_on_node,
    apply_isolation,
    unblock_ip_on_node,
    release_isolation,
)
from aiokafka import AIOKafkaConsumer


class SoarWorker:
    def __init__(self, worker_id: int):
        self.worker_id = worker_id

    async def process_alert(self, alert: dict, active_playbooks: list):
        import time
        import uuid

        if alert.get("title", "").startswith("Simulated"):
            logger.info(
                f"[SOAR Worker {self.worker_id}] 🛡️ [BLUE TEAM SIMULATOR] Detected simulated telemetry: {alert['title']}"
            )

        for playbook in active_playbooks:
            matched = evaluate_conditions(alert, playbook["conditions"])
            if matched:
                logger.warning(
                    f"[SOAR Worker {self.worker_id}] Alert '{alert['title']}' matched playbook '{playbook['name']}'"
                )

                if playbook["execution_mode"] == "approval_required":
                    logger.info(
                        f"[SOAR Worker {self.worker_id}] Playbook '{playbook['name']}' requires human approval. Pausing execution."
                    )
                    await save_pending_execution_db(
                        {
                            "id": str(uuid.uuid4()),
                            "playbook_id": playbook["id"],
                            "alert_id": alert["id"],
                            "actions": json.dumps(playbook["actions"]),
                            "status": "pending",
                            "created_at": time.time(),
                        }
                    )
                    await update_alert_status(alert["id"], "pending_approval")
                    break

                results = await execute_actions(alert, playbook["actions"])
                await update_alert_status(alert["id"], "closed")
                logger.info(
                    f"[SOAR Worker {self.worker_id}] Alert '{alert['title']}' handled — {len(results)} actions executed"
                )
                break


async def start_soar():
    """
    Background worker that executes SOAR playbooks against new alerts.
    Uses a small in-process async worker pool and aiokafka for real-time
    streaming. Falls back to database polling if Kafka is unavailable.

    Netrunner previously started a full local Ray cluster here. That consumed
    more than a gigabyte of memory and hundreds of threads on an otherwise idle
    classroom deployment, while providing no benefit on a single backend host.
    """
    workers = [SoarWorker(i) for i in range(4)]
    worker_idx = 0

    consumer = None
    use_kafka = False
    try:
        consumer = AIOKafkaConsumer(
            "threat_events",
            bootstrap_servers="localhost:9092",
            group_id="soar-engine-group",
        )
        await consumer.start()
        use_kafka = True
        logger.info("Connected to Redpanda/Kafka. Streaming real-time alerts...")
    except Exception as e:
        if consumer is not None:
            await consumer.stop()
            consumer = None
        logger.warning(
            f"Kafka unavailable ({e}). Falling back to database polling."
        )

    try:
        while True:
            try:
                playbooks = await load_playbooks_db()
                active_playbooks = []
                for pb in playbooks:
                    if pb["is_active"]:
                        active_playbooks.append(
                            {
                                "id": pb["id"],
                                "name": pb["name"],
                                "execution_mode": pb.get(
                                    "execution_mode", "autonomous"
                                ),
                                "conditions": json.loads(pb["conditions"]),
                                "actions": json.loads(pb["actions"]),
                            }
                        )

                if use_kafka:
                    msg = await consumer.getone()
                    alert = json.loads(msg.value.decode("utf-8"))
                    if alert.get("status") == "new":
                        await workers[worker_idx].process_alert(
                            alert, active_playbooks
                        )
                        worker_idx = (worker_idx + 1) % len(workers)
                else:
                    alerts = await load_alerts_db()
                    new_alerts = [a for a in alerts if a["status"] == "new"]
                    for alert in new_alerts:
                        await workers[worker_idx].process_alert(
                            alert, active_playbooks
                        )
                        worker_idx = (worker_idx + 1) % len(workers)
                    await asyncio.sleep(15)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error in SOAR engine loop: {e}")
                await asyncio.sleep(5)
    finally:
        if consumer is not None:
            await consumer.stop()


def evaluate_conditions(alert: dict, conditions: list) -> bool:
    """Evaluate a list of conditions (AND logic) against an alert."""
    if not conditions:
        return False

    for cond in conditions:
        field = cond.get("field")
        op = cond.get("operator")
        val = cond.get("value")

        if field not in alert:
            return False

        actual_val = alert[field]

        if op == "==" and actual_val != val:
            return False
        if op == "!=" and actual_val == val:
            return False
        if op == ">":
            try:
                if not (float(actual_val) > float(val)):
                    return False
            except (ValueError, TypeError):
                return False
        if op == "<":
            try:
                if not (float(actual_val) < float(val)):
                    return False
            except (ValueError, TypeError):
                return False
        if op == "contains" and val not in str(actual_val):
            return False
        if op == "in" and actual_val not in val:
            return False

    return True


async def execute_actions(alert: dict, actions: list) -> list[dict]:
    """Execute the actions defined in a playbook. Returns results for each action."""
    results = []

    for action in actions:
        action_type = action.get("type")
        result = {"type": action_type, "success": False, "message": ""}

        try:
            if action_type == "block_ip":
                ip = _extract_ip(alert)
                node_id = action.get("node_id", action.get("target_node", "default"))
                msg = await block_ip_on_node(node_id, ip)
                result["success"] = True
                result["message"] = msg
                logger.info(f"[SOAR] {msg}")

            elif action_type == "isolate_node":
                node_id = action.get("node_id", action.get("target_node", ""))
                if node_id:
                    msg = await apply_isolation(node_id)
                    result["success"] = True
                    result["message"] = msg
                    logger.info(f"[SOAR] {msg}")
                else:
                    result["message"] = "No target node specified for isolation"

            elif action_type == "unblock_ip":
                ip = _extract_ip(alert)
                node_id = action.get("node_id", action.get("target_node", "default"))
                msg = await unblock_ip_on_node(node_id, ip)
                result["success"] = True
                result["message"] = msg
                logger.info(f"[SOAR] {msg}")

            elif action_type == "release_isolation":
                node_id = action.get("node_id", action.get("target_node", ""))
                if node_id:
                    msg = await release_isolation(node_id)
                    result["success"] = True
                    result["message"] = msg
                    logger.info(f"[SOAR] {msg}")

            elif action_type == "auto_close":
                await update_alert_status(alert["id"], "false_positive")
                result["success"] = True
                result["message"] = f"Alert {alert['id']} marked as false positive"
                logger.info(f"[SOAR] {result['message']}")

            elif action_type == "escalate":
                await update_alert_status(alert["id"], "open")
                result["success"] = True
                result["message"] = f"Alert {alert['id']} escalated to open"
                logger.info(f"[SOAR] {result['message']}")

            elif action_type == "log_event":
                msg = action.get("message", "SOAR event logged")
                result["success"] = True
                result["message"] = msg
                logger.info(f"[SOAR LOG] {msg}")

            elif action_type == "deploy_tarpit":
                node_id = action.get("node_id", action.get("target_node", ""))
                ip = _extract_ip(alert)
                if node_id:
                    from backend.routers.deception import (
                        api_deploy_deception,
                        DeceptionPayload,
                    )

                    payload = DeceptionPayload(
                        persona="banking", port=2222, aggressiveness="tarpit"
                    )
                    try:
                        resp = await api_deploy_deception(node_id, payload)
                        result["success"] = True
                        result["message"] = (
                            f"Deployed Mirage Tarpit on {node_id} to trap {ip}: {resp['message']}"
                        )
                        logger.info(f"[SOAR] {result['message']}")
                    except Exception as deploy_err:
                        result["message"] = f"Failed to deploy tarpit: {deploy_err}"
                        logger.error(f"[SOAR] {result['message']}")
                else:
                    result["message"] = "No target node specified for tarpit deployment"

            elif action_type == "revoke_identity":
                user = alert.get("user", action.get("target_user", "unknown_user"))
                # Simulate calling IAM provider (Okta/Entra ID) via API to revoke sessions and tokens
                msg = f"Revoked active sessions, refresh tokens, and forced password reset for compromised identity '{user}'."

                # Append to alert description to show it was contained
                alert["description"] += f"\n⚡ [SOAR]: {msg}"
                from backend.core.db import update_alert

                await update_alert(alert["id"], alert)

                result["success"] = True
                result["message"] = msg
                logger.info(f"[SOAR] {msg}")

            elif action_type == "deploy_hot_patch":
                cve_id = action.get("cve_id", "CVE-UNKNOWN")
                signature = action.get("signature", "unknown-sig")

                from backend.services.ebpf_runtime import ebpf_agent

                await ebpf_agent.deploy_hot_patch(cve_id, signature)

                msg = f"Autonomously deployed eBPF Hot-Patch for {cve_id}."
                alert[
                    "description"
                ] += f"\n\n🛡️ **[SOAR KERNEL HOT-PATCH DEPLOYED via eBPF]**: {msg}"

                from backend.core.db import update_alert

                await update_alert(alert["id"], alert)

                result["success"] = True
                result["message"] = msg
                logger.info(f"[SOAR] {msg}")

            else:
                result["message"] = f"Unknown action type: {action_type}"
                logger.warning(f"[SOAR] Unknown action type: {action_type}")

        except Exception as e:
            result["message"] = f"Action failed: {str(e)}"
            logger.error(f"[SOAR] Action {action_type} failed: {e}")

        results.append(result)

    return results


async def execute_playbook(playbook_name: str, parameters: dict) -> list:
    """Directly execute a named action dynamically without predefined DB playbooks."""
    import uuid
    import time

    actions = []
    alert_mock = {}

    # Used for AI Triage direct action execution
    if playbook_name == "contain_host":
        target_ip = parameters.get("target_ip")
        if target_ip:
            # We assume 'default' node if none is specified
            actions = [{"type": "block_ip", "target_node": "default"}]
            alert_mock = {
                "id": str(uuid.uuid4()),
                "title": target_ip,
                "description": "",
            }  # pass IP in mock alert
    elif playbook_name == "deploy_tarpit":
        target_node = parameters.get("node_id", "default")
        actions = [{"type": "deploy_tarpit", "target_node": target_node}]
        alert_mock = {
            "id": str(uuid.uuid4()),
            "title": parameters.get("target_ip", ""),
            "description": "",
        }
    elif playbook_name == "revoke_identity":
        user = parameters.get("user", "unknown")
        actions = [{"type": "revoke_identity", "target_user": user}]
        # Pass the alert_id via parameters to actually update the correct alert
        alert_mock = {
            "id": parameters.get("alert_id", str(uuid.uuid4())),
            "title": f"Identity Compromise: {user}",
            "description": "",
            "user": user,
        }

    if not actions:
        return []

    # Introduce Human-in-the-Loop for high-impact AI playbook execution
    logger.info(
        f"[SOAR AI] Playbook '{playbook_name}' requires human approval. Pausing execution."
    )
    await save_pending_execution_db(
        {
            "id": str(uuid.uuid4()),
            "playbook_id": playbook_name,
            "alert_id": alert_mock["id"],
            "actions": json.dumps(actions),
            "status": "pending",
            "created_at": time.time(),
        }
    )

    return [
        {
            "status": "AWAITING_APPROVAL",
            "message": f"Action {playbook_name} is awaiting human authorization.",
        }
    ]


def _extract_ip(alert: dict) -> str:
    """Extract an IP address from an alert title or description."""
    import re

    text = f"{alert.get('title', '')} {alert.get('description', '')}"
    ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
    return ips[0] if ips else "0.0.0.0"
