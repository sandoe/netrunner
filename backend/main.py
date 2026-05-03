"""Netrunner — FastAPI backend entry point."""
from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routers import configs, nodes, preview, terminal

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
DATA_DIR = Path("data")


@asynccontextmanager
async def lifespan(app: FastAPI):
    for d in ("configs", "captures", "exports"):
        (DATA_DIR / d).mkdir(parents=True, exist_ok=True)
    yield
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
app.include_router(configs.router,  prefix="/api")
app.include_router(preview.router,  prefix="/api")
app.include_router(terminal.router)

if FRONTEND_DIST.exists():
    assets = FRONTEND_DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str = ""):
        # Don't serve SPA for API or WS routes
        if full_path.startswith(("api/", "ws/")):
            from fastapi import HTTPException
            raise HTTPException(404)
        return FileResponse(FRONTEND_DIST / "index.html")
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
    args = ap.parse_args()
    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
