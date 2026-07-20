"""Marketplace + Reputation phase smoke test."""
from __future__ import annotations
import os
import pytest
import httpx

BASE = os.environ.get("BASE_URL", "http://localhost:8001")
ELENA = ("elena.varga@synaptiq.io", "demo123")
ADMIN = ("admin@synaptiq.io", "admin123")


async def _login(client, email: str, password: str):
    r = await client.post(f"{BASE}/api/auth/login",
                          json={"email": email, "password": password})
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_reputation_me():
    async with httpx.AsyncClient(timeout=20) as c:
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/reputation/me")
        assert r.status_code == 200
        d = r.json()
        for k in ("collaboration", "publication", "reviewer", "funding", "activity", "overall"):
            assert k in d, f"missing {k}"
        assert isinstance(d["overall"], (int, float))


@pytest.mark.asyncio
async def test_marketplace_search_and_roles():
    async with httpx.AsyncClient(timeout=20) as c:
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/marketplace/roles")
        assert r.status_code == 200
        assert "co_author" in r.json()["roles"]
        r = await c.post(f"{BASE}/api/marketplace/search", json={"limit": 5})
        assert r.status_code == 200
        d = r.json()
        assert "results" in d
        # At least the seeded users should match.
        assert d["count"] >= 1


@pytest.mark.asyncio
async def test_expertise_request_flow():
    async with httpx.AsyncClient(timeout=20) as c:
        await _login(c, *ELENA)
        # Create
        r = await c.post(f"{BASE}/api/expertise", json={
            "kind": "statistician", "title": "Need PLS-SEM expert TEST",
            "description": "Pytest seed for marketplace integration tests; please ignore.",
            "required_skills": ["pls-sem"], "research_areas": ["management"],
        })
        assert r.status_code == 200, r.text
        rid = r.json()["id"]
        try:
            # List
            r = await c.get(f"{BASE}/api/expertise?kind=statistician")
            assert r.status_code == 200
            assert any(x["id"] == rid for x in r.json()["results"])

            # Switch to admin and apply
            await _login(c, *ADMIN)
            r = await c.post(f"{BASE}/api/expertise/{rid}/apply",
                              json={"message": "Pytest applicant — I can help with PLS-SEM."})
            assert r.status_code == 200

            # Owner sees applicant
            await _login(c, *ELENA)
            r = await c.get(f"{BASE}/api/expertise/{rid}")
            assert r.status_code == 200
            d = r.json()
            assert d["i_am_owner"] is True
            assert len(d.get("applicants") or []) == 1
            assert d["applicants"][0]["user"]["full_name"]

            # Decide accepted
            applicant_uid = d["applicants"][0]["user_id"]
            r = await c.post(
                f"{BASE}/api/expertise/{rid}/applications/{applicant_uid}/decide",
                json={"decision": "accepted"})
            assert r.status_code == 200

            # Verify request now "filled"
            r = await c.get(f"{BASE}/api/expertise/{rid}")
            assert r.json()["status"] == "filled"
        finally:
            await _login(c, *ELENA)
            await c.delete(f"{BASE}/api/expertise/{rid}")


@pytest.mark.asyncio
async def test_marketplace_invite_and_analytics():
    async with httpx.AsyncClient(timeout=20) as c:
        await _login(c, *ELENA)
        # Find a target admin user
        r = await c.post(f"{BASE}/api/marketplace/search", json={"limit": 5})
        results = r.json()["results"]
        target = next((x for x in results if x["user"]["full_name"] == "SYNAPTIQ Admin"), results[0])
        target_id = target["user"]["id"]

        r = await c.post(f"{BASE}/api/marketplace/invite", json={
            "target_user_id": target_id, "kind": "collaboration",
            "message": "Pytest invite — would you co-author?",
        })
        assert r.status_code == 200
        inv_id = r.json()["id"]

        # Verify shows up in sender's list
        r = await c.get(f"{BASE}/api/marketplace/invitations?direction=sent")
        assert any(x["id"] == inv_id for x in r.json())

        # Receiver decides
        await _login(c, *ADMIN)
        r = await c.get(f"{BASE}/api/marketplace/invitations?direction=received")
        assert any(x["id"] == inv_id for x in r.json())
        r = await c.post(f"{BASE}/api/marketplace/invitations/{inv_id}/decide",
                          json={"decision": "accepted"})
        assert r.status_code == 200

        # Sender analytics reflects the accept
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/marketplace/analytics")
        assert r.status_code == 200
        d = r.json()
        assert d["invitations_sent"] >= 1
        assert d["invitations_accepted"] >= 1
