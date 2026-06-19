from fastapi import APIRouter
from typing import List, Dict, Any
from ..core.db import AsyncSessionLocal, AlertModel, AuditLogModel
from sqlalchemy import select, or_

router = APIRouter(prefix="/hunting", tags=["hunting"])

@router.get("/search")
async def search_threats(q: str, limit: int = 50) -> Dict[str, Any]:
    """Search for a specific query string across alerts and audit logs."""
    
    async with AsyncSessionLocal() as session:
        # Search Alerts
        alert_stmt = select(AlertModel).where(
            or_(
                AlertModel.title.icontains(q),
                AlertModel.description.icontains(q),
                AlertModel.severity.icontains(q)
            )
        ).order_by(AlertModel.created_at.desc()).limit(limit)
        
        alert_res = await session.execute(alert_stmt)
        alerts = [
            {
                "id": a.id,
                "title": a.title,
                "description": a.description,
                "severity": a.severity,
                "status": a.status,
                "created_at": a.created_at
            } for a in alert_res.scalars().all()
        ]
        
        # Search Audit Logs
        audit_stmt = select(AuditLogModel).where(
            or_(
                AuditLogModel.action.icontains(q),
                AuditLogModel.resource.icontains(q),
                AuditLogModel.details.icontains(q)
            )
        ).order_by(AuditLogModel.timestamp.desc()).limit(limit)
        
        audit_res = await session.execute(audit_stmt)
        audits = [
            {
                "id": a.id,
                "user_id": a.user_id,
                "action": a.action,
                "details": a.details,
                "timestamp": a.timestamp
            } for a in audit_res.scalars().all()
        ]
        
        return {
            "query": q,
            "alerts_found": len(alerts),
            "audit_logs_found": len(audits),
            "alerts": alerts,
            "audit_logs": audits
        }
