"""
Netrunner Social Engineering Router — API endpoints for phishing simulation.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from .auth import require_admin
from ..core.social_engineering import (
    create_campaign,
    get_campaign,
    list_campaigns,
    list_templates,
    track_click,
    get_pretexting_scenarios,
    get_phishing_stats,
)

router = APIRouter()


class CampaignRequest(BaseModel):
    name: str
    template_id: str
    targets: list[dict]
    sender_name: str = "IT Support"
    company_name: str = "Acme Corp"
    tracking_url: str = "http://localhost:8000/phishing/track"


@router.get("/se/templates")
async def api_se_templates():
    """List available phishing templates."""
    templates = list_templates()
    return {"templates": templates}


@router.get("/se/campaigns")
async def api_se_campaigns():
    """List all phishing campaigns."""
    campaigns = list_campaigns()
    return {"campaigns": campaigns, "count": len(campaigns)}


@router.get("/se/campaigns/{campaign_id}")
async def api_se_campaign_detail(campaign_id: str):
    """Get campaign details."""
    campaign = await get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    return campaign


@router.post("/se/campaigns", dependencies=[Depends(require_admin)])
async def api_se_create_campaign(req: CampaignRequest):
    """
    Create a phishing simulation campaign.

    ⚠️  LEGAL: Only use for authorized security awareness training.
    """
    result = await create_campaign(
        name=req.name,
        template_id=req.template_id,
        targets=req.targets,
        sender_name=req.sender_name,
        company_name=req.company_name,
        tracking_url=req.tracking_url,
    )
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Failed"))
    return result


@router.get("/se/track/{email_id}")
async def api_se_track_click(email_id: str):
    """Track phishing link click (called when target opens the link)."""
    result = await track_click(email_id)
    return result


@router.get("/se/pretexting")
async def api_se_pretexting():
    """List predefined pretexting scenarios."""
    scenarios = get_pretexting_scenarios()
    return {"scenarios": scenarios}


@router.get("/se/stats")
async def api_se_stats():
    """Get overall phishing simulation statistics."""
    stats = get_phishing_stats()
    return stats
