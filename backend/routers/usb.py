from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel


class PortPayload(BaseModel):
    port: str


import httpx
import asyncio
import threading
from .auth import authenticate_ws, get_current_user
from ..core.db import load_nodes_db

router = APIRouter()

# Global memory cache for USB devices reported by agents
usb_cache = {}


async def receive_agent_usb_data(node_id: str, devices: list):
    usb_cache[node_id] = devices


from ..core.session import session_manager


@router.get("/{node_id}")
async def get_node_usb_devices(node_id: str, user=Depends(get_current_user)):
    nodes = await load_nodes_db()
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found")

    devices = usb_cache.get(node_id, [])

    # Fallback to SSH if no agent data but SSH is connected
    if not devices and session_manager.is_connected(node_id):
        # Try Linux/RPi first
        results, err = await session_manager.run(
            node_id,
            nodes[node_id],
            ["ls /dev/ttyUSB* /dev/ttyACM* /dev/ttyAMA* 2>/dev/null || true"],
        )
        if results and not err:
            output_str = results[0].get("output", "")
            if output_str:
                for line in output_str.split("\n"):
                    for p in line.split():
                        if p.strip().startswith("/dev/"):
                            devices.append(
                                {"device": p.strip(), "name": "Serial Device (via SSH)"}
                            )

        # If still empty, try Windows PowerShell
        if not devices:
            win_results, win_err = await session_manager.run(
                node_id,
                nodes[node_id],
                ['powershell -Command "[System.IO.Ports.SerialPort]::GetPortNames()"'],
            )
            if win_results and not win_err:
                output_str = win_results[0].get("output", "")
                if output_str:
                    for line in output_str.split("\n"):
                        p = line.strip()
                        if p.startswith("COM"):
                            devices.append({"device": p, "name": "COM Port (via SSH)"})

    return {"devices": devices}


class SerialWritePayload(BaseModel):
    port: str
    data: str
    baud: int = 115200


@router.post("/{node_id}/write")
async def write_node_usb_serial(
    node_id: str, payload: SerialWritePayload, user=Depends(get_current_user)
):
    """
    Instructs the local agent on the node to write data to a specific serial port.
    """
    import httpx

    nodes = await load_nodes_db()
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found")

    node = nodes[node_id]
    host = node.get("host")
    if not host:
        raise HTTPException(status_code=400, detail="Node has no IP address to contact")

    # Send request to the agent's internal API (which we will build next)
    try:
        from .agent import get_agent_token

        # Assuming the agent will listen on port 8001
        agent_url = f"http://{host}:8001/serial/write"
        agent_token = await get_agent_token()
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                agent_url,
                json={"port": payload.port, "data": payload.data, "baud": payload.baud},
                headers={"Authorization": f"Bearer {agent_token}"},
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Agent responded with {resp.status_code}: {resp.text}",
                )
        return {"status": "ok"}
    except (httpx.RequestError, HTTPException) as e:
        # Fallback to SSH
        if session_manager.is_connected(node_id):
            try:
                if payload.port.upper().startswith("COM"):
                    cmd = f"powershell -Command \"$port = new-Object System.IO.Ports.SerialPort {payload.port},{payload.baud},None,8,one; $port.open(); $port.WriteLine('{payload.data}'); $port.Close()\""
                else:
                    cmd = f"python3 -c \"import serial; s=serial.Serial('{payload.port}', {payload.baud}, timeout=1); s.write({repr(payload.data + chr(10))}); s.close()\""
                results, err = await session_manager.run(node_id, node, [cmd])
                return {"status": "ok", "note": "Sent via SSH fallback"}
            except Exception as ssh_err:
                raise HTTPException(
                    status_code=503,
                    detail=f"Agent unreachable and SSH fallback failed: {ssh_err}",
                )

        raise HTTPException(
            status_code=503,
            detail=f"Failed to reach agent at {host} and SSH is disconnected: {e}",
        )


class UsbNukePayload(BaseModel):
    port: str


@router.post("/{node_id}/nuke")
async def nuke_node_usb_serial(
    node_id: str, payload: UsbNukePayload, user=Depends(get_current_user)
):
    nodes = await load_nodes_db()
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found")

    if not session_manager.is_connected(node_id):
        raise HTTPException(
            status_code=503, detail="SSH is disconnected. Connect to the node first."
        )

    from ..core.vault import load_credentials

    username, password = await load_credentials(node_id)
    node = nodes[node_id]

    # Use the password if available for sudo, otherwise try without
    if password:
        sudo_prefix = f"echo '{password}' | sudo -S "
    else:
        sudo_prefix = "sudo "

    # We must be careful not to kill netrunner-platform itself if this is the host machine
    kill_script = f"""
    for pid in $({sudo_prefix}lsof -t {payload.port} 2>/dev/null); do
        if ! {sudo_prefix}cat /proc/$pid/cmdline 2>/dev/null | tr '\\0' ' ' | grep -qE 'netrunner|docker|containerd'; then
            {sudo_prefix}kill -9 $pid || true
        fi
    done
    """

    cmds = [
        kill_script,
        f"{sudo_prefix}chmod 666 {payload.port} || chmod 666 {payload.port}",
    ]

    results, err = await session_manager.run(node_id, node, cmds)
    if err:
        raise HTTPException(status_code=500, detail=str(err))

    return {"status": "ok", "message": f"Nuked {payload.port} and reset permissions"}


async def set_proxy_pause_state(node_id: str, port: str, paused: bool):
    from ..core.vault import load_credentials

    nodes = await load_nodes_db()
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found")

    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    username, password = await load_credentials(node_id)
    node = nodes[node_id]

    port_safe = port.replace("/", "_")
    pause_file = f"/tmp/nr_proxy_pause_{port_safe}"

    if paused:
        file_cmd = f"touch {pause_file}"
    else:
        file_cmd = f"rm -f {pause_file}"

    signal_cmd = f"""
    for pid in $(lsof -t {port} 2>/dev/null); do
        if cat /proc/$pid/cmdline 2>/dev/null | tr '\\0' ' ' | grep -qE 'python3 -c .*py_proxy'; then
            kill -SIGUSR2 $pid || true
        fi
    done
    """

    cmds = [file_cmd, signal_cmd]
    results, err = await session_manager.run(node_id, node, cmds)
    if err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/{node_id}/pause")
async def pause_proxy(
    node_id: str, payload: PortPayload, user=Depends(get_current_user)
):
    """Temporarily yields the serial port without dropping the underlying proxy process"""
    await set_proxy_pause_state(node_id, payload.port, True)
    return {"status": "ok", "message": f"Paused proxy for {payload.port}"}


@router.post("/{node_id}/resume")
async def resume_proxy(
    node_id: str, payload: PortPayload, user=Depends(get_current_user)
):
    """Resumes control of the serial port"""
    await set_proxy_pause_state(node_id, payload.port, False)
    return {"status": "ok", "message": f"Resumed proxy for {payload.port}"}


@router.websocket("/monitor/{node_id}")
async def serial_monitor(
    ws: WebSocket,
    node_id: str,
    port: str = "",
    baud: int = 115200,
    reset: str = "false",
):
    if await authenticate_ws(ws, allowed_roles=("admin", "analyst")) is None:
        return
    await ws.accept()
    try:
        import paramiko
    except ImportError:
        await ws.send_json({"type": "error", "data": "paramiko not installed\\r\\n"})
        await ws.close()
        return

    from .nodes import load_nodes, _get_node_with_creds

    nodes = await load_nodes()
    if node_id not in nodes:
        await ws.send_json({"type": "error", "data": "Node not found\\r\\n"})
        await ws.close()
        return

    # Load node WITH credentials from vault
    node = await _get_node_with_creds(node_id, nodes)

    if not port:
        await ws.send_json({"type": "error", "data": "Port parameter required\\r\\n"})
        await ws.close()
        return

    # Use session_manager for SSH connection (uses vault credentials)
    if not session_manager.is_connected(node_id):
        success, err = await session_manager.open(node_id, node, auto=True)
        if not success:
            await ws.send_json(
                {"type": "error", "data": f"SSH connect failed: {err}\\r\\n"}
            )
            await ws.close()
            return

    session = session_manager.get_session(node_id)
    if not session or not hasattr(session, "client"):
        await ws.send_json({"type": "error", "data": "SSH session not available\\r\\n"})
        await ws.close()
        return

    client = session.client
    chan = client.get_transport().open_session()
    chan.settimeout(0.05)

    do_reset_str = "True" if str(reset).lower() == "true" else "False"

    if port.upper().startswith("COM"):
        # Windows
        ps = f"$p=new-Object System.IO.Ports.SerialPort {port},{baud},None,8,one;$p.Open();while($true){{if($p.BytesToRead -gt 0){{[byte[]]$b=new-object byte[] $p.BytesToRead;$p.Read($b,0,$b.Length)|Out-Null;[Console]::OpenStandardOutput().Write($b,0,$b.Length)}};Start-Sleep -Milliseconds 10}}"
        chan.exec_command(f'powershell -Command "{ps}"')
    else:
        # Linux
        # Use python to proxy the serial port if available, otherwise fallback to stty+cat
        py_proxy = f"""
import sys, select, time, signal, os
try:
    import serial
    s = serial.Serial()
    s.port = '{port}'
    s.baudrate = {baud}
    s.dtr = False
    s.rts = False
    s.timeout = 0

    port_safe = '{port}'.replace('/', '_')
    pause_file = f'/tmp/nr_proxy_pause_{{port_safe}}'
    paused = False
    pause_req = False
    resume_req = False

    def do_reset():
        try:
            if not paused and s.is_open:
                # Send Ctrl+C exactly once
                s.write(b'\\x03')
                time.sleep(0.2)
                # Send Ctrl+D for soft reboot
                s.write(b'\\x04')
        except Exception as e:
            sys.stdout.write(f'\\r\\n\\x1b[31m[RESET ERROR] {{str(e)}}\\x1b[0m\\r\\n')
            sys.stdout.flush()

    def handle_signal(sig, frame):
        global pause_req, resume_req
        if sig == signal.SIGUSR1:
            do_reset()
        elif sig == signal.SIGUSR2:
            if os.path.exists(pause_file):
                pause_req = True
            else:
                resume_req = True

    signal.signal(signal.SIGUSR1, handle_signal)
    signal.signal(signal.SIGUSR2, handle_signal)

    first_connect = True
    while True:
        if paused:
            if resume_req:
                resume_req = False
                paused = False
                sys.stdout.write(f'\\r\\n\\x1b[33m[SYSTEM] Port {{s.port}} resumed.\\x1b[0m\\r\\n')
                sys.stdout.flush()
                continue
            r, _, _ = select.select([sys.stdin], [], [], 0.1)
            if sys.stdin in r:
                d = sys.stdin.buffer.read1(1024)
                if not d: sys.exit(0)
            continue

        try:
            s.open()
            if first_connect and {do_reset_str}:
                first_connect = False
                time.sleep(0.5)
                do_reset()
            s.dtr = False
            s.rts = False
            try:
                while True:
                    if pause_req:
                        pause_req = False
                        paused = True
                        sys.stdout.write(f'\\r\\n\\x1b[33m[SYSTEM] Port {{s.port}} paused.\\x1b[0m\\r\\n')
                        sys.stdout.flush()
                        break
                    
                    r, _, _ = select.select([sys.stdin, s], [], [], 0.05)
                    if sys.stdin in r:
                        d = sys.stdin.buffer.read1(1024)
                        if not d: sys.exit(0) # EOF from SSH
                        s.write(d)
                    if s in r:
                        d = s.read(1024)
                        if d: sys.stdout.buffer.write(d); sys.stdout.buffer.flush()
            finally:
                s.close()
        except Exception as e:
            msg = str(e)
            if 'device reports readiness' in msg or 'I/O error' in msg or 'Permission denied' in msg or 'could not open port' in msg or 'Busy' in msg:
                sys.stdout.write(f'\\r\\n\\x1b[33m[SYSTEM] Port busy: {{msg}}. Retrying in 1.5s...\\x1b[0m\\r\\n')
                sys.stdout.flush()
                time.sleep(1.5)
            else:
                if not paused:
                    sys.stdout.write(msg + '\\n')
                    break
except Exception as e:
    sys.stdout.write(f'\\r\\n\\x1b[31m[PROXY ERROR] {{str(e)}}\\x1b[0m\\r\\n')
    sys.exit(1)
"""
        safe_proxy = py_proxy.replace("$", "\\$").replace("`", "\\`")
        cmd = f'stty -F {port} -hupcl; (python3 -c "{safe_proxy}" || (stty -F {port} {baud} raw -echo -echoe -echok -echoctl -echoke; cat {port})) 2>&1'
        chan.exec_command(cmd)

    await ws.send_json({"type": "status", "connected": True})

    loop = asyncio.get_event_loop()
    stop = threading.Event()
    recv_queue = asyncio.Queue()

    def _read_ssh():
        while not stop.is_set():
            try:
                data = chan.recv(4096)
                if not data:
                    break
                asyncio.run_coroutine_threadsafe(recv_queue.put(data), loop)
            except Exception:
                import time

                time.sleep(0.05)
        asyncio.run_coroutine_threadsafe(recv_queue.put(None), loop)

    reader_thread = threading.Thread(target=_read_ssh, daemon=True)
    reader_thread.start()

    async def _send_to_client():
        while True:
            chunk = await recv_queue.get()
            if chunk is None:
                break
            try:
                await ws.send_json(
                    {"type": "output", "data": chunk.decode("utf-8", errors="replace")}
                )
            except Exception:
                break

    send_task = asyncio.create_task(_send_to_client())

    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("type") == "input":
                data = msg.get("data", "")
                if data:
                    chan.sendall(data.encode("utf-8"))
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        stop.set()
        send_task.cancel()
        try:
            chan.close()
        except:
            pass
        try:
            client.close()
        except:
            pass
