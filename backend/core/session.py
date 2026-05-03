"""Session management: Telnet + SSH clients with connection pooling."""
from __future__ import annotations

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

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.sock.settimeout(0.3)

    def _recv(self) -> bytes:
        try:
            return self.sock.recv(4096)
        except socket.timeout:
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
        if resp:
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
            for p in bpats:
                idx = self._buf.find(p)
                if idx >= 0:
                    end = idx + len(p)
                    data, self._buf = self._buf[:end], self._buf[end:]
                    return self._strip_ansi(data.decode("utf-8", errors="replace"))
            time.sleep(0.05)
        data, self._buf = self._buf, b""
        return self._strip_ansi(data.decode("utf-8", errors="replace"))

    def write(self, data: str | bytes) -> None:
        if isinstance(data, str):
            data = data.encode()
        if not self.sock:
            raise ConnectionError("socket is closed")
        self.sock.sendall(data + b"\r\n")

    def alive(self) -> bool:
        return self.sock is not None

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def run_command(self, cmd: str, timeout: float = 15) -> str:
        self._buf = b""
        self.write(cmd)
        raw = self.read_until(["# "], timeout=timeout)
        lines = raw.split("\n")
        if lines and cmd.strip() in lines[0]:
            lines = lines[1:]
        while lines and lines[-1].strip() in ("# ", "#", ""):
            lines.pop()
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
        self.sock = True  # mirrors TelnetClient.alive() interface

    def connect(self) -> None:
        if not _HAS_PARAMIKO:
            raise RuntimeError("paramiko is not installed — run: pip install paramiko")
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            timeout=self.timeout,
            look_for_keys=False,
            allow_agent=False,
            banner_timeout=10,
        )

    def alive(self) -> bool:
        try:
            return bool(
                self.client
                and self.client.get_transport()
                and self.client.get_transport().is_active()
            )
        except Exception:
            return False

    def close(self) -> None:
        try:
            if self.client:
                self.client.close()
        except Exception:
            pass
        self.client = None

    def run_command(self, cmd: str, timeout: float = 15) -> str:
        if not self.client:
            raise ConnectionError("SSH client is not connected")
        _, stdout, stderr = self.client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        if err:
            return (out + "\n" + err).strip() if out else err
        return out

    def open_shell(self, cols: int = 220, rows: int = 50) -> "paramiko.Channel":
        if not self.client:
            raise ConnectionError("SSH client is not connected")
        ch = self.client.invoke_shell(term="xterm-256color", width=cols, height=rows)
        ch.settimeout(0.1)
        return ch


# ---------------------------------------------------------------------------
# Session manager
# ---------------------------------------------------------------------------

class SessionManager:
    def __init__(self):
        self._sessions: dict[str, TelnetClient | SshClient] = {}
        self._lock = threading.Lock()

    def _open_telnet(self, nid: str, node: dict) -> tuple[Optional[TelnetClient], Optional[str]]:
        cl = TelnetClient(node["host"], node["port"])
        try:
            cl.connect()
        except Exception as e:
            return None, f"TCP connect failed: {e}"

        try:
            try:
                cl.write("")
            except (BrokenPipeError, ConnectionError, OSError) as e:
                cl.close()
                return None, f"Console closed connection immediately: {e}"

            banner = cl.read_until(SHELL_PROMPTS + LOGIN_PROMPTS + PASS_PROMPTS, timeout=8)

            if any(p in banner for p in LOGIN_PROMPTS):
                cl.write(node.get("username", "root"))
                resp = cl.read_until(SHELL_PROMPTS + PASS_PROMPTS, timeout=5)
                if any(p in resp for p in PASS_PROMPTS):
                    cl.write(node.get("password", ""))
                    cl.read_until(SHELL_PROMPTS, timeout=5)

            cl.write('export TERM=dumb; PS1="# "; stty -echo 2>/dev/null')
            cl.read_until(["# "], timeout=5)
        except Exception as e:
            cl.close()
            return None, f"Session setup failed: {e}"

        return cl, None

    def _open_ssh(self, nid: str, node: dict) -> tuple[Optional[SshClient], Optional[str]]:
        cl = SshClient(node["host"], node["port"], node.get("username", "root"), node.get("password", ""))
        try:
            cl.connect()
        except Exception as e:
            cl.close()
            return None, f"SSH connect failed: {e}"
        return cl, None

    def open(self, nid: str, node: dict) -> tuple[Optional[TelnetClient | SshClient], Optional[str]]:
        with self._lock:
            old = self._sessions.pop(nid, None)
            if old:
                try:
                    old.close()
                except Exception:
                    pass

        transport = (node.get("transport") or "telnet").lower()
        if transport == "ssh":
            cl, err = self._open_ssh(nid, node)
        else:
            cl, err = self._open_telnet(nid, node)

        if err:
            return None, err

        with self._lock:
            self._sessions[nid] = cl
        return cl, None

    def get(self, nid: str, node: dict) -> tuple[Optional[TelnetClient | SshClient], Optional[str]]:
        with self._lock:
            cl = self._sessions.get(nid)
        if cl and cl.alive():
            return cl, None
        return self.open(nid, node)

    def close(self, nid: str) -> None:
        with self._lock:
            cl = self._sessions.pop(nid, None)
        if cl:
            try:
                cl.close()
            except Exception:
                pass

    def close_all(self) -> None:
        with self._lock:
            sessions = dict(self._sessions)
            self._sessions.clear()
        for cl in sessions.values():
            try:
                cl.close()
            except Exception:
                pass

    def run(self, nid: str, node: dict, commands: list[str]) -> tuple[Optional[list], Optional[str]]:
        cl, err = self.get(nid, node)
        if err:
            return None, err
        results = []
        for cmd in commands:
            cmd = cmd.strip()
            if not cmd:
                continue
            try:
                output = cl.run_command(cmd, timeout=15)
                results.append({"command": cmd, "output": output, "error": None})
            except Exception as e:
                results.append({"command": cmd, "output": "", "error": str(e)})
                with self._lock:
                    self._sessions.pop(nid, None)
                break
        return results, None


session_manager = SessionManager()
