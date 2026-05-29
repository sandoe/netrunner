"""Netrunner — FastAPI backend entry point."""
from __future__ import annotations

import argparse
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routers import ai, configs, gns3, links, nodes, preview, terminal, settings, threats, defense, system, chaos, auth, redteam, deception, agent
from .routers.settings import load_settings
from .core.db import init_db

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
DATA_DIR = Path("data")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure directories exist
    for d in ("configs", "captures", "exports", "agents"):
        (DATA_DIR / d).mkdir(parents=True, exist_ok=True)
    
    # Initialize DB
    await init_db()

    # Load settings into env
    s = await load_settings()
    if s.get("openai_api_key"):
        os.environ["OPENAI_API_KEY"] = s["openai_api_key"]

    # Start background tasks for threats and chaos explicitly since lifespan bypasses on_event("startup")
    import asyncio
    from .routers import threats, chaos
    threats._threat_task = asyncio.create_task(threats.broadcast_threats())
    chaos._chaos_task = asyncio.create_task(chaos.chaos_loop())

    yield
    # Cleanup background tasks
    if threats._threat_task:
        threats._threat_task.cancel()
    if chaos._chaos_task:
        chaos._chaos_task.cancel()

    from .core.session import session_manager
    session_manager.close_all()


app = FastAPI(title="Netrunner", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nodes.router,    prefix="/api")
app.include_router(links.router,    prefix="/api")
app.include_router(gns3.router,     prefix="/api")
app.include_router(ai.router,       prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(configs.router,  prefix="/api")
app.include_router(preview.router,  prefix="/api")
app.include_router(defense.router,  prefix="/api")
app.include_router(threats.router)
app.include_router(system.router,   prefix="/api")
app.include_router(chaos.router,    prefix="/api")
app.include_router(redteam.router,  prefix="/api")
app.include_router(deception.router,prefix="/api")
app.include_router(auth.router,     prefix="/api")
app.include_router(agent.router,    prefix="/api/agent")
app.include_router(terminal.router)

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
