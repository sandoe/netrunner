import pytest
from httpx import AsyncClient

async def get_token(client: AsyncClient, username, password):
    resp = await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_rbac_student_vs_analyst_and_admin(anon_client: AsyncClient, client: AsyncClient):
    # Log in as analyst
    analyst_token = await get_token(anon_client, "analyst", "analyst")
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

    # Log in as student
    student_token = await get_token(anon_client, "student", "student")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Helper function to test an endpoint
    async def assert_restricted(method, url, json_data=None):
        # 1. Student should get 403 Forbidden
        if method == "POST":
            resp_student = await anon_client.post(url, headers=student_headers, json=json_data)
        elif method == "DELETE":
            resp_student = await anon_client.delete(url, headers=student_headers)
        elif method == "PATCH":
            resp_student = await anon_client.patch(url, headers=student_headers, json=json_data)
        assert resp_student.status_code == 403, f"Expected 403 for student on {url}, got {resp_student.status_code}"

        # 2. Analyst / Admin should NOT get 403 (could be 400, 404, or 200 depending on mock data/params)
        if method == "POST":
            resp_analyst = await anon_client.post(url, headers=analyst_headers, json=json_data)
        elif method == "DELETE":
            resp_analyst = await anon_client.delete(url, headers=analyst_headers)
        elif method == "PATCH":
            resp_analyst = await anon_client.patch(url, headers=analyst_headers, json=json_data)
        assert resp_analyst.status_code != 403, f"Expected non-403 for analyst on {url}, got {resp_analyst.status_code}"

    # Test recon endpoints
    await assert_restricted("POST", "/api/recon/dummy-nid/scan", {"target": "127.0.0.1"})
    await assert_restricted("POST", "/api/recon/dummy-nid/import", {"hosts": [{"ip": "10.0.0.1"}]})

    # Test redteam endpoints
    await assert_restricted("POST", "/api/redteam/deploy", {"node_id": "dummy", "tool_name": "scapy"})

    # Test chaos endpoints
    await assert_restricted("POST", "/api/chaos/attack", {"node_id": "dummy", "attack_type": "ssh"})

    # Test playbooks endpoints
    await assert_restricted("POST", "/playbooks/", {"name": "test-playbook", "conditions": "[]", "actions": "[]"})
    await assert_restricted("PATCH", "/playbooks/dummy-id", {"name": "updated-playbook"})
    await assert_restricted("DELETE", "/playbooks/dummy-id")
    await assert_restricted("POST", "/playbooks/executions/dummy-id/approve")
    await assert_restricted("POST", "/playbooks/executions/dummy-id/reject")
    await assert_restricted("POST", "/playbooks/simulate/syn-flood")

    # Test agents endpoints
    await assert_restricted("POST", "/api/nodes/dummy-nid/agents/recon/install")
    await assert_restricted("POST", "/api/nodes/dummy-nid/agents/recon/start")
    await assert_restricted("POST", "/api/nodes/dummy-nid/agents/recon/stop")
    await assert_restricted("DELETE", "/api/nodes/dummy-nid/agents/recon")
    await assert_restricted("POST", "/api/nodes/dummy-nid/agents/attack/vmware", {"target": "10.0.0.1"})
    await assert_restricted("POST", "/api/nodes/dummy-nid/agents/attack/docker", {"target": "10.0.0.1"})


@pytest.mark.asyncio
async def test_playbooks_read_allowed_for_student(anon_client: AsyncClient):
    student_token = await get_token(anon_client, "student", "student")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Students should be able to get playbooks and executions without 403
    resp_list = await anon_client.get("/playbooks/", headers=student_headers)
    assert resp_list.status_code == 200

    resp_pending = await anon_client.get("/playbooks/executions/pending", headers=student_headers)
    assert resp_pending.status_code == 200
