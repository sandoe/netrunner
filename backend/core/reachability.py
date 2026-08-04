"""Active reachability probing.

For every node we open a TCP connection to its management host:port (e.g. SSH 22
or a GNS3 telnet console port). This is distinct per node (even GNS3 consoles,
which each get their own port), needs no root/ICMP, and yields a real connect
latency — i.e. "can I actually reach this node's service right now".
"""

import asyncio
import time

from .db import load_nodes_db

# node_id -> {reachable: bool, latency_ms: float|None, ts: float}
reach_status: dict = {}

CHECK_INTERVAL = 5.0
TIMEOUT = 1.5

# GNS3 L2 fabric — no usable console, so a refused TCP probe isn't "down".
CONSOLELESS = {
    "ethernet_switch",
    "ethernet_hub",
    "frame_relay_switch",
    "atm_switch",
    "cloud",
    "nat",
}


def _is_consoleless(node: dict) -> bool:
    nt = (node.get("metadata") or {}).get("gns3", {}).get("node_type")
    return nt in CONSOLELESS


async def _tcp_check(host: str, port: int):
    loop = asyncio.get_event_loop()
    t0 = loop.time()
    try:
        fut = asyncio.open_connection(host, port)
        _, writer = await asyncio.wait_for(fut, timeout=TIMEOUT)
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=0.5)
        except Exception:
            pass
        return True, round((loop.time() - t0) * 1000, 1)
    except Exception:
        return False, None


async def reachability_loop(queue):
    """Probe all nodes every CHECK_INTERVAL and push results onto `queue`
    (the telemetry queue, broadcast over /ws/telemetry as type 'reach')."""
    while True:
        try:
            nodes = await load_nodes_db()

            async def chk(nid, n):
                host = n.get("host")
                port = n.get("port") or 22
                if not host or _is_consoleless(n):
                    return  # L2 fabric: no console to probe, never "offline"
                try:
                    ok, lat = await _tcp_check(str(host), int(port))
                except Exception:
                    ok, lat = False, None
                # Alert on transitions; also alert once if a node is already
                # DOWN on first sight (but stay quiet for healthy nodes).
                prev = reach_status.get(nid)
                from .events import record_event

                name = n.get("name") or nid
                if prev is None:
                    if not ok:
                        record_event(
                            "critical", nid, name, "reachability", f"{name} is OFFLINE"
                        )
                elif prev.get("reachable") != ok:
                    if ok:
                        record_event(
                            "info",
                            nid,
                            name,
                            "reachability",
                            f"{name} is back ONLINE ({lat} ms)",
                        )
                    else:
                        record_event(
                            "critical",
                            nid,
                            name,
                            "reachability",
                            f"{name} went OFFLINE",
                        )
                reach_status[nid] = {
                    "reachable": ok,
                    "latency_ms": lat,
                    "ts": time.time(),
                }
                try:
                    queue.put_nowait(
                        {
                            "type": "reach",
                            "node_id": nid,
                            "reachable": ok,
                            "latency_ms": lat,
                        }
                    )
                except Exception:
                    pass

            await asyncio.gather(*[chk(nid, n) for nid, n in nodes.items()])
        except Exception:
            pass
        await asyncio.sleep(CHECK_INTERVAL)
