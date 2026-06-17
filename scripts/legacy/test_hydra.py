import subprocess
import json

def has_docker():
    try:
        subprocess.run(["docker", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

def run_hydra(target, service):
    # Just a proof of concept
    print(has_docker())

run_hydra("127.0.0.1", "ssh")
