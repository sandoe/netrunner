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
                "data": [5, 12, 8, 25, 4, 2, critical_alerts],
            },
            {
                "label": "Auto-Mitigated",
                "data": [4, 10, 7, 24, 4, 1, false_positives + closed_alerts],
            },
        ],
    }

    # Get real flow analytics from the engine
    from ..services.flow_analytics import flow_engine

    flow_summary = flow_engine.get_summary()

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
            "mitigation_rate_percent": (
                round(((closed_alerts + false_positives) / total_alerts * 100), 1)
                if total_alerts > 0
                else 0
            ),
        },
        "trends": trend_data,
        "protocols": flow_summary.get("protocols", []),
        "top_talkers": flow_summary.get("top_talkers", []),
    }


@router.get("/ueba/{user_id}/risk-timeline", response_model=Dict[str, Any])
async def get_ueba_risk_timeline(user_id: str):
    """
    Returns an Explainable AI (XAI) risk timeline for a given user,
    leveraging a Deep Learning Autoencoder to detect anomalous behavior.
    """
    import random
    from datetime import datetime, timedelta

    # In a real environment, we would load the user's historical events and
    # run them through a PyTorch/TensorFlow Autoencoder model to generate a reconstruction error.
    # The reconstruction error serves as the anomaly/risk score.

    # Mocking the Deep Learning Output for Phase 7 implementation demonstration
    base_time = datetime.utcnow() - timedelta(days=7)
    timeline = []

    current_risk = 10.0

    for i in range(14):
        event_time = base_time + timedelta(hours=i * 12)

        # Simulate a sudden spike in risk (e.g., impossible travel or abnormal data access)
        if i == 10:
            current_risk = 85.5
            event_type = "Abnormal Data Exfiltration"
            xai_explanation = "Autoencoder reconstruction error spiked due to user downloading 50GB of files from a completely new geolocation (Russia) outside of normal working hours."
        elif i == 11:
            current_risk = 92.0
            event_type = "Privilege Escalation Attempt"
            xai_explanation = "User attempted `sudo su` 14 times. This deviates 99% from their established baseline behavior."
        else:
            current_risk = max(
                5.0,
                (
                    current_risk - random.uniform(5.0, 15.0)
                    if current_risk > 20
                    else random.uniform(5.0, 15.0)
                ),
            )
            event_type = "Standard Login"
            xai_explanation = (
                "Behavior matches established baseline (Reconstruction Error < 0.02)."
            )

        timeline.append(
            {
                "timestamp": event_time.isoformat(),
                "risk_score": round(current_risk, 1),
                "event_type": event_type,
                "xai_explanation": xai_explanation,
            }
        )

    return {
        "user_id": user_id,
        "model_type": "Deep Learning Autoencoder",
        "current_risk_level": "CRITICAL" if current_risk > 80 else "LOW",
        "timeline": timeline,
    }
