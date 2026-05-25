import base64
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from .auth import require_admin
from ..core.db import load_nodes_db
from ..core.vault import load_credentials
from ..core.session import session_manager

router = APIRouter()

class DeceptionPayload(BaseModel):
    persona: str = "banking"
    port: int = 2222
    aggressiveness: str = "tarpit"

def generate_mirage_script(persona: str, aggressiveness: str) -> str:
    return f"""
import socket
import paramiko
import threading
import time
import sys
import random

HOST_KEY = paramiko.RSAKey.generate(2048)

class MirageServer(paramiko.ServerInterface):
    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL
        
    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def get_allowed_auths(self, username):
        return 'password'

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True
        
    def check_channel_shell_request(self, channel):
        return True

def handle_cmd(cmd, chan):
    cmd = cmd.strip()
    if not cmd:
        return
        
    if cmd in ['ls', 'ls -la', 'll']:
        if '{persona}' == 'banking':
            chan.send('drwxr-xr-x 2 root root 4096 Jan 1 00:00 .\\r\\n')
            chan.send('-rw------- 1 root root 1024 Jan 1 00:00 SWIFT_transfers.csv\\r\\n')
            chan.send('-rw------- 1 root root  512 Jan 1 00:00 admin_passwords.txt\\r\\n')
        elif '{persona}' == 'hr':
            chan.send('-rw-r--r-- 1 root root 8192 Jan 1 00:00 employee_salaries_2026.xlsx\\r\\n')
        else:
            chan.send('-rw------- 1 root root 9999 Jan 1 00:00 classified_project_mirage.pdf\\r\\n')
            
    elif cmd.startswith('cat '):
        filename = cmd.split(' ', 1)[1]
        content = f"CONFIDENTIAL DATA FOR {{filename}}\\n" * 50
        
        if '{aggressiveness}' == 'tarpit':
            # Cognitive Tarpit: send 1 byte at a time extremely slowly
            for char in content:
                chan.send(char)
                time.sleep(0.5) # 1 byte every 0.5s = 2 bps!
        else:
            chan.send(content.replace('\\n', '\\r\\n'))
            
    elif cmd == 'whoami':
        chan.send('root\\r\\n')
    elif cmd == 'id':
        chan.send('uid=0(root) gid=0(root) groups=0(root)\\r\\n')
    else:
        chan.send(f"bash: {{cmd}}: command not found\\r\\n")

    if '{aggressiveness}' == 'tarpit' and random.random() < 0.2:
        chan.send("\\r\\n\\033[91m[SYSTEM] Tracing connection origin... IP identified.\\033[0m\\r\\n")

def handle_client(client_sock):
    transport = paramiko.Transport(client_sock)
    transport.add_server_key(HOST_KEY)
    server = MirageServer()
    try:
        transport.start_server(server=server)
        chan = transport.accept(20)
        if chan is None:
            return
            
        chan.send("\\r\\n\\033[92mWelcome to Project Mirage (Node {persona.upper()})\\033[0m\\r\\n")
        chan.send("root@mirage:~# ")
        
        buf = ""
        while True:
            char = chan.recv(1).decode('utf-8')
            if not char:
                break
            if char == '\\r':
                chan.send('\\r\\n')
                handle_cmd(buf, chan)
                buf = ""
                chan.send("root@mirage:~# ")
            elif char == '\\x03': # Ctrl+C
                chan.send('^C\\r\\nroot@mirage:~# ')
                buf = ""
            elif char == '\\x04': # Ctrl+D
                break
            else:
                buf += char
                chan.send(char)
                
    except Exception as e:
        print(e)
    finally:
        transport.close()

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', 2222))
    sock.listen(100)
    print("Project Mirage listening on port 2222...")
    while True:
        client, addr = sock.accept()
        print(f"Connection from {{addr}}")
        threading.Thread(target=handle_client, args=(client,)).start()

if __name__ == '__main__':
    main()
"""

@router.post("/nodes/{nid}/deception/deploy", dependencies=[Depends(require_admin)])
async def api_deploy_deception(nid: str, payload: DeceptionPayload):
    nodes = await load_nodes_db()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    node = dict(nodes[nid])
    username, password = await load_credentials(nid)
    node["username"] = username
    node["password"] = password

    # 1. Check if docker is installed
    check_docker = "docker --version"
    res, err = await session_manager.run(nid, node, [check_docker])
    if err or not res[0].get("output"):
        raise HTTPException(400, "Docker is not installed on the target node. Please install Docker first.")

    # 2. Generate script and Dockerfile
    mirage_py = generate_mirage_script(payload.persona, payload.aggressiveness)
    dockerfile = """
FROM python:3.10-alpine
RUN pip install cryptography paramiko
COPY mirage.py /mirage.py
EXPOSE 2222
CMD ["python", "/mirage.py"]
"""

    b64_py = base64.b64encode(mirage_py.encode()).decode()
    b64_df = base64.b64encode(dockerfile.encode()).decode()

    commands = [
        "mkdir -p /tmp/mirage",
        f"echo {b64_py} | base64 -d > /tmp/mirage/mirage.py",
        f"echo {b64_df} | base64 -d > /tmp/mirage/Dockerfile",
        "cd /tmp/mirage && docker build -t project-mirage .",
        # Remove existing container if any
        "docker rm -f mirage_honeypot 2>/dev/null || true",
        # Run new container
        f"docker run -d --name mirage_honeypot -p {payload.port}:2222 project-mirage"
    ]

    res, err = await session_manager.run(nid, node, commands)
    if err:
        raise HTTPException(500, f"Failed to deploy Mirage Honeypot: {err}")

    return {
        "status": "success",
        "message": f"Holographic Honeypot '{payload.persona}' deployed successfully on port {payload.port} with '{payload.aggressiveness}' mode."
    }
