import asyncio
from backend.core.logger import log as logger
from backend.core.db import load_nodes_db

async def start_scanner():
    logger.info("Starting Vulnerability Scanner...")
    while True:
        await asyncio.sleep(45)
        nodes = await load_nodes_db()
        if not nodes:
            logger.info("VulnScanner: No active nodes to scan.")
            continue
            
        for node_id, node_data in nodes.items():
            # Mock report generation
            logger.info(f"VulnScanner: Generated mock vulnerability report for node {node_data.get('name', node_id)}")
