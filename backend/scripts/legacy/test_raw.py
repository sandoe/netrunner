import asyncio
import sys
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
            node["username"] = un; node["password"] = pw
            await sm.open(nid, node, auto=True)
            
            # Use stty to configure, then send Ctrl-C and wait for output
            script = """#!/bin/bash
stty -F /dev/ttyUSB0 115200 raw -echo -hupcl
echo -ne '\\x03' > /dev/ttyUSB0
sleep 0.5
echo -ne '\\r\\n' > /dev/ttyUSB0
timeout 2 cat /dev/ttyUSB0
"""
            await sm.run(nid, node, ["cat << 'EOF_SCRIPT' > /tmp/raw_test.sh\n" + script + "\nEOF_SCRIPT"])
            out, err = await sm.run(nid, node, ["bash /tmp/raw_test.sh"])
            print("TARGET_OUT:", out)
            return
asyncio.run(run_test())
