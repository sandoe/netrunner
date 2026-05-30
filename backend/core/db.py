"""Database management using SQLAlchemy for multi-backend support."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Text, Boolean, ForeignKey, select, delete, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///data/netrunner.db")

# Ensure parent directory exists for SQLite
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.split(":///")[1]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class NodeModel(Base):
    __tablename__ = "nodes"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    host: Mapped[str] = mapped_column(String(100))
    port: Mapped[int] = mapped_column(Integer)
    username: Mapped[Optional[str]] = mapped_column(String(100))
    transport: Mapped[str] = mapped_column(String(20), default="telnet")
    device_type: Mapped[str] = mapped_column(String(50), default="unknown")
    created: Mapped[Optional[str]] = mapped_column(String(50))
    tags: Mapped[Optional[str]] = mapped_column(Text)  # JSON list
    metadata_json: Mapped[Optional[str]] = mapped_column("metadata", Text)  # JSON dict
    threat_monitoring: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)

class BeaconNodeModel(Base):
    __tablename__ = "beacon_nodes"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    ip: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(100))
    password: Mapped[str] = mapped_column(String(100))
    target_server_ip: Mapped[str] = mapped_column(String(100))
    csi_mode: Mapped[str] = mapped_column(String(50), default="AUTO")
    sample_rate: Mapped[int] = mapped_column(Integer, default=30)
    udp_port: Mapped[int] = mapped_column(Integer, default=8001)

class LinkModel(Base):
    __tablename__ = "links"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    source: Mapped[str] = mapped_column(String(50), ForeignKey("nodes.id", ondelete="CASCADE"))
    target: Mapped[str] = mapped_column(String(50), ForeignKey("nodes.id", ondelete="CASCADE"))
    auto_discovered: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[Optional[str]] = mapped_column("metadata", Text)


class SettingModel(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text)


class VaultModel(Base):
    __tablename__ = "vault"
    node_id: Mapped[str] = mapped_column(String(50), ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    data: Mapped[str] = mapped_column(Text)
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False)


class ThreatEventModel(Base):
    __tablename__ = "threat_events"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    timestamp: Mapped[float] = mapped_column()
    node_id: Mapped[str] = mapped_column(String(50))
    source_ip: Mapped[str] = mapped_column(String(50))
    target_ip: Mapped[str] = mapped_column(String(50))
    type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Dynamically adapt table to add threat_monitoring if it doesn't exist
    async with engine.connect() as conn:
        try:
            # Check if column exists by querying it
            await conn.execute(select(NodeModel.threat_monitoring).limit(1))
        except Exception:
            # If query fails, the column doesn't exist in the SQLite database.
            # Add the column dynamically using ALTER TABLE
            print("[DB] threat_monitoring column not found. Running SQLite table migration...")
            await conn.execute(text("ALTER TABLE nodes ADD COLUMN threat_monitoring BOOLEAN DEFAULT 0"))
            await conn.commit()
            print("[DB] SQLite table migration completed successfully.")


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# --- Helper methods (legacy interface compatible) ---

async def load_nodes_db() -> dict:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(NodeModel))
        nodes = {}
        for row in result.scalars():
            n = {
                "id": row.id,
                "name": row.name,
                "host": row.host,
                "port": row.port,
                "username": row.username,
                "transport": row.transport,
                "device_type": row.device_type,
                "created": row.created,
                "tags": json.loads(row.tags) if row.tags else [],
                "metadata": json.loads(row.metadata_json) if row.metadata_json else {},
                "threat_monitoring": bool(row.threat_monitoring)
            }
            nodes[row.id] = n
        return nodes


async def save_node_db(node: dict):
    async with AsyncSessionLocal() as session:
        n = NodeModel(
            id=node["id"],
            name=node["name"],
            host=node["host"],
            port=node["port"],
            username=node.get("username"),
            transport=node.get("transport", "telnet"),
            device_type=node.get("device_type", "unknown"),
            created=node.get("created"),
            tags=json.dumps(node.get("tags", [])),
            metadata_json=json.dumps(node.get("metadata", {})),
            threat_monitoring=node.get("threat_monitoring", False)
        )
        await session.merge(n)
        await session.commit()


async def delete_node_db(node_id: str):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(NodeModel).where(NodeModel.id == node_id))
        await session.commit()


async def load_links_db() -> dict:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(LinkModel))
        links = {}
        for row in result.scalars():
            l = {
                "id": row.id,
                "source": row.source,
                "target": row.target,
                "auto_discovered": row.auto_discovered,
                "metadata": json.loads(row.metadata_json) if row.metadata_json else {}
            }
            links[row.id] = l
        return links


async def save_link_db(link: dict):
    async with AsyncSessionLocal() as session:
        l = LinkModel(
            id=link["id"],
            source=link["source"],
            target=link["target"],
            auto_discovered=link.get("auto_discovered", False),
            metadata_json=json.dumps(link.get("metadata", {}))
        )
        await session.merge(l)
        await session.commit()


async def delete_link_db(link_id: str):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(LinkModel).where(LinkModel.id == link_id))
        await session.commit()


async def load_settings_db() -> dict:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SettingModel))
        return {s.key: s.value for s in result.scalars()}


async def save_setting_db(key: str, value: str):
    async with AsyncSessionLocal() as session:
        s = SettingModel(key=key, value=value)
        await session.merge(s)
        await session.commit()


async def load_vault_entry_db(node_id: str) -> Optional[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(VaultModel).where(VaultModel.node_id == node_id))
        row = result.scalar_one_or_none()
        if row:
            return {"data": row.data, "encrypted": row.encrypted}
        return None


async def save_vault_entry_db(node_id: str, data: str, encrypted: bool):
    async with AsyncSessionLocal() as session:
        v = VaultModel(node_id=node_id, data=data, encrypted=encrypted)
        await session.merge(v)
        await session.commit()


async def delete_vault_entry_db(node_id: str):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(VaultModel).where(VaultModel.node_id == node_id))
        await session.commit()


async def save_threat_event_db(event: dict):
    async with AsyncSessionLocal() as session:
        e = ThreatEventModel(
            id=event["id"],
            timestamp=event["timestamp"],
            node_id=event.get("node_id", "unknown"),
            source_ip=event["source_ip"],
            target_ip=event["target_ip"],
            type=event["type"],
            severity=event["severity"]
        )
        session.add(e)
        await session.commit()

async def load_threat_events_db(limit: int = 100) -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ThreatEventModel).order_by(ThreatEventModel.timestamp.desc()).limit(limit)
        )
        events = []
        for row in result.scalars():
            events.append({
                "id": row.id,
                "timestamp": row.timestamp,
                "node_id": row.node_id,
                "source_ip": row.source_ip,
                "target_ip": row.target_ip,
                "type": row.type,
                "severity": row.severity
            })
        return events

async def load_beacon_nodes_db() -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(BeaconNodeModel))
        nodes = []
        for row in result.scalars():
            nodes.append({
                "id": row.id,
                "ip": row.ip,
                "username": row.username,
                "password": row.password,
                "target_server_ip": row.target_server_ip,
                "csi_mode": row.csi_mode,
                "sample_rate": row.sample_rate,
                "udp_port": row.udp_port
            })
        return nodes

async def save_beacon_node_db(node: dict):
    async with AsyncSessionLocal() as session:
        b = BeaconNodeModel(
            id=node["id"],
            ip=node["ip"],
            username=node["username"],
            password=node["password"],
            target_server_ip=node.get("target_server_ip", ""),
            csi_mode=node.get("csi_mode", "AUTO"),
            sample_rate=node.get("sample_rate", 30),
            udp_port=node.get("udp_port", 8001)
        )
        await session.merge(b)
        await session.commit()

async def delete_beacon_node_db(node_id: str):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(BeaconNodeModel).where(BeaconNodeModel.id == node_id))
        await session.commit()
