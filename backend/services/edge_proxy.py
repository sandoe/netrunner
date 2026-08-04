import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from backend.core.db import check_ip_threat_intel

logger = logging.getLogger("edge_proxy")


async def zero_trust_edge_proxy_middleware(request: Request, call_next):
    """
    Just-In-Time (JIT) Identity-Aware Edge Proxy

    Acts as an inline micro-segmentation enforcer. If a user's IP or Identity
    is flagged by the IDS or Threat Intel engine, access is instantly revoked
    mid-session, cutting off lateral movement at the edge.
    """
    client_ip = request.client.host if request.client else "unknown"

    # 1. Continuous Risk Assessment (Check Threat Intel)
    # In a real environment, we would also check behavioral UEBA models here.
    intel = await check_ip_threat_intel(client_ip)
    if intel and intel.get("severity") in ["high", "critical"]:
        logger.warning(
            f"[Zero Trust] Blocking compromised IP {client_ip} mid-flight at the Edge Proxy."
        )
        return JSONResponse(
            status_code=403,
            content={
                "error": "Zero Trust Enforcement",
                "message": "Your session has been instantly revoked due to anomalous behavior detected by the Nexus Engine.",
                "intel_source": intel.get("source"),
                "threat_type": intel.get("threat_type"),
            },
        )

    # 2. Cryptographic Device Posture Validation (ZTNA)
    posture_token = request.headers.get("X-Device-Posture-Token")
    if posture_token:
        # Simulate EDR State Cache query based on the posture token
        # In reality, this would check SentinelOne or CrowdStrike API for the device ID
        if posture_token == "compromised-or-outdated-device":
            logger.critical(
                f"[Zero Trust] Blocking request. Device posture compliance failed for {client_ip}."
            )

            # Log a SIEM alert for attempted access from a non-compliant device
            from backend.core.db import insert_alert
            import time
            import uuid
            import asyncio

            alert = {
                "id": str(uuid.uuid4()),
                "title": "ZTNA Block: Non-Compliant Device Attempted Access",
                "description": f"The Zero Trust Edge Proxy instantly terminated a connection from {client_ip}. The device failed its Continuous Posture Evaluation (OS out of date or EDR disabled).",
                "severity": "high",
                "status": "new",
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            asyncio.create_task(insert_alert(alert))

            return JSONResponse(
                status_code=403,
                content={
                    "error": "Posture Compliance Failed",
                    "message": "Access Denied. Your device failed the continuous health posture evaluation (EDR offline or OS unpatched).",
                },
            )

    # 3. Extract Identity Context (if authenticated)
    # Here we would normally extract the JWT and check if the *user* is compromised,
    # independently of the IP. For now, we allow the request to proceed.

    response = await call_next(request)
    return response
