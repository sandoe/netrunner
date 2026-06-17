import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_report_summary_empty(client: AsyncClient):
    resp = await client.get("/reports/summary?timerange_hours=24")
    assert resp.status_code == 200
    data = resp.json()
    assert "generated_at" in data
    assert data["timerange_hours"] == 24
    assert data["total_active_nodes"] == 0
    assert data["alerts_summary"]["total"] == 0
    assert data["threats_summary"]["total_events"] == 0

@pytest.mark.asyncio
async def test_get_report_summary_with_data(client: AsyncClient):
    # Create an alert first to populate data
    alert_payload = {
        "title": "Malware detected",
        "severity": "high"
    }
    await client.post("/alerts", json=alert_payload)
    
    resp = await client.get("/reports/summary?timerange_hours=24")
    assert resp.status_code == 200
    data = resp.json()
    assert data["alerts_summary"]["total"] >= 1
    assert data["alerts_summary"]["by_severity"]["high"] >= 1
    assert data["alerts_summary"]["by_status"]["new"] >= 1
