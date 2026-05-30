import asyncio
import random
import time
import math
import json
import os
from datetime import datetime
from typing import List

# A global queue to hold CSI events to be broadcasted to clients
csi_queue = asyncio.Queue()
mesh_queue = asyncio.Queue()

# Global mode toggle
is_simulation = True
real_nodes = []

class SessionRecorder:
    def __init__(self):
        self.is_recording = False
        self.filename = ""
        self.file_handle = None
        
        # Ensure dir exists
        os.makedirs("data/captures", exist_ok=True)

    def start_recording(self):
        if self.is_recording:
            return self.filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = f"csi_capture_{timestamp}.jsonl"
        self.file_handle = open(os.path.join("data", "captures", self.filename), "a")
        self.is_recording = True
        return self.filename
        
    def stop_recording(self):
        if not self.is_recording:
            return None
        self.is_recording = False
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None
        return self.filename
        
    def record_payload(self, payload: dict):
        if self.is_recording and self.file_handle:
            self.file_handle.write(json.dumps(payload) + "\n")

recorder = SessionRecorder()

class CSIGenerator:
    def __init__(self):
        self.num_subcarriers = 64
        self.amplitudes = [random.uniform(10.0, 30.0) for _ in range(self.num_subcarriers)]
        self.running = False
        self.motion_active = False
        self.motion_end_time = 0

        self.typing_active = False
        self.typing_end_time = 0
        self.target_text = "ssh root@10.4.2.10 -p 22... \npassword: admin... \nAccess Granted... \n"
        self.typing_index = 0
        self.last_keystroke = ""

        self.heart_rate = 72
        self.radar_x = 0.5
        self.radar_y = 0.5
        
        self.words = ["hello", "system", "access", "password", "denied", "override", "root", "admin", "connect", "terminate"]
        self.gestures = ["SWIPE LEFT", "SWIPE RIGHT", "FIST CLENCH", "PALM OPEN", "ZOOM IN", "PINCH"]
        self.last_behavior = ""

    async def start(self):
        self.running = True
        while self.running:
            # Random walk for ambient noise
            for i in range(self.num_subcarriers):
                # Normal drift
                drift = random.uniform(-1.5, 1.5)
                self.amplitudes[i] += drift
                
                # Baseline constraint
                if self.amplitudes[i] < 5.0:
                    self.amplitudes[i] = 5.0
                elif self.amplitudes[i] > 40.0:
                    self.amplitudes[i] = 40.0

            # Simulate occasional motion events (spikes)
            current_time = time.time()
            if not self.motion_active and random.random() < 0.05: # 5% chance per tick to start motion
                self.motion_active = True
                self.motion_end_time = current_time + random.uniform(0.5, 2.0)
                
            if self.motion_active:
                if current_time > self.motion_end_time:
                    self.motion_active = False
                else:
                    # Apply a wave/spike over some subcarriers
                    center = random.randint(10, 54)
                    width = random.randint(3, 8)
                    for i in range(self.num_subcarriers):
                        dist = abs(i - center)
                        if dist < width:
                            # Spike amplitude based on distance from center
                            spike = (width - dist) * random.uniform(2.0, 5.0)
                            self.amplitudes[i] += spike

            # Simulate typing events (WiKey)
            if not self.typing_active and not self.motion_active and random.random() < 0.08: # 8% chance to type a key
                self.typing_active = True
                self.typing_end_time = current_time + random.uniform(0.1, 0.3)
                self.last_keystroke = ""

            if self.typing_active:
                if current_time > self.typing_end_time:
                    self.typing_active = False
                    char = self.target_text[self.typing_index]
                    self.last_keystroke = char
                    self.typing_index = (self.typing_index + 1) % len(self.target_text)
                else:
                    for i in range(15, 45):
                        self.amplitudes[i] += random.uniform(-8.0, 8.0)

            # Simulate Vital Signs (BPM drift)
            if random.random() < 0.1:
                self.heart_rate += random.uniform(-1.0, 1.0)
                self.heart_rate = max(60, min(100, self.heart_rate))
                
            # Simulate Radar (Target movement)
            self.radar_x += random.uniform(-0.02, 0.02)
            self.radar_y += random.uniform(-0.02, 0.02)
            self.radar_x = max(0.1, min(0.9, self.radar_x))
            self.radar_y = max(0.1, min(0.9, self.radar_y))
            
            # Simulate Behavior (Lip Reading / Gestures)
            if random.random() < 0.02:
                if random.random() < 0.5:
                    self.last_behavior = f"[SPEECH] \"{random.choice(self.words)}\""
                else:
                    self.last_behavior = f"[GESTURE] {random.choice(self.gestures)}"

            # Create data payload
            payload = {
                "node_id": "sim_node_1",
                "timestamp": time.time(),
                "amplitudes": self.amplitudes.copy(),
                "motion_detected": self.motion_active,
                "keystroke": self.last_keystroke,
                "text": self.target_text[:self.typing_index],
                "heart_rate": self.heart_rate,
                "behavior": self.last_behavior,
                "radar_x": self.radar_x,
                "radar_y": self.radar_y,
                "status": "SIMULATION"
            }
            
            recorder.record_payload(payload)
            await csi_queue.put(payload)
            
            # Reset event triggers
            if not self.typing_active:
                self.last_keystroke = ""
            self.last_behavior = ""
            
            # 10 Hz refresh rate for smooth animation
            await asyncio.sleep(0.1)

    def stop(self):
        self.running = False


class MeshGenerator:
    def __init__(self):
        self.running = False
        # Define 3 nodes in a 2D space (0 to 100)
        self.nodes = {
            "A": {"x": 10, "y": 10},
            "B": {"x": 90, "y": 10},
            "C": {"x": 50, "y": 90}
        }
        self.target = {"x": 50, "y": 50}
        self.target_vx = random.uniform(-1, 1)
        self.target_vy = random.uniform(-1, 1)

    def dist_to_line(self, p, a, b):
        # Distance from point p to line segment ab
        dx = b["x"] - a["x"]
        dy = b["y"] - a["y"]
        if dx == 0 and dy == 0:
            return math.hypot(p["x"] - a["x"], p["y"] - a["y"])
        
        t = ((p["x"] - a["x"]) * dx + (p["y"] - a["y"]) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))
        closest_x = a["x"] + t * dx
        closest_y = a["y"] + t * dy
        return math.hypot(p["x"] - closest_x, p["y"] - closest_y)

    async def start(self):
        self.running = True
        while self.running:
            # Move target
            self.target["x"] += self.target_vx
            self.target["y"] += self.target_vy
            
            # Bounce off walls
            if self.target["x"] < 0 or self.target["x"] > 100:
                self.target_vx *= -1
            if self.target["y"] < 0 or self.target["y"] > 100:
                self.target_vy *= -1

            # Occasionally change direction
            if random.random() < 0.05:
                self.target_vx = random.uniform(-1.5, 1.5)
                self.target_vy = random.uniform(-1.5, 1.5)

            # Calculate link disturbances
            dist_ab = self.dist_to_line(self.target, self.nodes["A"], self.nodes["B"])
            dist_bc = self.dist_to_line(self.target, self.nodes["B"], self.nodes["C"])
            dist_ca = self.dist_to_line(self.target, self.nodes["C"], self.nodes["A"])

            # Map distance to disturbance (0.0 to 1.0)
            def calc_disturbance(dist):
                if dist < 5.0:
                    return 1.0
                elif dist < 20.0:
                    return 1.0 - ((dist - 5.0) / 15.0)
                return 0.0

            payload = {
                "timestamp": time.time(),
                "nodes": self.nodes,
                "target": self.target,
                "links": {
                    "AB": {"disturbance": calc_disturbance(dist_ab)},
                    "BC": {"disturbance": calc_disturbance(dist_bc)},
                    "CA": {"disturbance": calc_disturbance(dist_ca)}
                }
            }

            recorder.record_payload(payload)
            await mesh_queue.put(payload)
            await asyncio.sleep(0.1)

    def stop(self):
        self.running = False


class BeaconProtocol(asyncio.DatagramProtocol):
    def datagram_received(self, data, addr):
        try:
            payload = json.loads(data.decode())
            payload["node_ip"] = addr[0]
            if not is_simulation:
                recorder.record_payload(payload)
                csi_queue.put_nowait(payload)
        except Exception:
            pass

class RealCSIGenerator:
    """
    Listens on UDP port 8001 for CSI data sent from deployed Netrunner Beacons.
    """
    def __init__(self):
        self.running = False
        self.transport = None
        
    async def start(self):
        self.running = True
        loop = asyncio.get_running_loop()
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: BeaconProtocol(),
            local_addr=('0.0.0.0', 8001)
        )
        
        while self.running:
            if not is_simulation and not self.transport:
                # Provide a fallback "waiting for data" payload for real nodes
                payload = {
                    "timestamp": time.time(),
                    "amplitudes": [0] * 64,
                    "motion_detected": False,
                    "keystroke": "",
                    "text": "WAITING FOR REAL HARDWARE DATA...",
                    "heart_rate": 0,
                    "behavior": "LISTENING ON UDP 8001",
                    "radar_x": 0.5,
                    "radar_y": 0.5,
                    "status": "WAITING_REAL_DATA"
                }
                recorder.record_payload(payload)
                await csi_queue.put(payload)
            await asyncio.sleep(1.0)
            
    def stop(self):
        self.running = False
        if self.transport:
            self.transport.close()

generator = CSIGenerator()
mesh_generator = MeshGenerator()
real_generator = RealCSIGenerator()

async def start_csi_engine():
    asyncio.create_task(generator.start())
    asyncio.create_task(mesh_generator.start())
    asyncio.create_task(real_generator.start())
