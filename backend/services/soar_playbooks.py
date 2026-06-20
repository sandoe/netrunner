"""
Netrunner SOAR Engine — Real playbook execution.

Evaluates alerts against user-defined playbooks and executes real actions
including IP blocking, node isolation, alert triage, and notification.
"""
import asyncio
import json
from backend.core.db import load_alerts_db, update_alert_status, load_playbooks_db
from backend.core.logger import log as logger
from backend.core.defense import block_ip_on_node, apply_isolation, unblock_ip_on_node, release_isolation


async def start_soar():
    """
    Background worker that executes SOAR playbooks against new alerts.
    Runs every 15 seconds and processes all new alerts.
    """
    logger.info("SOAR Engine started — watching for alerts...")
    while True:
        try:
            alerts = await load_alerts_db()
            playbooks = await load_playbooks_db()

            active_playbooks = []
            for pb in playbooks:
                if pb["is_active"]:
                    try:
                        active_playbooks.append({
                            "id": pb["id"],
                            "name": pb["name"],
                            "conditions": json.loads(pb["conditions"]),
                            "actions": json.loads(pb["actions"]),
                        })
                    except Exception as e:
                        logger.error(f"Failed to parse playbook {pb['name']}: {e}")

            new_alerts = [a for a in alerts if a["status"] == "new"]

            for alert in new_alerts:
                for playbook in active_playbooks:
                    matched = evaluate_conditions(alert, playbook["conditions"])
                    if matched:
                        logger.warning(
                            f"[SOAR] Alert '{alert['title']}' matched playbook '{playbook['name']}'"
                        )
                        results = await execute_actions(alert, playbook["actions"])
                        await update_alert_status(alert["id"], "closed")
                        logger.info(
                            f"[SOAR] Alert '{alert['title']}' handled — {len(results)} actions executed"
                        )
                        break

        except Exception as e:
            logger.error(f"Error in SOAR engine: {e}")

        await asyncio.sleep(15)


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

            else:
                result["message"] = f"Unknown action type: {action_type}"
                logger.warning(f"[SOAR] Unknown action type: {action_type}")

        except Exception as e:
            result["message"] = f"Action failed: {str(e)}"
            logger.error(f"[SOAR] Action {action_type} failed: {e}")

        results.append(result)

    return results


def _extract_ip(alert: dict) -> str:
    """Extract an IP address from an alert title or description."""
    import re
    text = f"{alert.get('title', '')} {alert.get('description', '')}"
    ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
    return ips[0] if ips else "0.0.0.0"
