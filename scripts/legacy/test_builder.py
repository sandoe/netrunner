import asyncio
import os

async def test():
    host_workspace_path = "/home/aso/Dokumenter/github/netrunner/data/projects/n1780913184722/workspace"
    image = "espressif/idf-rust:esp32_latest"
    cmd = "cargo build --release && espflash save-image --chip esp32 target/xtensa-esp32-none-elf/release/netrunner-firmware merged.bin"
    docker_cmd = [
        "docker", "run", "-t", "--rm",
        "-v", f"{host_workspace_path}:/project",
        "-w", "/project",
        image,
        "bash", "-c", cmd
    ]
    process = await asyncio.create_subprocess_exec(
        *docker_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    while True:
        chunk = await process.stdout.read(1024)
        if not chunk:
            break
        print(f"CHUNK: {chunk}")
    await process.wait()
    print(f"EXIT CODE: {process.returncode}")

asyncio.run(test())
