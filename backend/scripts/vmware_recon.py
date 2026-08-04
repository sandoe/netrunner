#!/usr/bin/env python3
import sys
import argparse
import socket
import json
import urllib.request
import ssl
import subprocess
import time
from pathlib import Path


def log_result(target, event_type, details, success=True):
    log_file = Path("/tmp/netrunner-vmware.jsonl")
    result = {
        "timestamp": time.time(),
        "target": target,
        "type": event_type,
        "success": success,
        "details": details,
    }
    SERVER_URL = __import__("os").environ.get("ORCHESTRATOR_URL")
    if SERVER_URL:
        try:
            import urllib.request

            req = urllib.request.Request(
                f"{SERVER_URL.rstrip('/')}/api/telemetry",
                data=json.dumps(result).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass

    with open(log_file, "a") as f:
        f.write(json.dumps(result) + "\n")


def check_port(target, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    return sock.connect_ex((target, port)) == 0


def nmap_recon(target):
    log_result(target, "recon", "Starting Nmap VMware Reconnaissance...", True)
    try:
        res = subprocess.run(
            [
                "nmap",
                "-p",
                "443,902",
                "--script",
                "vmware-version,vmauthd-brute",
                target,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if "vmware-version" in res.stdout or "vmauthd" in res.stdout:
            log_result(target, "nmap_result", res.stdout, True)
        else:
            log_result(
                target, "nmap_result", "No VMware specific info found by Nmap.", False
            )
    except Exception as e:
        log_result(target, "nmap_error", f"Nmap execution failed: {e}", False)


def unauth_api_check(target):
    context = ssl._create_unverified_context()
    urls = [
        f"https://{target}/sdk/vimService.wsdl",
        f"https://{target}/rest/vcenter/vm",
        f"https://{target}/mob/?moid=ha-folder-root",
    ]

    found = []
    for url in urls:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, context=context, timeout=3) as response:
                if response.status == 200:
                    found.append(url)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                found.append(f"{url} (Requires Auth)")
        except Exception:
            pass

    if found:
        log_result(
            target,
            "api_endpoints",
            f"Discovered API endpoints: {', '.join(found)}",
            True,
        )
    else:
        log_result(
            target, "api_endpoints", "No unauthenticated API endpoints found.", False
        )


def main():
    parser = argparse.ArgumentParser(description="Netrunner VMware Reconnaissance")
    parser.add_argument("--target", required=True, help="Target IP address")
    args = parser.parse_args()

    if not check_port(args.target, 443) and not check_port(args.target, 902):
        log_result(
            args.target,
            "error",
            "Ports 443 and 902 are closed. Not a VMware target.",
            False,
        )
        return

    nmap_recon(args.target)
    unauth_api_check(args.target)


if __name__ == "__main__":
    main()
