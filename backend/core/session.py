"""Session management: Telnet + SSH clients with connection pooling."""
from __future__ import annotations

import asyncio
import re
import socket
import threading
import time
from typing import Optional

try:
    import paramiko  # type: ignore
    _HAS_PARAMIKO = True
except ImportError:
    _HAS_PARAMIKO = False


SHELL_PROMPTS = ["# ", "$ ", ":~# ", ":~$ ", "> "]
LOGIN_PROMPTS  = ["login:", "Login:"]
PASS_PROMPTS   = ["Password:", "password:"]


# ---------------------------------------------------------------------------
# Telnet client
# ---------------------------------------------------------------------------

class TelnetClient:
    IAC  = 255
    WILL = 251; WONT = 252; DO = 253; DONT = 254
    SB   = 250; SE   = 240

    def __init__(self, host: str, port: int, timeout: int = 15):
        self.host = host
        self.port = int(port)
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self._buf = b""
        self._lock = threading.Lock()

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.sock.settimeout(0.3)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    def _recv(self) -> bytes:
        if not self.sock: return b""
        try:
            return self.sock.recv(4096)
        except (socket.timeout, BlockingIOError):
            return b""
        except (ConnectionResetError, BrokenPipeError, OSError):
            self.close()
            return b""

    def _process(self, data: bytes) -> bytes:
        """Strip IAC negotiation bytes and respond automatically."""
        out  = bytearray()
        resp = bytearray()
        i = 0
        while i < len(data):
            b = data[i]
            if b == self.IAC and i + 1 < len(data):
                cmd = data[i + 1]
                if cmd == self.IAC:
                    out.append(self.IAC); i += 2
                elif cmd in (self.WILL, self.WONT, self.DO, self.DONT) and i + 2 < len(data):
                    opt = data[i + 2]
                    # Simple rule: DONT/WONT to everything we don't handle
                    resp.extend([self.IAC, self.DONT if cmd == self.WILL else self.WONT, opt])
                    i += 3
                elif cmd == self.SB:
                    j = i + 2
                    while j < len(data) - 1:
                        if data[j] == self.IAC and data[j + 1] == self.SE:
                            j += 2; break
                        j += 1
                    i = j
                else:
                    i += 2
            else:
                out.append(b); i += 1
        if resp and self.sock:
            try:
                self.sock.sendall(bytes(resp))
            except Exception:
                pass
        return bytes(out)

    @staticmethod
    def _strip_ansi(s: str) -> str:
        return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", s)

    def read_until(self, patterns, timeout: float = 10) -> str:
        if isinstance(patterns, (str, bytes)):
            patterns = [patterns]
        bpats = [p.encode() if isinstance(p, str) else p for p in patterns]
        deadline = time.time() + timeout
        while time.time() < deadline:
            chunk = self._recv()
            if chunk:
                self._buf += self._process(chunk)
            if not self.sock:
                break
            for p in bpats:
                idx = self._buf.find(p)
                if idx >= 0:
                    end = idx + len(p)
                    data, self._buf = self._buf[:end], self._buf[end:]
                    return self._strip_ansi(data.decode("utf-8", errors="replace"))
            time.sleep(0.05)
        
        # If we broke out because socket is closed or lost
        if not self.sock:
            raise ConnectionError("Telnet connection lost during command execution")
        # If we reached the deadline without matching any patterns
        raise TimeoutError(f"Command execution timed out (expected prompts: {patterns})")

    def write(self, data: str | bytes) -> None:
        if isinstance(data, str):
            data = data.encode()
        if not self.sock:
            raise ConnectionError("socket is closed")
        try:
            self.sock.sendall(data + b"\r\n")
        except (BrokenPipeError, ConnectionResetError, OSError):
            self.close()
            raise ConnectionError("socket connection lost")

    def alive(self) -> bool:
        if not self.sock: return False
        try:
            # Check if socket is still readable/writable
            self.sock.send(b"", 0)
            return True
        except:
            self.close()
            return False

    def close(self) -> None:
        if self.sock:
            try:
                # Restore terminal echo and prompt states before disconnecting
                self.sock.sendall(b"\r\nstty echo; export PS1='\\h:\\w\\$ '\r\n")
                time.sleep(0.1)
            except Exception:
                pass
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def _drain(self) -> None:
        if not self.sock: return
        prev_to = self.sock.gettimeout()
        try:
            self.sock.settimeout(0.01)
            while True:
                try:
                    chunk = self.sock.recv(4096)
                    if not chunk: break
                except (socket.timeout, BlockingIOError, OSError):
                    break
        finally:
            if self.sock:
                try: self.sock.settimeout(prev_to)
                except Exception: pass
        self._buf = b""

    def run_command(self, cmd: str, timeout: float = 15) -> str:
        with self._lock:
            self._drain()
            self.write(cmd)
            try:
                raw = self.read_until(["NR_PROMPT# "], timeout=timeout)
            except TimeoutError as e:
                # Recover by sending Ctrl+C to interrupt the hung command on the node
                try:
                    if self.sock:
                        self.sock.sendall(b"\x03")
                        time.sleep(0.5)
                        self._drain()
                except Exception:
                    pass
                # Safely close the socket so a fresh, clean connection is opened next time
                self.close()
                raise e
            lines = raw.split("\n")
            # Remove echo if present
            if lines and cmd.strip() in lines[0]:
                lines = lines[1:]
            # Clean up trailing prompts robustly
            if lines:
                last_line = lines[-1].strip()
                if last_line == "NR_PROMPT#":
                    lines.pop()
                else:
                    if lines[-1].endswith("NR_PROMPT# "):
                        lines[-1] = lines[-1][:-11]
                    elif lines[-1].endswith("NR_PROMPT#"):
                        lines[-1] = lines[-1][:-10]
            return "\n".join(lines).strip()




# ---------------------------------------------------------------------------
# SSH client
# ---------------------------------------------------------------------------

class SshClient:
    def __init__(self, host: str, port: int, username: str, password: str, timeout: int = 15):
        self.host = host
        self.port = int(port)
        self.username = username or "root"
        self.password = password or ""
        self.timeout = timeout
        self.client: Optional["paramiko.SSHClient"] = None
        self._lock = threading.Lock()

    def connect(self) -> None:
        if not _HAS_PARAMIKO:
            raise RuntimeError("paramiko is not installed")
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            timeout=60,
            look_for_keys=False,
            allow_agent=False,
            banner_timeout=60,
            auth_timeout=60,
        )
        transport = self.client.get_transport()
        if transport:
            transport.set_keepalive(30)

    def alive(self) -> bool:
        if not self.client: return False
        try:
            transport = self.client.get_transport()
            return transport is not None and transport.is_active()
        except:
            return False

    def close(self) -> None:
        if self.client:
            try: self.client.close()
            except: pass
        self.client = None

    def run_command(self, cmd: str, timeout: float = 15) -> str:
        with self._lock:
            if not self.client:
                raise ConnectionError("SSH client is not connected")
            _, stdout, stderr = self.client.exec_command(cmd, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace").strip()
            err = stderr.read().decode("utf-8", errors="replace").strip()
            if err:
                return (out + "\n" + err).strip() if out else err
            return out


# ---------------------------------------------------------------------------
# Session manager
# ---------------------------------------------------------------------------

class SessionManager:
    def __init__(self):
        self._sessions: dict[str, TelnetClient | SshClient] = {}
        self._lock = threading.Lock()
        self._cmd_locks: dict[str, threading.Lock] = {}
        self._no_auto_open: set[str] = set()
        self._failed_attempts: dict[str, float] = {}

    def _cmd_lock(self, nid: str) -> threading.Lock:
        with self._lock:
            if nid not in self._cmd_locks:
                self._cmd_locks[nid] = threading.Lock()
            return self._cmd_locks[nid]

    async def open(self, nid: str, node: dict, auto: bool = False) -> tuple[bool, Optional[str]]:
        """Open a session. Returns (success, error_message)."""
        import time
        with self._lock:
            if nid in self._no_auto_open and auto:
                return False, "Node intentionally disconnected"
            if auto and self._failed_attempts.get(nid, 0) > time.time():
                return False, "Cooldown active due to recent failure"
            self._no_auto_open.discard(nid)
            
        transport = (node.get("transport") or "telnet").lower()
        
        # Use a thread for the blocking connection part
        def _do_connect():
            target_host = node["host"]
            if target_host in ("127.0.0.1", "localhost", "0.0.0.0"):
                target_host = "host.docker.internal"

            if transport == "ssh":
                cl = SshClient(target_host, node["port"], node.get("username") or "root", node.get("password", ""))
                try:
                    cl.connect()
                    return cl, None
                except Exception as e:
                    return None, str(e)
            else:
                cl = TelnetClient(target_host, node["port"])
                try:
                    cl.connect()
                    # Send Ctrl+C to interrupt any running or stuck processes
                    try:
                        if cl.sock:
                            cl.sock.sendall(b"\x03")
                            time.sleep(0.2)
                    except Exception:
                        pass
                    # Initial setup
                    cl.write("")
                    cl.read_until(SHELL_PROMPTS + LOGIN_PROMPTS + PASS_PROMPTS + ["NR_PROMPT# "], timeout=8)
                    # Handled simplified login for now
                    cl.write('export TERM=dumb; PS1="NR_PROMPT# "; stty -echo 2>/dev/null')
                    cl.read_until(["NR_PROMPT# "], timeout=5)
                    return cl, None
                except Exception as e:
                    cl.close()
                    return None, str(e)

        loop = asyncio.get_event_loop()
        cl, err = await loop.run_in_executor(None, _do_connect)
        
        with self._lock:
            if cl:
                old = self._sessions.pop(nid, None)
                if old: old.close()
                self._sessions[nid] = cl
                self._failed_attempts.pop(nid, None)
                return True, None
            else:
                import time
                self._failed_attempts[nid] = time.time() + 60
                return False, err

    def get_session(self, nid: str) -> Optional[TelnetClient | SshClient]:
        with self._lock:
            s = self._sessions.get(nid)
            if s and s.alive():
                return s
            self._sessions.pop(nid, None)
            return None

    def is_connected(self, nid: str) -> bool:
        return self.get_session(nid) is not None

    def close(self, nid: str) -> None:
        with self._lock:
            self._no_auto_open.add(nid)
            s = self._sessions.pop(nid, None)
        if s: s.close()

    def active_ids(self) -> list[str]:
        with self._lock:
            return [nid for nid, s in self._sessions.items() if s.alive()]

    def close_all(self) -> None:
        with self._lock:
            sessions = dict(self._sessions)
            self._sessions.clear()
        for s in sessions.values():
            s.close()

    async def run(self, nid: str, node: dict, commands: list[str]) -> tuple[list, Optional[str]]:
        """Run a list of commands, with auto-reconnect logic."""
        with self._cmd_lock(nid):
            session = self.get_session(nid)
            if not session:
                success, err = await self.open(nid, node, auto=True)
                if not success: return [], err
                session = self.get_session(nid)

            results = []
            for cmd in commands:
                if not cmd.strip(): continue
                try:
                    out = session.run_command(cmd)
                    results.append({"command": cmd, "output": out, "error": None})
                except Exception as e:
                    # Attempt ONE reconnect if session died
                    if not session.alive():
                        success, _ = await self.open(nid, node, auto=True)
                        if success:
                            session = self.get_session(nid)
                            try:
                                out = session.run_command(cmd)
                                results.append({"command": cmd, "output": out, "error": None})
                                continue
                            except: pass
                    results.append({"command": cmd, "output": "", "error": str(e)})
                    break
            return results, None


session_manager = SessionManager()
