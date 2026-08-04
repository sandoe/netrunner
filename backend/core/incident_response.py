"""
Netrunner Incident Response Module — Structured IR workflow.

Provides:
- Incident creation and tracking
- Evidence collection workflow
- Containment actions
- Eradication procedures
- Recovery steps
- Post-incident reporting
- Chain of custody tracking
"""

import asyncio
import json
import os
import time
import uuid
from typing import Optional
from backend.core.logger import log as logger

IR_DIR = "data/incident_response"


def _ensure_ir_dir():
    os.makedirs(IR_DIR, exist_ok=True)
    os.makedirs(os.path.join(IR_DIR, "incidents"), exist_ok=True)
    os.makedirs(os.path.join(IR_DIR, "evidence"), exist_ok=True)


# IR Phases
IR_PHASES = [
    {
        "id": "detection",
        "name": "Detection & Analysis",
        "description": "Identify and validate the incident",
    },
    {
        "id": "containment",
        "name": "Containment",
        "description": "Limit the damage of the incident",
    },
    {
        "id": "eradication",
        "name": "Eradication",
        "description": "Remove the threat from the environment",
    },
    {
        "id": "recovery",
        "name": "Recovery",
        "description": "Restore systems to normal operation",
    },
    {
        "id": "post_incident",
        "name": "Post-Incident",
        "description": "Lessons learned and documentation",
    },
]

# Common IR playbooks
IR_PLAYBOOKS = [
    {
        "id": "ransomware",
        "name": "Ransomware Response",
        "description": "Response playbook for ransomware incidents",
        "phases": {
            "detection": [
                "Isolate affected systems from network",
                "Preserve evidence (memory dump, disk image)",
                "Identify ransomware variant",
                "Assess scope of encryption",
            ],
            "containment": [
                "Block IOC IP addresses at firewall",
                "Disable affected user accounts",
                "Segment network to prevent lateral movement",
                "Take offline backup verification",
            ],
            "eradication": [
                "Remove malware from all affected systems",
                "Reset all credentials (local and domain)",
                "Patch vulnerability used for initial access",
                "Update IDS/IPS signatures",
            ],
            "recovery": [
                "Restore systems from clean backups",
                "Verify system integrity",
                "Monitor for re-infection indicators",
                "Gradually restore network connectivity",
            ],
            "post_incident": [
                "Document timeline of events",
                "Conduct lessons learned meeting",
                "Update incident response plan",
                "Report to relevant authorities if required",
            ],
        },
    },
    {
        "id": "data_breach",
        "name": "Data Breach Response",
        "description": "Response playbook for data breach incidents",
        "phases": {
            "detection": [
                "Identify compromised data types",
                "Assess volume of data exposed",
                "Determine exfiltration method",
                "Preserve log evidence",
            ],
            "containment": [
                "Block data exfiltration channels",
                "Revoke compromised credentials",
                "Isolate affected databases",
                "Enable enhanced logging",
            ],
            "eradication": [
                "Remove backdoors and persistence mechanisms",
                "Patch exploited vulnerabilities",
                "Review and harden access controls",
                "Update data loss prevention rules",
            ],
            "recovery": [
                "Restore data from secure backups if needed",
                "Verify data integrity",
                "Implement additional monitoring",
                "Conduct security awareness training",
            ],
            "post_incident": [
                "Notify affected parties as required",
                "File regulatory reports if applicable",
                "Document lessons learned",
                "Update security policies",
            ],
        },
    },
    {
        "id": "insider_threat",
        "name": "Insider Threat Response",
        "description": "Response playbook for insider threat incidents",
        "phases": {
            "detection": [
                "Review user activity logs",
                "Analyze data access patterns",
                "Interview relevant personnel",
                "Preserve digital evidence",
            ],
            "containment": [
                "Disable user accounts",
                "Revoke physical access badges",
                "Monitor communication channels",
                "Secure sensitive documents",
            ],
            "eradication": [
                "Remove unauthorized access",
                "Audit all permissions",
                "Review and update access controls",
                "Implement additional monitoring",
            ],
            "recovery": [
                "Restore normal operations",
                "Verify system integrity",
                "Conduct security awareness training",
                "Update background check procedures",
            ],
            "post_incident": [
                "Document findings",
                "Conduct lessons learned meeting",
                "Update security policies",
                "Review HR procedures",
            ],
        },
    },
    {
        "id": "malware",
        "name": "Malware Response",
        "description": "Response playbook for malware incidents",
        "phases": {
            "detection": [
                "Identify malware type and variant",
                "Determine infection vector",
                "Assess spread and impact",
                "Preserve evidence",
            ],
            "containment": [
                "Isolate infected systems",
                "Block malicious IPs/domains",
                "Disable affected accounts",
                "Monitor for C2 communication",
            ],
            "eradication": [
                "Remove malware from all systems",
                "Clean infected files",
                "Patch exploited vulnerabilities",
                "Update antivirus signatures",
            ],
            "recovery": [
                "Restore clean system state",
                "Verify system integrity",
                "Monitor for re-infection",
                "Gradually restore services",
            ],
            "post_incident": [
                "Document malware analysis",
                "Update detection rules",
                "Conduct lessons learned",
                "Improve security awareness",
            ],
        },
    },
]


async def create_incident(
    title: str,
    description: str,
    severity: str = "high",
    incident_type: str = "malware",
    playbook_id: str = "",
    affected_nodes: list[str] = None,
) -> dict:
    """
    Create a new incident for tracking.

    Args:
        title: Incident title
        description: Detailed description
        severity: Severity level (critical, high, medium, low)
        incident_type: Type of incident
        playbook_id: IR playbook to follow
        affected_nodes: List of affected node IDs

    Returns:
        dict with incident details
    """
    _ensure_ir_dir()
    incident_id = f"IR-{int(time.time())}-{str(uuid.uuid4())[:8]}"

    playbook = None
    if playbook_id:
        playbook = next((p for p in IR_PLAYBOOKS if p["id"] == playbook_id), None)

    incident = {
        "id": incident_id,
        "title": title,
        "description": description,
        "severity": severity,
        "type": incident_type,
        "status": "open",
        "current_phase": "detection",
        "playbook": playbook_id,
        "playbook_data": playbook,
        "affected_nodes": affected_nodes or [],
        "created_at": time.time(),
        "updated_at": time.time(),
        "timeline": [
            {
                "timestamp": time.time(),
                "action": "incident_created",
                "user": "system",
                "details": f"Incident created: {title}",
            }
        ],
        "evidence": [],
        "containment_actions": [],
        "eradication_actions": [],
        "recovery_actions": [],
        "lessons_learned": "",
    }

    # Save incident
    incident_path = os.path.join(IR_DIR, "incidents", f"{incident_id}.json")
    with open(incident_path, "w") as f:
        json.dump(incident, f, indent=2)

    logger.warning(f"[IR] Incident created: {incident_id} - {title} ({severity})")

    return {
        "success": True,
        "incident_id": incident_id,
        "title": title,
        "severity": severity,
        "playbook": playbook["name"] if playbook else None,
    }


async def update_incident_phase(incident_id: str, phase: str) -> dict:
    """Update the current phase of an incident."""
    incident = await get_incident(incident_id)
    if not incident:
        return {"success": False, "error": "Incident not found"}

    if phase not in [p["id"] for p in IR_PHASES]:
        return {"success": False, "error": f"Invalid phase: {phase}"}

    incident["current_phase"] = phase
    incident["updated_at"] = time.time()
    incident["timeline"].append(
        {
            "timestamp": time.time(),
            "action": "phase_changed",
            "user": "system",
            "details": f"Phase changed to {phase}",
        }
    )

    if phase == "post_incident":
        incident["status"] = "resolved"

    await _save_incident(incident)

    return {"success": True, "incident_id": incident_id, "new_phase": phase}


async def add_evidence(
    incident_id: str, evidence_type: str, description: str, file_path: str = ""
) -> dict:
    """Add evidence to an incident."""
    incident = await get_incident(incident_id)
    if not incident:
        return {"success": False, "error": "Incident not found"}

    evidence_id = f"ev_{int(time.time())}"
    evidence = {
        "id": evidence_id,
        "type": evidence_type,
        "description": description,
        "file_path": file_path,
        "collected_at": time.time(),
        "collected_by": "system",
    }

    incident["evidence"].append(evidence)
    incident["timeline"].append(
        {
            "timestamp": time.time(),
            "action": "evidence_added",
            "user": "system",
            "details": f"Evidence added: {evidence_type} - {description}",
        }
    )

    await _save_incident(incident)

    return {"success": True, "evidence_id": evidence_id}


async def add_action(
    incident_id: str, phase: str, action_type: str, description: str, result: str = ""
) -> dict:
    """Add an action to the incident (containment, eradication, recovery)."""
    incident = await get_incident(incident_id)
    if not incident:
        return {"success": False, "error": "Incident not found"}

    action = {
        "id": f"act_{int(time.time())}",
        "type": action_type,
        "description": description,
        "result": result,
        "timestamp": time.time(),
        "performed_by": "system",
    }

    key = f"{phase}_actions"
    if key not in incident:
        incident[key] = []
    incident[key].append(action)

    incident["timeline"].append(
        {
            "timestamp": time.time(),
            "action": f"{phase}_action",
            "user": "system",
            "details": f"{phase.title()} action: {description}",
        }
    )

    await _save_incident(incident)

    return {"success": True, "action_id": action["id"]}


async def close_incident(incident_id: str, lessons_learned: str = "") -> dict:
    """Close an incident."""
    incident = await get_incident(incident_id)
    if not incident:
        return {"success": False, "error": "Incident not found"}

    incident["status"] = "closed"
    incident["current_phase"] = "post_incident"
    incident["lessons_learned"] = lessons_learned
    incident["closed_at"] = time.time()
    incident["updated_at"] = time.time()
    incident["timeline"].append(
        {
            "timestamp": time.time(),
            "action": "incident_closed",
            "user": "system",
            "details": "Incident closed",
        }
    )

    await _save_incident(incident)

    return {"success": True, "incident_id": incident_id}


async def get_incident(incident_id: str) -> Optional[dict]:
    """Get incident details."""
    incident_path = os.path.join(IR_DIR, "incidents", f"{incident_id}.json")
    if os.path.exists(incident_path):
        with open(incident_path) as f:
            return json.load(f)
    return None


def list_incidents(status: str = "", severity: str = "") -> list[dict]:
    """List all incidents."""
    _ensure_ir_dir()
    incidents = []
    for f in sorted(os.listdir(os.path.join(IR_DIR, "incidents")), reverse=True):
        if f.endswith(".json"):
            try:
                with open(os.path.join(IR_DIR, "incidents", f)) as fh:
                    data = json.load(fh)
                    if status and data.get("status") != status:
                        continue
                    if severity and data.get("severity") != severity:
                        continue
                    incidents.append(
                        {
                            "id": data["id"],
                            "title": data["title"],
                            "severity": data["severity"],
                            "type": data["type"],
                            "status": data["status"],
                            "current_phase": data.get("current_phase", ""),
                            "created_at": data["created_at"],
                            "updated_at": data["updated_at"],
                        }
                    )
            except Exception:
                pass
    return incidents


def get_playbooks() -> list[dict]:
    """List available IR playbooks."""
    return IR_PLAYBOOKS


def get_phases() -> list[dict]:
    """List IR phases."""
    return IR_PHASES


async def _save_incident(incident: dict):
    """Save incident to file."""
    incident_path = os.path.join(IR_DIR, "incidents", f"{incident['id']}.json")
    with open(incident_path, "w") as f:
        json.dump(incident, f, indent=2)


def get_ir_stats() -> dict:
    """Get IR statistics."""
    _ensure_ir_dir()
    incidents = list_incidents()
    stats = {
        "total": len(incidents),
        "open": sum(1 for i in incidents if i["status"] == "open"),
        "closed": sum(1 for i in incidents if i["status"] == "closed"),
        "by_severity": {},
        "by_type": {},
    }
    for inc in incidents:
        sev = inc.get("severity", "unknown")
        itype = inc.get("type", "unknown")
        stats["by_severity"][sev] = stats["by_severity"].get(sev, 0) + 1
        stats["by_type"][itype] = stats["by_type"].get(itype, 0) + 1
    return stats
