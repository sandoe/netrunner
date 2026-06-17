import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_alerts_lifecycle(client: AsyncClient):
    # 1. Get empty alerts
    resp = await client.get("/alerts")
    assert resp.status_code == 200
    assert resp.json() == []

    # 2. Create alert
    payload = {
        "title": "SQL Injection Attempt",
        "description": "Detected payload in user-agent",
        "severity": "critical"
    }
    resp = await client.post("/alerts", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "SQL Injection Attempt"
    assert data["severity"] == "critical"
    assert data["status"] == "new"
    alert_id = data["id"]

    # 3. Update alert status
    resp = await client.patch(f"/alerts/{alert_id}", json={"status": "open"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "open"

    # 4. Filter by status
    resp = await client.get("/alerts?status=open")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 5. Delete alert
    resp = await client.delete(f"/alerts/{alert_id}")
    assert resp.status_code == 200

    # 6. Verify deleted
    resp = await client.get("/alerts")
    assert resp.status_code == 200
    assert len(resp.json()) == 0

@pytest.mark.asyncio
async def test_update_missing_alert(client: AsyncClient):
    resp = await client.patch("/alerts/alrt_fake123", json={"status": "open"})
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_delete_missing_alert(client: AsyncClient):
    resp = await client.delete("/alerts/alrt_fake123")
    assert resp.status_code == 404
