import json
import os
import sys
import subprocess

def get_node_stats():
    stats = {}
    
    # Established connections
    try:
        established = os.popen("netstat -ant | grep ESTABLISHED | wc -l").read().strip()
        stats["established_connections"] = int(established) if established else 0
    except Exception:
        stats["established_connections"] = -1

    # Docker containers
    try:
        res = subprocess.run(["docker", "ps", "--format", "{{json .}}"], capture_output=True, text=True)
        lines = res.stdout.strip().split("\n")
        stats["docker_containers"] = len([l for l in lines if l])
    except Exception:
        stats["docker_containers"] = -1

    # OS Info
    try:
        uptime = os.popen("uptime -p").read().strip()
        stats["uptime"] = uptime
    except Exception:
        stats["uptime"] = "Unknown"

    print(json.dumps(stats))

if __name__ == "__main__":
    get_node_stats()
