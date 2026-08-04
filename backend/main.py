"""Netrunner — FastAPI backend entry point."""

from __future__ import annotations

import argparse
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .routers import (
    ai,
    scripts,
    gns3,
    links,
    nodes,
    preview,
    terminal,
    settings,
    threats,
    defense,
    system,
    chaos,
    auth,
    redteam,
    deception,
    agent,
    rules,
    internal,
    telemetry,
    wifi,
    recon,
    analyze,
    kubernetes,
    vpn,
    bluetooth,
    agents,
    bruteforce,
    intelligence,
    sdn,
    database,
    host,
    usb,
    mcu,
    files,
    events,
    mcu_repl,
    alerts,
    reports,
    playbooks,
    analytics,
    integrations,
    hunting,
    kismet,
    wifi_attack,
    forensics,
    compliance,
    lateral_movement,
    log_aggregation,
    social_engineering,
    privesc,
    incident_response,
    exfiltration,
    protocol_tester,
    network_config,
    layer2,
    layer3,
    layer4,
    layer5,
    layer6,
    layer7,
    graph,
    protocol_containers,
)
from .routers.auth import decode_access_token, get_current_user

# Require a valid JWT for protected routers (login + internal m2m stay open).
AUTH = [Depends(get_current_user)]
from .routers.settings import load_settings
from .core.db import init_db

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
DATA_DIR = Path("data")


# CORS: Read from env var (set from settings on startup) or default to localhost
# Comma-separated list of origins. Empty = localhost only (secure default).
def _get_cors_origins() -> list[str]:
    env = os.environ.get("NETRUNNER_CORS_ORIGINS")
    if env:
        return [o.strip() for o in env.split(",") if o.strip()]
    # Default: allow local frontend dev server and packaged frontend
    return [
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:8000",  # Packaged frontend served by FastAPI
        "http://127.0.0.1:8000",
    ]


from .services.flow_analytics import flow_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ready = False
    # Ensure directories exist
    for d in ("configs", "captures", "exports", "agents"):
        (DATA_DIR / d).mkdir(parents=True, exist_ok=True)

    # Initialize DB
    await init_db()

    # Seed default users (admin/analyst) on first run
    from .routers.auth import seed_default_users

    await seed_default_users()

    # Load settings into env
    s = await load_settings()
    if s.get("ai_api_key") and (s.get("ai_provider") or "openai").lower() == "openai":
        os.environ["OPENAI_API_KEY"] = s["ai_api_key"]
    elif s.get("openai_api_key"):
        os.environ["OPENAI_API_KEY"] = s["openai_api_key"]

    # CORS: Load from settings into env for use by _get_cors_origins()
    if s.get("cors_origins"):
        os.environ["NETRUNNER_CORS_ORIGINS"] = s["cors_origins"]

    # Start background tasks for threats and chaos explicitly since lifespan bypasses on_event("startup")
    import asyncio
    from .routers import threats, chaos, telemetry, wifi, bluetooth
    from .core.telemetry import poll_telemetry_loop
    from .core.wifi_csi import start_csi_engine
    from .core.bluetooth import start_bluetooth_engine

    from .services.ids_engine import start_ids
    from .services.soar_playbooks import start_soar
    from .services.ebpf_runtime import start_ebpf_agent
    from .core.storage import check_storage_limits

    threats._threat_task = asyncio.create_task(threats.broadcast_threats())
    chaos._chaos_task = asyncio.create_task(chaos.chaos_loop())
    telemetry._telemetry_task = asyncio.create_task(telemetry.broadcast_telemetry())
    telemetry._nexus_task = asyncio.create_task(telemetry.broadcast_nexus())
    telemetry._poll_task = asyncio.create_task(poll_telemetry_loop())
    from .core.reachability import reachability_loop
    from .core.state import telemetry_queue

    telemetry._reach_task = asyncio.create_task(reachability_loop(telemetry_queue))

    # Start Flow Analytics Engine
    from .services.flow_analytics import flow_engine

    flow_task = asyncio.create_task(flow_engine.start())

    # Start Advanced Network Services (IDS, SOAR, Vulnerability Scanner, eBPF)
    ids_task = asyncio.create_task(start_ids())
    soar_task = asyncio.create_task(start_soar())
    ebpf_task = asyncio.create_task(start_ebpf_agent())

    from .services.api_analyzer import ShadowAPIDetector

    api_analyzer = ShadowAPIDetector(app)
    api_analyzer_task = asyncio.create_task(api_analyzer.run())

    from .services.bas_replay import start_bas_simulation

    bas_task = asyncio.create_task(start_bas_simulation(interval=3600))

    from .services.sbom_analyzer import start_sbom_analyzer

    sbom_task = asyncio.create_task(start_sbom_analyzer())

    from .services.firmware_security import start_firmware_security

    fw_task = asyncio.create_task(start_firmware_security())

    from .services.ot_twin_emulator import start_ot_emulator

    ot_task = asyncio.create_task(start_ot_emulator())

    from .services.ciem_engine import ciem_engine, start_ciem_engine

    ciem_task = asyncio.create_task(start_ciem_engine())

    from .services.deepfake_scanner import start_deepfake_scanner

    deepfake_task = asyncio.create_task(start_deepfake_scanner())

    from .services.deception import start_deception_orchestrator

    deception_task = asyncio.create_task(start_deception_orchestrator())

    from .services.asm_engine import start_asm_engine

    asm_task = asyncio.create_task(start_asm_engine())

    from .services.nhi_monitor import start_nhi_monitor

    nhi_task = asyncio.create_task(start_nhi_monitor())

    from backend.services.behavior_engine import (
        start_behavior_engine,
        stop_behavior_engine,
    )
    from backend.services.easm_engine import start_easm_engine, stop_easm_engine
    from backend.services.datalake import datalake_archiver_loop

    start_behavior_engine()
    start_easm_engine()
    asyncio.create_task(datalake_archiver_loop())

    wifi._broadcast_csi_task = asyncio.create_task(wifi.broadcast_csi())
    asyncio.create_task(check_storage_limits())
    wifi._broadcast_mesh_task = asyncio.create_task(wifi.broadcast_mesh())
    bluetooth._bluetooth_broadcast_task = asyncio.create_task(
        bluetooth.broadcast_bluetooth()
    )
    kismet._kismet_broadcast_task = asyncio.create_task(kismet.broadcast_kismet())
    await start_csi_engine()
    await start_bluetooth_engine()

    app.state.ready = True
    yield
    # Cleanup background tasks
    app.state.ready = False
    if threats._threat_task:
        threats._threat_task.cancel()
    if chaos._chaos_task:
        chaos._chaos_task.cancel()
    if telemetry._telemetry_task:
        telemetry._telemetry_task.cancel()
    if hasattr(telemetry, "_nexus_task") and telemetry._nexus_task:
        telemetry._nexus_task.cancel()
    if hasattr(telemetry, "_poll_task") and telemetry._poll_task:
        telemetry._poll_task.cancel()
    if hasattr(wifi, "_broadcast_csi_task") and wifi._broadcast_csi_task:
        wifi._broadcast_csi_task.cancel()
    if hasattr(wifi, "_broadcast_mesh_task") and wifi._broadcast_mesh_task:
        wifi._broadcast_mesh_task.cancel()
    if (
        hasattr(bluetooth, "_bluetooth_broadcast_task")
        and bluetooth._bluetooth_broadcast_task
    ):
        bluetooth._bluetooth_broadcast_task.cancel()

    if hasattr(kismet, "_kismet_broadcast_task") and kismet._kismet_broadcast_task:
        kismet._kismet_broadcast_task.cancel()

    from .services.ebpf_runtime import ebpf_agent

    await ebpf_agent.stop()

    stop_behavior_engine()
    stop_easm_engine()
    await ciem_engine.stop()

    from .core.bluetooth import stop_bluetooth_engine

    await stop_bluetooth_engine()

    from .core.wifi_csi import generator, mesh_generator

    generator.stop()
    mesh_generator.stop()

    from .core.session import session_manager

    session_manager.close_all()


app = FastAPI(title="Netrunner", version="1.0.0", lifespan=lifespan)
app.state.ready = False

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from .core.limiter import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
app.add_middleware(SlowAPIMiddleware)


_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_STUDENT_WRITE_ALLOWLIST = {"/api/auth/login", "/api/telemetry/ui"}
_NON_USER_API_PREFIXES = ("/api/agent/", "/mcp")


@app.middleware("http")
async def enforce_authenticated_writes_and_student_read_only(request, call_next):
    """Require user auth for writes and keep student accounts read-only.

    This is a defense-in-depth release gate: new routers cannot accidentally
    expose attack or configuration actions to classroom student accounts.
    Agent and MCP traffic use separate authentication mechanisms.
    """
    path = request.url.path
    if (
        request.method in _MUTATING_METHODS
        and path not in _STUDENT_WRITE_ALLOWLIST
        and not path.startswith(_NON_USER_API_PREFIXES)
    ):
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
            )
        try:
            token = authorization.removeprefix("Bearer ").strip()
            user = decode_access_token(token)
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})
        if user["role"] == "student":
            return JSONResponse(
                status_code=403,
                content={"detail": "Student accounts are read-only"},
            )

    return await call_next(request)


@app.middleware("http")
async def security_headers(request, call_next):
    # API Security Middleware (Traffic Mirroring)
    from .services.api_analyzer import api_events_queue

    user = None
    if "Authorization" in request.headers:
        user = "authenticated_user"  # Simplified for this demo

    # Asynchronously push metadata for BOLA & Shadow API detection
    try:
        api_events_queue.put_nowait(
            {"path": request.url.path, "method": request.method, "user": user}
        )
    except Exception:
        pass

    # Active Zero Trust Edge Proxy Interception
    from .services.edge_proxy import zero_trust_edge_proxy_middleware

    # We delegate the actual request yielding to the proxy
    response = await zero_trust_edge_proxy_middleware(request, call_next)

    # It might return a direct JSONResponse (403) before hitting the application
    if hasattr(response, "headers"):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Auth must stay public (login). Internal is machine-to-machine (Go mux) and is
# left open for now — see note in routers/internal.py.
app.include_router(auth.router, prefix="/api")
app.include_router(internal.router)

# Protected HTTP routers — every endpoint requires a valid JWT.
app.include_router(nodes.router, prefix="/api", dependencies=AUTH)
app.include_router(links.router, prefix="/api", dependencies=AUTH)
app.include_router(gns3.router, prefix="/api", dependencies=AUTH)
app.include_router(layer2.router, prefix="/api", dependencies=AUTH)
app.include_router(layer3.router, prefix="/api", dependencies=AUTH)
app.include_router(layer4.router, prefix="/api", dependencies=AUTH)
app.include_router(layer5.router, prefix="/api", dependencies=AUTH)
app.include_router(layer6.router, prefix="/api", dependencies=AUTH)
app.include_router(layer7.router, prefix="/api", dependencies=AUTH)
app.include_router(settings.router, prefix="/api", dependencies=AUTH)
app.include_router(scripts.router, prefix="/api", dependencies=AUTH)
app.include_router(preview.router, prefix="/api", dependencies=AUTH)
app.include_router(analyze.router, prefix="/api", dependencies=AUTH)
app.include_router(defense.router, prefix="/api", dependencies=AUTH)
app.include_router(system.router, prefix="/api", dependencies=AUTH)
app.include_router(chaos.router, prefix="/api", dependencies=AUTH)
app.include_router(redteam.router, prefix="/api", dependencies=AUTH)
app.include_router(deception.router, prefix="/api", dependencies=AUTH)
app.include_router(intelligence.router, prefix="/api", dependencies=AUTH)
app.include_router(agent.router, prefix="/api/agent")
app.include_router(rules.router, prefix="/api/rules", dependencies=AUTH)
app.include_router(recon.router, prefix="/api", dependencies=AUTH)
app.include_router(agents.router, prefix="/api", dependencies=AUTH)
app.include_router(kubernetes.router, prefix="/api", dependencies=AUTH)
app.include_router(vpn.router, prefix="/api", dependencies=AUTH)
app.include_router(bruteforce.router, prefix="/api", dependencies=AUTH)
app.include_router(database.router, prefix="/api/v1", dependencies=AUTH)
app.include_router(host.router, prefix="/api/v1", dependencies=AUTH)
app.include_router(files.router, prefix="/api/v1/files", dependencies=AUTH)
app.include_router(graph.router, prefix="/api/v1", dependencies=AUTH)
from .routers import workspace, builder

app.include_router(workspace.router, prefix="/api/v1/workspace", dependencies=AUTH)
app.include_router(mcu.router, prefix="/api/v1/mcu", dependencies=AUTH)
app.include_router(mcu.public_router, prefix="/api/v1/mcu")

# Mixed HTTP + WebSocket routers — auth applied per-endpoint inside the router
# (router-level deps would also reject browser WS handshakes).
app.include_router(builder.router, prefix="/api/v1/workspace")
app.include_router(threats.router)
app.include_router(usb.router, prefix="/api/v1/usb")
app.include_router(terminal.router)
app.include_router(telemetry.router)
app.include_router(wifi.router)
app.include_router(bluetooth.router)
app.include_router(ai.router, prefix="/api")
app.include_router(sdn.router)
app.include_router(events.router)
app.include_router(mcu_repl.router)
app.include_router(alerts.router, dependencies=AUTH)
app.include_router(reports.router, prefix="/api/v1", dependencies=AUTH)
app.include_router(playbooks.router)
app.include_router(analytics.router, dependencies=AUTH)
app.include_router(integrations.router, dependencies=AUTH)
app.include_router(hunting.router, dependencies=AUTH)
app.include_router(kismet.router)
app.include_router(wifi_attack.router, prefix="/api", dependencies=AUTH)
app.include_router(forensics.router, prefix="/api", dependencies=AUTH)
app.include_router(compliance.router, prefix="/api", dependencies=AUTH)
app.include_router(lateral_movement.router, prefix="/api", dependencies=AUTH)
app.include_router(log_aggregation.router, prefix="/api", dependencies=AUTH)
app.include_router(social_engineering.router, prefix="/api", dependencies=AUTH)
app.include_router(privesc.router, prefix="/api", dependencies=AUTH)
app.include_router(incident_response.router, prefix="/api", dependencies=AUTH)
app.include_router(exfiltration.router, prefix="/api", dependencies=AUTH)
app.include_router(protocol_tester.router, prefix="/api", dependencies=AUTH)
app.include_router(protocol_containers.router, prefix="/api", dependencies=AUTH)
app.include_router(network_config.router, prefix="/api/network", dependencies=AUTH)

# Super Expert Plugins
from backend.plugins.packet_capture.router import router as packet_capture_router
from backend.plugins.netbox_sync.router import router as netbox_sync_router
from backend.plugins.bgp_control.router import router as bgp_control_router

app.include_router(packet_capture_router, prefix="/api", dependencies=AUTH)
app.include_router(netbox_sync_router, prefix="/api", dependencies=AUTH)
app.include_router(bgp_control_router, prefix="/api", dependencies=AUTH)

from .routers.mcp_server import mcp_app

app.mount("/mcp", mcp_app)


@app.get("/api/health", tags=["system"])
async def health():
    """Lightweight liveness probe that has no external dependencies."""
    return {"status": "ok", "service": "netrunner", "version": app.version}


@app.get("/api/ready", tags=["system"])
async def ready():
    """Report ready only after startup initialization has completed."""
    if not app.state.ready:
        return JSONResponse(status_code=503, content={"status": "starting"})
    return {"status": "ready", "service": "netrunner"}


class NoCacheStaticFiles(StaticFiles):
    def is_not_modified(self, response_headers, request_headers) -> bool:
        return False

    def file_response(self, *args, **kwargs):
        resp = super().file_response(*args, **kwargs)
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp


if FRONTEND_DIST.exists():
    assets = FRONTEND_DIST / "assets"
    if assets.exists():
        app.mount("/assets", NoCacheStaticFiles(directory=assets), name="assets")

    frontend_data = FRONTEND_DIST / "data"
    if frontend_data.exists():
        app.mount("/data", NoCacheStaticFiles(directory=frontend_data), name="data")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str = ""):
        # Don't serve SPA for API or WS routes
        if full_path.startswith(("api/", "ws/")):
            from fastapi import HTTPException

            raise HTTPException(404)

        from fastapi.responses import FileResponse

        resp = FileResponse(FRONTEND_DIST / "index.html")
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

else:

    @app.get("/", include_in_schema=False)
    async def root():
        from fastapi.responses import JSONResponse

        return JSONResponse(
            {
                "message": "Netrunner backend running. Build the frontend with: cd frontend && npm install && npm run build",
                "docs": "/docs",
            }
        )


def main():
    ap = argparse.ArgumentParser(
        description="Netrunner — network & Linux management tool"
    )
    ap.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    ap.add_argument("--port", default=8000, type=int, help="Bind port (default: 8000)")
    ap.add_argument(
        "--reload", action="store_true", help="Enable auto-reload (dev mode)"
    )
    ap.add_argument("--ssl-keyfile", default=None, help="Path to SSL key file")
    ap.add_argument("--ssl-certfile", default=None, help="Path to SSL certificate file")
    args = ap.parse_args()

    run_kwargs = {
        "host": args.host,
        "port": args.port,
        "reload": args.reload,
    }
    if args.ssl_keyfile and args.ssl_certfile:
        run_kwargs["ssl_keyfile"] = args.ssl_keyfile
        run_kwargs["ssl_certfile"] = args.ssl_certfile

    uvicorn.run("backend.main:app", **run_kwargs)


if __name__ == "__main__":
    main()
