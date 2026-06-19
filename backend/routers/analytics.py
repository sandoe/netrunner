from fastapi import APIRouter
from typing import Dict, Any
from ..core.db import load_alerts_db, load_playbooks_db

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/summary", response_model=Dict[str, Any])
async def get_dashboard_summary():
    """Returns high-level statistics for the Executive Dashboard."""
    alerts = await load_alerts_db()
    playbooks = await load_playbooks_db()

    total_alerts = len(alerts)
    critical_alerts = len([a for a in alerts if a["severity"] == "critical"])
    high_alerts = len([a for a in alerts if a["severity"] == "high"])
    
    # Calculate statuses
    new_alerts = len([a for a in alerts if a["status"] == "new"])
    investigating_alerts = len([a for a in alerts if a["status"] == "investigating"])
    closed_alerts = len([a for a in alerts if a["status"] == "closed"])
    false_positives = len([a for a in alerts if a["status"] == "false_positive"])

    active_playbooks = len([p for p in playbooks if p["is_active"]])
    
    # Mock some data for chart generation
    # In a real app, this would group by date/timestamp
    trend_data = {
        "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "datasets": [
            {
                "label": "Critical Threats",
                "data": [5, 12, 8, 25, 4, 2, critical_alerts]
            },
            {
                "label": "Auto-Mitigated",
                "data": [4, 10, 7, 24, 4, 1, false_positives + closed_alerts]
            }
        ]
    }

    return {
        "metrics": {
            "total_alerts": total_alerts,
            "critical_alerts": critical_alerts,
            "high_alerts": high_alerts,
            "new_alerts": new_alerts,
            "investigating_alerts": investigating_alerts,
            "closed_alerts": closed_alerts,
            "false_positives": false_positives,
            "active_playbooks": active_playbooks,
            "mitigation_rate_percent": round(((closed_alerts + false_positives) / total_alerts * 100), 1) if total_alerts > 0 else 0
        },
        "trends": trend_data
    }
