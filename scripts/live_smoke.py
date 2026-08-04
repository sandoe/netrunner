#!/usr/bin/env python3
"""Non-destructive live smoke test. Never prints credentials or JWTs."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("NETRUNNER_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def request(path: str, *, method: str = "GET", token: str = "", body=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = response.read()
            return response.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        try:
            decoded = json.loads(payload) if payload else None
        except json.JSONDecodeError:
            decoded = None
        return exc.code, decoded


def mux_request(token: str = "") -> int:
    parsed = urllib.parse.urlsplit(BASE)
    mux_base = urllib.parse.urlunsplit(
        (parsed.scheme, f"{parsed.hostname}:8081", "/ws/terminal", "", "")
    )
    query = urllib.parse.urlencode({"token": token}) if token else ""
    target = mux_base + ("?" + query if query else "")
    try:
        with urllib.request.urlopen(target, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def expect(label: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
    print(f"PASS  {label}")


def expect_one_of(label: str, actual, expected) -> None:
    if actual not in expected:
        raise AssertionError(f"{label}: expected one of {expected!r}, got {actual!r}")
    print(f"PASS  {label}")


def login(username: str, password: str) -> str:
    status, payload = request(
        "/api/auth/login",
        method="POST",
        body={"username": username, "password": password},
    )
    expect(f"{username} login", status, 200)
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise AssertionError(f"{username} login returned no access token")
    expect(f"{username} role", payload.get("role"), username)
    return str(payload["access_token"])


def main() -> int:
    env = load_env()
    mode = env.get("NETRUNNER_DEPLOYMENT_MODE", "server").strip().lower()
    if mode not in ("server", "student"):
        raise RuntimeError(f"Invalid NETRUNNER_DEPLOYMENT_MODE: {mode}")
    required = ["NETRUNNER_STUDENT_PASSWORD"]
    if mode == "server":
        required.extend(
            ["NETRUNNER_ADMIN_PASSWORD", "NETRUNNER_ANALYST_PASSWORD"]
        )
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise RuntimeError("Missing deployment credentials in .env: " + ", ".join(missing))

    status, payload = request("/api/health")
    expect("liveness HTTP", status, 200)
    expect("liveness JSON", payload.get("status"), "ok")
    status, payload = request("/api/ready")
    expect("readiness HTTP", status, 200)
    expect("readiness JSON", payload.get("status"), "ready")

    status, _ = request("/api/nodes")
    expect("anonymous API rejection", status, 401)
    status, _ = request("/api/internal/node/nonexistent")
    expect("internal credential rejection", status, 401)

    student = login("student", env["NETRUNNER_STUDENT_PASSWORD"])
    tokens = [("student", student)]
    if mode == "server":
        admin = login("admin", env["NETRUNNER_ADMIN_PASSWORD"])
        analyst = login("analyst", env["NETRUNNER_ANALYST_PASSWORD"])
        tokens[0:0] = [("admin", admin), ("analyst", analyst)]
    else:
        for username in ("admin", "analyst"):
            status, _ = request(
                "/api/auth/login",
                method="POST",
                body={"username": username, "password": "disabled-in-student-mode"},
            )
            expect(f"{username} disabled", status, 401)

    for username, token in tokens:
        status, payload = request("/api/auth/me", token=token)
        expect(f"{username} authenticated", status, 200)
        expect(f"{username} identity", payload.get("role"), username)

    status, _ = request("/api/__release_probe__", method="POST", token=student, body={})
    expect("student write denied", status, 403)
    if mode == "server":
        status, _ = request("/api/__release_probe__", method="POST", token=analyst, body={})
        expect_one_of("analyst passes write gate", status, (404, 405))

    expect("anonymous terminal rejection", mux_request(), 401)
    expect("student terminal rejection", mux_request(student), 401)
    if mode == "server":
        expect("analyst terminal authentication", mux_request(analyst), 400)

    print("LIVE SMOKE PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"LIVE SMOKE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
