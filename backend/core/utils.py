import subprocess


def cleanup_docker_containers():
    """Kill any docker containers associated with nodes, or test containers."""
    cmd = "docker rm -f $(docker ps -a -q -f name=test-sw -f name=netrunner-sw) 2>/dev/null || true"
    subprocess.run(cmd, shell=True, check=False)
