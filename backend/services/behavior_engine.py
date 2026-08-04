import asyncio
import time
import random
from backend.core.logger import log as logger
from backend.core.db import insert_alert


class BehavioralBiometricsEngine:
    """
    Continuous Behavioral Authentication Engine.

    Simulates receiving frontend telemetry (mouse movements, keystroke cadence)
    and scores the patterns against a user's known baseline to detect
    Session Hijacking or Insider Threats without MFA friction.
    """

    def __init__(self):
        self.running = False
        self.baseline = {
            "admin_user": {
                "avg_dwell_time_ms": 110,  # Human average ~100-150ms
                "avg_flight_time_ms": 150,  # Human average ~150-250ms
                "mouse_velocity_px_s": 400,  # Moderate mouse speed
            }
        }

    async def start(self):
        self.running = True
        logger.info("[BIOMETRICS] Continuous Behavioral Authentication Engine started.")
        while self.running:
            await self._simulate_telemetry_stream()
            await asyncio.sleep(720)  # Check every 12 mins in simulation

    async def stop(self):
        self.running = False
        logger.info("[BIOMETRICS] Engine stopped.")

    async def _simulate_telemetry_stream(self):
        try:
            # 5% chance to simulate a hijacked session (robotic/attacker behavior)
            if random.randint(0, 100) < 5:
                # Simulated telemetry for a hijacked session
                hijack_telemetry = {
                    "user_id": "admin_user",
                    "avg_dwell_time_ms": 5,  # Robotic/scripted dwell time
                    "avg_flight_time_ms": 10,  # Impossible human flight time
                    "mouse_velocity_px_s": 8500,  # Erratic/Bot-like mouse snapping
                }

                await self._analyze_telemetry(hijack_telemetry)

        except Exception as e:
            logger.error(f"[BIOMETRICS] Analysis failed: {e}")

    async def _analyze_telemetry(self, telemetry: dict):
        user_id = telemetry["user_id"]
        baseline = self.baseline.get(user_id)

        if not baseline:
            return

        # Calculate deviation (simplistic anomaly score for simulation)
        dwell_dev = (
            abs(telemetry["avg_dwell_time_ms"] - baseline["avg_dwell_time_ms"])
            / baseline["avg_dwell_time_ms"]
        )
        flight_dev = (
            abs(telemetry["avg_flight_time_ms"] - baseline["avg_flight_time_ms"])
            / baseline["avg_flight_time_ms"]
        )
        mouse_dev = (
            abs(telemetry["mouse_velocity_px_s"] - baseline["mouse_velocity_px_s"])
            / baseline["mouse_velocity_px_s"]
        )

        anomaly_score = (dwell_dev + flight_dev + mouse_dev) / 3.0

        # If deviation is extreme (e.g. > 2.0 or 200% off baseline), it's a hijacking
        if anomaly_score > 2.0:
            await self._trigger_hijack_alert(user_id, telemetry, anomaly_score)

    async def _trigger_hijack_alert(self, user_id: str, telemetry: dict, score: float):
        alert_id = f"alert_bio_{int(time.time())}"

        description = (
            f"**[SESSION HIJACK / INSIDER THREAT DETECTED]**\n\n"
            f"**User:** `{user_id}`\n"
            f"**Anomaly Score:** `{score:.2f}x deviation`\n\n"
            f"Netrunner's Continuous Behavioral Authentication engine detected a massive deviation in typing cadence and mouse dynamics for the active session.\n"
            f"- **Expected Dwell Time:** ~{self.baseline[user_id]['avg_dwell_time_ms']}ms | **Detected:** {telemetry['avg_dwell_time_ms']}ms\n"
            f"- **Expected Mouse Velocity:** ~{self.baseline[user_id]['mouse_velocity_px_s']} px/s | **Detected:** {telemetry['mouse_velocity_px_s']} px/s\n\n"
            f"**Conclusion:** The input patterns are highly indicative of an automated script or an unauthorized physical user taking over an unlocked workstation.\n"
            f"**SOAR Action Initiated:** Terminating active session token and locking account."
        )

        alert = {
            "id": alert_id,
            "title": f"Behavioral Anomaly: Session Hijack Detected ({user_id})",
            "description": description,
            "severity": "critical",
            "status": "new",
            "created_at": time.time(),
            "updated_at": time.time(),
            "target_node": "Netrunner Console",
            "src_ip": "127.0.0.1",  # Internal session
        }
        await insert_alert(alert)
        logger.critical(
            f"[BIOMETRICS] Session Hijack detected for {user_id}! Extreme behavioral deviation."
        )


behavior_engine = BehavioralBiometricsEngine()


async def start_behavior_engine():
    await behavior_engine.start()


async def stop_behavior_engine():
    await behavior_engine.stop()
