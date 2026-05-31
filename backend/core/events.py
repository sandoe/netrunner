"""Infrastructure events / alerts.

Turns the live data we already collect (reachability transitions, CPU/RAM
thresholds) into a stream of operational events so the user is told when
something goes wrong instead of having to watch the dashboard.
"""
import itertools
import time
from collections import deque

# Newest first; bounded ring buffer.
events: deque = deque(maxlen=300)
_counter = itertools.count(1)


def record_event(severity: str, node_id: str, node_name: str, kind: str, message: str) -> dict:
    """severity: info | warning | critical. Returns the event."""
    ev = {
        "id": next(_counter),
        "ts": time.time(),
        "severity": severity,
        "node_id": node_id,
        "node_name": node_name,
        "kind": kind,          # reachability | cpu | ram | ...
        "message": message,
    }
    events.appendleft(ev)
    # Broadcast over the telemetry websocket (lazy import avoids a cycle).
    try:
        from .telemetry import telemetry_queue
        telemetry_queue.put_nowait({"type": "event", **ev})
    except Exception:
        pass
    return ev


def recent_events(limit: int = 150) -> list:
    return list(itertools.islice(events, 0, limit))
