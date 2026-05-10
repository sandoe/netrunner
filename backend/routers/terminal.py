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


# ---------------------------------------------------------------------------
# Telnet terminal (raw passthrough)
# ---------------------------------------------------------------------------

async def _telnet_terminal(ws: WebSocket, nid: str, node: dict) -> None:
    host = node["host"]
    port = int(node["port"])
    loop = asyncio.get_event_loop()

    try:
        sock = socket.create_connection((host, port), timeout=10)
        sock.settimeout(0.05)
    except Exception as e:
        await ws.send_json({"type": "error", "data": f"Telnet connect failed: {e}"})
        return

    await ws.send_json({"type": "status", "connected": True})

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
                await ws.send_json({"type": "output", "data": chunk.decode("utf-8", errors="replace")})
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
    except (WebSocketDisconnect, asyncio.TimeoutError, Exception):
        pass
    finally:
        stop.set()
        send_task.cancel()
        try:
            sock.close()
        except Exception:
            pass


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
