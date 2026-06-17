import os
import asyncio
import subprocess
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .workspace import PROJECTS_DIR
from ..core.logger import log as logger

router = APIRouter()

@router.websocket("/build")
async def build_workspace(websocket: WebSocket, node_id: str, template: str):
    await websocket.accept()
    workspace_path = os.path.join(PROJECTS_DIR, node_id, "workspace")
    
    if not os.path.exists(workspace_path):
        await websocket.send_text("Error: Workspace not found.")
        await websocket.close()
        return

    # Use the host's absolute path since Docker is mounted from the host
    # This assumes netrunner data dir is at /home/aso/Dokumenter/github/netrunner/data
    host_data_dir = os.environ.get("HOST_DATA_DIR", "/home/aso/Dokumenter/github/netrunner/data")
    host_workspace_path = f"{host_data_dir}/projects/{node_id}/workspace"
    
    if template == "esp-idf-c":
        image = "espressif/idf:latest"
        cmd = "idf.py build && cd build && esptool.py --chip esp32 merge_bin -o merged.bin @flash_args"
    elif template == "rust-std":
        image = "espressif/idf-rust:esp32_latest"
        cmd = ". /home/esp/export-esp.sh && cargo build --release && espflash save-image --chip esp32 --merge target/xtensa-esp32-espidf/release/netrunner-firmware merged.bin"
    else:
        await websocket.send_text("Error: Unknown template.")
        await websocket.close()
        return
        
    await websocket.send_text(f"[Netrunner Builder] Starting build for {template} in {host_workspace_path}...\r\n")
    
    # Fix permissions so non-root containers (like rust) can write to the workspace
    container_workspace_path = f"/app/data/projects/{node_id}/workspace"
    chmod_proc = await asyncio.create_subprocess_exec("chmod", "-R", "777", container_workspace_path)
    await chmod_proc.wait()
    
    # Run docker container
    docker_cmd = [
        "docker", "run", "-t", "--rm",
        "-v", f"{host_workspace_path}:/project",
        "-w", "/project",
        image,
        "bash", "-c", cmd
    ]
    
    await websocket.send_text(f"[Netrunner Builder] Executing: {' '.join(docker_cmd)}\r\n")
    
    process = await asyncio.create_subprocess_exec(
        *docker_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    
    try:
        while True:
            chunk = await process.stdout.read(1024)
            if not chunk:
                break
            await websocket.send_text(chunk.decode('utf-8', errors='replace'))
            
        await process.wait()
        
        if process.returncode == 0:
            await websocket.send_text("\r\n[Netrunner Builder] Build completed successfully!\r\n")
            
            # Now we need to flash it. The flashing logic will be triggered by the frontend
            # calling the flash endpoint, or we can do it here. Let's let the frontend trigger it.
        else:
            await websocket.send_text(f"\r\n[Netrunner Builder] Build failed with exit code {process.returncode}.\r\n")
            
    except WebSocketDisconnect:
        logger.warning("WebSocket disconnected. Terminating build process.")
        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=3.0)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error during build: {e}")
        try:
            process.terminate()
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
