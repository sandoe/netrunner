import asyncio
import logging
import time
from typing import Dict
from .session import session_manager
from .db import load_nodes_db
from .state import telemetry_queue
from .events import record_event

logger = logging.getLogger("telemetry")

# Per-interface network cache (used by the topology link particles):
#   node_id -> interface -> {rx_bytes, tx_bytes, timestamp, mbps_rx, mbps_tx}
telemetry_cache: Dict[str, Dict[str, dict]] = {}

# Node-level real vitals derived over SSH (CPU%, RAM%, aggregate net):
#   node_id -> {cpu, ram, net_tx, net_rx, timestamp}
node_vitals: Dict[str, dict] = {}
# Rolling per-node history for the overview charts (last ~60 samples).
vitals_history: Dict[str, list] = {}
# Previous CPU jiffies for delta computation: node_id -> (busy, total)
_prev_cpu: Dict[str, tuple] = {}
# Per-node alert latch so we emit once on crossing a threshold, not every poll
_alert_state: Dict[str, dict] = {}
CPU_ALERT = 90.0
RAM_ALERT = 90.0


def _check_threshold(nid, name, metric, value, limit):
    st = _alert_state.setdefault(nid, {})
    over = value is not None and value >= limit
    if over and not st.get(metric):
        st[metric] = True
        record_event("warning", nid, name, metric, f"{name} {metric.upper()} high: {value}%")
    elif not over and st.get(metric):
        st[metric] = False

HISTORY_LEN = 60


def _parse_cpu(stat_out: str, nid: str) -> float | None:
    """CPU utilisation % from /proc/stat, computed as a delta between polls."""
    for line in stat_out.splitlines():
        if line.startswith("cpu "):
            parts = [int(x) for x in line.split()[1:] if x.isdigit()]
            if len(parts) < 5:
                return None
            idle = parts[3] + parts[4]              # idle + iowait
            total = sum(parts)
            busy = total - idle
            prev = _prev_cpu.get(nid)
            _prev_cpu[nid] = (busy, total)
            if not prev:
                return None
            dt_total = total - prev[1]
            dt_busy = busy - prev[0]
            if dt_total <= 0:
                return None
            return max(0.0, min(100.0, dt_busy / dt_total * 100.0))
    return None


def _parse_mem(mem_out: str) -> float | None:
    """RAM used % from /proc/meminfo (MemTotal vs MemAvailable)."""
    total = avail = None
    for line in mem_out.splitlines():
        if line.startswith("MemTotal:"):
            total = float(line.split()[1])
        elif line.startswith("MemAvailable:"):
            avail = float(line.split()[1])
    if total and avail is not None and total > 0:
        return max(0.0, min(100.0, (1.0 - avail / total) * 100.0))
    return None


async def poll_telemetry_loop():
    logger.info("Starting Telemetry polling loop...")
    while True:
        try:
            nodes = await load_nodes_db()

            async def poll_node(nid, node):
                try:
                    # Real vitals over SSH only: a separate exec channel that
                    # doesn't disturb an interactive session. Telnet (e.g. GNS3
                    # consoles) is a single shared stream, so we skip it.
                    if (node.get("transport") or "telnet").lower() != "ssh":
                        return
                    # Only poll nodes with a live session — don't auto-open.
                    if not session_manager.is_connected(nid):
                        return

                    res, err = await session_manager.run(
                        nid, node, ["cat /proc/stat", "cat /proc/meminfo", "cat /proc/net/dev"]
                    )
                    if err or not res or len(res) < 3:
                        return
                    stat_out = res[0].get("output", "")
                    mem_out = res[1].get("output", "")
                    net_out = res[2].get("output", "")

                    current_time = time.time()
                    cpu = _parse_cpu(stat_out, nid)
                    ram = _parse_mem(mem_out)
                    _name = node.get("name") or nid
                    _check_threshold(nid, _name, "cpu", cpu, CPU_ALERT)
                    _check_threshold(nid, _name, "ram", ram, RAM_ALERT)

                    # --- per-interface network (drives topology particles) ---
                    if nid not in telemetry_cache:
                        telemetry_cache[nid] = {}
                    total_rx = total_tx = 0.0
                    for line in net_out.split('\n')[2:]:  # skip headers
                        if ':' not in line:
                            continue
                        iface = line.split(':')[0].strip()
                        stats = line.split(':')[1].split()
                        if iface == 'lo' or len(stats) < 16:
                            continue
                        rx_bytes = int(stats[0])
                        tx_bytes = int(stats[8])
                        prev = telemetry_cache[nid].get(iface)
                        mbps_rx = mbps_tx = 0.0
                        if prev:
                            dt = current_time - prev['timestamp']
                            if dt > 0:
                                mbps_rx = max(0.0, (rx_bytes - prev['rx_bytes']) * 8 / 1e6 / dt)
                                mbps_tx = max(0.0, (tx_bytes - prev['tx_bytes']) * 8 / 1e6 / dt)
                        data = {
                            "rx_bytes": rx_bytes, "tx_bytes": tx_bytes,
                            "timestamp": current_time,
                            "mbps_rx": round(mbps_rx, 2), "mbps_tx": round(mbps_tx, 2),
                        }
                        telemetry_cache[nid][iface] = data
                        total_rx += mbps_rx
                        total_tx += mbps_tx
                        await telemetry_queue.put({
                            "type": "update", "node_id": nid, "interface": iface, **data
                        })

                    # --- node-level vitals + history ---
                    vit = {
                        "cpu": round(cpu, 1) if cpu is not None else None,
                        "ram": round(ram, 1) if ram is not None else None,
                        "net_tx": round(total_tx, 2),
                        "net_rx": round(total_rx, 2),
                        "timestamp": current_time,
                    }
                    node_vitals[nid] = vit
                    hist = vitals_history.setdefault(nid, [])
                    hist.append({
                        "time": int(current_time),
                        "cpu": vit["cpu"] or 0.0,
                        "ram": vit["ram"] or 0.0,
                        "net_tx": total_tx * 1e6 / 8,   # back to bytes/s-ish for the chart
                        "net_rx": total_rx * 1e6 / 8,
                    })
                    if len(hist) > HISTORY_LEN:
                        del hist[:-HISTORY_LEN]
                    await telemetry_queue.put({"type": "vitals", "node_id": nid, **vit})
                except Exception:
                    pass

            tasks = [poll_node(nid, n) for nid, n in nodes.items()]
            if tasks:
                await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(f"Telemetry loop error: {e}")

        await asyncio.sleep(2.0)
