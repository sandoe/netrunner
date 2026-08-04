import asyncio
import sys
import time

sys.path.insert(0, "/app")
from backend.core.db import load_nodes_db
from backend.core.session import SessionManager
from backend.core.vault import load_credentials


async def run_test():
    sm = SessionManager()
    nodes = await load_nodes_db()
    for nid, node in nodes.items():
        if node.get("host") == "192.168.1.17":
            un, pw = await load_credentials(nid)
            node["username"] = un
            node["password"] = pw
            print(f"Connecting to {nid}...")
            res, err = await sm.open(nid, node, auto=True)
            if not res:
                print("Failed to connect!")
                return

            print("Fixing permissions...")
            chmod_cmd = f"echo {pw} | sudo -S chmod a+rw /dev/ttyUSB0"
            await sm.run(nid, node, [chmod_cmd])

            print("Uploading scripts...")
            await sm.run(nid, node, ["mkdir -p /tmp/nr_scripts"])
            await sm.upload_file(
                nid,
                node,
                "/app/backend/scripts/mpremote_api.py",
                "/tmp/nr_scripts/mpremote_api.py",
            )
            await sm.upload_file(
                nid,
                node,
                "/app/backend/scripts/nr_mcu_cli.py",
                "/tmp/nr_scripts/nr_mcu_cli.py",
            )

            cmds = [
                ("LS", "python3 /tmp/nr_scripts/nr_mcu_cli.py /dev/ttyUSB0 ls /"),
                (
                    "CREATE_TEST_FILE",
                    "echo 'Hello from Antigravity SSH test!' > /tmp/test_file.txt",
                ),
                (
                    "WRITE",
                    "python3 /tmp/nr_scripts/nr_mcu_cli.py /dev/ttyUSB0 write /hello.txt /tmp/test_file.txt",
                ),
                (
                    "READ",
                    "python3 /tmp/nr_scripts/nr_mcu_cli.py /dev/ttyUSB0 read /hello.txt",
                ),
                (
                    "RM",
                    "python3 /tmp/nr_scripts/nr_mcu_cli.py /dev/ttyUSB0 rm /hello.txt",
                ),
            ]

            for name, cmd in cmds:
                print(f"--- RUNNING {name} ---")
                start = time.monotonic()
                try:
                    out, err = await sm.run(nid, node, [f"timeout 30 {cmd}"])
                    print(f"OUTPUT: {out}")
                    print(f"ERROR: {err}")
                except Exception as e:
                    print(f"EXCEPTION: {e}")
                print(f"Time taken: {time.monotonic() - start:.2f}s\n")

            print("ALL DONE")
            return


asyncio.run(run_test())
