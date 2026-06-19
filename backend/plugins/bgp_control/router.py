import asyncio
import os
import shlex
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/bgp", tags=["BGP Control"])

class RouteModel(BaseModel):
    prefix: str
    next_hop: str
    local_preference: Optional[int] = None
    med: Optional[int] = None
    as_path: Optional[str] = None
    communities: Optional[list[str]] = None

async def execute_exabgp_command(command_str: str):
    """
    Executes an ExaBGP command using an async shell.
    It expects 'exabgpcli' to be available on the path, or a custom wrapper script.
    """
    # Use exabgpcli by default to send commands to ExaBGP
    base_cmd = os.getenv("EXABGP_CMD", "exabgpcli")
    
    # We construct the full shell command safely
    safe_command = shlex.quote(command_str)
    full_cmd = f"{base_cmd} {safe_command}"
    
    process = await asyncio.create_subprocess_shell(
        full_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    return {
        "stdout": stdout.decode("utf-8").strip(),
        "stderr": stderr.decode("utf-8").strip(),
        "returncode": process.returncode,
        "command": full_cmd
    }

def build_route_string(action: str, route: RouteModel) -> str:
    """Builds the ExaBGP route command string."""
    parts = [f"{action} route {route.prefix} next-hop {route.next_hop}"]
    
    if route.local_preference is not None:
        parts.append(f"local-preference {route.local_preference}")
    if route.med is not None:
        parts.append(f"med {route.med}")
    if route.as_path is not None:
        parts.append(f"as-path {route.as_path}")
    if route.communities:
        parts.append(f"community [{', '.join(route.communities)}]")
        
    return " ".join(parts)

@router.post("/inject")
async def inject_route(route: RouteModel):
    """
    Injects a BGP route via ExaBGP.
    """
    cmd_str = build_route_string("announce", route)
    result = await execute_exabgp_command(cmd_str)
    
    if result["returncode"] != 0:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to inject route. Error: {result['stderr']}"
        )
        
    return {"status": "success", "message": f"Route {route.prefix} injected", "details": result}

@router.post("/withdraw")
async def withdraw_route(route: RouteModel):
    """
    Withdraws a BGP route via ExaBGP.
    """
    cmd_str = build_route_string("withdraw", route)
    result = await execute_exabgp_command(cmd_str)
    
    if result["returncode"] != 0:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to withdraw route. Error: {result['stderr']}"
        )
        
    return {"status": "success", "message": f"Route {route.prefix} withdrawn", "details": result}
