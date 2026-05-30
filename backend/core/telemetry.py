import asyncio
import logging
import time
from typing import Dict
from .session import session_manager
from .db import load_nodes_db

logger = logging.getLogger("telemetry")

# Global cache: node_id -> interface -> {rx_bytes, tx_bytes, timestamp, mbps_rx, mbps_tx}
telemetry_cache: Dict[str, Dict[str, dict]] = {}
telemetry_queue = asyncio.Queue()

async def poll_telemetry_loop():
    logger.info("Starting Telemetry polling loop...")
    while True:
        try:
            nodes = await load_nodes_db()
            
            async def poll_node(nid, node):
                try:
                    # Run cat /proc/net/dev to get stats
                    res, err = await session_manager.run(nid, node, ["cat /proc/net/dev"])
                    if err or not res:
                        return
                    out = res[0]
                    lines = out.split('\n')
                    
                    if nid not in telemetry_cache:
                        telemetry_cache[nid] = {}
                        
                    current_time = time.time()
                    
                    for line in lines[2:]: # Skip header lines
                        if ':' not in line:
                            continue
                        parts = line.split(':')
                        iface = parts[0].strip()
                        stats = parts[1].split()
                        if len(stats) >= 16:
                            rx_bytes = int(stats[0])
                            tx_bytes = int(stats[8])
                            
                            prev = telemetry_cache[nid].get(iface)
                            mbps_rx = 0.0
                            mbps_tx = 0.0
                            if prev:
                                delta_time = current_time - prev['timestamp']
                                if delta_time > 0:
                                    # bytes to bits (*8), divide by delta_time, divide by 1,000,000 for Mbps
                                    mbps_rx = max(0.0, (rx_bytes - prev['rx_bytes']) * 8 / 1000000 / delta_time)
                                    mbps_tx = max(0.0, (tx_bytes - prev['tx_bytes']) * 8 / 1000000 / delta_time)
                            
                            data = {
                                "rx_bytes": rx_bytes,
                                "tx_bytes": tx_bytes,
                                "timestamp": current_time,
                                "mbps_rx": round(mbps_rx, 2),
                                "mbps_tx": round(mbps_tx, 2)
                            }
                            telemetry_cache[nid][iface] = data
                            
                            # Put to queue for websocket
                            await telemetry_queue.put({
                                "type": "update",
                                "node_id": nid,
                                "interface": iface,
                                **data
                            })
                except Exception as e:
                    pass

            # Poll all nodes concurrently
            tasks = [poll_node(nid, n) for nid, n in nodes.items()]
            if tasks:
                await asyncio.gather(*tasks)
                
        except Exception as e:
            logger.error(f"Telemetry loop error: {e}")
            
        await asyncio.sleep(2.0)
