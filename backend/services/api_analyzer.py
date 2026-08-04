import asyncio
from backend.core.logger import log as logger
from backend.core.db import insert_alert
from fastapi import FastAPI
import time

api_events_queue = asyncio.Queue()


class ShadowAPIDetector:
    def __init__(self, app: FastAPI):
        self.app = app
        self.known_paths = set()
        self.user_access_history = {}  # simple in-memory tracker for BOLA

    def update_schema(self):
        schema = self.app.openapi()
        paths = schema.get("paths", {})
        self.known_paths = set(paths.keys())

    async def run(self):
        logger.info("[API Analyzer] Shadow API and BOLA Detection Engine started...")
        while True:
            try:
                # Wait for API telemetry from middleware
                event = await api_events_queue.get()
                path = event.get("path")
                method = event.get("method")
                user = event.get("user")

                # Update schema periodically
                if len(self.known_paths) == 0:
                    self.update_schema()

                # 1. Shadow API Detection
                # Ignore internal routes like /docs or static files
                if path.startswith("/api/") and path not in self.known_paths:
                    # Very simple matching, in reality would use path templating regex
                    is_known = False
                    for p in self.known_paths:
                        if path.startswith(p.split("{")[0]):
                            is_known = True
                            break
                    if not is_known:
                        await insert_alert(
                            title=f"[SHADOW API] Undocumented Endpoint Accessed: {path}",
                            description=f"An active endpoint {method} {path} is not documented in the official OpenAPI spec.",
                            severity="high",
                            node_id="default",
                            kind="api_discovery",
                        )

                # 2. BOLA Detection (Fast Enumeration)
                if (
                    user and "{" in path
                ):  # Only track endpoints that take parameters like IDs
                    now = time.time()
                    if user not in self.user_access_history:
                        self.user_access_history[user] = []

                    history = self.user_access_history[user]
                    history.append({"path": path, "time": now})

                    # Keep last 60 seconds
                    history = [h for h in history if now - h["time"] < 60]
                    self.user_access_history[user] = history

                    if len(history) > 20:  # 20 parameterized accesses in 60s
                        await insert_alert(
                            title=f"[KNOWN THREAT: BOLA/IDOR] Automated Enumeration by {user}",
                            description=f"User {user} has made {len(history)} rapid requests to parameterized endpoints, indicating a potential Broken Object Level Authorization enumeration attack.",
                            severity="critical",
                            node_id="default",
                            kind="bola_attack",
                        )
                        # Clear history to prevent alert spam
                        self.user_access_history[user] = []

            except Exception as e:
                logger.error(f"[API Analyzer] Error processing event: {e}")
