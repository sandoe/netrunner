"""WebSocket terminal — bidirectional xterm.js ↔ SSH/Telnet bridge."""
from __future__ import annotations

import asyncio
import json
import socket
import threading
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


from ..core.db import load_nodes_db

async def _load_node(nid: str) -> dict | None:
    nodes = await load_nodes_db()
    return nodes.get(nid)


# ---------------------------------------------------------------------------
# SSH terminal
# ---------------------------------------------------------------------------

async def _ssh_terminal(ws: WebSocket, nid: str, node: dict) -> None:
    from ..core.vault import load_credentials
    try:
        import paramiko  # type: ignore
    except ImportError:
        await ws.send_json({"type": "error", "data": "paramiko not installed"})
        return

    username, password = await load_credentials(nid)
    host = node["host"]
    port = int(node["port"])

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=host, port=port,
            username=username, password=password,
            timeout=10, look_for_keys=False, allow_agent=False,
        )
    except Exception as e:
        await ws.send_json({"type": "error", "data": f"SSH connect failed: {e}"})
        return

    chan = client.invoke_shell(term="xterm-256color", width=220, height=50)
    chan.settimeout(0.05)

    await ws.send_json({"type": "status", "connected": True})

    loop = asyncio.get_event_loop()
    stop = threading.Event()
    recv_queue: asyncio.Queue = asyncio.Queue()

    def _read_ssh():
        while not stop.is_set():
            try:
                data = chan.recv(4096)
                if not data:
                    break
                asyncio.run_coroutine_threadsafe(recv_queue.put(data), loop)
            except Exception:
                import time; time.sleep(0.05)
        asyncio.run_coroutine_threadsafe(recv_queue.put(None), loop)

    reader_thread = threading.Thread(target=_read_ssh, daemon=True)
    reader_thread.start()

    async def _send_to_client():
        while True:
            chunk = await recv_queue.get()
            if chunk is None:
                break
            try:
                await ws.send_json({"type": "output", "data": chunk.decode("utf-8", errors="replace")})
            except Exception:
                break

    send_task = asyncio.create_task(_send_to_client())

    try:
        while True:
            msg = await asyncio.wait_for(ws.receive_json(), timeout=30)
            if msg.get("type") == "input":
                data = msg.get("data", "")
                if isinstance(data, str):
                    data = data.encode("utf-8", errors="replace")
                chan.sendall(data)
            elif msg.get("type") == "resize":
                cols = int(msg.get("cols", 220))
                rows = int(msg.get("rows", 50))
                chan.resize_pty(width=cols, height=rows)
    except (WebSocketDisconnect, asyncio.TimeoutError, Exception):
        pass
    finally:
        stop.set()
        send_task.cancel()
        try:
            chan.close()
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass


class TelnetHandler:
    def __init__(self, cols: int = 220, rows: int = 50):
        self.state = "data"
        self.sb_buf = bytearray()
        self.option = None
        self.cmd = None
        self.cols = cols
        self.rows = rows

    def feed(self, data: bytes) -> tuple[bytes, bytes]:
        clean_data = bytearray()
        response = bytearray()
        
        i = 0
        n = len(data)
        while i < n:
            b = data[i]
            if self.state == "data":
                if b == 255: # IAC
                    self.state = "iac"
                else:
                    clean_data.append(b)
            elif self.state == "iac":
                if b in (251, 252, 253, 254): # WILL, WONT, DO, DONT
                    self.cmd = b
                    self.state = "opt"
                elif b == 250: # SB
                    self.state = "sb"
                    self.sb_buf.clear()
                elif b == 255: # Escaped IAC
                    clean_data.append(255)
                    self.state = "data"
                else:
                    self.state = "data"
            elif self.state == "opt":
                opt = b
                if self.cmd == 253: # DO
                    if opt == 1: # ECHO
                        response.extend(b"\xff\xfc\x01")
                    elif opt == 3: # SUPPRESS GO AHEAD
                        response.extend(b"\xff\xfb\x03")
                    elif opt == 24: # TERMINAL TYPE
                        response.extend(b"\xff\xfb\x18")
                    elif opt == 31: # NAWS (Window size)
                        response.extend(b"\xff\xfb\x1f")
                        response.extend(self.resize(self.cols, self.rows))
                    elif opt == 0: # BINARY TRANSMISSION
                        response.extend(b"\xff\xfb\x00")
                    else:
                        response.extend(bytes([255, 252, opt]))
                elif self.cmd == 254: # DONT
                    response.extend(bytes([255, 252, opt]))
                elif self.cmd == 251: # WILL
                    if opt == 1: # ECHO
                        response.extend(b"\xff\xfd\x01")
                    elif opt == 3: # SUPPRESS GO AHEAD
                        response.extend(b"\xff\xfd\x03")
                    elif opt == 0: # BINARY TRANSMISSION
                        response.extend(b"\xff\xfd\x00")
                    else:
                        response.extend(bytes([255, 253, opt]))
                elif self.cmd == 252: # WONT
                    response.extend(bytes([255, 254, opt]))
                self.state = "data"
            elif self.state == "sb":
                if b == 255: # IAC
                    self.state = "sb_iac"
                else:
                    self.sb_buf.append(b)
            elif self.state == "sb_iac":
                if b == 240: # SE
                    if len(self.sb_buf) > 1 and self.sb_buf[0] == 24: # TERMINAL TYPE
                        if self.sb_buf[1] == 1: # SEND
                            response.extend(b"\xff\xfa\x18\x00xterm-256color\xff\xf0")
                    self.state = "data"
                else:
                    self.sb_buf.append(255)
                    self.sb_buf.append(b)
                    self.state = "sb"
            i += 1
            
        return bytes(clean_data), bytes(response)

    def resize(self, cols: int, rows: int) -> bytes:
        self.cols = cols
        self.rows = rows
        w_h = (cols >> 8) & 0xff
        w_l = cols & 0xff
        h_h = (rows >> 8) & 0xff
        h_l = rows & 0xff
        return bytes([255, 250, 31, w_h, w_l, h_h, h_l, 255, 240])


# ---------------------------------------------------------------------------
# Telnet terminal
# ---------------------------------------------------------------------------

async def _telnet_terminal(ws: WebSocket, nid: str, node: dict) -> None:
    from ..core.session import session_manager
    session_manager.close(nid)

    try:
        host = node["host"]
        port = int(node["port"])
        loop = asyncio.get_event_loop()

        try:
            sock = socket.create_connection((host, port), timeout=10)
            sock.settimeout(0.05)
            # Send restore command sequence to turn stty echo back on, restore standard prompt, and reset TERM capability
            sock.sendall(b"\r\nstty echo; export TERM=xterm-256color; export PS1='\\h:\\w\\$ '; clear\r\n")
        except Exception as e:
            await ws.send_json({"type": "error", "data": f"Telnet connect failed: {e}"})
            return

        await ws.send_json({"type": "status", "connected": True})

        handler = TelnetHandler(cols=220, rows=50)
        stop = threading.Event()
        recv_queue: asyncio.Queue = asyncio.Queue()

        def _read_telnet():
            while not stop.is_set():
                try:
                    data = sock.recv(4096)
                    if not data:
                        break
                    asyncio.run_coroutine_threadsafe(recv_queue.put(data), loop)
                except socket.timeout:
                    continue
                except Exception:
                    break
            asyncio.run_coroutine_threadsafe(recv_queue.put(None), loop)

        reader_thread = threading.Thread(target=_read_telnet, daemon=True)
        reader_thread.start()

        async def _send_to_client():
            while True:
                chunk = await recv_queue.get()
                if chunk is None:
                    break
                try:
                    clean_data, response = handler.feed(chunk)
                    if response:
                        sock.sendall(response)
                    if clean_data:
                        await ws.send_json({"type": "output", "data": clean_data.decode("utf-8", errors="replace")})
                except Exception:
                    break

        send_task = asyncio.create_task(_send_to_client())

        try:
            while True:
                msg = await asyncio.wait_for(ws.receive_json(), timeout=60)
                if msg.get("type") == "input":
                    data = msg.get("data", "")
                    if isinstance(data, str):
                        data = data.encode("utf-8", errors="replace")
                    try:
                        sock.sendall(data)
                    except Exception:
                        break
                elif msg.get("type") == "resize":
                    cols = int(msg.get("cols", 220))
                    rows = int(msg.get("rows", 50))
                    resize_payload = handler.resize(cols, rows)
                    try:
                        sock.sendall(resize_payload)
                    except Exception:
                        break
        except (WebSocketDisconnect, asyncio.TimeoutError, Exception):
            pass
        finally:
            stop.set()
            send_task.cancel()
            try:
                sock.close()
            except Exception:
                pass
    finally:
        session_manager._no_auto_open.discard(nid)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@router.websocket("/ws/terminal/{nid}")
async def ws_terminal(ws: WebSocket, nid: str):
    await ws.accept()

    node = await _load_node(nid)
    if not node:
        await ws.send_json({"type": "error", "data": f"Node '{nid}' not found"})
        await ws.close()
        return

    transport = (node.get("transport") or "telnet").lower()

    if transport == "ssh":
        await _ssh_terminal(ws, nid, node)
    else:
        await _telnet_terminal(ws, nid, node)

    try:
        await ws.close()
    except Exception:
        pass
