import asyncio
import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Assuming the existance of these models from db.py
# from backend.core.db import AsyncSessionLocal, NodeModel, ThreatEventModel, AuditLogModel
from core.db import AsyncSessionLocal, NodeModel, ThreatEventModel, AuditLogModel
from core.nexus_stream import get_producer
from core.nexus_events import NodeDiscoveredEvent, ThreatDetectedEvent


async def migrate_data():
    producer = await get_producer()

    async with AsyncSessionLocal() as session:
        # 1. Synthesize Node Events
        # We don't just dump the current state, we reconstruct the timeline.
        # For simplicity in this draft, we assume nodes were discovered at their 'created' timestamp
        result = await session.execute(select(NodeModel))
        nodes = result.scalars().all()

        node_events = []
        for node in nodes:
            # We reconstruct the historical "discovery" event
            event = NodeDiscoveredEvent(
                event_id=str(uuid.uuid4()),
                timestamp=float(node.created) if node.created else 0.0,
                is_replay=True,  # STRICT CQRS: Do not trigger SOAR!
                node_id=node.id,
                ip_address=node.host,
                tags=json.loads(node.tags) if node.tags else [],
            )
            node_events.append(event)

        # Sort by timestamp to maintain temporal causality
        node_events.sort(key=lambda x: x.timestamp)

        for event in node_events:
            await producer.send_and_wait("nexus-topology", event.model_dump())
            print(f"Migrated NodeDiscoveredEvent: {event.node_id}")

        # 2. Synthesize Threat Events
        threat_result = await session.execute(select(ThreatEventModel))
        threats = threat_result.scalars().all()

        threat_events = []
        for threat in threats:
            event = ThreatDetectedEvent(
                event_id=threat.id,
                timestamp=threat.timestamp,
                is_replay=True,  # STRICT CQRS: Do not trigger SOAR!
                threat_id=threat.id,
                source_id=threat.source_ip,
                target_id=threat.target_ip,
                severity=threat.severity,
                attack_type=threat.type,
            )
            threat_events.append(event)

        threat_events.sort(key=lambda x: x.timestamp)

        for event in threat_events:
            await producer.send_and_wait("nexus-threats", event.model_dump())
            print(f"Migrated ThreatDetectedEvent: {event.threat_id}")

    await producer.stop()
    print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate_data())
