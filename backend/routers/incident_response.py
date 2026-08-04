"""
Netrunner Incident Response Router — API endpoints for IR workflow.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from .auth import require_admin
from ..core.incident_response import (
    create_incident,
    update_incident_phase,
    add_evidence,
    add_action,
    close_incident,
    get_incident,
    list_incidents,
    get_playbooks,
    get_phases,
    get_ir_stats,
)

router = APIRouter()


class CreateIncidentRequest(BaseModel):
    title: str
    description: str
    severity: str = "high"
    incident_type: str = "malware"
    playbook_id: str = ""
    affected_nodes: list[str] = []


class UpdatePhaseRequest(BaseModel):
    phase: str


class AddEvidenceRequest(BaseModel):
    evidence_type: str
    description: str
    file_path: str = ""


class AddActionRequest(BaseModel):
    phase: str
    action_type: str
    description: str
    result: str = ""


class CloseIncidentRequest(BaseModel):
    lessons_learned: str = ""


@router.get("/ir/incidents")
async def api_ir_incidents(status: str = "", severity: str = ""):
    """List all incidents."""
    incidents = list_incidents(status=status, severity=severity)
    return {"incidents": incidents, "count": len(incidents)}


@router.get("/ir/incidents/{incident_id}")
async def api_ir_incident_detail(incident_id: str):
    """Get incident details."""
    incident = await get_incident(incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return incident


@router.post("/ir/incidents", dependencies=[Depends(require_admin)])
async def api_ir_create_incident(req: CreateIncidentRequest):
    """Create a new incident."""
    result = await create_incident(
        title=req.title,
        description=req.description,
        severity=req.severity,
        incident_type=req.incident_type,
        playbook_id=req.playbook_id,
        affected_nodes=req.affected_nodes,
    )
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed"))
    return result


@router.post("/ir/incidents/{incident_id}/phase", dependencies=[Depends(require_admin)])
async def api_ir_update_phase(incident_id: str, req: UpdatePhaseRequest):
    """Update the current phase of an incident."""
    result = await update_incident_phase(incident_id, req.phase)
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed"))
    return result


@router.post(
    "/ir/incidents/{incident_id}/evidence", dependencies=[Depends(require_admin)]
)
async def api_ir_add_evidence(incident_id: str, req: AddEvidenceRequest):
    """Add evidence to an incident."""
    result = await add_evidence(
        incident_id, req.evidence_type, req.description, req.file_path
    )
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed"))
    return result


@router.post(
    "/ir/incidents/{incident_id}/action", dependencies=[Depends(require_admin)]
)
async def api_ir_add_action(incident_id: str, req: AddActionRequest):
    """Add an action to the incident."""
    result = await add_action(
        incident_id, req.phase, req.action_type, req.description, req.result
    )
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed"))
    return result


@router.post("/ir/incidents/{incident_id}/close", dependencies=[Depends(require_admin)])
async def api_ir_close_incident(incident_id: str, req: CloseIncidentRequest):
    """Close an incident."""
    result = await close_incident(incident_id, req.lessons_learned)
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed"))
    return result


@router.get("/ir/playbooks")
async def api_ir_playbooks():
    """List available IR playbooks."""
    playbooks = get_playbooks()
    return {"playbooks": playbooks}


@router.get("/ir/phases")
async def api_ir_phases():
    """List IR phases."""
    phases = get_phases()
    return {"phases": phases}


@router.get("/ir/stats")
async def api_ir_stats():
    """Get IR statistics."""
    stats = get_ir_stats()
    return stats
