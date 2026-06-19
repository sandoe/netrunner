"""Database management using SQLAlchemy for multi-backend support."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Text, Boolean, ForeignKey, select, delete, text, Column, Float
from dotenv import load_dotenv
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from .logger import log as logger

try:
    from cryptography.fernet import Fernet
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False

load_dotenv()

# --- Encryption helpers for beacon nodes and vault ---
_DATA_DIR = Path("data")
_VAULT_KEY_FILE = _DATA_DIR / ".vault_key"


def _get_or_create_vault_key() -> bytes:
    _DATA_DIR.mkdir(exist_ok=True)
    if _VAULT_KEY_FILE.exists():
        return _VAULT_KEY_FILE.read_bytes().strip()
    if not _HAS_CRYPTO:
        # Fallback: use a deterministic key for non-crypto environments (NOT SECURE)
        return b"fallback-key-not-secure-do-not-use-in-production-32b=="
    key = Fernet.generate_key()
    _VAULT_KEY_FILE.write_bytes(key)
    try:
        _VAULT_KEY_FILE.chmod(0o600)
    except OSError:
        pass
    return key


def _fernet() -> "Fernet":
    if not _HAS_CRYPTO:
        raise RuntimeError("cryptography package not installed — run: pip install cryptography")
    return Fernet(_get_or_create_vault_key())


def _encrypt_password(password: str) -> str:
    """Encrypt a password using the vault key."""
    if not _HAS_CRYPTO:
        return password  # No encryption available
    f = _fernet()
    return f.encrypt(password.encode()).decode()


def _decrypt_password(encrypted: str) -> str:
    """Decrypt a password using the vault key."""
    if not _HAS_CRYPTO:
        return encrypted
    try:
        f = _fernet()
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        return encrypted  # Return as-is if decryption fails

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///data/netrunner.db")
INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://127.0.0.1:8086")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN", "")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG", "netrunner")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET", "traffic")

_influx_client = None

def get_influx_client():
    global _influx_client
    if _influx_client is None:
        _influx_client = InfluxDBClientAsync(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    return _influx_client


from sqlalchemy.pool import NullPool
from sqlalchemy import event

# Ensure parent directory exists for SQLite
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.split(":///")[1]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
else:
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

class UserModel(Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(100), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    salt: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(20), default="analyst")
    created: Mapped[Optional[str]] = mapped_column(String(50))

class BeaconNodeModel(Base):
    __tablename__ = "beacon_nodes"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    ip: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(100))
    password: Mapped[str] = mapped_column(String(255))  # Encrypted
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
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

class PlaybookModel(Base):
    __tablename__ = "playbooks"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    conditions: Mapped[str] = mapped_column(Text)
    actions: Mapped[str] = mapped_column(Text)
    created_at: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[float] = mapped_column(Float)

class IntegrationModel(Base):
    __tablename__ = "integrations"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    provider: Mapped[str] = mapped_column(String(50))  # e.g., "slack", "splunk", "teams"
    name: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[float] = mapped_column(Float)

class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    resource: Mapped[str] = mapped_column(String(100))
    details: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[float] = mapped_column(Float)

class ThreatIntelModel(Base):
    __tablename__ = "threat_intel"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    ip: Mapped[str] = mapped_column(String(100), index=True)
    source: Mapped[str] = mapped_column(String(100))
    threat_type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(50))
    timestamp: Mapped[float] = mapped_column(Float)


class AlertModel(Base):
    __tablename__ = "alerts"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20)) # "low", "medium", "high", "critical"
    status: Mapped[str] = mapped_column(String(20), default="new") # "new", "open", "closed", "false_positive"
    assignee_id: Mapped[Optional[str]] = mapped_column(String(100), ForeignKey("users.username", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[float] = mapped_column()
    updated_at: Mapped[float] = mapped_column()


class ReportModel(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    timerange_hours: Mapped[int] = mapped_column(Integer)
    summary_json: Mapped[str] = mapped_column(Text)
    markdown_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[float] = mapped_column(Float)

# --- SDN & Infrastructure Models ---

class NetworkConfigModel(Base):
    __tablename__ = "network_configs"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    type: Mapped[str] = mapped_column(String(20)) # "vlan", "ssid", "port_profile"
    name: Mapped[str] = mapped_column(String(100))
    config_json: Mapped[str] = mapped_column(Text) # JSON config payload
    node_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=True) # if null, global config

class ClientModel(Base):
    __tablename__ = "clients"
    mac: Mapped[str] = mapped_column(String(50), primary_key=True)
    ip: Mapped[Optional[str]] = mapped_column(String(100))
    hostname: Mapped[Optional[str]] = mapped_column(String(100))
    node_id: Mapped[str] = mapped_column(String(50), ForeignKey("nodes.id", ondelete="CASCADE"))
    rssi: Mapped[Optional[int]] = mapped_column(Integer)
    rx_bytes: Mapped[int] = mapped_column(Integer, default=0)
    tx_bytes: Mapped[int] = mapped_column(Integer, default=0)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[float] = mapped_column()

class TrafficStatModel(Base):
    __tablename__ = "traffic_stats"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    timestamp: Mapped[float] = mapped_column()
    node_id: Mapped[str] = mapped_column(String(50), ForeignKey("nodes.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(50)) # "streaming", "p2p", "web", "social"
    rx_bytes: Mapped[int] = mapped_column(Integer, default=0)
    tx_bytes: Mapped[int] = mapped_column(Integer, default=0)

class VoucherModel(Base):
    __tablename__ = "vouchers"
    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    duration_hours: Mapped[int] = mapped_column(Integer, default=24)
    data_limit_mb: Mapped[Optional[int]] = mapped_column(Integer)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[float] = mapped_column()

class GuestSessionModel(Base):
    __tablename__ = "guest_sessions"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    mac: Mapped[str] = mapped_column(String(50))
    node_id: Mapped[str] = mapped_column(String(50), ForeignKey("nodes.id", ondelete="CASCADE"))
    voucher_code: Mapped[Optional[str]] = mapped_column(String(20))
    authorized_at: Mapped[float] = mapped_column()
    expires_at: Mapped[float] = mapped_column()
    rx_bytes: Mapped[int] = mapped_column(Integer, default=0)
    tx_bytes: Mapped[int] = mapped_column(Integer, default=0)

class FirmwareModel(Base):
    __tablename__ = "firmwares"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    version: Mapped[str] = mapped_column(String(50))
    arch: Mapped[str] = mapped_column(String(20)) # "amd64", "arm64"
    url: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[float] = mapped_column()


async def init_db():
    # Base.metadata.create_all is handled by alembic migrations now
    pass


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
            password = row.password
            # Decrypt if encrypted
            if row.encrypted:
                password = _decrypt_password(password)
            nodes.append({
                "id": row.id,
                "ip": row.ip,
                "username": row.username,
                "password": password,
                "target_server_ip": row.target_server_ip,
                "csi_mode": row.csi_mode,
                "sample_rate": row.sample_rate,
                "udp_port": row.udp_port
            })
        return nodes

async def save_beacon_node_db(node: dict):
    async with AsyncSessionLocal() as session:
        password = node["password"]
        encrypted = False
        if password and _HAS_CRYPTO:
            password = _encrypt_password(password)
            encrypted = True
        b = BeaconNodeModel(
            id=node["id"],
            ip=node["ip"],
            username=node["username"],
            password=password,
            encrypted=encrypted,
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


# --- users ----------------------------------------------------------------- #
def _user_to_dict(row: "UserModel") -> dict:
    return {
        "username": row.username,
        "password_hash": row.password_hash,
        "salt": row.salt,
        "role": row.role,
        "created": row.created,
    }

async def load_users_db() -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserModel))
        return [_user_to_dict(r) for r in result.scalars()]

async def get_user_db(username: str) -> Optional[dict]:
    async with AsyncSessionLocal() as session:
        row = await session.get(UserModel, username)
        return _user_to_dict(row) if row else None

async def save_user_db(user: dict):
    async with AsyncSessionLocal() as session:
        await session.merge(UserModel(
            username=user["username"],
            password_hash=user["password_hash"],
            salt=user["salt"],
            role=user.get("role", "analyst"),
            created=user.get("created"),
        ))
        await session.commit()

async def delete_user_db(username: str):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(UserModel).where(UserModel.username == username))
        await session.commit()

async def wipe_all_data_db():
    """Wipes all active operational data (Ghost Protocol cleanup)."""
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM beacon_nodes"))
        await session.execute(text("DELETE FROM threat_events"))
        await session.execute(text("DELETE FROM links"))
        await session.execute(text("DELETE FROM clients"))
        await session.execute(text("DELETE FROM traffic_stats"))
        await session.execute(text("DELETE FROM guest_sessions"))
        await session.execute(text("DELETE FROM vault"))
        await session.execute(text("DELETE FROM nodes"))
        await session.execute(text("DELETE FROM alerts"))
        await session.commit()


# --- alerts ---------------------------------------------------------------- #
def _alert_to_dict(row: "AlertModel") -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "description": row.description,
        "severity": row.severity,
        "status": row.status,
        "assignee_id": row.assignee_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }

async def load_alerts_db(status: Optional[str] = None) -> list[dict]:
    async with AsyncSessionLocal() as session:
        query = select(AlertModel).order_by(AlertModel.created_at.desc())
        if status:
            query = query.where(AlertModel.status == status)
        result = await session.execute(query)
        return [_alert_to_dict(r) for r in result.scalars()]

async def get_alert_db(alert_id: str) -> Optional[dict]:
    async with AsyncSessionLocal() as session:
        row = await session.get(AlertModel, alert_id)
        return _alert_to_dict(row) if row else None

async def save_alert_db(alert: dict):
    async with AsyncSessionLocal() as session:
        await session.merge(AlertModel(
            id=alert["id"],
            title=alert["title"],
            description=alert.get("description"),
            severity=alert["severity"],
            status=alert.get("status", "new"),
            assignee_id=alert.get("assignee_id"),
            created_at=alert["created_at"],
            updated_at=alert.get("updated_at", alert["created_at"])
        ))
        await session.commit()

async def delete_alert_db(alert_id: str):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(AlertModel).where(AlertModel.id == alert_id))
        await session.commit()

async def insert_alert(alert: dict):
    await save_alert_db(alert)

async def update_alert_status(alert_id: str, status: str):
    import time
    async with AsyncSessionLocal() as session:
        row = await session.get(AlertModel, alert_id)
        if row:
            row.status = status
            row.updated_at = time.time()
            await session.commit()

# --- reports --------------------------------------------------------------- #
def _report_to_dict(row: "ReportModel") -> dict:
    return {
        "id": row.id,
        "timerange_hours": row.timerange_hours,
        "summary_json": json.loads(row.summary_json),
        "markdown_content": row.markdown_content,
        "created_at": row.created_at,
    }

async def load_reports_db() -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ReportModel).order_by(ReportModel.created_at.desc()))
        return [_report_to_dict(r) for r in result.scalars()]

async def get_report_db(report_id: str) -> Optional[dict]:
    async with AsyncSessionLocal() as session:
        row = await session.get(ReportModel, report_id)
        return _report_to_dict(row) if row else None

async def save_report_db(report: dict):
    async with AsyncSessionLocal() as session:
        await session.merge(ReportModel(
            id=report["id"],
            timerange_hours=report["timerange_hours"],
            summary_json=json.dumps(report["summary_json"]),
            markdown_content=report["markdown_content"],
            created_at=report["created_at"]
        ))
        await session.commit()

async def load_playbooks_db():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(PlaybookModel))
        return [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "is_active": r.is_active,
                "conditions": r.conditions,
                "actions": r.actions,
                "created_at": r.created_at,
                "updated_at": r.updated_at
            } for r in result.scalars().all()
        ]

async def save_playbook_db(playbook: dict):
    async with AsyncSessionLocal() as session:
        obj = PlaybookModel(**playbook)
        session.add(obj)
        await session.commit()

async def update_playbook_db(playbook_id: str, data: dict):
    async with AsyncSessionLocal() as session:
        row = await session.get(PlaybookModel, playbook_id)
        if row:
            for k, v in data.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            import time
            row.updated_at = time.time()
            await session.commit()

async def delete_playbook_db(playbook_id: str):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(PlaybookModel).where(PlaybookModel.id == playbook_id))
        await session.commit()

async def load_integrations_db() -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(IntegrationModel))
        return [
            {
                "id": r.id,
                "provider": r.provider,
                "name": r.name,
                "url": r.url,
                "is_active": r.is_active,
                "created_at": r.created_at
            } for r in result.scalars().all()
        ]

async def save_integration_db(integration: dict):
    async with AsyncSessionLocal() as session:
        obj = IntegrationModel(**integration)
        await session.merge(obj)
        await session.commit()

async def update_integration_db(integration_id: str, data: dict):
    async with AsyncSessionLocal() as session:
        row = await session.get(IntegrationModel, integration_id)
        if row:
            for k, v in data.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            await session.commit()

async def delete_integration_db(integration_id: str):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(IntegrationModel).where(IntegrationModel.id == integration_id))
        await session.commit()

async def insert_audit_log(log_entry: dict):
    async with AsyncSessionLocal() as session:
        obj = AuditLogModel(**log_entry)
        session.add(obj)
        await session.commit()

async def load_audit_logs_db(limit: int = 100) -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AuditLogModel).order_by(AuditLogModel.timestamp.desc()).limit(limit))
        return [
            {
                "id": r.id,
                "user_id": r.user_id,
                "action": r.action,
                "resource": r.resource,
                "details": r.details,
                "timestamp": r.timestamp
            } for r in result.scalars().all()
        ]

async def insert_threat_intel(intel_entry: dict):
    async with AsyncSessionLocal() as session:
        # Check if already exists
        result = await session.execute(select(ThreatIntelModel).where(ThreatIntelModel.ip == intel_entry["ip"]))
        existing = result.scalars().first()
        if existing:
            return
        obj = ThreatIntelModel(**intel_entry)
        session.add(obj)
        await session.commit()

async def check_ip_threat_intel(ip: str) -> dict | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ThreatIntelModel).where(ThreatIntelModel.ip == ip))
        r = result.scalars().first()
        if r:
            return {
                "ip": r.ip,
                "source": r.source,
                "threat_type": r.threat_type,
                "severity": r.severity
            }
        return None

