#!/usr/bin/env python3
"""Cross-platform installer/launcher for Netrunner."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
PROGRESS_TOTAL = 5
_progress_step = 0


def command(name: str) -> str | None:
    return shutil.which(name)


def progress(label: str, status: str = "running") -> None:
    width = 28
    filled = int(width * _progress_step / PROGRESS_TOTAL)
    bar = "#" * filled + "-" * (width - filled)
    print(f"[{bar}] {_progress_step}/{PROGRESS_TOTAL} {status}: {label}", flush=True)


def finish_step(label: str, skipped: bool = False) -> None:
    global _progress_step
    _progress_step += 1
    progress(label, "skip" if skipped else "done")


def run(cmd: list[str], cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=str(cwd), env=env)


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def ensure_venv() -> Path:
    py = venv_python()
    if not py.exists():
        progress("Creating Python virtual environment")
        run([sys.executable, "-m", "venv", str(VENV)])
        finish_step("Python virtual environment")
    else:
        finish_step("Python virtual environment", skipped=True)
    return py


def ensure_backend(py: Path) -> None:
    env = os.environ.copy()
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    progress("Installing backend dependencies")
    run([str(py), "-m", "pip", "install", "-q", "-r", "backend/requirements.txt"], env=env)
    finish_step("Backend dependencies")


def ensure_frontend(skip: bool) -> None:
    if skip:
        finish_step("Frontend dependencies", skipped=True)
        finish_step("Frontend build", skipped=True)
        return
    npm = command("npm.cmd" if os.name == "nt" else "npm") or command("npm")
    if not npm:
        raise SystemExit(
            "npm was not found. Install Node.js LTS from https://nodejs.org/ and run this again."
        )
    frontend = ROOT / "frontend"
    if not (frontend / "node_modules").exists():
        progress("Installing frontend dependencies")
        run([npm, "install", "--silent"], cwd=frontend)
        finish_step("Frontend dependencies")
    else:
        finish_step("Frontend dependencies", skipped=True)
    if not (frontend / "dist").exists():
        progress("Building frontend")
        run([npm, "run", "build"], cwd=frontend)
        finish_step("Frontend build")
    else:
        finish_step("Frontend build", skipped=True)


def ensure_certs() -> tuple[Path, Path]:
    openssl = command("openssl")
    if not openssl:
        raise SystemExit("OpenSSL was not found, so HTTPS certificates cannot be generated.")
    cert_dir = ROOT / ".certs"
    cert_dir.mkdir(exist_ok=True)
    cert = cert_dir / "cert.pem"
    key = cert_dir / "key.pem"
    if not cert.exists() or not key.exists():
        print("Generating self-signed HTTPS certificates...", flush=True)
        run([
            openssl,
            "req",
            "-x509",
            "-newkey",
            "rsa:4096",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-sha256",
            "-days",
            "365",
            "-nodes",
            "-subj",
            "/CN=localhost",
        ])
    return cert, key


def main() -> None:
    parser = argparse.ArgumentParser(description="Install dependencies and start Netrunner.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Default: 127.0.0.1")
    parser.add_argument("--port", default=8000, type=int, help="Bind port. Default: 8000")
    parser.add_argument("--https", action="store_true", help="Start with a self-signed HTTPS certificate.")
    parser.add_argument("--skip-frontend", action="store_true", help="Do not install/build the frontend.")
    args, netrunner_args = parser.parse_known_args()

    py = ensure_venv()
    ensure_backend(py)
    ensure_frontend(args.skip_frontend)
    finish_step("Launcher ready")

    url = f"{'https' if args.https else 'http'}://localhost:{args.port}"
    print("", flush=True)
    print("Netrunner is starting.", flush=True)
    print(f"Open: {url}", flush=True)
    print("Login: admin / admin", flush=True)
    print("", flush=True)

    cmd = [str(py), "netrunner.py", "--host", args.host, "--port", str(args.port)]
    if args.https:
        cert, key = ensure_certs()
        cmd.extend(["--ssl-keyfile", str(key), "--ssl-certfile", str(cert)])
    cmd.extend(netrunner_args)
    os.execv(str(py), cmd)


if __name__ == "__main__":
    main()
