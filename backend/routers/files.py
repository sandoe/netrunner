"""SFTP / SSH File Explorer router."""

from __future__ import annotations

import stat
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .auth import get_current_user
from ..core.db import load_nodes_db
from ..core.vault import load_credentials

router = APIRouter()


async def _get_sftp_client(nid: str):
    nodes = await load_nodes_db()
    node = nodes.get(nid)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    transport = (node.get("transport") or "telnet").lower()
    if transport != "ssh":
        raise HTTPException(
            status_code=400, detail="File explorer requires SSH transport"
        )

    try:
        import paramiko
    except ImportError:
        raise HTTPException(status_code=500, detail="paramiko not installed")

    username, password = await load_credentials(nid)
    host = node["host"]
    port = int(node["port"])

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect with short timeout for file ops
        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=5,
            look_for_keys=False,
            allow_agent=False,
        )
        sftp = client.open_sftp()
        return client, sftp
    except paramiko.ssh_exception.AuthenticationException:
        raise HTTPException(status_code=401, detail="SSH Authentication failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSH connect failed: {e}")


@router.get("/api/nodes/{nid}/fs/list", dependencies=[Depends(get_current_user)])
async def list_directory(nid: str, path: str = Query("/", description="Path to list")):
    client, sftp = await _get_sftp_client(nid)
    try:
        entries = sftp.listdir_attr(path)
        result = []
        for attr in entries:
            is_dir = stat.S_ISDIR(attr.st_mode) if attr.st_mode else False
            result.append(
                {
                    "name": attr.filename,
                    "is_dir": is_dir,
                    "size": attr.st_size,
                    "permissions": stat.filemode(attr.st_mode) if attr.st_mode else "",
                    "mtime": attr.st_mtime,
                }
            )

        # Sort directories first, then alphabetically
        result.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"path": path, "entries": result}
    except IOError as e:
        raise HTTPException(
            status_code=403, detail=f"Permission denied or path not found: {e}"
        )
    finally:
        sftp.close()
        client.close()


@router.get("/api/nodes/{nid}/fs/read", dependencies=[Depends(get_current_user)])
async def read_file(nid: str, path: str = Query(..., description="Path to read")):
    client, sftp = await _get_sftp_client(nid)
    try:
        # Check size before reading to avoid crashing memory
        attr = sftp.stat(path)
        if attr.st_size > 5 * 1024 * 1024:  # 5 MB limit
            raise HTTPException(
                status_code=400, detail="File too large to preview (limit 5MB)"
            )

        with sftp.open(path, "r") as f:
            content = f.read().decode("utf-8", errors="replace")

        return {"path": path, "content": content}
    except IOError as e:
        raise HTTPException(
            status_code=403, detail=f"Permission denied or file not found: {e}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Read failed: {e}")
    finally:
        sftp.close()
        client.close()
