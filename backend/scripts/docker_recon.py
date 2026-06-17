#!/usr/bin/env python3
import sys
import argparse
import socket
import json
import urllib.request
import urllib.error
import time
from pathlib import Path

def log_result(target, event_type, details, success=True):
    log_file = Path("/tmp/netrunner-docker.jsonl")
    result = {
        "timestamp": time.time(),
        "target": target,
        "type": event_type,
        "success": success,
        "details": details
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(result) + "\n")

def check_port(target, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    return sock.connect_ex((target, port)) == 0

def query_docker_api(target, endpoint):
    url = f"http://{target}:2375{endpoint}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                return json.loads(response.read().decode())
    except Exception:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description="Netrunner Docker Daemon Recon")
    parser.add_argument("--target", required=True, help="Target IP address")
    args = parser.parse_args()

    if not check_port(args.target, 2375):
        log_result(args.target, "error", "Port 2375 is closed. Docker Daemon is not exposed unauthenticated.", False)
        return

    log_result(args.target, "recon", "Unprotected Docker Daemon found on port 2375. Fetching data...", True)

    info = query_docker_api(args.target, "/info")
    if info:
        details = f"Server Version: {info.get('ServerVersion')}, OS: {info.get('OperatingSystem')}, Containers: {info.get('Containers')}"
        log_result(args.target, "info", details, True)

    containers = query_docker_api(args.target, "/containers/json?all=1")
    if containers:
        container_list = [f"{c.get('Names', [''])[0].strip('/')} ({c.get('Image')}) - {c.get('State')}" for c in containers]
        log_result(args.target, "containers", f"Found {len(containers)} containers:\n" + "\n".join(container_list), True)

    images = query_docker_api(args.target, "/images/json")
    if images:
        log_result(args.target, "images", f"Found {len(images)} images on host.", True)

if __name__ == "__main__":
    main()
