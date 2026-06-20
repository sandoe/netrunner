"""Netrunner — FastAPI backend entry point."""
from __future__ import annotations

import argparse
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routers import ai, scripts, gns3, links, nodes, preview, terminal, settings, threats, defense, system, chaos, auth, redteam, deception, agent, rules, internal, telemetry, wifi, recon, analyze, kubernetes, vpn, bluetooth, agents, bruteforce, intelligence, sdn, database, host, usb, mcu, files, events, mcu_repl, alerts, reports, playbooks, analytics, integrations, hunting, kismet, wifi_attack, forensics, compliance, lateral_movement, log_aggregation, social_engineering, privesc, incident_response, exfiltration
from .routers.auth import get_current_user

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
        "http://localhost:5173",      # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:8000",      # Packaged frontend served by FastAPI
        "http://127.0.0.1:8000",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    from .services.vuln_scanner import start_scanner
    from .services.threat_intel import start_threat_intel_sync
    from .core.storage import check_storage_limits

    threats._threat_task = asyncio.create_task(threats.broadcast_threats())
    chaos._chaos_task = asyncio.create_task(chaos.chaos_loop())
    telemetry._telemetry_task = asyncio.create_task(telemetry.broadcast_telemetry())
    telemetry._poll_task = asyncio.create_task(poll_telemetry_loop())
    from .core.reachability import reachability_loop
    from .core.state import telemetry_queue
    telemetry._reach_task = asyncio.create_task(reachability_loop(telemetry_queue))
    

    
    # Start Advanced Network Services (IDS, SOAR, Vulnerability Scanner)
    ids_task = asyncio.create_task(start_ids())
    soar_task = asyncio.create_task(start_soar())
    vuln_task = asyncio.create_task(start_scanner())
    threat_intel_task = asyncio.create_task(start_threat_intel_sync())
    
    wifi._broadcast_csi_task = asyncio.create_task(wifi.broadcast_csi())
    asyncio.create_task(check_storage_limits())
    wifi._broadcast_mesh_task = asyncio.create_task(wifi.broadcast_mesh())
    bluetooth._bluetooth_broadcast_task = asyncio.create_task(bluetooth.broadcast_bluetooth())
    kismet._kismet_broadcast_task = asyncio.create_task(kismet.broadcast_kismet())
    await start_csi_engine()
    await start_bluetooth_engine()

    yield
    # Cleanup background tasks
    if threats._threat_task:
        threats._threat_task.cancel()
    if chaos._chaos_task:
        chaos._chaos_task.cancel()
    if telemetry._telemetry_task:
        telemetry._telemetry_task.cancel()
    if hasattr(telemetry, "_poll_task") and telemetry._poll_task:
        telemetry._poll_task.cancel()
    if hasattr(wifi, "_broadcast_csi_task") and wifi._broadcast_csi_task:
        wifi._broadcast_csi_task.cancel()
    if hasattr(wifi, "_broadcast_mesh_task") and wifi._broadcast_mesh_task:
        wifi._broadcast_mesh_task.cancel()
    if hasattr(bluetooth, "_bluetooth_broadcast_task") and bluetooth._bluetooth_broadcast_task:
        bluetooth._bluetooth_broadcast_task.cancel()
    
    if hasattr(kismet, "_kismet_broadcast_task") and kismet._kismet_broadcast_task:
        kismet._kismet_broadcast_task.cancel()

    from .core.bluetooth import stop_bluetooth_engine
    await stop_bluetooth_engine()

    from .core.wifi_csi import generator, mesh_generator
    generator.stop()
    mesh_generator.stop()

    from .core.session import session_manager
    session_manager.close_all()


app = FastAPI(title="Netrunner", version="1.0.0", lifespan=lifespan)

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from .core.limiter import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
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
app.include_router(auth.router,     prefix="/api")
app.include_router(internal.router)

# Protected HTTP routers — every endpoint requires a valid JWT.
app.include_router(nodes.router,    prefix="/api", dependencies=AUTH)
app.include_router(links.router,    prefix="/api", dependencies=AUTH)
app.include_router(gns3.router,     prefix="/api", dependencies=AUTH)
app.include_router(settings.router, prefix="/api", dependencies=AUTH)
app.include_router(scripts.router,  prefix="/api", dependencies=AUTH)
app.include_router(preview.router,  prefix="/api", dependencies=AUTH)
app.include_router(analyze.router,  prefix="/api", dependencies=AUTH)
app.include_router(defense.router,  prefix="/api", dependencies=AUTH)
app.include_router(system.router,   prefix="/api", dependencies=AUTH)
app.include_router(chaos.router,    prefix="/api", dependencies=AUTH)
app.include_router(redteam.router,  prefix="/api", dependencies=AUTH)
app.include_router(deception.router,prefix="/api", dependencies=AUTH)
app.include_router(intelligence.router, prefix="/api", dependencies=AUTH)
app.include_router(agent.router,    prefix="/api/agent")
app.include_router(rules.router,    prefix="/api/rules", dependencies=AUTH)
app.include_router(recon.router,    prefix="/api", dependencies=AUTH)
app.include_router(agents.router,   prefix="/api", dependencies=AUTH)
app.include_router(kubernetes.router, prefix="/api", dependencies=AUTH)
app.include_router(vpn.router,      prefix="/api", dependencies=AUTH)
app.include_router(bruteforce.router, prefix="/api", dependencies=AUTH)
app.include_router(database.router, prefix="/api/v1", dependencies=AUTH)
app.include_router(host.router,     prefix="/api/v1", dependencies=AUTH)
app.include_router(files.router,    prefix="/api/v1/files", dependencies=AUTH)
from .routers import workspace, builder
app.include_router(workspace.router, prefix="/api/v1/workspace", dependencies=AUTH)
app.include_router(mcu.router,      prefix="/api/v1/mcu", dependencies=AUTH)
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
app.include_router(ai.router,       prefix="/api")
app.include_router(sdn.router)
app.include_router(events.router)
app.include_router(mcu_repl.router)
app.include_router(alerts.router)
app.include_router(reports.router)
app.include_router(playbooks.router)
app.include_router(analytics.router)
app.include_router(integrations.router)
app.include_router(hunting.router)
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

# Super Expert Plugins
from backend.plugins.packet_capture.router import router as packet_capture_router
from backend.plugins.netbox_sync.router import router as netbox_sync_router
from backend.plugins.bgp_control.router import router as bgp_control_router

app.include_router(packet_capture_router, prefix="/api", dependencies=AUTH)
app.include_router(netbox_sync_router, prefix="/api", dependencies=AUTH)
app.include_router(bgp_control_router, prefix="/api", dependencies=AUTH)

from .routers import files
app.include_router(files.router)

from .routers.mcp_server import mcp_app
app.mount("/mcp", mcp_app)

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
        return JSONResponse({
            "message": "Netrunner backend running. Build the frontend with: cd frontend && npm install && npm run build",
            "docs": "/docs",
        })


def main():
    ap = argparse.ArgumentParser(description="Netrunner — network & Linux management tool")
    ap.add_argument("--host",   default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    ap.add_argument("--port",   default=8000, type=int, help="Bind port (default: 8000)")
    ap.add_argument("--reload", action="store_true", help="Enable auto-reload (dev mode)")
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
