import asyncio
import json
from backend.core.db import load_alerts_db, update_alert_status, load_playbooks_db
from backend.core.logger import log as logger

async def start_soar():
    """
    Background worker that executes SOAR playbooks against new alerts.
    """
    logger.info("SOAR Engine started. Waiting for alerts...")
    while True:
        try:
            alerts = await load_alerts_db()
            playbooks = await load_playbooks_db()
            
            # Filter for active playbooks and parse JSON
            active_playbooks = []
            for pb in playbooks:
                if pb["is_active"]:
                    try:
                        active_playbooks.append({
                            "id": pb["id"],
                            "name": pb["name"],
                            "conditions": json.loads(pb["conditions"]),
                            "actions": json.loads(pb["actions"])
                        })
                    except Exception as e:
                        logger.error(f"Failed to parse playbook {pb['name']}: {e}")

            # Find new alerts that haven't been triaged
            new_alerts = [a for a in alerts if a["status"] == "new"]
            
            for alert in new_alerts:
                # Evaluate against all active playbooks
                for playbook in active_playbooks:
                    matched = evaluate_conditions(alert, playbook["conditions"])
                    if matched:
                        logger.warning(f"[SOAR] Alert '{alert['title']}' matched playbook '{playbook['name']}'")
                        await execute_actions(alert, playbook["actions"])
                        # Once matched and mitigated, we can close the alert to prevent duplicate triggers
                        await update_alert_status(alert["id"], "closed")
                        break # Stop evaluating other playbooks for this alert if handled

        except Exception as e:
            logger.error(f"Error in SOAR engine: {e}")
            
        await asyncio.sleep(20)

def evaluate_conditions(alert: dict, conditions: list) -> bool:
    """ Evaluate a list of conditions (AND logic) against an alert. """
    if not conditions:
        return False
        
    for cond in conditions:
        field = cond.get("field")
        op = cond.get("operator")
        val = cond.get("value")
        
        if field not in alert:
            return False
            
        actual_val = alert[field]
        
        if op == "==" and actual_val != val: return False
        if op == "!=" and actual_val == val: return False
        # Expand with >, <, contains as needed
        
    return True

async def execute_actions(alert: dict, actions: list):
    """ Execute the actions defined in a playbook. """
    for action in actions:
        action_type = action.get("type")
        if action_type == "block_ip":
            logger.error(f"[SOAR ACTION] IPTABLES: Banning IP associated with Alert {alert['id']}")
        elif action_type == "isolate_node":
            logger.error(f"[SOAR ACTION] QUARANTINE: Isolating node associated with Alert {alert['id']}")
        elif action_type == "auto_close":
            logger.info(f"[SOAR ACTION] AUTO-CLOSE: Marking alert as false positive.")
            await update_alert_status(alert["id"], "false_positive")
        else:
            logger.warning(f"[SOAR ACTION] Unknown action type: {action_type}")
