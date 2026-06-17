from fastapi import APIRouter, Depends
from typing import Dict, Any
import time
from ..core.db import (
    load_alerts_db,
    load_threat_events_db,
    load_nodes_db
)

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/summary", response_model=Dict[str, Any])
async def get_report_summary(timerange_hours: int = 24):
    """
    Generate a high-level summary for the SOC report.
    """
    now = time.time()
    cutoff_time = now - (timerange_hours * 3600)
    
    # Load all data
    # Note: In a real enterprise system, we would use SQL aggregations.
    # For this scale, loading and filtering in memory is fine.
    all_alerts = await load_alerts_db()
    all_threats = await load_threat_events_db(limit=5000)
    all_nodes = await load_nodes_db()
    
    # Filter by timerange
    recent_alerts = [a for a in all_alerts if a["created_at"] >= cutoff_time]
    recent_threats = [t for t in all_threats if t["timestamp"] >= cutoff_time]
    
    # Aggregations
    alerts_by_severity = {
        "critical": len([a for a in recent_alerts if a["severity"] == "critical"]),
        "high": len([a for a in recent_alerts if a["severity"] == "high"]),
        "medium": len([a for a in recent_alerts if a["severity"] == "medium"]),
        "low": len([a for a in recent_alerts if a["severity"] == "low"])
    }
    
    alerts_by_status = {
        "new": len([a for a in recent_alerts if a["status"] == "new"]),
        "open": len([a for a in recent_alerts if a["status"] == "open"]),
        "closed": len([a for a in recent_alerts if a["status"] == "closed"]),
        "false_positive": len([a for a in recent_alerts if a["status"] == "false_positive"])
    }
    
    # Top targeted nodes (from threats)
    node_hits = {}
    for t in recent_threats:
        target = t["target_ip"] or t["node_id"]
        node_hits[target] = node_hits.get(target, 0) + 1
        
    top_targeted_nodes = sorted([{"target": k, "hits": v} for k, v in node_hits.items()], key=lambda x: x["hits"], reverse=True)[:5]
    
    return {
        "generated_at": now,
        "timerange_hours": timerange_hours,
        "total_active_nodes": len(all_nodes),
        "alerts_summary": {
            "total": len(recent_alerts),
            "by_severity": alerts_by_severity,
            "by_status": alerts_by_status
        },
        "threats_summary": {
            "total_events": len(recent_threats),
            "top_targets": top_targeted_nodes
        }
    }
