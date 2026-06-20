"""
Netrunner Compliance Scanner — CIS Benchmarks and NIST Framework scanning.

Provides:
- CIS Benchmark compliance checks for Linux systems
- NIST 800-53 framework mapping
- Automated security posture assessment
- Remediation recommendations
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

COMPLIANCE_DIR = "data/compliance"


def _ensure_compliance_dir():
    os.makedirs(COMPLIANCE_DIR, exist_ok=True)


# CIS Benchmark checks for Linux
CIS_CHECKS = [
    {
        "id": "CIS-1.1.1",
        "title": "Disable unused filesystems (cramfs, freevxfs, hfs, hfsplus, udf)",
        "severity": "medium",
        "category": "Filesystem",
        "command": "for fs in cramfs freevxfs hfs hfsplus udf; do modprobe -n -v $fs 2>/dev/null | grep -q 'install /bin/true' || echo \"FAIL: $fs not disabled\"; done",
        "remediation": "Add to /etc/modprobe.d/disable-fs.conf: install cramfs /bin/true, etc.",
        "frameworks": ["CIS", "NIST-800-53:CM-7"],
    },
    {
        "id": "CIS-1.1.2",
        "title": "Ensure /tmp is configured with nodev,nosuid,noexec",
        "severity": "medium",
        "category": "Filesystem",
        "command": "mount | grep ' /tmp ' | grep -q 'nodev.*nosuid.*noexec' && echo 'PASS' || echo 'FAIL: /tmp not properly mounted'",
        "remediation": "Add to /etc/fstab: /tmp /tmp tmpfs defaults,nosuid,nodev,noexec 0 0",
        "frameworks": ["CIS", "NIST-800-53:SC-4"],
    },
    {
        "id": "CIS-1.3",
        "title": "Ensure AIDE is installed and configured",
        "severity": "medium",
        "category": "File Integrity",
        "command": "which aide >/dev/null 2>&1 && echo 'PASS' || echo 'FAIL: AIDE not installed'",
        "remediation": "Install AIDE: apt-get install aide && aideinit",
        "frameworks": ["CIS", "NIST-800-53:SI-7"],
    },
    {
        "id": "CIS-1.5",
        "title": "Ensure bootloader permissions are configured",
        "severity": "high",
        "category": "Boot",
        "command": "stat -c '%a' /boot/grub/grub.cfg 2>/dev/null | grep -q '400' && echo 'PASS' || echo 'FAIL: Bootloader permissions too open'",
        "remediation": "chmod 600 /boot/grub/grub.cfg",
        "frameworks": ["CIS", "NIST-800-53:AC-3"],
    },
    {
        "id": "CIS-2.1",
        "title": "Ensure unnecessary services are disabled",
        "severity": "medium",
        "category": "Services",
        "command": "for svc in avahi-daemon cups dhcpd slapd nfs rpcbind named vsftpd httpd dovecot smb squid snmpd ypserv telnet.socket rsh.socket; do systemctl is-enabled $svc 2>/dev/null | grep -q 'enabled' && echo \"FAIL: $svc enabled\"; done; echo 'DONE'",
        "remediation": "systemctl disable <service>",
        "frameworks": ["CIS", "NIST-800-53:CM-7"],
    },
    {
        "id": "CIS-3.1",
        "title": "Ensure IP forwarding is disabled",
        "severity": "medium",
        "category": "Network",
        "command": "sysctl net.ipv4.ip_forward 2>/dev/null | grep -q '= 0' && echo 'PASS' || echo 'FAIL: IP forwarding enabled'",
        "remediation": "sysctl -w net.ipv4.ip_forward=0 && echo 'net.ipv4.ip_forward=0' >> /etc/sysctl.conf",
        "frameworks": ["CIS", "NIST-800-53:SC-7"],
    },
    {
        "id": "CIS-3.2",
        "title": "Ensure source routed packets are rejected",
        "severity": "medium",
        "category": "Network",
        "command": "sysctl net.ipv4.conf.all.accept_source_route 2>/dev/null | grep -q '= 0' && echo 'PASS' || echo 'FAIL: Source routing enabled'",
        "remediation": "sysctl -w net.ipv4.conf.all.accept_source_route=0",
        "frameworks": ["CIS", "NIST-800-53:SC-7"],
    },
    {
        "id": "CIS-3.3",
        "title": "Ensure ICMP redirects are not accepted",
        "severity": "medium",
        "category": "Network",
        "command": "sysctl net.ipv4.conf.all.accept_redirects 2>/dev/null | grep -q '= 0' && echo 'PASS' || echo 'FAIL: ICMP redirects accepted'",
        "remediation": "sysctl -w net.ipv4.conf.all.accept_redirects=0",
        "frameworks": ["CIS", "NIST-800-53:SC-7"],
    },
    {
        "id": "CIS-3.4",
        "title": "Ensure secure ICMP redirects are not accepted",
        "severity": "medium",
        "category": "Network",
        "command": "sysctl net.ipv4.conf.all.secure_redirects 2>/dev/null | grep -q '= 0' && echo 'PASS' || echo 'FAIL: Secure ICMP redirects accepted'",
        "remediation": "sysctl -w net.ipv4.conf.all.secure_redirects=0",
        "frameworks": ["CIS", "NIST-800-53:SC-7"],
    },
    {
        "id": "CIS-3.5",
        "title": "Ensure suspicious packets are logged",
        "severity": "medium",
        "category": "Network",
        "command": "sysctl net.ipv4.conf.all.log_martians 2>/dev/null | grep -q '= 1' && echo 'PASS' || echo 'FAIL: Martians not logged'",
        "remediation": "sysctl -w net.ipv4.conf.all.log_martians=1",
        "frameworks": ["CIS", "NIST-800-53:AU-2"],
    },
    {
        "id": "CIS-3.6",
        "title": "Ensure TCP SYN cookies are enabled",
        "severity": "medium",
        "category": "Network",
        "command": "sysctl net.ipv4.tcp_syncookies 2>/dev/null | grep -q '= 1' && echo 'PASS' || echo 'FAIL: SYN cookies disabled'",
        "remediation": "sysctl -w net.ipv4.tcp_syncookies=1",
        "frameworks": ["CIS", "NIST-800-53:SC-5"],
    },
    {
        "id": "CIS-4.1",
        "title": "Ensure auditd is installed and running",
        "severity": "high",
        "category": "Auditing",
        "command": "systemctl is-active auditd 2>/dev/null | grep -q 'active' && echo 'PASS' || echo 'FAIL: auditd not running'",
        "remediation": "apt-get install auditd && systemctl enable auditd && systemctl start auditd",
        "frameworks": ["CIS", "NIST-800-53:AU-2", "NIST-800-53:AU-12"],
    },
    {
        "id": "CIS-4.2",
        "title": "Ensure audit log storage size is configured",
        "severity": "medium",
        "category": "Auditing",
        "command": "grep -q 'max_log_file' /etc/audit/auditd.conf && echo 'PASS' || echo 'FAIL: Audit log size not configured'",
        "remediation": "Edit /etc/audit/auditd.conf: max_log_file = 50",
        "frameworks": ["CIS", "NIST-800-53:AU-4"],
    },
    {
        "id": "CIS-5.1",
        "title": "Ensure cron daemon is running",
        "severity": "medium",
        "category": "Scheduling",
        "command": "systemctl is-active cron 2>/dev/null | grep -q 'active' && echo 'PASS' || echo 'FAIL: cron not running'",
        "remediation": "systemctl enable cron && systemctl start cron",
        "frameworks": ["CIS", "NIST-800-53:CM-7"],
    },
    {
        "id": "CIS-5.2",
        "title": "Ensure /etc/crontab permissions are restricted",
        "severity": "medium",
        "category": "Scheduling",
        "command": "stat -c '%a' /etc/crontab 2>/dev/null | grep -q '600' && echo 'PASS' || echo 'FAIL: /etc/crontab permissions too open'",
        "remediation": "chmod 600 /etc/crontab",
        "frameworks": ["CIS", "NIST-800-53:AC-6"],
    },
    {
        "id": "CIS-5.3",
        "title": "Ensure at/cron is restricted to authorized users",
        "severity": "medium",
        "category": "Scheduling",
        "command": "ls /etc/cron.allow >/dev/null 2>&1 && echo 'PASS' || echo 'FAIL: /etc/cron.allow not found'",
        "remediation": "touch /etc/cron.allow && chmod 600 /etc/cron.allow",
        "frameworks": ["CIS", "NIST-800-53:AC-3"],
    },
    {
        "id": "CIS-5.4",
        "title": "Ensure system-wide temp directory is sticky-bit protected",
        "severity": "medium",
        "category": "Scheduling",
        "command": "stat -c '%a' /tmp 2>/dev/null | grep -q '1777' && echo 'PASS' || echo 'FAIL: /tmp missing sticky bit'",
        "remediation": "chmod 1777 /tmp",
        "frameworks": ["CIS", "NIST-800-53:AC-6"],
    },
    {
        "id": "CIS-6.1",
        "title": "Ensure permissions on /etc/passwd are configured",
        "severity": "high",
        "category": "User Accounts",
        "command": "stat -c '%a' /etc/passwd 2>/dev/null | grep -q '644' && echo 'PASS' || echo 'FAIL: /etc/passwd permissions incorrect'",
        "remediation": "chmod 644 /etc/passwd",
        "frameworks": ["CIS", "NIST-800-53:AC-6"],
    },
    {
        "id": "CIS-6.2",
        "title": "Ensure permissions on /etc/shadow are configured",
        "severity": "critical",
        "category": "User Accounts",
        "command": "stat -c '%a' /etc/shadow 2>/dev/null | grep -q '640' && echo 'PASS' || echo 'FAIL: /etc/shadow permissions incorrect'",
        "remediation": "chmod 640 /etc/shadow",
        "frameworks": ["CIS", "NIST-800-53:AC-3"],
    },
    {
        "id": "CIS-6.3",
        "title": "Ensure password policies are configured",
        "severity": "high",
        "category": "User Accounts",
        "command": "grep -q 'PASS_MAX_DAYS\\s*90' /etc/login.defs && echo 'PASS' || echo 'FAIL: Password max days not set to 90'",
        "remediation": "Edit /etc/login.defs: PASS_MAX_DAYS 90",
        "frameworks": ["CIS", "NIST-800-53:IA-5"],
    },
    {
        "id": "CIS-6.4",
        "title": "Ensure default group for root account is GID 0",
        "severity": "medium",
        "category": "User Accounts",
        "command": "id root 2>/dev/null | grep -q 'gid=0' && echo 'PASS' || echo 'FAIL: Root GID not 0'",
        "remediation": "usermod -g 0 root",
        "frameworks": ["CIS", "NIST-800-53:AC-6"],
    },
    {
        "id": "CIS-6.5",
        "title": "Ensure root login is restricted to system console",
        "severity": "medium",
        "category": "User Accounts",
        "command": "grep -q '^console' /etc/securetty 2>/dev/null && echo 'PASS' || echo 'FAIL: Root login not restricted'",
        "remediation": "Edit /etc/securetty to only allow console",
        "frameworks": ["CIS", "NIST-800-53:AC-6"],
    },
    {
        "id": "CIS-7.1",
        "title": "Ensure permissions on SSH config are configured",
        "severity": "high",
        "category": "SSH",
        "command": "stat -c '%a' /etc/ssh/sshd_config 2>/dev/null | grep -q '600' && echo 'PASS' || echo 'FAIL: SSH config permissions incorrect'",
        "remediation": "chmod 600 /etc/ssh/sshd_config",
        "frameworks": ["CIS", "NIST-800-53:AC-3"],
    },
    {
        "id": "CIS-7.2",
        "title": "Ensure SSH Protocol 2 is enabled",
        "severity": "high",
        "category": "SSH",
        "command": "grep -q '^Protocol 2' /etc/ssh/sshd_config 2>/dev/null && echo 'PASS' || echo 'FAIL: SSH Protocol 1 may be enabled'",
        "remediation": "Add 'Protocol 2' to /etc/ssh/sshd_config",
        "frameworks": ["CIS", "NIST-800-53:SC-8"],
    },
    {
        "id": "CIS-7.3",
        "title": "Ensure SSH X11 forwarding is disabled",
        "severity": "medium",
        "category": "SSH",
        "command": "grep -q '^X11Forwarding no' /etc/ssh/sshd_config 2>/dev/null && echo 'PASS' || echo 'FAIL: X11 forwarding may be enabled'",
        "remediation": "Add 'X11Forwarding no' to /etc/ssh/sshd_config",
        "frameworks": ["CIS", "NIST-800-53:SC-7"],
    },
    {
        "id": "CIS-7.4",
        "title": "Ensure SSH MaxAuthTries is set to 3 or less",
        "severity": "medium",
        "category": "SSH",
        "command": "grep -qE '^MaxAuthTries\\s+[0-3]$' /etc/ssh/sshd_config 2>/dev/null && echo 'PASS' || echo 'FAIL: MaxAuthTries too high or not set'",
        "remediation": "Add 'MaxAuthTries 3' to /etc/ssh/sshd_config",
        "frameworks": ["CIS", "NIST-800-53:AC-7"],
    },
    {
        "id": "CIS-7.5",
        "title": "Ensure SSH root login is disabled",
        "severity": "high",
        "category": "SSH",
        "command": "grep -q '^PermitRootLogin no' /etc/ssh/sshd_config 2>/dev/null && echo 'PASS' || echo 'FAIL: SSH root login may be enabled'",
        "remediation": "Add 'PermitRootLogin no' to /etc/ssh/sshd_config",
        "frameworks": ["CIS", "NIST-800-53:AC-6"],
    },
    {
        "id": "CIS-7.6",
        "title": "Ensure SSH empty passwords are disabled",
        "severity": "critical",
        "category": "SSH",
        "command": "grep -q '^PermitEmptyPasswords no' /etc/ssh/sshd_config 2>/dev/null && echo 'PASS' || echo 'FAIL: Empty passwords may be permitted'",
        "remediation": "Add 'PermitEmptyPasswords no' to /etc/ssh/sshd_config",
        "frameworks": ["CIS", "NIST-800-53:IA-5"],
    },
    {
        "id": "CIS-8.1",
        "title": "Ensure NTP is configured and synchronized",
        "severity": "medium",
        "category": "Time Synchronization",
        "command": "systemctl is-active chrony 2>/dev/null | grep -q 'active' || systemctl is-active ntp 2>/dev/null | grep -q 'active' && echo 'PASS' || echo 'FAIL: NTP not running'",
        "remediation": "apt-get install chrony && systemctl enable chrony && systemctl start chrony",
        "frameworks": ["CIS", "NIST-800-53:AU-8"],
    },
    {
        "id": "CIS-9.1",
        "title": "Ensure kernel dmesg restriction is enabled",
        "severity": "medium",
        "category": "Kernel",
        "command": "sysctl kernel.dmesg_restrict 2>/dev/null | grep -q '= 1' && echo 'PASS' || echo 'FAIL: dmesg not restricted'",
        "remediation": "sysctl -w kernel.dmesg_restrict=1",
        "frameworks": ["CIS", "NIST-800-53:AC-3"],
    },
    {
        "id": "CIS-9.2",
        "title": "Ensure ASLR is enabled",
        "severity": "medium",
        "category": "Kernel",
        "command": "sysctl kernel.randomize_va_space 2>/dev/null | grep -q '= 2' && echo 'PASS' || echo 'FAIL: ASLR not fully enabled'",
        "remediation": "sysctl -w kernel.randomize_va_space=2",
        "frameworks": ["CIS", "NIST-800-53:SI-16"],
    },
    {
        "id": "CIS-10.1",
        "title": "Ensure SELinux or AppArmor is enabled",
        "severity": "high",
        "category": "MAC",
        "command": "getenforce 2>/dev/null | grep -qi 'enforcing' && echo 'PASS' || (aa-status --enabled 2>/dev/null && echo 'PASS' || echo 'FAIL: No MAC system enabled')",
        "remediation": "Enable SELinux: setenforce 1 and edit /etc/selinux/config",
        "frameworks": ["CIS", "NIST-800-53:AC-3"],
    },
    {
        "id": "CIS-11.1",
        "title": "Ensure unused kernel modules are disabled",
        "severity": "medium",
        "category": "Kernel Hardening",
        "command": "grep -q 'install usb-storage /bin/true' /etc/modprobe.d/*.conf 2>/dev/null && echo 'PASS' || echo 'WARN: usb-storage module may be loadable'",
        "remediation": "Add 'install usb-storage /bin/true' to /etc/modprobe.d/hardening.conf",
        "frameworks": ["CIS", "NIST-800-53:CM-7"],
    },
    {
        "id": "CIS-12.1",
        "title": "Ensure no world-writable files exist",
        "severity": "medium",
        "category": "File Permissions",
        "command": "find / -xdev -type f -perm -0002 2>/dev/null | head -5 | grep -q . && echo 'FAIL: World-writable files found' || echo 'PASS'",
        "remediation": "chmod o-w <file>",
        "frameworks": ["CIS", "NIST-800-53:AC-6"],
    },
    {
        "id": "CIS-12.2",
        "title": "Ensure no SUID/SGID executables in world-writable dirs",
        "severity": "medium",
        "category": "File Permissions",
        "command": "find / -xdev -type d -perm -0002 -exec find {} -perm -6000 \\; 2>/dev/null | head -5 | grep -q . && echo 'FAIL: SUID/SGID in world-writable dirs' || echo 'PASS'",
        "remediation": "Remove SUID/SGID bits or move files to restricted directories",
        "frameworks": ["CIS", "NIST-800-53:AC-6"],
    },
]


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
        _, stdout, stderr = await asyncio.to_thread(client.exec_command, command, timeout=30)
        exit_code = await asyncio.to_thread(stdout.channel.recv_exit_status)
        out = await asyncio.to_thread(stdout.read().decode, errors="replace")
        err = await asyncio.to_thread(stderr.read().decode, errors="replace")
        return exit_code, out, err
    except Exception as e:
        return -1, "", str(e)
    finally:
        client.close()


async def run_compliance_scan(node_id: str, host: str, username: str, password: str, framework: str = "CIS") -> dict:
    """
    Run compliance scan against a node.

    Args:
        node_id: Node identifier
        host: Node hostname/IP
        username: SSH username
        password: SSH password
        framework: Compliance framework (CIS, NIST-800-53)

    Returns:
        dict with scan results
    """
    _ensure_compliance_dir()
    scan_id = f"scan_{int(time.time())}"

    logger.info(f"[COMPLIANCE] Starting {framework} scan on {host} (node={node_id})")

    results = []
    passed = 0
    failed = 0
    warnings = 0

    # Filter checks by framework
    applicable_checks = [c for c in CIS_CHECKS if framework in c.get("frameworks", [])]

    for check in applicable_checks:
        exit_code, out, err = await _ssh_exec(host, username, password, check["command"])

        status = "pass"
        output = out.strip()
        if "FAIL" in output or exit_code != 0:
            status = "fail"
            failed += 1
        elif "WARN" in output:
            status = "warning"
            warnings += 1
        else:
            passed += 1

        results.append({
            "id": check["id"],
            "title": check["title"],
            "severity": check["severity"],
            "category": check["category"],
            "status": status,
            "output": output,
            "remediation": check.get("remediation", ""),
            "frameworks": check.get("frameworks", []),
        })

    # Calculate score
    total = len(results)
    score = round((passed / total * 100) if total > 0 else 0, 1)

    scan_result = {
        "scan_id": scan_id,
        "node_id": node_id,
        "host": host,
        "framework": framework,
        "timestamp": time.time(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "score": score,
        },
        "results": results,
    }

    # Save scan results
    scan_path = os.path.join(COMPLIANCE_DIR, f"{scan_id}.json")
    with open(scan_path, "w") as f:
        json.dump(scan_result, f, indent=2)

    logger.info(f"[COMPLIANCE] Scan {scan_id} complete: {score}% ({passed}/{total} passed)")

    return scan_result


def get_scan_history() -> list[dict]:
    """List all compliance scans."""
    _ensure_compliance_dir()
    scans = []
    for f in sorted(os.listdir(COMPLIANCE_DIR), reverse=True):
        if f.endswith(".json") and f.startswith("scan_"):
            try:
                with open(os.path.join(COMPLIANCE_DIR, f)) as fh:
                    data = json.load(fh)
                    scans.append({
                        "scan_id": data["scan_id"],
                        "node_id": data["node_id"],
                        "host": data["host"],
                        "framework": data["framework"],
                        "timestamp": data["timestamp"],
                        "summary": data["summary"],
                    })
            except Exception:
                pass
    return scans


def get_scan_detail(scan_id: str) -> Optional[dict]:
    """Get detailed results of a specific scan."""
    scan_path = os.path.join(COMPLIANCE_DIR, f"{scan_id}.json")
    if os.path.exists(scan_path):
        with open(scan_path) as f:
            return json.load(f)
    return None


def get_frameworks() -> list[dict]:
    """List available compliance frameworks."""
    frameworks = {}
    for check in CIS_CHECKS:
        for fw in check.get("frameworks", []):
            if fw not in frameworks:
                frameworks[fw] = {"id": fw, "check_count": 0}
            frameworks[fw]["check_count"] += 1
    return list(frameworks.values())
