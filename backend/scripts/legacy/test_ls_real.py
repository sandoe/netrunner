import asyncio
from backend.core.session import session_manager
from backend.core.db import load_nodes_db
from backend.core.vault import load_credentials
from backend.routers.mcu import ensure_mcu_cli


async def main():
    nodes = await load_nodes_db()
    node = nodes["n1780913184722"]
    un, pw = await load_credentials("n1780913184722")
    node["username"] = un
    node["password"] = pw

    await ensure_mcu_cli("n1780913184722", node)

    res, err = await session_manager.run(
        "n1780913184722",
        node,
        ["python3 /tmp/nr_scripts/nr_mcu_cli.py /dev/ttyUSB0 ls /"],
    )
    print(res)


asyncio.run(main())
