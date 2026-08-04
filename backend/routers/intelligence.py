from fastapi import APIRouter, Depends, HTTPException
from ..core.knowledge_graph import kg
from ..core.db import load_nodes_db
from ..core.vault import load_credentials
from ..core.events import recent_events
from ..core.session import session_manager

router = APIRouter(tags=["intelligence"])


@router.get("/intelligence/graph")
async def get_knowledge_graph():
    # Sync the graph with current state before returning
    nodes_db = await load_nodes_db()

    # We need to format credentials from the db
    creds = {}
    for nid in nodes_db:
        username, password = await load_credentials(nid)
        if password:  # If we have a stored password, consider it compromised
            creds[nid] = (username, password)

    # Connections
    connections = {
        nid: {"connected": session_manager.get_session(nid) is not None}
        for nid in nodes_db
    }
    from ..core.db import load_threat_events_db

    events = await load_threat_events_db(limit=50)

    kg.rebuild_from_state(nodes_db, connections, creds)

    return kg.get_vis_json()


@router.post("/intelligence/query")
async def query_knowledge_graph(payload: dict):
    from ..routers.settings import load_settings
    import os
    import json
    from openai import OpenAI

    query = payload.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

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
            status_code=400,
            detail="AI API key is not set. Go to Settings -> AI Config.",
        )

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    # Ensure graph is up-to-date
    nodes_db = await load_nodes_db()
    creds = {}
    for nid in nodes_db:
        username, password = await load_credentials(nid)
        if password:
            creds[nid] = (username, password)
    connections = {
        nid: {"connected": session_manager.get_session(nid) is not None}
        for nid in nodes_db
    }
    from ..core.db import load_threat_events_db

    events = await load_threat_events_db(limit=50)
    kg.rebuild_from_state(nodes_db, connections, creds)

    # Extract Context
    context = kg.export_context_string()

    system_prompt = f"""
You are a top-tier Cyber Security Analyst.
You have access to a real-time Memory Graph that maps out a compromised network environment.
Analyze the following Network Topology Graph to answer the user's question.

{context}

Provide a human-readable cyber intelligence report based on the provided graph context.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        final_ans = response.choices[0].message.content
        return {"answer": final_ans, "nodes_referenced": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
