import socket
import json
import time
import random
import sys

TARGET_IP = "127.0.0.1"
TARGET_PORT = 8001
NODE_ID = "test_beacon_123"

def send_mock_data():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"Sending mock telemetry to {TARGET_IP}:{TARGET_PORT} for node: {NODE_ID}")
    
    try:
        while True:
            # Generate random subcarrier amplitudes
            amps = [random.uniform(0, 30) for _ in range(64)]
            
            payload = {
                "node_id": NODE_ID,
                "timestamp": time.time(),
                "amplitudes": amps,
                "motion_detected": max(amps) > 25.0,
                "keystroke": random.choice(["A", "B", "C", "D", "E"]) if random.random() > 0.8 else "",
                "text": "Beacon Stream Active",
                "heart_rate": 75 + random.uniform(-5, 5),
                "behavior": "BEHAVIOR_NORMAL",
                "radar_x": 0.5 + random.uniform(-0.1, 0.1),
                "radar_y": 0.5 + random.uniform(-0.1, 0.1),
                "status": "BEACON_STREAMING"
            }
            
            sock.sendto(json.dumps(payload).encode(), (TARGET_IP, TARGET_PORT))
            print(".", end="", flush=True)
            time.sleep(0.1)  # 10Hz
    except KeyboardInterrupt:
        print("\nStopped.")
        
if __name__ == "__main__":
    send_mock_data()
