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
    model: str = "gpt-4o"

# ---------------------------------------------------------------------------
# Tool Implementations
# ---------------------------------------------------------------------------

def list_nodes_tool():
    nodes = load_nodes()
    return [{
        "id": nid,
        "name": n.get("name"),
        "host": n.get("host"),
        "device_type": n.get("device_type")
    } for nid, n in nodes.items()]

def get_topology_tool():
    links = load_links()
    return list(links.values())

async def run_discovery_tool():
    return await discover_links()

async def create_link_tool(source_id: str, target_id: str):
    try:
        res = await create_link_logic(LinkCreate(source=source_id, target=target_id))
        return res.model_dump()
    except Exception as e:
        return {"error": str(e)}

def read_node_tool(node_id: str, read_type: str):
    from .nodes import READ_CMDS
    if read_type not in READ_CMDS:
        return {"error": f"Invalid read_type. Valid: {', '.join(READ_CMDS.keys())}"}
    
    cmds = READ_CMDS[read_type]
    results = []
    try:
        session = session_manager.get_session(node_id) 
        if not session:
            nodes = load_nodes()
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

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/ai/chat")
async def chat(req: ChatRequest):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY not set in backend environment.")

    client = OpenAI(api_key=api_key)
    
    try:
        response = client.chat.completions.create(
            model=req.model,
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
                    result = list_nodes_tool()
                elif func_name == "get_topology":
                    result = get_topology_tool()
                elif func_name == "run_discovery":
                    result = await run_discovery_tool()
                elif func_name == "create_link":
                    result = await create_link_tool(args.get("source_id"), args.get("target_id"))
                elif func_name == "read_node":
                    result = read_node_tool(args.get("node_id"), args.get("read_type"))
                else:
                    result = {"error": "Unknown tool"}
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": func_name,
                    "content": json.dumps(result)
                })
            
            final_response = client.chat.completions.create(
                model=req.model,
                messages=messages
            )
            return {"role": "assistant", "content": final_response.choices[0].message.content}
        
        return {"role": "assistant", "content": msg.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
