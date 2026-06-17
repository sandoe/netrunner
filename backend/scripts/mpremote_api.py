from __future__ import annotations
import ast, contextlib, io, os, stat as stat_module, threading, time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable, Iterator, List, Optional, Tuple, Union
import mpremote
from mpremote import mip
from mpremote.transport import TransportError, TransportExecError
from mpremote.transport_serial import SerialTransport
try:
    from serial.tools import list_ports as _list_ports
except Exception:
    _list_ports = None

class MPRemoteError(Exception): pass
class NotConnectedError(MPRemoteError): pass
class DeviceError(MPRemoteError):
    def __init__(self, message: str, traceback_text: str = "") -> None:
        super().__init__(message)
        self.traceback_text = traceback_text or message

def _to_mpremote_error(exc: Exception, context: str = "") -> MPRemoteError:
    prefix = f"{context}: " if context else ""
    if isinstance(exc, TransportExecError):
        tb = exc.args[-1] if exc.args else str(exc)
        if isinstance(tb, bytes):
            tb = tb.decode("utf-8", "replace")
        first = str(tb).strip().splitlines()[-1] if str(tb).strip() else str(exc)
        return DeviceError(f"{prefix}{first}", traceback_text=str(tb))
    if isinstance(exc, (TransportError, OSError)):
        return MPRemoteError(f"{prefix}{exc}")
    return MPRemoteError(f"{prefix}{exc}")

@dataclass(frozen=True)
class SerialPortInfo:
    device: str
    description: str = ""
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    vid: Optional[int] = None
    pid: Optional[int] = None
    hwid: str = ""
    @property
    def vid_pid(self) -> Optional[str]:
        if self.vid is None or self.pid is None: return None
        return f"{self.vid:04X}:{self.pid:04X}"
    def __str__(self) -> str:
        extra = self.description or self.manufacturer or ""
        return f"{self.device}" + (f"  ({extra})" if extra else "")

@dataclass(frozen=True)
class DirEntry:
    name: str
    path: str
    is_dir: bool
    size: int = 0
    @property
    def is_file(self) -> bool: return not self.is_dir

@dataclass(frozen=True)
class StatResult:
    st_mode: int = 0
    st_ino: int = 0
    st_dev: int = 0
    st_nlink: int = 0
    st_uid: int = 0
    st_gid: int = 0
    st_size: int = 0
    st_atime: int = 0
    st_mtime: int = 0
    st_ctime: int = 0
    @property
    def is_dir(self) -> bool: return bool(stat_module.S_ISDIR(self.st_mode))
    @property
    def is_file(self) -> bool: return bool(stat_module.S_ISREG(self.st_mode))

@dataclass(frozen=True)
class DfInfo:
    path: str
    total: int
    used: int
    free: int
    block_size: int = 0
    @property
    def used_percent(self) -> float: return (self.used / self.total * 100.0) if self.total else 0.0

class MPRemote:
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200, *, connect_timeout: Optional[float] = None, exclusive: bool = True) -> None:
        self._port = port
        self._baudrate = baudrate
        self._connect_timeout = connect_timeout
        self._exclusive = exclusive
        self._transport: Optional[SerialTransport] = None
        self._in_raw = False
        self._lock = threading.RLock()

    @staticmethod
    def list_ports() -> List[SerialPortInfo]:
        if _list_ports is None: return []
        ports: List[SerialPortInfo] = []
        for p in _list_ports.comports():
            ports.append(SerialPortInfo(device=p.device, description=(p.description or "").strip(), manufacturer=getattr(p, "manufacturer", None), serial_number=getattr(p, "serial_number", None), vid=getattr(p, "vid", None), pid=getattr(p, "pid", None), hwid=getattr(p, "hwid", "") or ""))
        return ports

    @property
    def connected(self) -> bool: return self._transport is not None
    @property
    def in_raw_repl(self) -> bool: return self._in_raw
    @property
    def port(self) -> Optional[str]: return self._port

    def connect(self, port: Optional[str] = None) -> None:
        with self._lock:
            if self._transport is not None: raise MPRemoteError("Already connected")
            if port is not None: self._port = port
            if self._port is None:
                candidates = self.list_ports()
                if not candidates: raise MPRemoteError("No serial ports found")
                self._port = candidates[0].device
            try: self._transport = SerialTransport(self._port, baudrate=self._baudrate, timeout=self._connect_timeout, exclusive=self._exclusive)
            except Exception as exc:
                self._transport = None
                raise _to_mpremote_error(exc, f"connect({self._port})") from None
            self._in_raw = False

    def disconnect(self) -> None:
        with self._lock:
            if self._transport is None: return
            try:
                if self._in_raw:
                    with contextlib.suppress(Exception): self._transport.exit_raw_repl()
            finally:
                with contextlib.suppress(Exception): self._transport.close()
                self._transport = None
                self._in_raw = False

    def __enter__(self) -> "MPRemote":
        self.connect()
        return self
    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()

    def enter_raw_repl(self, *, soft_reset: bool = False) -> None:
        with self._lock:
            self._require_transport()
            try: self._transport.enter_raw_repl(soft_reset=soft_reset)
            except Exception as exc: raise _to_mpremote_error(exc, "enter_raw_repl") from None
            self._in_raw = True

    def exit_raw_repl(self) -> None:
        with self._lock:
            self._require_transport()
            if not self._in_raw: return
            try: self._transport.exit_raw_repl()
            except Exception as exc: raise _to_mpremote_error(exc, "exit_raw_repl") from None
            self._in_raw = False

    def exec(self, code: str, *, output=None, timeout: Optional[float] = 10.0) -> str:
        with self._lock:
            self._ensure_raw()
            consumer = (lambda b: output(b.decode("utf-8", "replace"))) if output is not None else None
            try: ret, err = self._transport.exec_raw(code, timeout=timeout, data_consumer=consumer)
            except Exception as exc: raise _to_mpremote_error(exc, "exec") from None
            if err:
                tb = err.decode("utf-8", "replace")
                first = tb.strip().splitlines()[-1] if tb.strip() else "device error"
                raise DeviceError(first, traceback_text=tb)
            return ret.decode("utf-8", "replace")

    def eval(self, expression: str) -> object:
        with self._lock:
            self._ensure_raw()
            try: return self._transport.eval(expression, parse=True)
            except Exception as exc: raise _to_mpremote_error(exc, "eval") from None

    def run(self, local_path, *, output=None, timeout: Optional[float] = None) -> str:
        source = Path(local_path).read_text(encoding="utf-8")
        return self.exec(source, output=output, timeout=timeout)

    def ls(self, path: str = "/") -> List[DirEntry]:
        path = self._norm(path)
        with self._lock:
            self._ensure_raw()
            try: entries = self._transport.fs_listdir(path)
            except Exception as exc: raise _to_mpremote_error(exc, f"ls({path})") from None
        out = []
        for e in entries:
            is_dir = bool(stat_module.S_ISDIR(e.st_mode))
            out.append(DirEntry(name=e.name, path=self._join(path, e.name), is_dir=is_dir, size=int(getattr(e, "st_size", 0) or 0)))
        out.sort(key=lambda d: (not d.is_dir, d.name.lower()))
        return out

    def stat(self, path: str) -> StatResult:
        path = self._norm(path)
        with self._lock:
            self._ensure_raw()
            try: raw = self._transport.fs_stat(path)
            except Exception as exc: raise _to_mpremote_error(exc, f"stat({path})") from None
        values = list(tuple(raw))[:10]
        values += [0] * (10 - len(values))
        return StatResult(*values)

    def exists(self, path: str) -> bool:
        path = self._norm(path)
        with self._lock:
            self._ensure_raw()
            try: return bool(self._transport.fs_exists(path))
            except Exception as exc: raise _to_mpremote_error(exc, f"exists({path})") from None

    def isdir(self, path: str) -> bool:
        path = self._norm(path)
        with self._lock:
            self._ensure_raw()
            try: return bool(self._transport.fs_isdir(path))
            except Exception as exc: raise _to_mpremote_error(exc, f"isdir({path})") from None

    def walk(self, path: str = "/") -> List[DirEntry]:
        path = self._norm(path)
        result: List[DirEntry] = []
        self._walk_into(path, result)
        return result

    def tree(self, path: str = "/") -> dict:
        path = self._norm(path)
        with self._lock: return self._tree_node(path, name=PurePosixPath(path).name or "/")

    def read_bytes(self, path: str, *, chunk_size: int = 256, progress=None) -> bytes:
        path = self._norm(path)
        with self._lock:
            self._ensure_raw()
            cb = self._wrap_progress(progress, path)
            try: data = self._transport.fs_readfile(path, chunk_size=chunk_size, progress_callback=cb)
            except Exception as exc: raise _to_mpremote_error(exc, f"read_bytes({path})") from None
        if progress is not None: progress(len(data), len(data), path)
        return bytes(data)

    def read_text(self, path: str, encoding: str = "utf-8", *, chunk_size: int = 256, progress=None) -> str:
        return self.read_bytes(path, chunk_size=chunk_size, progress=progress).decode(encoding)

    def write_bytes(self, path: str, data: bytes, *, chunk_size: int = 256, progress=None) -> None:
        path = self._norm(path)
        if isinstance(data, str): raise TypeError("write_bytes expects bytes; use write_text for str.")
        with self._lock:
            self._ensure_raw()
            cb = self._wrap_progress(progress, path)
            try: self._transport.fs_writefile(path, bytes(data), chunk_size=chunk_size, progress_callback=cb)
            except Exception as exc: raise _to_mpremote_error(exc, f"write_bytes({path})") from None
        if progress is not None: progress(len(data), len(data), path)

    def write_text(self, path: str, text: str, encoding: str = "utf-8", *, chunk_size: int = 256, progress=None) -> None:
        self.write_bytes(path, text.encode(encoding), chunk_size=chunk_size, progress=progress)

    def put(self, local, remote: Optional[str] = None, *, recursive: bool = False, chunk_size: int = 256, progress=None) -> None:
        local_path = Path(local)
        if not local_path.exists(): raise MPRemoteError(f"Local path does not exist: {local_path}")
        if remote is None: remote = "/" + local_path.name
        elif remote.endswith("/"): remote = self._join(remote, local_path.name)
        remote = self._norm(remote)
        with self._lock:
            if local_path.is_file():
                self.write_bytes(remote, local_path.read_bytes(), chunk_size=chunk_size, progress=progress)
                return
            if not recursive: raise MPRemoteError(f"{local_path} is a directory; pass recursive=True to copy it.")
            self.makedirs(remote, exist_ok=True)
            for child in sorted(local_path.rglob("*")):
                rel = child.relative_to(local_path).as_posix()
                target = self._join(remote, rel)
                if child.is_dir(): self.makedirs(target, exist_ok=True)
                else: self.write_bytes(target, child.read_bytes(), chunk_size=chunk_size, progress=progress)

    def get(self, remote: str, local=None, *, recursive: bool = False, chunk_size: int = 256, progress=None) -> Path:
        remote = self._norm(remote)
        local_path = Path(local) if local is not None else Path(PurePosixPath(remote).name)
        with self._lock:
            self._ensure_raw()
            if not self.isdir(remote):
                if local_path.is_dir(): local_path = local_path / PurePosixPath(remote).name
                local_path.parent.mkdir(parents=True, exist_ok=True)
                data = self.read_bytes(remote, chunk_size=chunk_size, progress=progress)
                local_path.write_bytes(data)
                return local_path
            if not recursive: raise MPRemoteError(f"{remote} is a directory; pass recursive=True to copy it.")
            local_path.mkdir(parents=True, exist_ok=True)
            for entry in self.walk(remote):
                rel = entry.path[len(remote):].lstrip("/")
                dest = local_path / rel
                if entry.is_dir: dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(self.read_bytes(entry.path, chunk_size=chunk_size, progress=progress))
            return local_path

    def mkdir(self, path: str, *, exist_ok: bool = False) -> None:
        path = self._norm(path)
        with self._lock:
            self._ensure_raw()
            if exist_ok and self.exists(path): return
            try: self._transport.fs_mkdir(path)
            except Exception as exc: raise _to_mpremote_error(exc, f"mkdir({path})") from None

    def makedirs(self, path: str, *, exist_ok: bool = True) -> None:
        path = self._norm(path)
        with self._lock:
            self._ensure_raw()
            parts = [p for p in path.split("/") if p]
            cur = ""
            for part in parts:
                cur = cur + "/" + part
                if self.exists(cur):
                    if not self.isdir(cur): raise MPRemoteError(f"Path component is not a directory: {cur}")
                    continue
                try: self._transport.fs_mkdir(cur)
                except Exception as exc: raise _to_mpremote_error(exc, f"makedirs({cur})") from None
            if not parts and not exist_ok: raise MPRemoteError("Refusing to create root directory.")

    def rmdir(self, path: str) -> None:
        path = self._norm(path)
        with self._lock:
            self._ensure_raw()
            try: self._transport.fs_rmdir(path)
            except Exception as exc: raise _to_mpremote_error(exc, f"rmdir({path})") from None

    def remove(self, path: str) -> None:
        path = self._norm(path)
        with self._lock:
            self._ensure_raw()
            try: self._transport.fs_rmfile(path)
            except Exception as exc: raise _to_mpremote_error(exc, f"remove({path})") from None

    def rm(self, path: str, *, recursive: bool = False, force: bool = False) -> None:
        path = self._norm(path)
        with self._lock:
            self._ensure_raw()
            if not self.exists(path):
                if force: return
                raise MPRemoteError(f"No such file or directory: {path}")
            if not self.isdir(path):
                self.remove(path)
                return
            if not recursive: raise MPRemoteError(f"{path} is a directory; pass recursive=True to remove it.")
            for entry in reversed(self.walk(path)):
                if entry.is_dir: self.rmdir(entry.path)
                else: self.remove(entry.path)
            self.rmdir(path)

    def touch(self, path: str) -> None:
        path = self._norm(path)
        with self._lock:
            self._ensure_raw()
            try: self._transport.fs_touchfile(path)
            except Exception as exc: raise _to_mpremote_error(exc, f"touch({path})") from None

    def rename(self, src: str, dst: str) -> None:
        src, dst = self._norm(src), self._norm(dst)
        with self._lock: self.exec(f"import os; os.rename({src!r}, {dst!r})")

    def df(self, path: str = "/") -> DfInfo:
        path = self._norm(path)
        snippet = ("import os\n" f"s = os.statvfs({path!r})\n" "frsize = s[1]; blocks = s[2]; bfree = s[3]\n" "print(repr((blocks*frsize, (blocks-bfree)*frsize, bfree*frsize, frsize)))")
        out = self.exec(snippet).strip()
        try: total, used, free, frsize = ast.literal_eval(out)
        except Exception as exc: raise MPRemoteError(f"df({path}): could not parse result {out!r}: {exc}")
        return DfInfo(path=path, total=total, used=used, free=free, block_size=frsize)

    def hashfile(self, path: str, algo: str = "sha256", *, chunk_size: int = 256) -> str:
        path = self._norm(path)
        with self._lock:
            self._ensure_raw()
            try: result = self._transport.fs_hashfile(path, algo, chunk_size=chunk_size)
            except Exception as exc: raise _to_mpremote_error(exc, f"hashfile({path})") from None
        if isinstance(result, (bytes, bytearray)): return bytes(result).hex()
        return str(result)

    def sha256(self, path: str, *, chunk_size: int = 256) -> str:
        return self.hashfile(path, "sha256", chunk_size=chunk_size)

    def soft_reset(self) -> None:
        with self._lock:
            self._require_transport()
            try: self._transport.enter_raw_repl(soft_reset=True)
            except Exception as exc: raise _to_mpremote_error(exc, "soft_reset") from None
            self._in_raw = True

    def hard_reset(self, *, disconnect: bool = True) -> None:
        with self._lock:
            self._ensure_raw()
            try: self._transport.exec_raw_no_follow("import machine; machine.reset()")
            except Exception as exc: raise _to_mpremote_error(exc, "hard_reset") from None
            time.sleep(0.1)
            if disconnect: self.disconnect()

    def _require_transport(self) -> None:
        if self._transport is None: raise NotConnectedError("Not connected")

    def _ensure_raw(self) -> None:
        self._require_transport()
        if not self._in_raw:
            try: self._transport.enter_raw_repl(soft_reset=False)
            except Exception as exc: raise _to_mpremote_error(exc, "enter_raw_repl") from None
            self._in_raw = True

    @staticmethod
    def _wrap_progress(progress, name: str):
        if progress is None: return None
        return lambda transferred, total: progress(transferred, total, name)

    @staticmethod
    def _norm(path: str) -> str:
        if not path: return "/"
        p = str(path).replace("\\", "/")
        if not p.startswith("/"): p = "/" + p
        while "//" in p: p = p.replace("//", "/")
        if len(p) > 1 and p.endswith("/"): p = p[:-1]
        return p

    @staticmethod
    def _join(base: str, name: str) -> str:
        base = base if base.endswith("/") else base + "/"
        return MPRemote._norm(base + name)

    def _walk_into(self, path: str, acc: List[DirEntry]) -> None:
        for entry in self.ls(path):
            acc.append(entry)
            if entry.is_dir: self._walk_into(entry.path, acc)

    def _tree_node(self, path: str, name: str) -> dict:
        if self.isdir(path):
            node = {"name": name, "path": path, "is_dir": True, "children": []}
            for entry in self.ls(path):
                if entry.is_dir: node["children"].append(self._tree_node(entry.path, entry.name))
                else: node["children"].append({"name": entry.name, "path": entry.path, "is_dir": False, "size": entry.size})
            return node
        st = self.stat(path)
        return {"name": name, "path": path, "is_dir": False, "size": st.st_size}
