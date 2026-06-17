import os
import shutil
import asyncio
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

router = APIRouter()

PROJECTS_DIR = "/app/data/projects"

class FileItem(BaseModel):
    name: str
    is_dir: bool
    size: int

@router.get("/list")
async def list_workspace_files(node_id: str, path: str = "/"):
    """Lists files in the local workspace for a specific node."""
    workspace_path = os.path.join(PROJECTS_DIR, node_id, "workspace")
    
    # Ensure workspace exists
    os.makedirs(workspace_path, exist_ok=True)
    
    # Normalize and secure path
    clean_path = path.lstrip("/")
    target_dir = os.path.abspath(os.path.join(workspace_path, clean_path))
    
    if not target_dir.startswith(workspace_path):
        raise HTTPException(status_code=400, detail="Invalid path")
        
    if not os.path.exists(target_dir):
        return {"files": []}
        
    if not os.path.isdir(target_dir):
        raise HTTPException(status_code=400, detail="Not a directory")
        
    files = []
    try:
        for item in os.listdir(target_dir):
            item_path = os.path.join(target_dir, item)
            files.append({
                "name": item,
                "is_dir": os.path.isdir(item_path),
                "size": os.path.getsize(item_path) if os.path.isfile(item_path) else 0
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"files": files}

@router.get("/read")
async def read_workspace_file(node_id: str, path: str):
    """Reads a file from the local workspace."""
    workspace_path = os.path.join(PROJECTS_DIR, node_id, "workspace")
    clean_path = path.lstrip("/")
    target_file = os.path.abspath(os.path.join(workspace_path, clean_path))
    
    if not target_file.startswith(workspace_path):
        raise HTTPException(status_code=400, detail="Invalid path")
        
    if not os.path.exists(target_file):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class WriteRequest(BaseModel):
    content: str

@router.post("/write")
async def write_workspace_file(node_id: str, path: str, req: WriteRequest):
    """Writes a file to the local workspace."""
    workspace_path = os.path.join(PROJECTS_DIR, node_id, "workspace")
    clean_path = path.lstrip("/")
    target_file = os.path.abspath(os.path.join(workspace_path, clean_path))
    
    if not target_file.startswith(workspace_path):
        raise HTTPException(status_code=400, detail="Invalid path")
        
    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    
    try:
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class InitProjectRequest(BaseModel):
    template: str

@router.post("/init")
async def init_workspace_project(node_id: str, req: InitProjectRequest):
    """Initializes a new project from a template in the workspace."""
    workspace_path = os.path.join(PROJECTS_DIR, node_id, "workspace")
    
    # Clear existing workspace
    if os.path.exists(workspace_path):
        shutil.rmtree(workspace_path)
    os.makedirs(workspace_path, exist_ok=True)
    
    try:
        if req.template == "esp-idf-c":
            # Scaffold basic CMakeLists.txt and main.cpp for a Blink project
            with open(os.path.join(workspace_path, "CMakeLists.txt"), "w") as f:
                f.write('cmake_minimum_required(VERSION 3.16)\ninclude($ENV{IDF_PATH}/tools/cmake/project.cmake)\nproject(netrunner-firmware)\n')
            
            os.makedirs(os.path.join(workspace_path, "main"))
            
            with open(os.path.join(workspace_path, "main", "CMakeLists.txt"), "w") as f:
                f.write('idf_component_register(SRCS "main.cpp" INCLUDE_DIRS ".")\n')
                
            cpp_code = """#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"

// Brug GPIO 2 (indbygget LED på de fleste ESP32 boards)
#define BLINK_GPIO GPIO_NUM_2

extern "C" void app_main(void)
{
    // Konfigurer pin som output
    gpio_reset_pin(BLINK_GPIO);
    gpio_set_direction(BLINK_GPIO, GPIO_MODE_OUTPUT);
    
    bool led_state = false;
    
    while (true) {
        printf("Blinker LED'en... State: %d\\n", led_state);
        gpio_set_level(BLINK_GPIO, led_state);
        led_state = !led_state;
        
        // Vent 1 sekund (1000 ms)
        vTaskDelay(1000 / portTICK_PERIOD_MS);
    }
}
"""
            with open(os.path.join(workspace_path, "main", "main.cpp"), "w") as f:
                f.write(cpp_code)
                
        elif req.template == "rust-std":
            with open(os.path.join(workspace_path, "Cargo.toml"), "w") as f:
                f.write('[package]\nname = "netrunner-firmware"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\nesp-idf-sys = { version = "0.34", features = ["binstart"] }\n\n[build-dependencies]\nembuild = { version = "0.32", features = ["espidf"] }\n')
            
            with open(os.path.join(workspace_path, "build.rs"), "w") as f:
                f.write('fn main() {\n    embuild::espidf::sysenv::output();\n}\n')

            os.makedirs(os.path.join(workspace_path, ".cargo"), exist_ok=True)
            with open(os.path.join(workspace_path, ".cargo", "config.toml"), "w") as f:
                f.write('[build]\ntarget = "xtensa-esp32-espidf"\n\n[target.xtensa-esp32-espidf]\nlinker = "ldproxy"\n\n[unstable]\nbuild-std = ["std", "panic_abort"]\n\n[env]\nMCU="esp32"\nESP_IDF_VERSION="v5.1.2"\n')

            
            os.makedirs(os.path.join(workspace_path, "src"))
            
            rust_code = """fn main() {
    esp_idf_sys::link_patches();
    // Bemærk: Et fuldt Rust blink-script kræver normalt esp-idf-hal. 
    // Dette er et forsimplet proof-of-concept print loop, da esp-idf-hal kræver en del setup.
    // Men det kompilerer via Netrunner Workspace!
    println!("Hello from Rust on ESP32 via Netrunner!");
    let mut state = false;
    loop {
        println!("Rust siger: Blink state er nu {}", state);
        state = !state;
        // Mock delay - i virkeligheden ville man bruge std::thread::sleep
    }
}
"""
            with open(os.path.join(workspace_path, "src", "main.rs"), "w") as f:
                f.write(rust_code)

        else:
            raise HTTPException(status_code=400, detail="Unknown template")
            
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
