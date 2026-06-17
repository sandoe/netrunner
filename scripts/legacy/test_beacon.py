import socket
import time
import json
import random

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
payload = {"test": 1}
# simulate unreachable
try:
    sock.sendto(json.dumps(payload).encode(), ("192.168.255.255", 8001))
    print("sent")
except Exception as e:
    print("error", e)
