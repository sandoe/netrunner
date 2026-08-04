import asyncio
import json
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from backend.core.logger import log as logger
from backend.core.db import insert_alert
from backend.routers.settings import load_settings


class DLPCheckRequest(BaseModel):
    node_id: str
    user: str
    destination: str
    content: str
    filename: Optional[str] = None


async def _analyze_content_with_llm(req: DLPCheckRequest) -> dict:
    from openai import AsyncOpenAI

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
        # If no AI is configured, default to allow but warn
        return {"action": "allow", "reason": "No AI configured for Semantic DLP."}

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = AsyncOpenAI(**client_kwargs)

    system_prompt = f"""You are a Semantic Data Loss Prevention (DLP) AI Gateway.
You must analyze the following outgoing content transfer and determine if it violates corporate security policies.
Context:
- User: {req.user}
- Destination: {req.destination}
- Filename: {req.filename or 'N/A'}

Violations include:
1. PII or PHI (Social Security Numbers, Medical Records)
2. Corporate Secrets (Source code, Financial reports)
3. Credentials (API Keys, Passwords, Tokens)

Return a strict JSON response:
{{
    "action": "block" or "allow",
    "reason": "Brief explanation of why it was blocked or allowed."
}}
"""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Content to analyze:\n{req.content[:2000]}",
                },
            ],
        )
        content = response.choices[0].message.content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        else:
            json_str = content

        result = json.loads(json_str)
        return result
    except Exception as e:
        logger.error(f"[DLP Engine] AI Analysis failed: {e}")
        return {"action": "allow", "reason": f"AI failure fallback. Error: {str(e)}"}


async def process_dlp_event(req: DLPCheckRequest):
    """Process an outgoing data transfer through the Semantic DLP engine."""
    logger.info(f"[DLP Engine] Analyzing transfer from {req.user} to {req.destination}")

    analysis = await _analyze_content_with_llm(req)

    if analysis.get("action") == "block":
        import time
        import str4uuid  # Not existing, just use uuid
        import uuid

        alert_id = f"alert_dlp_{int(time.time())}"
        await insert_alert(
            {
                "id": alert_id,
                "title": f"[SEMANTIC DLP BLOCK] Data Exfiltration Attempt by {req.user}",
                "description": f"The Layered AI Gateway intercepted and blocked a data transfer to {req.destination}.\n\nFilename: {req.filename}\n\n🤖 [LLM Evaluator]: {analysis.get('reason')}",
                "severity": "critical",
                "status": "new",
                "created_at": time.time(),
                "updated_at": time.time(),
            }
        )
        return {"status": "blocked", "reason": analysis.get("reason")}

    return {"status": "allowed", "reason": analysis.get("reason")}
