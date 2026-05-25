import sys
sys.path.append("/home/aso/repos/projects/netrunner")

from backend.generators.docker import gen_docker

def run_tests():
    print("=== TEST 1: DOCKER RUN SIMPLE ===")
    print("\n".join(gen_docker({"name": "webserver", "image": "nginx:alpine", "action": "run"})))

    print("\n=== TEST 2: DOCKER RUN FULL ===")
    cfg_run = {
        "name": "postgres-db",
        "image": "postgres:15",
        "ports": "5432:5432, 5433:5433",
        "volumes": "/var/data/pg:/var/lib/postgresql/data",
        "env": "POSTGRES_PASSWORD=secret, POSTGRES_USER=netrunner",
        "options": "--restart unless-stopped",
        "action": "run"
    }
    print("\n".join(gen_docker(cfg_run)))

    print("\n=== TEST 3: DOCKER START ===")
    print("\n".join(gen_docker({"name": "postgres-db", "action": "start"})))

    print("\n=== TEST 4: DOCKER STOP ===")
    print("\n".join(gen_docker({"name": "postgres-db", "action": "stop"})))

    print("\n=== TEST 5: DOCKER RESTART ===")
    print("\n".join(gen_docker({"name": "postgres-db", "action": "restart"})))

    print("\n=== TEST 6: DOCKER DELETE ===")
    print("\n".join(gen_docker({"name": "postgres-db", "action": "delete"})))

    print("\n=== TEST 7: DOCKER PRUNE ===")
    print("\n".join(gen_docker({"action": "prune"})))

if __name__ == "__main__":
    run_tests()
