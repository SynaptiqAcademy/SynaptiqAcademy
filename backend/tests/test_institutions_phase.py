"""Institutional Layer integration tests."""
from __future__ import annotations
import os
import pytest
import httpx

BASE = os.environ.get("BASE_URL", "http://localhost:8001")
ELENA = ("elena.varga@synaptiq.io", "demo123")
ADMIN = ("admin@synaptiq.io", "admin123")


async def _login(c, email, password):
    r = await c.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_directory_lists_institutions():
    async with httpx.AsyncClient(timeout=20) as c:
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/institutions")
        assert r.status_code == 200
        d = r.json()
        assert d["total"] >= 1
        first = d["results"][0]
        assert "name" in first and "member_count" in first


@pytest.mark.asyncio
async def test_institution_overview_and_analytics():
    async with httpx.AsyncClient(timeout=20) as c:
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/institutions")
        iid = r.json()["results"][0]["id"]
        for path in ["analytics", "analytics/publications", "analytics/collaboration",
                     "analytics/funding", "analytics/reputation", "analytics/marketplace",
                     "analytics/health"]:
            r = await c.get(f"{BASE}/api/institutions/{iid}/{path}")
            assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
            d = r.json()
            assert isinstance(d, dict)


@pytest.mark.asyncio
async def test_create_unit_and_membership():
    async with httpx.AsyncClient(timeout=20) as c:
        await _login(c, *ADMIN)
        r = await c.get(f"{BASE}/api/institutions?q=synaptiq")
        iid = r.json()["results"][0]["id"]

        # Create a unit
        r = await c.post(f"{BASE}/api/institutions/{iid}/units",
                          json={"name": "Pytest Lab", "type": "lab",
                                "research_areas": ["test"]})
        assert r.status_code == 200
        unit = r.json()
        uid = unit["id"]
        try:
            # Get detail
            r = await c.get(f"{BASE}/api/units/{uid}")
            assert r.status_code == 200
            assert r.json()["institution"]["name"]

            # Update
            r = await c.patch(f"{BASE}/api/units/{uid}", json={"description": "Updated"})
            assert r.status_code == 200

            # Members list endpoint
            r = await c.get(f"{BASE}/api/institutions/{iid}/members?status=approved")
            assert r.status_code == 200
            members = r.json()
            assert len(members) >= 1

            # Add ALL approved members to this unit
            user_ids = [m["user_id"] for m in members][:3]
            r = await c.post(f"{BASE}/api/units/{uid}/members",
                              json={"user_ids": user_ids, "action": "add"})
            assert r.status_code == 200

            r = await c.get(f"{BASE}/api/units/{uid}")
            assert r.json()["member_count"] >= 1

            # Audit log shows the actions
            r = await c.get(f"{BASE}/api/institutions/{iid}/audit")
            assert r.status_code == 200
            actions = [x["action"] for x in r.json()]
            assert "unit_created" in actions
        finally:
            await c.delete(f"{BASE}/api/units/{uid}")


@pytest.mark.asyncio
async def test_claim_flow():
    """Elena claims a NEW institution (no domain match) -> goes to pending."""
    async with httpx.AsyncClient(timeout=20) as c:
        await _login(c, *ADMIN)
        # Create a fresh institution
        r = await c.post(f"{BASE}/api/institutions",
                          json={"name": "Pytest Claim Inst",
                                "country": "AT", "type": "research_institute"})
        iid = r.json()["id"]
        try:
            await _login(c, *ELENA)
            r = await c.post(f"{BASE}/api/institutions/{iid}/claim",
                              json={"note": "I'd like to join"})
            assert r.status_code == 200
            assert r.json()["status"] in ("pending", "approved")

            # Admin sees pending member
            await _login(c, *ADMIN)
            r = await c.get(f"{BASE}/api/institutions/{iid}/members?status=pending")
            assert r.status_code == 200
            elena_mem = [m for m in r.json() if m["user_id"] != m.get("created_by")][0] if r.json() else None

            # Decide approved
            r = await c.post(f"{BASE}/api/institutions/{iid}/members/{elena_mem['user_id']}/decide",
                              json={"decision": "approved"})
            assert r.status_code == 200

            # Role assignment
            r = await c.post(f"{BASE}/api/institutions/{iid}/members/{elena_mem['user_id']}/role",
                              json={"role": "research_lead"})
            assert r.status_code == 200
        finally:
            await _login(c, *ADMIN)
            await c.delete(f"{BASE}/api/institutions/{iid}")
