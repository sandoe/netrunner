"""
Netrunner Social Engineering Module — Phishing awareness and simulation tools.

Provides:
- Phishing email template generation
- Credential harvesting simulation
- Pretexting scenario builder
- Security awareness training tools

⚠️  LEGAL NOTICE: These tools are for AUTHORIZED security awareness training
    and penetration testing only. Unauthorized social engineering is illegal.
"""
import asyncio
import json
import os
import time
import uuid
from typing import Optional
from backend.core.logger import log as logger

SE_DIR = "data/social_engineering"


def _ensure_se_dir():
    os.makedirs(SE_DIR, exist_ok=True)
    os.makedirs(os.path.join(SE_DIR, "campaigns"), exist_ok=True)
    os.makedirs(os.path.join(SE_DIR, "templates"), exist_ok=True)
    os.makedirs(os.path.join(SE_DIR, "results"), exist_ok=True)


# Pre-built phishing templates
PHISHING_TEMPLATES = [
    {
        "id": "password_expire",
        "name": "Password Expiration",
        "category": "credential",
        "description": "Classic password expiration notification",
        "subject": "Your password will expire in 24 hours",
        "body": """Dear {target_name},

Your corporate password will expire in 24 hours. To avoid account lockout, please update your password immediately by clicking the link below:

{tracking_url}

If you do not update your password, you will be locked out of all corporate systems.

IT Security Team""",
        "sender_display": "IT Security",
        "sender_email": "security@company-portal.com",
    },
    {
        "id": "vpn_update",
        "name": "VPN Client Update",
        "category": "malware",
        "description": "Fake VPN client update notification",
        "subject": "Urgent: VPN Client Security Update Required",
        "body": """Dear {target_name},

A critical security vulnerability has been discovered in our VPN client. All employees must update immediately.

Download the latest version here: {tracking_url}

This update patches CVE-2024-XXXXX which allows remote code execution.

IT Operations""",
        "sender_display": "IT Operations",
        "sender_email": "vpn-updates@company-support.com",
    },
    {
        "id": "share_file",
        "name": "Shared Document",
        "category": "credential",
        "description": "Fake shared document notification",
        "subject": "{sender_name} shared a document with you",
        "body": """Dear {target_name},

{sender_name} has shared a confidential document with you.

Document: Q4_Financial_Report_2024.xlsx
Shared via: Corporate SharePoint

Click here to view the document: {tracking_url}

This link will expire in 48 hours.

SharePoint Online""",
        "sender_display": "Microsoft SharePoint",
        "sender_email": "noreply@sharepoint-online.com",
    },
    {
        "id": "hr_survey",
        "name": "HR Benefits Survey",
        "category": "credential",
        "description": "Fake HR benefits survey",
        "subject": "Action Required: Annual Benefits Enrollment Survey",
        "body": """Dear {target_name},

It's time for our annual benefits enrollment survey. Please complete the survey by {deadline} to ensure your benefits selections are current.

Take the survey here: {tracking_url}

Your participation is mandatory per company policy.

Human Resources""",
        "sender_display": "Human Resources",
        "sender_email": "benefits@company-hr.com",
    },
    {
        "id": "invoice",
        "name": "Pending Invoice",
        "category": "financial",
        "description": "Fake invoice notification",
        "subject": "Overdue Invoice - Immediate Payment Required",
        "body": """Dear {target_name},

Our records indicate that invoice #INV-2024-{random_num} is overdue.

Amount: $2,450.00
Due Date: {deadline}
Status: OVERDUE

Please process payment immediately to avoid service interruption: {tracking_url}

Accounts Payable""",
        "sender_display": "Accounts Payable",
        "sender_email": "billing@vendor-payments.com",
    },
    {
        "id": "wireless_cert",
        "name": "WiFi Certificate Update",
        "category": "credential",
        "description": "Fake WiFi certificate update",
        "subject": "WiFi Certificate Expiring - Action Required",
        "body": """Dear {target_name},

The wireless network security certificate for {company_name} will expire on {deadline}.

To maintain uninterrupted WiFi access, please install the new certificate: {tracking_url}

Without this update, you will be unable to connect to the corporate WiFi network.

Network Operations""",
        "sender_display": "Network Operations",
        "sender_email": "wifi-cert@company-network.com",
    },
]


async def create_campaign(
    name: str,
    template_id: str,
    targets: list[dict],
    sender_name: str = "IT Support",
    company_name: str = "Acme Corp",
    tracking_url: str = "http://localhost:8000/phishing/track",
) -> dict:
    """
    Create a phishing simulation campaign.

    Args:
        name: Campaign name
        template_id: Template to use
        targets: List of target dicts with name, email
        sender_name: Name to use as sender
        company_name: Target company name
        tracking_url: URL for tracking clicks

    Returns:
        dict with campaign details
    """
    _ensure_se_dir()
    campaign_id = f"camp_{int(time.time())}"

    template = next((t for t in PHISHING_TEMPLATES if t["id"] == template_id), None)
    if not template:
        return {"success": False, "error": f"Template '{template_id}' not found"}

    emails = []
    for target in targets:
        email_id = str(uuid.uuid4())[:8]
        personalized_body = template["body"].format(
            target_name=target.get("name", "Employee"),
            sender_name=sender_name,
            company_name=company_name,
            tracking_url=f"{tracking_url}?id={email_id}",
            deadline="2024-12-31",
            random_num=str(int(time.time()) % 10000),
        )
        personalized_subject = template["subject"].format(
            target_name=target.get("name", "Employee"),
            sender_name=sender_name,
        )

        emails.append({
            "id": email_id,
            "to": target.get("email", ""),
            "to_name": target.get("name", ""),
            "subject": personalized_subject,
            "body": personalized_body,
            "sender": template["sender_email"],
            "sender_display": sender_name,
            "status": "draft",
        })

    campaign = {
        "id": campaign_id,
        "name": name,
        "template_id": template_id,
        "template_name": template["name"],
        "category": template["category"],
        "sender_name": sender_name,
        "company_name": company_name,
        "emails": emails,
        "created_at": time.time(),
        "status": "created",
        "stats": {
            "total": len(emails),
            "sent": 0,
            "opened": 0,
            "clicked": 0,
            "credentials_submitted": 0,
        },
    }

    # Save campaign
    campaign_path = os.path.join(SE_DIR, "campaigns", f"{campaign_id}.json")
    with open(campaign_path, "w") as f:
        json.dump(campaign, f, indent=2)

    logger.info(f"[SE] Campaign created: {name} ({len(emails)} targets)")

    return {
        "success": True,
        "campaign_id": campaign_id,
        "name": name,
        "emails_generated": len(emails),
        "template": template["name"],
    }


async def get_campaign(campaign_id: str) -> Optional[dict]:
    """Get campaign details."""
    campaign_path = os.path.join(SE_DIR, "campaigns", f"{campaign_id}.json")
    if os.path.exists(campaign_path):
        with open(campaign_path) as f:
            return json.load(f)
    return None


def list_campaigns() -> list[dict]:
    """List all campaigns."""
    _ensure_se_dir()
    campaigns = []
    for f in sorted(os.listdir(os.path.join(SE_DIR, "campaigns")), reverse=True):
        if f.endswith(".json"):
            try:
                with open(os.path.join(SE_DIR, "campaigns", f)) as fh:
                    data = json.load(fh)
                    campaigns.append({
                        "id": data["id"],
                        "name": data["name"],
                        "template_name": data.get("template_name", ""),
                        "status": data["status"],
                        "created_at": data["created_at"],
                        "stats": data.get("stats", {}),
                    })
            except Exception:
                pass
    return campaigns


def list_templates() -> list[dict]:
    """List available phishing templates."""
    return PHISHING_TEMPLATES


async def track_click(email_id: str) -> dict:
    """Track when a target clicks the phishing link."""
    _ensure_se_dir()
    logger.warning(f"[SE] Phishing link clicked: {email_id}")

    # Find and update the campaign
    for f in os.listdir(os.path.join(SE_DIR, "campaigns")):
        if f.endswith(".json"):
            path = os.path.join(SE_DIR, "campaigns", f)
            try:
                with open(path) as fh:
                    data = json.load(fh)
                for email in data.get("emails", []):
                    if email["id"] == email_id:
                        email["status"] = "clicked"
                        email["clicked_at"] = time.time()
                        data["stats"]["clicked"] = data["stats"].get("clicked", 0) + 1
                        with open(path, "w") as fh:
                            json.dump(data, fh, indent=2)
                        return {"success": True, "message": "Click tracked"}
            except Exception:
                pass

    return {"success": False, "message": "Email not found"}


def get_pretexting_scenarios() -> list[dict]:
    """List predefined pretexting scenarios for social engineering tests."""
    scenarios = [
        {
            "id": "it_support",
            "name": "IT Support Call",
            "description": "Pretend to be IT support calling about a critical security issue",
            "script": [
                "Hi, this is {agent_name} from IT Security. We've detected unusual activity on your account.",
                "For verification, could you confirm your employee ID and current system password?",
                "We need to reset your credentials immediately to prevent data breach.",
            ],
            "tips": "Use a confident, urgent tone. Reference the recent security incident.",
            "category": "phone",
        },
        {
            "id": "delivery_person",
            "name": "Delivery Personnel",
            "description": "Impersonate delivery person to gain physical access",
            "script": [
                "Hi, I have a package for {target_name}. Could you sign for it?",
                "The label says it's urgent - maybe from the IT department?",
                "Could you point me to where I should leave this? I need to use the restroom too.",
            ],
            "tips": "Carry a clipboard and wear a uniform. Look confident.",
            "category": "physical",
        },
        {
            "id": "new_employee",
            "name": "New Employee",
            "description": "Pretend to be a new employee who forgot their badge",
            "script": [
                "Hi, I'm new here. My name is {agent_name} and I'm starting today in Marketing.",
                "I forgot my badge at home. Could you hold the door for me?",
                "Which way to the HR office? I need to complete my onboarding.",
            ],
            "tips": "Dress professionally. Carry an empty folder. Be friendly.",
            "category": "physical",
        },
        {
            "id": "vendor",
            "name": "Vendor/Contractor",
            "description": "Impersonate a vendor to gain network access",
            "script": [
                "Hi, I'm from {vendor_name}. We're here for the scheduled maintenance.",
                "We need to connect to your network to update the firewall firmware.",
                "Could you provide the WiFi password or a network jack?",
            ],
            "tips": "Carry tool bags. Wear a lanyard with a fake badge. Be assertive.",
            "category": "physical",
        },
        {
            "id": "executive_phish",
            "name": "Executive Impersonation",
            "description": "Pretend to be a senior executive requesting urgent action",
            "script": [
                "This is {exec_name}, CEO. I need you to do something urgent.",
                "I'm in a board meeting and can't talk. Wire $5000 to this account immediately.",
                "Don't call me back. Just do it now. This is time-sensitive.",
            ],
            "tips": "Use urgency and authority. Reference real executive names.",
            "category": "email",
        },
    ]
    return scenarios


def get_phishing_stats() -> dict:
    """Get overall phishing simulation statistics."""
    _ensure_se_dir()
    stats = {
        "total_campaigns": 0,
        "total_emails": 0,
        "total_clicked": 0,
        "total_credentials": 0,
        "click_rate": 0.0,
    }

    for f in os.listdir(os.path.join(SE_DIR, "campaigns")):
        if f.endswith(".json"):
            try:
                with open(os.path.join(SE_DIR, "campaigns", f)) as fh:
                    data = json.load(fh)
                    s = data.get("stats", {})
                    stats["total_campaigns"] += 1
                    stats["total_emails"] += s.get("total", 0)
                    stats["total_clicked"] += s.get("clicked", 0)
                    stats["total_credentials"] += s.get("credentials_submitted", 0)
            except Exception:
                pass

    if stats["total_emails"] > 0:
        stats["click_rate"] = round(stats["total_clicked"] / stats["total_emails"] * 100, 1)

    return stats
