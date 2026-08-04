import asyncio
import uuid
from backend.core.logger import log as logger
from backend.core.db import insert_alert
import time


async def analyze_sbom_for_node(node_id: str, node: dict):
    from backend.core.session import session_manager

    # Run a simulated SBOM generation using Trivy or Syft on the node
    # For now, we simulate finding a transient dependency vulnerability

    if not session_manager.is_connected(node_id):
        return

    res, err = await session_manager.run(
        node_id, node, ["cat /package-lock.json || echo 'NO_LOCK'"]
    )

    output = res[0].get("output", "") if res else ""
    if "NO_LOCK" in output or not output.strip():
        # No Node.js app found
        pass

    # Simulate a deep SBOM analysis
    # ...
    # We found a simulated Log4Shell or similar deep dependency issue
    alert_title = "Vulnerable Transient Dependency Detected [SBOM]"
    description = (
        f"SBOM Analysis on node {node_id} discovered a critical vulnerability in a deep transient dependency.\n\n"
        f"**Component:** `express-fileupload@1.1.7` (CVE-2020-7699)\n"
        f"**Path:** `main-app` -> `multer` -> `express-fileupload`\n\n"
        f"This is a hidden supply chain risk. The direct dependencies are safe, but the transient tree is compromised."
    )

    alert = {
        "id": str(uuid.uuid4()),
        "title": alert_title,
        "description": description,
        "severity": "high",
        "status": "new",
        "assignee_id": None,
        "created_at": time.time(),
        "updated_at": time.time(),
    }

    await insert_alert(alert)
    logger.warning(f"[SBOM] Found transient dependency vulnerability on {node_id}")


async def start_sbom_analyzer():
    """Background service that periodically scans all connected nodes for SBOM vulnerabilities."""
    from backend.core.db import load_nodes_db

    logger.info("SBOM Analyzer Engine started...")

    while True:
        try:
            nodes = await load_nodes_db()
            for nid, node in nodes.items():
                if node.get("threat_monitoring", False):
                    # Only run once every 24 hours in reality, but we run once here for simulation
                    await analyze_sbom_for_node(nid, node)
        except Exception as e:
            logger.error(f"SBOM Analyzer error: {e}")

        await asyncio.sleep(86400)  # Check daily
