from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from typing import Optional
import base64
import os
import json
from .auth import get_current_user
from ..core.db import load_nodes_db
from ..core.session import session_manager

router = APIRouter()
public_router = APIRouter()

from contextlib import asynccontextmanager
import asyncio


@asynccontextmanager
async def yield_port(node_id: str, port: str):
    from ..core.db import load_nodes_db
    from ..core.session import session_manager

    nodes = await load_nodes_db()
    interrupt_cmd = f"pkill -9 -f 'mpremote.*{port}' || true"
    await session_manager.run(node_id, nodes[node_id], [interrupt_cmd])

    from .usb import set_proxy_pause_state

    try:
        await set_proxy_pause_state(node_id, port, True)
        await asyncio.sleep(0.3)
    except Exception:
        pass
    try:
        yield
    finally:
        try:
            await set_proxy_pause_state(node_id, port, False)
        except Exception:
            pass


async def ensure_mcu_cli(node_id: str, node: dict):
    await session_manager.run(node_id, node, ["mkdir -p /tmp/nr_scripts"])
    await session_manager.upload_file(
        node_id,
        node,
        "/app/backend/scripts/mpremote_api.py",
        "/tmp/nr_scripts/mpremote_api.py",
    )
    await session_manager.upload_file(
        node_id,
        node,
        "/app/backend/scripts/nr_mcu_cli.py",
        "/tmp/nr_scripts/nr_mcu_cli.py",
    )


@router.get("/{node_id}/files")
async def list_mcu_files(
    node_id: str,
    port: str,
    path: str = ".",
    sudo_password: str = "",
    user=Depends(get_current_user),
):
    nodes = await load_nodes_db()
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    from ..core.vault import load_credentials

    un, pw = await load_credentials(node_id)
    nodes[node_id]["username"] = un
    nodes[node_id]["password"] = pw

    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    async with yield_port(node_id, port):
        await ensure_mcu_cli(node_id, nodes[node_id])
        if sudo_password:
            await session_manager.run(
                node_id,
                nodes[node_id],
                [f"echo '{sudo_password}' | sudo -S chmod 666 {port}"],
            )
        cmd = f"timeout 15 python3 /tmp/nr_scripts/nr_mcu_cli.py {port} ls {path}"
        results, err = await session_manager.run(node_id, nodes[node_id], [cmd])
    if err:
        raise HTTPException(status_code=500, detail=str(err))

    try:
        output = results[0].get("output", "")
        lines = output.splitlines()
        try:
            json_line = next(
                line
                for line in reversed(lines)
                if line.startswith("[") or line.startswith("{")
            )
            parsed = json.loads(json_line)
        except (StopIteration, json.JSONDecodeError):
            raise HTTPException(
                status_code=500, detail=f"Failed to parse ls output. Raw: {output}"
            )

        if isinstance(parsed, dict) and "error" in parsed:
            raise HTTPException(status_code=500, detail=parsed["error"])

        files = [
            {"name": e["name"], "is_dir": e["is_dir"], "size": e["size"]}
            for e in parsed
        ]
        return {"files": files}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/{node_id}/read")
async def read_mcu_file(
    node_id: str,
    port: str,
    path: str,
    sudo_password: str = "",
    user=Depends(get_current_user),
):
    nodes = await load_nodes_db()
    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    async with yield_port(node_id, port):
        await ensure_mcu_cli(node_id, nodes[node_id])
        if sudo_password:
            await session_manager.run(
                node_id,
                nodes[node_id],
                [f"echo '{sudo_password}' | sudo -S chmod 666 {port}"],
            )
        cmd = f"timeout 15 python3 /tmp/nr_scripts/nr_mcu_cli.py {port} read {path}"
        results, err = await session_manager.run(node_id, nodes[node_id], [cmd])
    if err:
        raise HTTPException(status_code=500, detail=str(err))

    out = results[0].get("output", "")
    return {"content": out}


class McuWritePayload(BaseModel):
    port: str
    path: str
    content: str
    sudo_password: Optional[str] = None


@router.post("/{node_id}/write")
async def write_mcu_file(
    node_id: str, payload: McuWritePayload, user=Depends(get_current_user)
):
    nodes = await load_nodes_db()
    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    interrupt_cmd = f"pkill -9 -f 'mpremote.*{payload.port}' || true"
    await session_manager.run(node_id, nodes[node_id], [interrupt_cmd])
    await ensure_mcu_cli(node_id, nodes[node_id])
    if payload.sudo_password:
        await session_manager.run(
            node_id,
            nodes[node_id],
            [f"echo '{payload.sudo_password}' | sudo -S chmod 666 {payload.port}"],
        )

    import tempfile

    try:
        with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as f:
            f.write(payload.content)
            temp_path = f.name

        success, upload_err = await session_manager.upload_file(
            node_id, nodes[node_id], temp_path, "/tmp/nr_upload.tmp"
        )
        if not success:
            raise HTTPException(
                status_code=500, detail=f"File upload failed: {upload_err}"
            )

        cmds = [
            f"timeout 15 python3 /tmp/nr_scripts/nr_mcu_cli.py {payload.port} write {payload.path} /tmp/nr_upload.tmp"
        ]
        results, err = await session_manager.run(node_id, nodes[node_id], cmds)
        if err:
            raise HTTPException(status_code=500, detail=str(err))
    finally:
        if "temp_path" in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

    return {"status": "ok"}


@router.post("/{node_id}/upload_lib")
async def upload_lib(
    node_id: str,
    port: str = Form(...),
    path: str = Form("/"),
    sudo_password: str = Form(""),
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    nodes = await load_nodes_db()
    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    interrupt_cmd = f"pkill -9 -f 'mpremote.*{port}' || true"
    await session_manager.run(node_id, nodes[node_id], [interrupt_cmd])
    await ensure_mcu_cli(node_id, nodes[node_id])
    if sudo_password:
        await session_manager.run(
            node_id,
            nodes[node_id],
            [f"echo '{sudo_password}' | sudo -S chmod 666 {port}"],
        )

    import tempfile
    import os

    try:
        # Save ZIP locally
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as f:
            f.write(await file.read())
            local_zip = f.name

        # Upload ZIP to node
        remote_zip = "/tmp/nr_upload.zip"
        remote_extract = "/tmp/nr_upload_extract"

        success, upload_err = await session_manager.upload_file(
            node_id, nodes[node_id], local_zip, remote_zip
        )
        if not success:
            raise HTTPException(
                status_code=500, detail=f"ZIP upload failed: {upload_err}"
            )

        cmds = [
            f"rm -rf {remote_extract} && mkdir -p {remote_extract}",
            f"python3 -m zipfile -e {remote_zip} {remote_extract}",
            # Use nr_mcu_cli.py to put the contents
            f"timeout 60 python3 /tmp/nr_scripts/nr_mcu_cli.py {port} put {remote_extract} {path}",
        ]
        results, err = await session_manager.run(node_id, nodes[node_id], cmds)
        if err:
            raise HTTPException(status_code=500, detail=str(err))

    finally:
        if "local_zip" in locals() and os.path.exists(local_zip):
            os.remove(local_zip)

    return {"status": "ok"}


class RunScriptPayload(BaseModel):
    port: str
    language: str
    code: str
    sudo_password: Optional[str] = None


@router.post("/{node_id}/run_script")
async def run_script(
    node_id: str, payload: RunScriptPayload, user=Depends(get_current_user)
):
    nodes = await load_nodes_db()
    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    import tempfile
    import os

    try:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(payload.code.encode("utf-8"))
            temp_path = f.name

        if payload.language == "micropython":
            remote_path = "/tmp/nr_script.py"
        elif payload.language == "arduino":
            remote_path = "/tmp/nr_arduino_sketch.ino"
        elif payload.language == "rust":
            remote_path = "/tmp/nr_main.rs"
        else:
            raise HTTPException(status_code=400, detail="Unsupported language")

        success, upload_err = await session_manager.upload_file(
            node_id, nodes[node_id], temp_path, remote_path
        )
        if not success:
            raise HTTPException(
                status_code=500, detail=f"File upload failed: {upload_err}"
            )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    cmds = []

    if payload.language == "micropython":
        interrupt_cmd = f"pkill -9 -f 'mpremote.*{payload.port}' || true"
        cmds.append(interrupt_cmd)
        await ensure_mcu_cli(node_id, nodes[node_id])
        if payload.sudo_password:
            cmds.append(
                f"echo '{payload.sudo_password}' | sudo -S chmod 666 {payload.port}"
            )
        cmds.append(
            f"timeout 15 python3 /tmp/nr_scripts/nr_mcu_cli.py {payload.port} run {remote_path}"
        )
    elif payload.language == "arduino":
        cmds.append("mkdir -p /tmp/nr_arduino_sketch")
        cmds.append(f"mv {remote_path} /tmp/nr_arduino_sketch/nr_arduino_sketch.ino")
        cmds.append(
            f"arduino-cli compile --fqbn arduino:avr:uno /tmp/nr_arduino_sketch"
        )
        cmds.append(
            f"arduino-cli upload -p {payload.port} --fqbn arduino:avr:uno /tmp/nr_arduino_sketch"
        )
    elif payload.language == "rust":
        cmds.append("mkdir -p /tmp/nr_rust_proj/src")
        cmds.append("cd /tmp/nr_rust_proj && [ -f Cargo.toml ] || cargo init --bin")
        cmds.append(f"mv {remote_path} /tmp/nr_rust_proj/src/main.rs")
        cmds.append(f"cd /tmp/nr_rust_proj && cargo build --release")
        cmds.append(
            f"cd /tmp/nr_rust_proj && espflash flash --port {payload.port} target/release/nr_rust_proj"
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported language")

    results, err = await session_manager.run(node_id, nodes[node_id], cmds)
    if err:
        raise HTTPException(status_code=500, detail=str(err))

    out = "\n".join([r.get("output", "") for r in results])
    return {"status": "ok", "output": out}


class PortPayload(BaseModel):
    port: str
    sudo_password: Optional[str] = None


@router.post("/{node_id}/stop")
async def stop_mcu(node_id: str, payload: PortPayload, user=Depends(get_current_user)):
    nodes = await load_nodes_db()
    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")
    await ensure_mcu_cli(node_id, nodes[node_id])
    if payload.sudo_password:
        await session_manager.run(
            node_id,
            nodes[node_id],
            [f"echo '{payload.sudo_password}' | sudo -S chmod 666 {payload.port}"],
        )
    # Ingen pkill her: stop sender bare Ctrl-C over seriel og må ikke dræbe en åben REPL-session
    cmd = f"timeout 15 python3 /tmp/nr_scripts/nr_mcu_cli.py {payload.port} stop"
    await session_manager.run(node_id, nodes[node_id], [cmd])
    return {"status": "ok"}


@router.post("/{node_id}/reset")
async def reset_mcu(node_id: str, payload: PortPayload, user=Depends(get_current_user)):
    nodes = await load_nodes_db()
    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    # Try sending SIGUSR1 to the active process holding the port (py_proxy)
    # Use sudo if sudo_password is provided so we can see root processes
    sudo_prefix = (
        f"echo '{payload.sudo_password}' | sudo -S " if payload.sudo_password else ""
    )
    proxy_cmd = f"{sudo_prefix}lsof -t {payload.port} 2>/dev/null"
    results, err = await session_manager.run(node_id, nodes[node_id], [proxy_cmd])
    if results and results[0].get("output", "").strip():
        pids = results[0].get("output", "").strip().split()
        for pid in pids:
            # Check if it's our python proxy
            check_cmd = f"{sudo_prefix}cat /proc/{pid}/cmdline 2>/dev/null | tr '\\0' ' ' | grep -q python3 && echo 'yes' || echo 'no'"
            res, _ = await session_manager.run(node_id, nodes[node_id], [check_cmd])
            if res and "yes" in res[0].get("output", ""):
                await session_manager.run(
                    node_id, nodes[node_id], [f"{sudo_prefix}kill -USR1 {pid}"]
                )
                return {
                    "status": "ok",
                    "message": "Sent SIGUSR1 to active serial monitor",
                }

    await ensure_mcu_cli(node_id, nodes[node_id])
    if payload.sudo_password:
        await session_manager.run(
            node_id,
            nodes[node_id],
            [f"echo '{payload.sudo_password}' | sudo -S chmod 666 {payload.port}"],
        )
    # Ingen pkill her: reset sender Ctrl-C + Ctrl-D (soft reset) og må ikke dræbe en åben REPL-session
    cmd = f"timeout 15 python3 /tmp/nr_scripts/nr_mcu_cli.py {payload.port} reset"
    await session_manager.run(node_id, nodes[node_id], [cmd])
    return {"status": "ok"}


@router.delete("/{node_id}/delete")
async def delete_mcu_file(
    node_id: str,
    port: str,
    path: str,
    sudo_password: str = "",
    user=Depends(get_current_user),
):
    nodes = await load_nodes_db()
    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    interrupt_cmd = f"pkill -9 -f 'mpremote.*{port}' || true"
    await session_manager.run(node_id, nodes[node_id], [interrupt_cmd])
    await ensure_mcu_cli(node_id, nodes[node_id])
    if sudo_password:
        await session_manager.run(
            node_id,
            nodes[node_id],
            [f"echo '{sudo_password}' | sudo -S chmod 666 {port}"],
        )

    cmd = f"timeout 15 python3 /tmp/nr_scripts/nr_mcu_cli.py {port} rm {path}"

    results, err = await session_manager.run(node_id, nodes[node_id], [cmd])
    if err:
        raise HTTPException(status_code=500, detail=str(err))
    return {"status": "ok"}


class McuMkdirPayload(BaseModel):
    port: str
    path: str
    sudo_password: Optional[str] = None


@router.post("/{node_id}/mkdir")
async def mkdir_mcu(
    node_id: str, payload: McuMkdirPayload, user=Depends(get_current_user)
):
    nodes = await load_nodes_db()
    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    interrupt_cmd = f"pkill -9 -f 'mpremote.*{payload.port}' || true"
    await session_manager.run(node_id, nodes[node_id], [interrupt_cmd])
    await ensure_mcu_cli(node_id, nodes[node_id])
    if payload.sudo_password:
        await session_manager.run(
            node_id,
            nodes[node_id],
            [f"echo '{payload.sudo_password}' | sudo -S chmod 666 {payload.port}"],
        )

    cmd = f"timeout 15 python3 /tmp/nr_scripts/nr_mcu_cli.py {payload.port} mkdir {payload.path}"
    results, err = await session_manager.run(node_id, nodes[node_id], [cmd])
    if err:
        raise HTTPException(status_code=500, detail=str(err))
    return {"status": "ok"}


class OtaPayload(BaseModel):
    content: str


@router.post("/{node_id}/ota")
async def setup_ota(node_id: str, payload: OtaPayload, user=Depends(get_current_user)):
    nodes = await load_nodes_db()
    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    import tempfile

    try:
        with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as f:
            f.write(payload.content)
            temp_path = f.name

        success, upload_err = await session_manager.upload_file(
            node_id, nodes[node_id], temp_path, "/tmp/ota_firmware.py"
        )
        if not success:
            raise HTTPException(
                status_code=500, detail=f"OTA setup failed: {upload_err}"
            )
    finally:
        if "temp_path" in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

    return {"status": "ok"}


from fastapi.responses import PlainTextResponse


@public_router.get("/{node_id}/ota", response_class=PlainTextResponse)
async def get_ota(node_id: str):
    nodes = await load_nodes_db()
    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    results, err = await session_manager.run(
        node_id, nodes[node_id], ["cat /tmp/ota_firmware.py || echo ''"]
    )
    if err:
        raise HTTPException(status_code=500, detail=str(err))

    out = results[0].get("output", "")
    return out


class InstallToolsPayload(BaseModel):
    tools: list[str] = ["mpremote", "esptool", "pyserial"]
    sudo_password: Optional[str] = None


@router.post("/{node_id}/install_tools")
async def install_mcu_tools(
    node_id: str, payload: InstallToolsPayload, user=Depends(get_current_user)
):
    nodes = await load_nodes_db()
    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    python_tools = [t for t in payload.tools if t not in ["espflash", "probe-rs"]]
    rust_tools = [t for t in payload.tools if t in ["espflash", "probe-rs"]]

    cmds = []
    if python_tools:
        tools_str = " ".join(python_tools)
        cmds.append(
            f"pip3 install --user --break-system-packages {tools_str} || pip install --user --break-system-packages {tools_str} || pip install {tools_str}"
        )

    if "espflash" in rust_tools:
        cmds.append("cargo install espflash")
    if "probe-rs" in rust_tools:
        cmds.append(
            "curl --proto '=https' --tlsv1.2 -LsSf https://github.com/probe-rs/probe-rs/releases/latest/download/probe-rs-tools-installer.sh | sh"
        )

    if not cmds:
        return {"status": "ok", "output": "No tools specified"}

    results, err = await session_manager.run(node_id, nodes[node_id], cmds)
    if err:
        raise HTTPException(status_code=500, detail=str(err))

    out = "\n".join([r.get("output", "") for r in results])
    return {"status": "ok", "output": out}


class FlashFirmwarePayload(BaseModel):
    port: str
    tool: str  # "esptool", "avrdude", "espflash", "probe-rs"
    chip: Optional[str] = "esp32"
    baud: Optional[int] = 460800
    offset: Optional[str] = "0x10000"
    file_b64: str  # base64 encoded firmware file
    sudo_password: Optional[str] = None


@router.post("/{node_id}/flash")
async def flash_firmware(
    node_id: str, payload: FlashFirmwarePayload, user=Depends(get_current_user)
):
    nodes = await load_nodes_db()
    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    import tempfile
    import os

    try:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(base64.b64decode(payload.file_b64))
            temp_path = f.name

        success, upload_err = await session_manager.upload_file(
            node_id, nodes[node_id], temp_path, "/tmp/firmware_upload.bin"
        )
        if not success:
            raise HTTPException(
                status_code=500, detail=f"Firmware upload failed: {upload_err}"
            )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # Determine flash command
    if payload.tool == "esptool":
        cmd2 = f"python3 -m esptool --port {payload.port} --baud {payload.baud} write-flash -z {payload.offset} /tmp/firmware_upload.bin"
    elif payload.tool == "avrdude":
        cmd2 = f"avrdude -c arduino -p m328p -P {payload.port} -b {payload.baud} -U flash:w:/tmp/firmware_upload.bin"
    elif payload.tool == "espflash":
        cmd2 = f"espflash flash --port {payload.port} --baud {payload.baud} /tmp/firmware_upload.bin"
    elif payload.tool == "probe-rs":
        cmd2 = f"probe-rs download --chip {payload.chip} --format bin /tmp/firmware_upload.bin"
    else:
        raise HTTPException(status_code=400, detail="Unsupported flash tool")

    if payload.sudo_password:
        sudo_cmd = f"echo '{payload.sudo_password}' | sudo -S chmod 666 {payload.port}"
    else:
        sudo_cmd = f"sudo chmod 666 {payload.port}"

    results, err = await session_manager.run(node_id, nodes[node_id], [sudo_cmd, cmd2])
    if err:
        raise HTTPException(status_code=500, detail=str(err))

    full_output = "\n".join(
        [
            r.get("output", "")
            + (("\nError: " + r.get("error")) if r.get("error") else "")
            for r in results
        ]
    )
    for r in results:
        if (
            r.get("error")
            or "error" in r.get("output", "").lower()
            or "not found" in r.get("output", "").lower()
        ):
            raise HTTPException(status_code=500, detail="Flash failed:\n" + full_output)

    return {"status": "ok", "output": full_output}


class FlashWorkspacePayload(BaseModel):
    port: str
    template: str
    baud: Optional[int] = 460800
    sudo_password: Optional[str] = None


@router.post("/{node_id}/flash_workspace")
async def flash_workspace(
    node_id: str, payload: FlashWorkspacePayload, user=Depends(get_current_user)
):
    nodes = await load_nodes_db()
    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    from .workspace import PROJECTS_DIR
    import os

    workspace_path = os.path.join(PROJECTS_DIR, node_id, "workspace")
    if payload.template == "esp-idf-c":
        bin_path = os.path.join(workspace_path, "build", "merged.bin")
        offset = "0x0"
    elif payload.template == "rust-std":
        bin_path = os.path.join(workspace_path, "merged.bin")
        offset = "0x0"
    else:
        raise HTTPException(status_code=400, detail="Unknown template")

    if not os.path.exists(bin_path):
        raise HTTPException(
            status_code=404,
            detail=f"Compiled firmware not found at {bin_path}. Did the build succeed?",
        )

    remote_bin = "/tmp/nr_workspace_fw.bin"
    success, upload_err = await session_manager.upload_file(
        node_id, nodes[node_id], bin_path, remote_bin
    )
    if not success:
        raise HTTPException(
            status_code=500, detail=f"Firmware upload failed: {upload_err}"
        )

    if payload.sudo_password:
        sudo_cmd = f"echo '{payload.sudo_password}' | sudo -S chmod 666 {payload.port}"
    else:
        sudo_cmd = f"sudo chmod 666 {payload.port}"

    cmds = [
        sudo_cmd,
        f"python3 -m esptool --port {payload.port} --baud {payload.baud} write-flash -z {offset} {remote_bin}",
        f"rm {remote_bin}",
    ]

    results, err = await session_manager.run(node_id, nodes[node_id], cmds)
    if err:
        raise HTTPException(status_code=500, detail=str(err))

    full_output = "\n".join(
        [
            r.get("output", "")
            + (("\nError: " + r.get("error")) if r.get("error") else "")
            for r in results
        ]
    )
    for r in results:
        if (
            r.get("error")
            or "error" in r.get("output", "").lower()
            or "not found" in r.get("output", "").lower()
        ):
            raise HTTPException(status_code=500, detail="Flash failed:\n" + full_output)

    return {"status": "ok", "output": full_output}


class FlashAutoPayload(BaseModel):
    port: str
    tool: str
    url: str
    baud: Optional[int] = 460800
    offset: Optional[str] = "0x10000"
    sudo_password: Optional[str] = None


@router.post("/{node_id}/flash_auto")
async def flash_auto(
    node_id: str, payload: FlashAutoPayload, user=Depends(get_current_user)
):
    nodes = await load_nodes_db()
    if not session_manager.is_connected(node_id):
        raise HTTPException(status_code=503, detail="SSH is disconnected")

    if not payload.url.strip():
        raise HTTPException(status_code=400, detail="Firmware URL cannot be empty.")

    if payload.sudo_password:
        sudo_cmd = f"echo '{payload.sudo_password}' | sudo -S chmod 666 {payload.port}"
    else:
        sudo_cmd = f"sudo chmod 666 {payload.port}"

    cmds = [
        sudo_cmd,
        f"wget -qO /tmp/fw_auto.bin {payload.url} 2>&1 || wget -O /tmp/fw_auto.bin {payload.url}",
        f"python3 -m esptool --port {payload.port} --baud {payload.baud} erase-flash",
        f"python3 -m esptool --port {payload.port} --baud {payload.baud} write-flash -z {payload.offset} /tmp/fw_auto.bin",
        "rm /tmp/fw_auto.bin",
    ]

    results, err = await session_manager.run(node_id, nodes[node_id], cmds)
    if err:
        raise HTTPException(status_code=500, detail=str(err))

    out = "\n".join([r.get("output", "") for r in results])
    return {"status": "ok", "output": out}
