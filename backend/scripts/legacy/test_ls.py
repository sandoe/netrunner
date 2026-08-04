import asyncio
from backend.core.session import session_manager
from backend.core.db import load_nodes_db
from backend.core.vault import load_credentials


async def main():
    nodes = await load_nodes_db()
    node = nodes["n1780913184722"]
    un, pw = await load_credentials("n1780913184722")
    node["username"] = un
    node["password"] = pw

    res, err = await session_manager.run(
        "n1780913184722", node, ["ls -la /tmp/nr_scripts", "find /tmp/nr_scripts"]
    )
    print(res)


asyncio.run(main())
