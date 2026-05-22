import asyncio
from datetime import datetime
from .state import global_state
from .db import load_nodes_db

class SOAREngine:
    def __init__(self):
        self.action_logs = []

    async def process_event(self, event):
        if not global_state.autopilot:
            return

        if event.get("severity") == "critical":
            target_ip = event["target"]["ip"]
            # Check if this IP belongs to any of our nodes
            nodes = await load_nodes_db()
            for nid, node in nodes.items():
                if node.get("host") == target_ip:
                    # To avoid circular imports, import here
                    from ..routers.defense import api_defense_isolate
                    # AI triggers isolation!
                    try:
                        await api_defense_isolate(nid)
                        now = datetime.now()
                        log_msg = {
                            "timestamp": now.isoformat(),
                            "message": f"[AI AUTOPILOT] Isolated node {node.get('name', nid)} ({target_ip}) due to critical threat: {event.get('type')}",
                            "ts": now.strftime("%H:%M:%S"),
                            "msg": f"[AI AUTOPILOT] Isolated node {node.get('name', nid)} ({target_ip}) due to critical threat: {event.get('type')}"
                        }
                        self.action_logs.insert(0, log_msg)
                        if len(self.action_logs) > 50:
                            self.action_logs.pop()
                    except Exception as e:
                        print(f"[SOAR] Failed to isolate node: {e}")

soar_engine = SOAREngine()
