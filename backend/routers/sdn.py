from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
import time
import uuid

from backend.core.db import (
    get_db,
    NetworkConfigModel,
    ClientModel,
    TrafficStatModel,
    VoucherModel,
    GuestSessionModel,
    FirmwareModel,
    VlanConfigModel,
    NatRuleModel,
)
from backend.routers.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

router = APIRouter(prefix="/api/v1/sdn", tags=["SDN"])


# --- Network Configuration ---
@router.get("/networks")
async def list_networks(
    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    result = await db.execute(select(NetworkConfigModel))
    configs = []
    for row in result.scalars():
        configs.append(
            {
                "id": row.id,
                "type": row.type,
                "name": row.name,
                "config_json": row.config_json,
                "node_id": row.node_id,
            }
        )
    return configs


@router.post("/networks")
async def create_network(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")

    config_id = payload.get("id", str(uuid.uuid4()))
    config = NetworkConfigModel(
        id=config_id,
        type=payload["type"],
        name=payload["name"],
        config_json=payload["config_json"],
        node_id=payload.get("node_id"),
    )
    db.add(config)
    await db.commit()
    return {"status": "ok", "id": config_id}


@router.delete("/networks/{config_id}")
async def delete_network(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    await db.execute(
        delete(NetworkConfigModel).where(NetworkConfigModel.id == config_id)
    )
    await db.commit()
    return {"status": "ok"}


# --- VLANs ---
@router.get("/vlans")
async def list_vlans(
    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    result = await db.execute(select(VlanConfigModel))
    vlans = []
    for row in result.scalars():
        vlans.append(
            {"id": row.id, "tag": row.tag, "name": row.name, "subnet": row.subnet}
        )
    return vlans


@router.post("/vlans")
async def create_vlan(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    vlan_id = payload.get("id", str(uuid.uuid4()))
    vlan = VlanConfigModel(
        id=vlan_id, tag=payload["tag"], name=payload["name"], subnet=payload["subnet"]
    )
    db.add(vlan)
    await db.commit()
    return {"status": "ok", "id": vlan_id}


@router.delete("/vlans/{vlan_id}")
async def delete_vlan(
    vlan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    await db.execute(delete(VlanConfigModel).where(VlanConfigModel.id == vlan_id))
    await db.commit()
    return {"status": "ok"}


# --- NAT Rules ---
@router.get("/nat")
async def list_nat_rules(
    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    result = await db.execute(select(NatRuleModel))
    rules = []
    for row in result.scalars():
        rules.append(
            {
                "id": row.id,
                "type": row.type,
                "src": row.src,
                "dst": row.dst,
                "port": row.port,
            }
        )
    return rules


@router.post("/nat")
async def create_nat_rule(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    rule_id = payload.get("id", str(uuid.uuid4()))
    rule = NatRuleModel(
        id=rule_id,
        type=payload["type"],
        src=payload["src"],
        dst=payload["dst"],
        port=payload.get("port"),
    )
    db.add(rule)
    await db.commit()
    return {"status": "ok", "id": rule_id}


@router.delete("/nat/{rule_id}")
async def delete_nat_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    await db.execute(delete(NatRuleModel).where(NatRuleModel.id == rule_id))
    await db.commit()
    return {"status": "ok"}


# --- Clients ---
@router.get("/clients")
async def list_clients(
    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    result = await db.execute(select(ClientModel))
    clients = []
    for row in result.scalars():
        clients.append(
            {
                "mac": row.mac,
                "ip": row.ip,
                "hostname": row.hostname,
                "node_id": row.node_id,
                "rssi": row.rssi,
                "rx_bytes": row.rx_bytes,
                "tx_bytes": row.tx_bytes,
                "is_blocked": row.is_blocked,
                "last_seen": row.last_seen,
            }
        )
    return clients


@router.post("/clients/{mac}/block")
async def block_client(
    mac: str,
    blocked: bool,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")

    client = await db.get(ClientModel, mac)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    client.is_blocked = blocked
    await db.commit()
    return {"status": "ok", "blocked": blocked}


# --- Traffic Analytics ---
@router.get("/traffic")
async def get_traffic_stats(
    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    # Group by category and sum rx/tx bytes
    # For now, just return all stats
    result = await db.execute(
        select(TrafficStatModel).order_by(TrafficStatModel.timestamp.desc()).limit(1000)
    )
    stats = []
    for row in result.scalars():
        stats.append(
            {
                "id": row.id,
                "timestamp": row.timestamp,
                "node_id": row.node_id,
                "category": row.category,
                "rx_bytes": row.rx_bytes,
                "tx_bytes": row.tx_bytes,
            }
        )
    return stats


# --- Hotspot Manager (Vouchers) ---
@router.get("/vouchers")
async def list_vouchers(
    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    result = await db.execute(
        select(VoucherModel).order_by(VoucherModel.created_at.desc())
    )
    vouchers = []
    for row in result.scalars():
        vouchers.append(
            {
                "code": row.code,
                "duration_hours": row.duration_hours,
                "data_limit_mb": row.data_limit_mb,
                "is_used": row.is_used,
                "created_at": row.created_at,
            }
        )
    return vouchers


@router.post("/vouchers")
async def create_voucher(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")

    # Generate 8 char alphanumeric code
    import random, string

    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

    v = VoucherModel(
        code=code,
        duration_hours=payload.get("duration_hours", 24),
        data_limit_mb=payload.get("data_limit_mb"),
        created_at=time.time(),
    )
    db.add(v)
    await db.commit()
    return {"status": "ok", "code": code}


# --- Firmware & OTA ---
@router.get("/firmwares")
async def list_firmwares(
    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    result = await db.execute(
        select(FirmwareModel).order_by(FirmwareModel.uploaded_at.desc())
    )
    firmwares = []
    for row in result.scalars():
        firmwares.append(
            {
                "id": row.id,
                "version": row.version,
                "arch": row.arch,
                "url": row.url,
                "uploaded_at": row.uploaded_at,
            }
        )
    return firmwares
