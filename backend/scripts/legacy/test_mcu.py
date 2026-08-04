import asyncio
import sys

sys.path.insert(0, "/app")
from backend.core.session import session_manager
from backend.core.db import load_nodes_db


async def main():
    nodes = await load_nodes_db()
    for nid, node in nodes.items():
        if node.get("host") == "192.168.1.17":
            print("Found node:", nid)
            await session_manager.open(nid, node)
            res, err = await session_manager.run(
                nid,
                node,
                ["python3 /tmp/nr_scripts/nr_mcu_cli.py /dev/ttyUSB0 ls umqtt"],
            )
            print("ls umqtt:", res, err)
            res, err = await session_manager.run(
                nid,
                node,
                [
                    "python3 /tmp/nr_scripts/nr_mcu_cli.py /dev/ttyUSB0 read umqtt/simple.py"
                ],
            )
            print("read simple.py:", res, err)
            break


asyncio.run(main())
