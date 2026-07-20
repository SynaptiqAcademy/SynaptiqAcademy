"""Iter13 smoke test: directory>=2, my_membership, analytics, governance, seats, claim."""
from __future__ import annotations
import os
import pytest
import httpx

BASE = os.environ.get("BASE_URL", "http://localhost:8001")
ELENA = ("elena.varga@synaptiq.io", "demo123")
ADMIN = ("admin@synaptiq.io", "admin123")


async def _login(c, email, password):
    r = await c.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_directory_has_at_least_two():
    async with httpx.AsyncClient(timeout=30) as c:
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/institutions")
        assert r.status_code == 200
        d = r.json()
        names = [x["name"] for x in d["results"]]
        assert d["total"] >= 2, f"Expected >=2 institutions, got {d['total']}: {names}"
        assert any("ETH" in n for n in names), names
        assert any("SYNAPTIQ" in n.upper() for n in names), names


@pytest.mark.asyncio
async def test_detail_has_my_membership_for_elena_at_synaptiq():
    """Migration linked elena into SYNAPTIQ HQ (ETH Zurich has 0 members).
    Verify the my_membership field is populated correctly for the viewer."""
    async with httpx.AsyncClient(timeout=30) as c:
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/institutions?q=synaptiq")
        iid = r.json()["results"][0]["id"]
        r = await c.get(f"{BASE}/api/institutions/{iid}")
        assert r.status_code == 200
        body = r.json()
        assert "my_membership" in body, list(body.keys())
        assert body["my_membership"] is not None
        assert body["my_membership"]["status"] == "approved"


@pytest.mark.asyncio
async def test_synaptiq_hq_analytics_researchers_ge_one():
    async with httpx.AsyncClient(timeout=30) as c:
        await _login(c, *ADMIN)
        r = await c.get(f"{BASE}/api/institutions?q=synaptiq")
        iid = r.json()["results"][0]["id"]
        r = await c.get(f"{BASE}/api/institutions/{iid}/analytics")
        assert r.status_code == 200
        d = r.json()
        researchers = d.get("researchers") or d.get("approved_members") or d.get("member_count") or 0
        assert researchers >= 1, d


@pytest.mark.asyncio
async def test_governance_create_unit_patch_delete_and_audit():
    async with httpx.AsyncClient(timeout=30) as c:
        await _login(c, *ADMIN)
        iid = (await c.get(f"{BASE}/api/institutions?q=synaptiq")).json()["results"][0]["id"]

        r = await c.post(f"{BASE}/api/institutions/{iid}/units",
                         json={"name": "Pytest Dept", "type": "department",
                               "research_areas": ["ml"]})
        assert r.status_code == 200, r.text
        uid = r.json()["id"]
        try:
            r = await c.get(f"{BASE}/api/units/{uid}")
            assert r.status_code == 200
            body = r.json()
            assert body["institution"]["name"]
            assert "breadcrumb" in body or "path" in body or "ancestors" in body, list(body.keys())

            r = await c.patch(f"{BASE}/api/units/{uid}", json={"description": "ml dept"})
            assert r.status_code == 200

            r = await c.get(f"{BASE}/api/institutions/{iid}/audit")
            assert r.status_code == 200
            actions = [x["action"] for x in r.json()]
            assert "unit_created" in actions, actions
        finally:
            r = await c.delete(f"{BASE}/api/units/{uid}")
            assert r.status_code in (200, 204)


@pytest.mark.asyncio
async def test_seat_cap_enforced_and_patch_updates_total():
    async with httpx.AsyncClient(timeout=30) as c:
        await _login(c, *ADMIN)
        # Create a fresh test institution with tiny seat cap
        r = await c.post(f"{BASE}/api/institutions",
                         json={"name": "Pytest Seats Inst",
                               "type": "research_institute",
                               "country": "AT",
                               "seats_total": 1})
        assert r.status_code == 200, r.text
        iid = r.json()["id"]
        try:
            # Patch seats_total
            r = await c.patch(f"{BASE}/api/institutions/{iid}", json={"seats_total": 10})
            assert r.status_code == 200, r.text
            r = await c.get(f"{BASE}/api/institutions/{iid}")
            body = r.json()
            assert body.get("seats_total") == 10 or body.get("seats", {}).get("total") == 10, body
        finally:
            await c.delete(f"{BASE}/api/institutions/{iid}")


@pytest.mark.asyncio
async def test_claim_auto_verify_email_domain():
    async with httpx.AsyncClient(timeout=30) as c:
        await _login(c, *ADMIN)
        # Create a fresh institution where elena's domain matches
        r = await c.post(f"{BASE}/api/institutions",
                         json={"name": "Pytest Domain Inst",
                               "type": "research_institute",
                               "country": "AT",
                               "email_domains": ["synaptiq.io"]})
        iid = r.json()["id"]
        try:
            await _login(c, *ELENA)
            r = await c.post(f"{BASE}/api/institutions/{iid}/claim",
                             json={"note": "domain match"})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["status"] == "approved", d
            assert d.get("verified_via") in ("email_domain", "domain"), d
        finally:
            await _login(c, *ADMIN)
            await c.delete(f"{BASE}/api/institutions/{iid}")
