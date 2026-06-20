"""
Netrunner Forensics Module — Memory and disk forensics with Volatility integration.

Provides:
- Memory dump acquisition (LiME, /proc/kcore, dd)
- Volatility3 plugin execution and result parsing
- Disk image analysis
- Timeline generation
- Evidence chain of custody tracking
"""
import asyncio
import os
import json
import time
import hashlib
import subprocess
from typing import Optional
from backend.core.logger import log as logger

try:
    from .vault import get_credential
except ImportError:
    get_credential = None

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

# Forensics storage
FORENSICS_DIR = "data/forensics"
EvidenceDB: dict[str, dict] = {}  # In-memory evidence tracking


def _ensure_forensics_dir():
    os.makedirs(FORENSICS_DIR, exist_ok=True)
    os.makedirs(os.path.join(FORENSICS_DIR, "memory"), exist_ok=True)
    os.makedirs(os.path.join(FORENSICS_DIR, "disk"), exist_ok=True)
    os.makedirs(os.path.join(FORENSICS_DIR, "reports"), exist_ok=True)
    os.makedirs(os.path.join(FORENSICS_DIR, "timeline"), exist_ok=True)


async def _ssh_exec(host: str, username: str, password: str, command: str, port: int = 22) -> tuple[int, str, str]:
    """Execute a command over SSH."""
    if not PARAMIKO_AVAILABLE:
        return -1, "", "paramiko not installed"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        await asyncio.to_thread(
            client.connect,
            hostname=host, port=port, username=username, password=password,
            timeout=10, look_for_keys=False, allow_agent=False,
        )
        _, stdout, stderr = await asyncio.to_thread(client.exec_command, command, timeout=300)
        exit_code = await asyncio.to_thread(stdout.channel.recv_exit_status)
        out = await asyncio.to_thread(stdout.read().decode, errors="replace")
        err = await asyncio.to_thread(stderr.read().decode, errors="replace")
        return exit_code, out, err
    except Exception as e:
        return -1, "", str(e)
    finally:
        client.close()


async def acquire_memory_dump(node_id: str, host: str, username: str, password: str, method: str = "lime") -> dict:
    """
    Acquire a memory dump from a remote node.

    Methods:
    - lime: Use LiME kernel module (requires root + kernel headers)
    - dd: Use dd to read /dev/mem (requires root)
    - proc: Read /proc/kcore (limited, no full dump)
    """
    _ensure_forensics_dir()
    case_id = f"case_{int(time.time())}"
    dump_path = os.path.join(FORENSICS_DIR, "memory", f"{case_id}.lime")

    logger.info(f"[FORENSICS] Acquiring memory dump from {host} using method={method}")

    if method == "lime":
        # LiME kernel module approach
        cmd = f"""
        if [ ! -f /tmp/lime.ko ]; then
            ARCH=$(uname -r)
            if [ -d /lib/modules/$ARCH/build ]; then
                cd /tmp
                git clone https://github.com/504ensicsLabs/LiME.git 2>/dev/null || true
                cd LiME/src
                make 2>/dev/null || echo "LiME build failed — kernel headers missing"
                cp lime.ko /tmp/lime.ko
            else
                echo "ERROR: Kernel headers not found for $ARCH"
                exit 1
            fi
        fi
        insmod /tmp/lime.ko "path=/tmp/memdump.lime format=lime"
        """
    elif method == "dd":
        # Direct dd dump
        cmd = "dd if=/dev/mem of=/tmp/memdump.lime bs=1M count=512 2>&1"
    elif method == "proc":
        # /proc/kcore (limited)
        cmd = "cat /proc/kcore > /tmp/memdump.lime 2>/dev/null || echo 'kcore not readable'"
    else:
        return {"success": False, "error": f"Unknown method: {method}"}

    exit_code, out, err = await _ssh_exec(host, username, password, cmd)

    if exit_code != 0 and "ERROR" in out:
        return {"success": False, "error": out, "method": method}

    # Transfer the dump back
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        await asyncio.to_thread(
            client.connect, hostname=host, port=22, username=username, password=password,
            timeout=30, look_for_keys=False, allow_agent=False,
        )

        sftp = await asyncio.to_thread(client.open_sftp)
        await asyncio.to_thread(sftp.get, "/tmp/memdump.lime", dump_path)
        await asyncio.to_thread(sftp.close)
        client.close()

        # Calculate hash
        file_hash = await asyncio.to_thread(_hash_file, dump_path)
        file_size = os.path.getsize(dump_path)

        evidence_id = f"mem_{case_id}"
        EvidenceDB[evidence_id] = {
            "id": evidence_id,
            "case_id": case_id,
            "type": "memory_dump",
            "source_node": node_id,
            "source_host": host,
            "method": method,
            "file_path": dump_path,
            "file_size": file_size,
            "sha256": file_hash,
            "acquired_at": time.time(),
            "analyst": "system",
        }

        return {
            "success": True,
            "evidence_id": evidence_id,
            "case_id": case_id,
            "file_path": dump_path,
            "file_size": file_size,
            "sha256": file_hash,
            "method": method,
        }

    except Exception as e:
        return {"success": False, "error": f"Transfer failed: {str(e)}"}


async def run_volatility_plugin(evidence_id: str, plugin: str, extra_args: str = "") -> dict:
    """
    Run a Volatility3 plugin against a memory dump.

    Supported plugins:
    - linux.pslist: List processes
    - linux.bash: Recover bash history
    - linux.check_syscall: Check syscall table
    - linux.lsmod: List kernel modules
    - linux.netstat: Network connections
    - linux.tty_check: TTY input
    - windows.pslist: Windows processes
    - windows.cmdline: Command line arguments
    - windows.netscan: Network scan
    - windows.filescan: File scan
    - windows.handles: Handle table
    - malfind: Detect injected code
    """
    if evidence_id not in EvidenceDB:
        return {"success": False, "error": f"Evidence {evidence_id} not found"}

    evidence = EvidenceDB[evidence_id]
    dump_path = evidence["file_path"]

    if not os.path.exists(dump_path):
        return {"success": False, "error": f"Memory dump file not found: {dump_path}"}

    logger.info(f"[FORENSICS] Running Volatility plugin '{plugin}' on {evidence_id}")

    # Build volatility command
    vol_cmd = f"python3 -m volatility3 -f {dump_path} {plugin}"
    if extra_args:
        vol_cmd += f" {extra_args}"

    try:
        # Try to find volatility3
        result = await asyncio.to_thread(
            subprocess.run,
            vol_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
        )

        output = result.stdout
        error = result.stderr

        # Parse output into structured data
        parsed = _parse_volatility_output(plugin, output)

        # Generate timeline
        timeline_path = os.path.join(FORENSICS_DIR, "timeline", f"{evidence_id}_{plugin.replace('.', '_')}.json")
        await asyncio.to_thread(_write_json, timeline_path, {
            "evidence_id": evidence_id,
            "plugin": plugin,
            "output": output,
            "parsed": parsed,
            "timestamp": time.time(),
        })

        return {
            "success": True,
            "evidence_id": evidence_id,
            "plugin": plugin,
            "output": output,
            "parsed": parsed,
            "timeline_path": timeline_path,
        }

    except FileNotFoundError:
        # Volatility3 not installed — try via SSH on a node
        return {
            "success": False,
            "error": "Volatility3 not installed on this system. Install with: pip install volatility3",
            "suggestion": "Deploy to a remote node with Volatility3 installed",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Volatility plugin timed out after 300s"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _parse_volatility_output(plugin: str, output: str) -> list[dict]:
    """Parse Volatility3 text output into structured data."""
    parsed = []
    lines = output.strip().splitlines()

    if not lines:
        return parsed

    # Find header line (after the banner)
    header_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("Vol") or line.startswith("---") or not line.strip():
            continue
        if "PID" in line or "PPID" in line or "Offset" in line:
            header_idx = i
            break

    if header_idx >= len(lines):
        return parsed

    headers = [h.strip() for h in lines[header_idx].split() if h.strip()]

    for line in lines[header_idx + 1:]:
        if not line.strip() or line.startswith("---"):
            continue
        values = line.split()
        if len(values) >= len(headers):
            row = {}
            for i, header in enumerate(headers):
                row[header] = values[i] if i < len(values) else ""
            parsed.append(row)
        elif values:
            parsed.append({"raw": line.strip()})

    return parsed


async def analyze_disk_image(image_path: str) -> dict:
    """Analyze a disk image using forensic tools."""
    if not os.path.exists(image_path):
        return {"success": False, "error": f"Disk image not found: {image_path}"}

    logger.info(f"[FORENSICS] Analyzing disk image: {image_path}")

    results = {}

    # Try fls (The Sleuth Kit)
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["fls", "-r", "-d", image_path],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            results["file_system"] = _parse_flst_output(result.stdout)
    except FileNotFoundError:
        pass

    # Try mmls (disk layout)
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["mmls", image_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            results["disk_layout"] = result.stdout
    except FileNotFoundError:
        pass

    # Try img_stat
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["img_stat", image_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            results["image_info"] = result.stdout
    except FileNotFoundError:
        pass

    # Calculate hash
    file_hash = await asyncio.to_thread(_hash_file, image_path)
    results["sha256"] = file_hash
    results["file_size"] = os.path.getsize(image_path)

    return {
        "success": True,
        "image_path": image_path,
        "results": results,
    }


def _parse_flst_output(output: str) -> list[dict]:
    """Parse fls output into structured data."""
    entries = []
    for line in output.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split(",", 1)
        if len(parts) == 2:
            meta = parts[0].strip()
            name = parts[1].strip()
            entries.append({"metadata": meta, "name": name})
    return entries


async def generate_timeline(evidence_ids: list[str]) -> dict:
    """Generate a combined timeline from multiple evidence sources."""
    events = []

    for eid in evidence_ids:
        if eid in EvidenceDB:
            ev = EvidenceDB[evidence_id]
            events.append({
                "timestamp": ev["acquired_at"],
                "type": ev["type"],
                "source": ev.get("source_host", "unknown"),
                "evidence_id": eid,
            })

        # Check for timeline files
        timeline_dir = os.path.join(FORENSICS_DIR, "timeline")
        if os.path.exists(timeline_dir):
            for f in os.listdir(timeline_dir):
                if f.startswith(eid) and f.endswith(".json"):
                    tl_path = os.path.join(timeline_dir, f)
                    try:
                        tl_data = await asyncio.to_thread(_read_json, tl_path)
                        for entry in tl_data.get("parsed", []):
                            if "timestamp" in entry or "Date" in entry:
                                events.append({
                                    "timestamp": entry.get("timestamp", entry.get("Date", "")),
                                    "type": "volatility_result",
                                    "source": eid,
                                    "data": entry,
                                })
                    except Exception:
                        pass

    events.sort(key=lambda x: str(x.get("timestamp", "")))

    return {
        "success": True,
        "event_count": len(events),
        "events": events,
    }


def _hash_file(filepath: str) -> str:
    """Calculate SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _write_json(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _read_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def get_evidence_list() -> list[dict]:
    """Return all evidence items."""
    return list(EvidenceDB.values())
