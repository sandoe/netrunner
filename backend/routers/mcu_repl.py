import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import paramiko
from ..core.db import load_nodes_db

router = APIRouter(prefix="/ws/mcu_repl", tags=["mcu_repl"])

@router.websocket("")
async def mcu_repl_endpoint(websocket: WebSocket, port: str, node_id: str = None):
    await websocket.accept()
    
    if not node_id:
        await websocket.send_text("\r\n[Error: No node_id provided!]\r\n")
        await websocket.close()
        return

    nodes = await load_nodes_db()
    if node_id not in nodes:
        await websocket.send_text("\r\n[Error: Node not found!]\r\n")
        await websocket.close()
        return
        
    node = nodes[node_id]
    host = node.get("host", "127.0.0.1")
    if host in ("127.0.0.1", "localhost", "0.0.0.0"):
        host = "host.docker.internal"
        
    transport_type = node.get("transport", "telnet").lower()
    if transport_type != "ssh":
        await websocket.send_text("\r\n[Error: REPL streaming is only supported for SSH nodes!]\r\n")
        await websocket.close()
        return

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    await websocket.send_text("\r\n[Backend: Connecting to node via SSH...]\r\n")
    from ..core.vault import load_credentials
    username, password = await load_credentials(node_id)
    
    try:
        # Use run_in_executor for the blocking connect
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            lambda: client.connect(
                hostname=host,
                port=int(node.get("port", 22)),
                username=username,
                password=password,
                timeout=60,
                look_for_keys=False,
                allow_agent=False,
                banner_timeout=60,
                auth_timeout=60
            )
        )
    except Exception as e:
        await websocket.send_text(f"\r\n[SSH Connect Error: {e}]\r\n")
        await websocket.close()
        return

    cmd = f"pkill -9 -f 'mpremote.*{port}' || true; timeout 15 python3 /tmp/nr_scripts/nr_mcu_cli.py {port} fix; stty eof undef; python3 -m mpremote connect {port} repl"
    
    try:
        transport = client.get_transport()
        channel = transport.open_session()
        channel.get_pty()  # Important for interactive terminal REPL
        channel.exec_command(cmd)

        async def read_from_ssh():
            while True:
                def _recv():
                    if channel.recv_ready():
                        return channel.recv(1024)
                    elif channel.recv_stderr_ready():
                        return channel.recv_stderr(1024)
                    if channel.exit_status_ready() and not channel.recv_ready():
                        return b""
                    import time
                    time.sleep(0.1)
                    return None
                    
                data = await loop.run_in_executor(None, _recv)
                if data == b"":
                    break
                if data is not None:
                    await websocket.send_text(data.decode("utf-8", errors="replace"))
                else:
                    await asyncio.sleep(0.01)

        async def write_to_ssh():
            while True:
                try:
                    data = await websocket.receive_text()
                    channel.sendall(data.encode("utf-8"))
                except WebSocketDisconnect:
                    break

        tasks = [
            asyncio.create_task(read_from_ssh()),
            asyncio.create_task(write_to_ssh())
        ]
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in tasks:
            t.cancel()
    except Exception as e:
        print(f"WebSocket REPL Error: {e}")
    finally:
        try:
            # Send Ctrl+C to stop REPL cleanly
            channel.sendall(b"\x03")
        except:
            pass
            
        try:
            # Kill any lingering mpremote process on this specific port
            kill_ch = client.get_transport().open_session()
            kill_ch.exec_command(f"pkill -9 -f \'mpremote.*{port}\' || true")
            kill_ch.recv_exit_status()
            kill_ch.close()
        except:
            pass
            
        try:
            channel.close()
            client.close()
        except:
            pass
