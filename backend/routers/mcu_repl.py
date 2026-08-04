import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import paramiko
from ..core.db import load_nodes_db
from .auth import authenticate_ws

router = APIRouter(prefix="/ws/mcu_repl", tags=["mcu_repl"])


@router.websocket("")
async def mcu_repl_endpoint(websocket: WebSocket, port: str, node_id: str = None):
    if await authenticate_ws(
        websocket, allowed_roles=("admin", "analyst")
    ) is None:
        return
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
        await websocket.send_text(
            "\r\n[Error: REPL streaming is only supported for SSH nodes!]\r\n"
        )
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
                auth_timeout=60,
            ),
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

        from ..core.session import WebSocketParamikoBridge

        bridge = WebSocketParamikoBridge(
            websocket, channel, is_json=False, timeout=None
        )
        await bridge.run()
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
            kill_ch.exec_command(f"pkill -9 -f 'mpremote.*{port}' || true")
            kill_ch.recv_exit_status()
            kill_ch.close()
        except:
            pass

        try:
            channel.close()
            client.close()
        except:
            pass
