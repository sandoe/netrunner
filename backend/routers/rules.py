import json
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class Rule(BaseModel):
    id: int
    name: str
    port: int
    signature: str
    severity: str

@router.get("/active")
async def get_active_rules():
    """Returns a list of active DPI rules for the agents to enforce."""
    return {
        "rules": [
            {
                "id": 1,
                "name": "HTTP GET Request",
                "port": 80,
                "signature": "GET ",
                "severity": "low"
            },
            {
                "id": 2,
                "name": "HTTP POST Request",
                "port": 80,
                "signature": "POST",
                "severity": "medium"
            },
            {
                "id": 3,
                "name": "SQL Injection Attempt (SELECT)",
                "port": 80,
                "signature": "SELECT ",
                "severity": "critical"
            },
            {
                "id": 4,
                "name": "SQL Injection Attempt (UNION)",
                "port": 80,
                "signature": "UNION ",
                "severity": "critical"
            },
            {
                "id": 5,
                "name": "SSH Potential Brute Force Header",
                "port": 22,
                "signature": "SSH-2.0-",
                "severity": "low"
            }
        ]
    }
