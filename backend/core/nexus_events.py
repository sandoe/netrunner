from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class BaseNexusEvent(BaseModel):
    event_id: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    is_replay: bool = Field(
        default=False,
        description="Strict CQRS flag. If True, SOAR/SSH must NOT execute commands.",
    )


class NodeDiscoveredEvent(BaseNexusEvent):
    node_id: str
    ip_address: str
    os_type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class LinkEstablishedEvent(BaseNexusEvent):
    source_id: str
    target_id: str
    port: int
    protocol: str


class ThreatDetectedEvent(BaseNexusEvent):
    threat_id: str
    source_id: str
    target_id: str
    severity: str
    attack_type: str
    details: Dict[str, Any] = Field(default_factory=dict)
