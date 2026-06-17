"""Saved shell script configs API."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

CONFIGS_DIR = Path("data") / "configs"


def _ensure_dir():
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/configs")
def api_configs_list():
    _ensure_dir()
    out = []
    for f in sorted(CONFIGS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.is_file():
            out.append({
                "name": f.name,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return out


class ConfigSave(BaseModel):
    name: str = ""
    type: str = "misc"
    content: str = ""


@router.post("/configs", status_code=201)
def api_configs_save(body: ConfigSave):
    _ensure_dir()
    import time
    name  = re.sub(r"[^a-zA-Z0-9_\-]", "_", body.name or f"config_{int(time.time())}")
    fname = f"{name}_{body.type}.sh"
    (CONFIGS_DIR / fname).write_text(
        f"#!/bin/sh\n# Saved: {datetime.now().isoformat()}\n# Type: {body.type}\n\n{body.content}\n"
    )
    return {"name": fname}


@router.get("/configs/{fname}")
def api_configs_get(fname: str):
    _ensure_dir()
    fname = Path(fname).name
    p = CONFIGS_DIR / fname
    if not p.exists():
        raise HTTPException(404, "Not found")
    return {"name": fname, "content": p.read_text()}


@router.delete("/configs/{fname}")
def api_configs_delete(fname: str):
    _ensure_dir()
    fname = Path(fname).name
    p = CONFIGS_DIR / fname
    if p.exists():
        p.unlink()
    return {"ok": True}
