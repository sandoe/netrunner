import unittest
import requests
import json
import socket
import asyncio
import websockets
import time
import threading

API_BASE = "http://localhost:8000"
UDP_IP = "127.0.0.1"
UDP_PORT = 8001
WS_URL = "ws://localhost:8000/ws/csi"

class TestNetrunnerFAT(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Create a test node
        cls.test_node_ip = "192.168.99.99"
        cls.test_node_id = "fat_test_node_1"
        pass

    def test_01_node_crud(self):
        # 1. Add node
        payload = {"id": self.test_node_id, "ip": "192.168.99.100", "username": "fat", "password": "fat"}
        r = requests.post(f"{API_BASE}/api/wifi/beacons", json=payload)
        self.assertEqual(r.status_code, 200, "Failed to add node")
        
        # 2. Get nodes
        r2 = requests.get(f"{API_BASE}/api/wifi/beacons")
        nodes = r2.json().get("beacons", [])
        self.assertTrue(any(n["id"] == self.test_node_id for n in nodes), "Node not found in DB")
        
        # 3. Delete node
        r3 = requests.delete(f"{API_BASE}/api/wifi/beacons/{self.test_node_id}")
        self.assertEqual(r3.status_code, 200, "Failed to delete node")

    def test_02_deployment_template(self):
        # We test deployment template logic directly if possible.
        # But since it uses SSH and we don't have a real device, we'll verify the file template exists and contains {{NODE_ID}}
        with open("backend/core/beacon_script.py", "r") as f:
            content = f.read()
        self.assertIn('NODE_ID = "{{NODE_ID}}"', content, "NODE_ID template missing from beacon script")
        self.assertIn('"node_id": NODE_ID', content, "node_id payload missing from beacon script")

    def test_03_telemetry_pipeline(self):
        # Disable simulation mode so UDP packets are accepted
        requests.post(f"{API_BASE}/api/wifi/mode", json={"simulation": False, "nodes": ["fat_test_node_1"]})

        # We will spin up a websocket client, send UDP data, and verify receipt.
        received_data = []
        stop_event = threading.Event()

        async def ws_client():
            try:
                async with websockets.connect(WS_URL) as ws:
                    while not stop_event.is_set():
                        msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        data = json.loads(msg)
                        # The backend's simulation might be broadcasting. Filter for our specific mock payload.
                        if data.get("node_id") == "fat_test_node_1":
                            received_data.append(data)
                            break
            except Exception as e:
                pass

        def run_ws():
            asyncio.run(ws_client())

        t = threading.Thread(target=run_ws)
        t.start()
        time.sleep(1.0)

        # Send UDP packet
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = {
            "node_id": "fat_test_node_1",
            "timestamp": time.time(),
            "amplitudes": [10.0] * 64,
            "motion_detected": True,
            "keystroke": "F",
            "text": "Beacon Stream Active",
            "heart_rate": 80.0,
            "behavior": "FAT_TEST",
            "radar_x": 0.5,
            "radar_y": 0.5,
            "status": "BEACON_STREAMING"
        }
        # Send multiple to ensure it's picked up during the ws stream
        for _ in range(5):
            sock.sendto(json.dumps(payload).encode(), (UDP_IP, UDP_PORT))
            time.sleep(0.1)
        
        stop_event.set()
        t.join(timeout=3.0)

        self.assertTrue(len(received_data) > 0, "No valid data received via WebSocket matching our FAT UDP payload")
        data = received_data[0]
        
        # Verify normalization / payload format on broadcast
        self.assertEqual(data.get("node_id"), "fat_test_node_1", "Node ID mismatch")
        self.assertEqual(data.get("motion_detected"), True, "Motion mismatch")
        self.assertEqual(data.get("heart_rate"), 80.0, "Heart rate mismatch")
        self.assertEqual(data.get("keystroke"), "F", "Keystroke mismatch")
        self.assertEqual(data.get("radar_x"), 0.5, "Radar X mismatch")

if __name__ == '__main__':
    unittest.main()
