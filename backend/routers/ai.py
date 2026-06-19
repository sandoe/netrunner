"""AI Agent API endpoints using LLM + Tool calling."""
from __future__ import annotations

import os
import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI

from .nodes import load_nodes, READ_CMDS
from .links import load_links, discover_links, create_link as create_link_logic, LinkCreate
from ..core.session import session_manager

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None

# ---------------------------------------------------------------------------
# Tool Implementations
# ---------------------------------------------------------------------------

async def list_nodes_tool():
    nodes = await load_nodes()
    return [{
        "id": nid,
        "name": n.get("name"),
        "host": n.get("host"),
        "device_type": n.get("device_type")
    } for nid, n in nodes.items()]

async def get_topology_tool():
    links = await load_links()
    return list(links.values())

async def run_discovery_tool():
    return await discover_links()

async def create_link_tool(source_id: str, target_id: str):
    try:
        res = await create_link_logic(LinkCreate(source=source_id, target=target_id))
        return res.model_dump()
    except Exception as e:
        return {"error": str(e)}

async def read_node_tool(node_id: str, read_type: str):
    from .nodes import READ_CMDS
    if read_type not in READ_CMDS:
        return {"error": f"Invalid read_type. Valid: {', '.join(READ_CMDS.keys())}"}
    
    cmds = READ_CMDS[read_type]
    results = []
    try:
        session = session_manager.get_session(node_id) 
        if not session:
            nodes = await load_nodes()
            if node_id not in nodes:
                return {"error": "Node not found"}
            return {"error": "Node not connected. Please connect via UI first."}

        for cmd in cmds:
            out, err = session.execute(cmd)
            results.append({"command": cmd, "output": out, "error": err})
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------------------------------------
# Tool Definitions for LLM
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_nodes",
            "description": "List all network nodes and their IDs.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_topology",
            "description": "Get the current network topology (all links between nodes).",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_discovery",
            "description": "Run the auto-discovery engine to find new links between nodes automatically.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_link",
            "description": "Manually create a link between two nodes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string", "description": "The ID of the source node."},
                    "target_id": {"type": "string", "description": "The ID of the target node."}
                },
                "required": ["source_id", "target_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_node",
            "description": "Read live state (IP, routes, services, etc.) from a node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "The unique ID of the node."},
                    "read_type": {"type": "string", "description": "Type of data to read (e.g. 'ip', 'routes', 'services', 'cpu')."}
                },
                "required": ["node_id", "read_type"]
            }
        }
    }
]

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from .auth import get_current_user, authenticate_ws
import pty
import os
import fcntl
import termios
import struct
import shlex

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.websocket("/ai/ws")
async def ai_ws(ws: WebSocket):
    token_data = await authenticate_ws(ws)
    if not token_data:
        return
    await ws.accept()
    from .settings import load_settings
    settings = await load_settings()

    cli_path = settings.get("ai_cli_path")
    if not cli_path:
        await ws.send_json({"type": "error", "data": "AI CLI command path is not set in Settings."})
        await ws.close()
        return

    cli_type = settings.get("ai_cli_type", "opencode")
    
    env = os.environ.copy()
    api_key = settings.get("ai_api_key")
    if api_key:
        env["OPENAI_API_KEY"] = api_key
        env["ANTHROPIC_API_KEY"] = api_key
        env["GOOGLE_GENERATIVE_AI_API_KEY"] = api_key
        env["GEMINI_API_KEY"] = api_key
        env["NVIDIA_API_KEY"] = api_key
        
    base_url = settings.get("ai_base_url")
    if base_url:
        env["OPENAI_BASE_URL"] = base_url
        
    model = settings.get("ai_model")
    if model:
        env["LLM_MODEL"] = model
        env["OPENAI_MODEL_NAME"] = model
        
    # Construct command
    # For opencode, we can pass the workspace directory
    if cli_type == "opencode":
        cmd_str = f"{cli_path} /host/home/aso/Dokumenter/github/netrunner"
    else:
        cmd_str = cli_path

    pid, fd = pty.fork()
    if pid == 0:
        # Child process
        os.execvpe("sh", ["sh", "-c", cmd_str], env)
    
    # Parent process
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        
        def pty_data_available():
            try:
                data = os.read(fd, 4096)
                if data:
                    asyncio.create_task(ws.send_json({
                        "type": "output", 
                        "data": data.decode('utf-8', errors='replace')
                    }))
            except Exception:
                pass
                
        loop.add_reader(fd, pty_data_available)
        
        await ws.send_json({"type": "status", "connected": True})
        
        while True:
            msg = await ws.receive_json()
            if msg.get("type") == "input":
                os.write(fd, msg["data"].encode("utf-8"))
            elif msg.get("type") == "resize":
                cols, rows = msg.get("cols", 80), msg.get("rows", 24)
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
                
    except WebSocketDisconnect:
        pass
    finally:
        try:
            loop.remove_reader(fd)
            os.close(fd)
        except Exception:
            pass
            
        import signal
        try:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        except Exception:
            pass

@router.post("/ai/chat", dependencies=[Depends(get_current_user)])
async def chat(req: ChatRequest):
    from .settings import load_settings

    settings = await load_settings()
    execution_mode = settings.get("ai_execution_mode", "api")

    # -----------------------------------------------------------------------
    # CLI Execution Mode
    # -----------------------------------------------------------------------
    if execution_mode == "cli":
        cli_path = settings.get("ai_cli_path")
        if not cli_path:
            raise HTTPException(status_code=400, detail="AI CLI command path is not set in Settings.")
        
        last_msg = req.messages[-1].content if req.messages else ""
        import asyncio
        import shlex
        
        safe_msg = shlex.quote(last_msg)
        cli_type = settings.get("ai_cli_type", "antigravity")
        model = settings.get("ai_model", "")
        
        if cli_type == "opencode":
            cmd = f"{cli_path} run {safe_msg}"
            if model:
                cmd += f" -m {shlex.quote(model)}"
        elif cli_type == "claude":
            cmd = f"{cli_path} -p {safe_msg}"
        else:
            cmd = f"{cli_path} {safe_msg}"
        
        env = os.environ.copy()
        api_key = settings.get("ai_api_key")
        
        if api_key:
            # Inject the key into all standard provider variables
            # so the CLI can use it regardless of which model string it receives
            env["OPENAI_API_KEY"] = api_key
            env["ANTHROPIC_API_KEY"] = api_key
            env["GOOGLE_GENERATIVE_AI_API_KEY"] = api_key
            env["GEMINI_API_KEY"] = api_key
            env["NVIDIA_API_KEY"] = api_key
            
        base_url = settings.get("ai_base_url")
        if base_url:
            env["OPENAI_BASE_URL"] = base_url
            
        model = settings.get("ai_model")
        if model:
            env["LLM_MODEL"] = model
            env["OPENAI_MODEL_NAME"] = model
            
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, stderr = await proc.communicate()
            
            out_text = stdout.decode().strip()
            err_text = stderr.decode().strip()
            
            if proc.returncode != 0:
                raise Exception(f"Process exited with code {proc.returncode}. Error: {err_text} | Output: {out_text}")
                
            return {"role": "assistant", "content": out_text or err_text or "Process completed with no output."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"CLI execution failed: {e}")

    # -----------------------------------------------------------------------
    # API Execution Mode
    # -----------------------------------------------------------------------
    provider = (settings.get("ai_provider") or "openai").strip().lower()
    model = req.model or settings.get("ai_model") or ("llama3.1" if provider == "ollama" else "gpt-4o")
    api_key = settings.get("ai_api_key") or settings.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
    base_url = (settings.get("ai_base_url") or "").strip()

    if provider == "openai":
        base_url = ""
    elif provider == "openrouter" and not base_url:
        base_url = "https://openrouter.ai/api/v1"
    elif provider == "ollama":
        base_url = base_url or "http://127.0.0.1:11434/v1"
        api_key = api_key or "ollama"

    if not api_key:
        raise HTTPException(status_code=400, detail="AI API key is not set in Settings.")

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in req.messages],
            tools=TOOLS,
            tool_choice="auto"
        )
        
        msg = response.choices[0].message
        
        if msg.tool_calls:
            messages = [{"role": m.role, "content": m.content} for m in req.messages]
            messages.append(msg)
            
            for tc in msg.tool_calls:
                func_name = tc.function.name
                args = json.loads(tc.function.arguments)
                
                if func_name == "list_nodes":
                    result = await list_nodes_tool()
                elif func_name == "get_topology":
                    result = await get_topology_tool()
                elif func_name == "run_discovery":
                    result = await run_discovery_tool()
                elif func_name == "create_link":
                    result = await create_link_tool(args.get("source_id"), args.get("target_id"))
                elif func_name == "read_node":
                    result = await read_node_tool(args.get("node_id"), args.get("read_type"))
                else:
                    result = {"error": "Unknown tool"}
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": func_name,
                    "content": json.dumps(result)
                })
            
            final_response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            return {"role": "assistant", "content": final_response.choices[0].message.content}
        
        return {"role": "assistant", "content": msg.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
