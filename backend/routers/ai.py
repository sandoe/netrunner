"""AI Agent API endpoints using LLM + Tool calling."""

from __future__ import annotations

import os
import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI

from .nodes import load_nodes, READ_CMDS
from .links import (
    load_links,
    discover_links,
    create_link as create_link_logic,
    LinkCreate,
)
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
    return [
        {
            "id": nid,
            "name": n.get("name"),
            "host": n.get("host"),
            "device_type": n.get("device_type"),
        }
        for nid, n in nodes.items()
    ]


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


async def deploy_agent_tool(node_id: str, agent_id: str):
    from .agents import AVAILABLE_AGENTS
    from .nodes import load_nodes, _get_node_with_creds
    import base64
    from pathlib import Path

    if agent_id not in AVAILABLE_AGENTS:
        return {
            "error": f"Unknown agent type. Valid: {', '.join(AVAILABLE_AGENTS.keys())}"
        }

    nodes = await load_nodes()
    if node_id not in nodes:
        return {"error": "Node not found"}

    script_name = AVAILABLE_AGENTS[agent_id]["script"]
    script_path = Path(__file__).parent.parent / "scripts" / script_name

    if not script_path.exists():
        return {"error": f"Agent script {script_name} not found on server"}

    with open(script_path, "r", encoding="utf-8") as f:
        script_content = f.read()

    encoded_script = base64.b64encode(script_content.encode("utf-8")).decode("utf-8")
    install_cmd = f"echo {encoded_script} | base64 -d > /tmp/{script_name}"
    start_cmd = f"nohup python3 /tmp/{script_name} > /dev/null 2>&1 &"

    try:
        node = await _get_node_with_creds(node_id, nodes)
        results, err = await session_manager.run(
            node_id, node, [install_cmd, start_cmd]
        )
        if err:
            return {"error": f"Install failed: {err}"}
        return {
            "status": "success",
            "message": f"{AVAILABLE_AGENTS[agent_id]['name']} deployed to {node_id}.",
        }
    except Exception as e:
        return {"error": str(e)}


async def generate_report_tool(report_type: str, node_id: Optional[str] = None):
    # Stub for future implementation
    if report_type not in ["pdf", "md", "latex", "word"]:
        return {"error": "Invalid report_type. Expected: pdf, md, latex, word"}
    return {
        "status": "success",
        "message": f"Generated {report_type.upper()} report"
        + (f" for node {node_id}." if node_id else "."),
        "file_path": f"/tmp/report_{report_type}.{report_type}",
    }


async def run_playbook_tool(name: str, commands: List[str], node_ids: List[str]):
    from .nodes import load_nodes, _get_node_with_creds

    nodes = await load_nodes()

    results = {}
    for node_id in node_ids:
        if node_id not in nodes:
            results[node_id] = {"error": "Node not found"}
            continue

        try:
            node = await _get_node_with_creds(node_id, nodes)
            out, err = await session_manager.run(node_id, node, commands)
            results[node_id] = {"output": out, "error": err}
        except Exception as e:
            results[node_id] = {"error": str(e)}

    return {"playbook_name": name, "results": results}


# ---------------------------------------------------------------------------
# Tool Definitions for LLM
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_nodes",
            "description": "List all network nodes and their IDs.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_topology",
            "description": "Get the current network topology (all links between nodes).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_discovery",
            "description": "Run the auto-discovery engine to find new links between nodes automatically.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_link",
            "description": "Manually create a link between two nodes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "The ID of the source node.",
                    },
                    "target_id": {
                        "type": "string",
                        "description": "The ID of the target node.",
                    },
                },
                "required": ["source_id", "target_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_node",
            "description": "Read live state (IP, routes, services, etc.) from a node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "The unique ID of the node.",
                    },
                    "read_type": {
                        "type": "string",
                        "description": "Type of data to read (e.g. 'ip', 'routes', 'services', 'cpu').",
                    },
                },
                "required": ["node_id", "read_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deploy_agent",
            "description": "Deploy a specialized agent to a target node. Valid agents: recon, tracker, scanner, sniffer, honeypot, auth_monitor, usb_monitor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "The unique ID of the node to deploy to.",
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "The ID of the agent to deploy (e.g., 'recon').",
                    },
                },
                "required": ["node_id", "agent_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": "Generate a report for the system or a specific node. Output formats include pdf, md, latex, word.",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_type": {
                        "type": "string",
                        "description": "The format of the report: pdf, md, latex, or word.",
                    },
                    "node_id": {
                        "type": "string",
                        "description": "Optional node ID to generate the report for.",
                    },
                },
                "required": ["report_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_playbook_tool",
            "description": "Execute a multi-step playbook or swarm command (a sequence of shell commands) across one or multiple target nodes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the playbook (e.g., 'scan then deploy').",
                    },
                    "commands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of shell commands to execute in sequence on the target nodes.",
                    },
                    "node_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of target node IDs to execute the playbook on.",
                    },
                },
                "required": ["name", "commands", "node_ids"],
            },
        },
    },
]

from fastapi import (
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    Request,
)
from .auth import get_current_user, authenticate_ws
from ..services.ai_guardrails import GuardrailEngine
from ..core.db import load_alerts_db
from ..core.limiter import limiter
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
    token_data = await authenticate_ws(ws, allowed_roles=("admin", "analyst"))
    if not token_data:
        return
    await ws.accept()
    from .settings import load_settings

    settings = await load_settings()

    cli_path = settings.get("ai_cli_path")
    if not cli_path:
        await ws.send_json(
            {"type": "error", "data": "AI CLI command path is not set in Settings."}
        )
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
                    asyncio.create_task(
                        ws.send_json(
                            {
                                "type": "output",
                                "data": data.decode("utf-8", errors="replace"),
                            }
                        )
                    )
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
@limiter.limit("100/minute")
async def chat(req: ChatRequest, request: Request):
    from .settings import load_settings
    from ..services.ai_guardrails import GuardrailEngine, GuardrailViolation

    # 1. Guardrail: Validate all incoming user messages
    try:
        for msg in req.messages:
            if msg.role == "user":
                await GuardrailEngine.validate_input(msg.content)
    except GuardrailViolation as e:
        raise HTTPException(status_code=400, detail=str(e))

    settings = await load_settings()
    execution_mode = settings.get("ai_execution_mode", "api")

    # -----------------------------------------------------------------------
    # CLI Execution Mode
    # -----------------------------------------------------------------------
    if execution_mode == "cli":
        cli_path = settings.get("ai_cli_path")
        if not cli_path:
            raise HTTPException(
                status_code=400, detail="AI CLI command path is not set in Settings."
            )

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
                env=env,
            )
            stdout, stderr = await proc.communicate()

            out_text = stdout.decode().strip()
            err_text = stderr.decode().strip()

            if proc.returncode != 0:
                raise Exception(
                    f"Process exited with code {proc.returncode}. Error: {err_text} | Output: {out_text}"
                )

            return {
                "role": "assistant",
                "content": out_text or err_text or "Process completed with no output.",
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"CLI execution failed: {e}")

    # -----------------------------------------------------------------------
    # API Execution Mode
    # -----------------------------------------------------------------------
    provider = (settings.get("ai_provider") or "openai").strip().lower()
    model = (
        req.model
        or settings.get("ai_model")
        or ("llama3.1" if provider == "ollama" else "gpt-4o")
    )
    api_key = (
        settings.get("ai_api_key")
        or settings.get("openai_api_key")
        or os.environ.get("OPENAI_API_KEY")
    )
    base_url = (settings.get("ai_base_url") or "").strip()

    if provider == "openai":
        base_url = ""
    elif provider == "openrouter" and not base_url:
        base_url = "https://openrouter.ai/api/v1"
    elif provider == "ollama":
        base_url = base_url or "http://127.0.0.1:11434/v1"
        api_key = api_key or "ollama"

    if not api_key:
        raise HTTPException(
            status_code=400, detail="AI API key is not set in Settings."
        )

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = AsyncOpenAI(**client_kwargs)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in req.messages],
            tools=TOOLS,
            tool_choice="auto",
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
                    result = await create_link_tool(
                        args.get("source_id"), args.get("target_id")
                    )
                elif func_name == "read_node":
                    result = await read_node_tool(
                        args.get("node_id"), args.get("read_type")
                    )
                elif func_name == "deploy_agent":
                    result = await deploy_agent_tool(
                        args.get("node_id"), args.get("agent_id")
                    )
                elif func_name == "generate_report":
                    result = await generate_report_tool(
                        args.get("report_type"), args.get("node_id")
                    )
                elif func_name == "run_playbook_tool":
                    result = await run_playbook_tool(
                        args.get("name", "Playbook"),
                        args.get("commands", []),
                        args.get("node_ids", []),
                    )
                else:
                    result = {"error": "Unknown tool"}

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": func_name,
                        "content": json.dumps(result),
                    }
                )

            final_response = await client.chat.completions.create(
                model=model, messages=messages  # type: ignore
            )
            raw_output = final_response.choices[0].message.content or ""
            safe_output = GuardrailEngine.validate_output(raw_output)
            return {"role": "assistant", "content": safe_output}

        raw_output = msg.content or ""
        safe_output = GuardrailEngine.validate_output(raw_output)
        return {"role": "assistant", "content": safe_output}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Threat Storylines
# ---------------------------------------------------------------------------


class StorylineResponse(BaseModel):
    id: str
    title: str
    summary: str
    recommended_action: str
    alert_ids: List[str]
    status: str


@router.get(
    "/ai/storylines",
    response_model=List[StorylineResponse],
    dependencies=[Depends(get_current_user)],
)
async def generate_storylines():
    from .settings import load_settings

    settings = await load_settings()

    # 1. Fetch active alerts
    alerts = await load_alerts_db(status="new")
    open_alerts = await load_alerts_db(status="open")
    active_alerts = alerts + open_alerts

    if not active_alerts:
        return []

    # 2. Setup AI client
    provider = (settings.get("ai_provider") or "openai").strip().lower()
    model = settings.get("ai_model") or (
        "llama3.1" if provider == "ollama" else "gpt-4o"
    )
    api_key = (
        settings.get("ai_api_key")
        or settings.get("openai_api_key")
        or os.environ.get("OPENAI_API_KEY")
    )
    base_url = (settings.get("ai_base_url") or "").strip()

    if provider == "openai":
        base_url = ""
    elif provider == "openrouter" and not base_url:
        base_url = "https://openrouter.ai/api/v1"
    elif provider == "ollama":
        base_url = base_url or "http://127.0.0.1:11434/v1"
        api_key = api_key or "ollama"

    if not api_key:
        raise HTTPException(
            status_code=400, detail="AI API key is not set in Settings."
        )

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = AsyncOpenAI(**client_kwargs)

    # 3. Construct prompt
    alerts_json = json.dumps(
        [
            {
                "id": a["id"],
                "title": a["title"],
                "severity": a["severity"],
                "description": a.get("description", ""),
            }
            for a in active_alerts
        ]
    )

    system_prompt = f"""You are an elite AI SOC Analyst.
You are given a list of raw security alerts in JSON format.
Your job is to analyze them, find correlations (if any), and group them into 1 or more cohesive "Attack Storylines" or "Threat Narratives".
If alerts are unrelated, you can create separate storylines for them, but try to group them if they seem like part of a larger campaign (e.g. initial access -> lateral movement).

Return a JSON array of objects, where each object has:
- "id": a unique string (e.g. "story_1")
- "title": A catchy, professional name for the attack campaign (e.g. "Suspicious Lateral Movement via SSH")
- "summary": A 2-3 sentence human-readable summary of what the attacker is doing based on the alerts.
- "recommended_action": A brief, actionable mitigation step (e.g. "Isolate Host and Block IP 192.168.1.50").
- "alert_ids": A list of the string IDs of the alerts that belong to this storyline.
- "status": "active"

ONLY RETURN VALID JSON. Do not include markdown formatting like ```json or anything else. Just the raw JSON array.

ALERTS:
{alerts_json}
"""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.2,
        )

        content = response.choices[0].message.content.strip()
        # Clean up markdown if the LLM hallucinated it
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]

        storylines = json.loads(content)
        return storylines
    except Exception as e:
        print(f"Failed to generate storylines: {e}")
        # Fallback for when AI fails or no API key is working during testing
        return [
            {
                "id": "fallback_story_1",
                "title": "Uncorrelated Alerts (AI Analysis Failed)",
                "summary": "The AI engine could not analyze the alerts due to an API error. Review the alerts manually.",
                "recommended_action": "Manually Triage",
                "alert_ids": [a["id"] for a in active_alerts],
                "status": "active",
            }
        ]


# ---------------------------------------------------------------------------
# AI Log Parsing
# ---------------------------------------------------------------------------


class ParseLogRequest(BaseModel):
    log_entry: str
    selection: str


class ParseLogResponse(BaseModel):
    pattern: str
    extracted_fields: dict
    explanation: str


@router.post(
    "/ai/parse-log",
    response_model=ParseLogResponse,
    dependencies=[Depends(get_current_user)],
)
async def parse_log_with_ai(req: ParseLogRequest):
    from .settings import load_settings

    settings = await load_settings()

    provider = (settings.get("ai_provider") or "openai").strip().lower()
    model = settings.get("ai_model") or (
        "llama3.1" if provider == "ollama" else "gpt-4o"
    )
    api_key = (
        settings.get("ai_api_key")
        or settings.get("openai_api_key")
        or os.environ.get("OPENAI_API_KEY")
    )
    base_url = (settings.get("ai_base_url") or "").strip()

    if provider == "openai":
        base_url = ""
    elif provider == "openrouter" and not base_url:
        base_url = "https://openrouter.ai/api/v1"
    elif provider == "ollama":
        base_url = base_url or "http://127.0.0.1:11434/v1"
        api_key = api_key or "ollama"

    if not api_key:
        raise HTTPException(
            status_code=400, detail="AI API key is not set in Settings."
        )

    if base_url:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    else:
        client = AsyncOpenAI(api_key=api_key)

    system_prompt = f"""You are an elite DevOps/SecOps engineer specializing in log parsing.
The user will provide a raw log entry and a specific substring they selected from it.
Your job is to generate a Regex or Grok pattern that extracts the selected data, as well as any other obvious structured fields in the log (like IPs, timestamps, log levels).

Return ONLY a valid JSON object with the following structure:
- "pattern": The generated Regex or Grok pattern.
- "extracted_fields": A key-value dictionary showing what your pattern extracts from the log (e.g. {{"ip": "192.168.1.1", "user": "admin"}}).
- "explanation": A 1-2 sentence explanation of the pattern.

Raw Log Entry: {req.log_entry}
User Selection: {req.selection}
"""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Extract the pattern."},
            ],
            temperature=0.1,
        )

        raw_output = response.choices[0].message.content or ""
        clean_output = raw_output.strip()
        safe_output = GuardrailEngine.validate_output(clean_output)

        if safe_output != clean_output:
            # Guardrail triggered
            raise Exception("Guardrail intercepted malicious output during log parsing")

        if safe_output.endswith("```"):
            safe_output = safe_output[:-3]

        return json.loads(safe_output)
    except Exception as e:
        print(f"Failed to parse log: {e}")
        return {
            "pattern": "^(?P<matched>.*)$",
            "extracted_fields": {
                "matched": req.selection,
                "error": "AI failed to generate true pattern",
            },
            "explanation": "Fallback pattern due to API failure or Guardrail block.",
        }


# ---------------------------------------------------------------------------
# Centralized Internal AI Utility
# ---------------------------------------------------------------------------


async def _ask_gemini(prompt: str) -> str:
    """
    Centralized utility for internal AI calls (like ai_triage.py).
    Wrapped with Guardrail Engine.
    """
    from .settings import load_settings
    from ..services.ai_guardrails import GuardrailEngine, GuardrailViolation

    try:
        await GuardrailEngine.validate_input(prompt)
    except GuardrailViolation as e:
        return f"Blocked by Guardrail: {e}"

    settings = await load_settings()
    provider = (settings.get("ai_provider") or "openai").strip().lower()
    model = settings.get("ai_model") or (
        "llama3.1" if provider == "ollama" else "gpt-4o"
    )
    api_key = (
        settings.get("ai_api_key")
        or settings.get("openai_api_key")
        or os.environ.get("OPENAI_API_KEY")
    )
    base_url = (settings.get("ai_base_url") or "").strip()

    if provider == "openai":
        base_url = ""
    elif provider == "openrouter" and not base_url:
        base_url = "https://openrouter.ai/api/v1"
    elif provider == "ollama":
        base_url = base_url or "http://127.0.0.1:11434/v1"
        api_key = api_key or "ollama"

    if not api_key:
        return "Error: AI API key is not set in Settings."

    if base_url:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    else:
        client = AsyncOpenAI(api_key=api_key)

    try:
        response = await client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}], temperature=0.2
        )
        content = response.choices[0].message.content
        raw_output = content.strip() if content else ""
        safe_output = GuardrailEngine.validate_output(raw_output)
        return safe_output
    except Exception as e:
        return f"Error connecting to LLM: {e}"
