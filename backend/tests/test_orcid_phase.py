"""ORCID integration smoke tests — dry-run mode (no real ORCID credentials)."""
from __future__ import annotations
import os
import pytest
import httpx

BASE = os.environ.get("BASE_URL", "http://localhost:8001")
ELENA = ("elena.varga@synaptiq.io", "demo123")


async def _login(c, email, password):
    r = await c.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_config_endpoint_public():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE}/api/orcid/config")
        assert r.status_code == 200
        d = r.json()
        assert "configured" in d
        assert d["environment"] in ("sandbox", "production")
        assert d["redirect_uri"].endswith("/api/orcid/callback")


@pytest.mark.asyncio
async def test_status_for_unlinked_user():
    async with httpx.AsyncClient(timeout=10) as c:
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/orcid/status")
        assert r.status_code == 200
        d = r.json()
        assert d["connected"] is False
        assert d["orcid_id"] is None
        assert d["publications_imported"] == 0


@pytest.mark.asyncio
async def test_authorize_gracefully_503_when_not_configured():
    async with httpx.AsyncClient(timeout=10) as c:
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/orcid/authorize?mode=link")
        # In dry-run: should 503; in configured mode: 200 with authorization_url.
        assert r.status_code in (200, 503)
        if r.status_code == 503:
            assert "not configured" in r.json().get("detail", "").lower()
        else:
            assert "authorization_url" in r.json()


@pytest.mark.asyncio
async def test_sync_history_endpoint():
    async with httpx.AsyncClient(timeout=10) as c:
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/orcid/sync-history")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_publications_endpoint_empty():
    async with httpx.AsyncClient(timeout=10) as c:
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/orcid/publications")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d.get("results"), list)
        assert d["total"] >= 0


@pytest.mark.asyncio
async def test_seed_orcid_publication_appears_in_listing():
    """Insert a fake ORCID-sourced publication directly + verify listing surfaces it."""
    import motor.motor_asyncio as motor
    from dotenv import load_dotenv
    load_dotenv()
    uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URL", "mongodb://localhost:27017/")
    db_name = os.environ.get("MONGODB_DB_NAME") or os.environ.get("DB_NAME", "synaptiq")
    client = motor.AsyncIOMotorClient(uri)
    db = client[db_name]
    async with httpx.AsyncClient(timeout=10) as c:
        await _login(c, *ELENA)
        me = await c.get(f"{BASE}/api/auth/me")
        uid = me.json()["id"]
        try:
            doc = {
                "owner_id": uid, "source": "orcid", "imported_via": "orcid",
                "title": "Pytest ORCID seed publication",
                "title_norm": "pytest orcid seed publication",
                "journal": "Pytest Journal", "year": 2025, "type": "journal_article",
                "doi": "10.9999/pytest-orcid-seed",
                "orcid_put_code": "999999",
            }
            r = await db.publications.insert_one(doc)
            try:
                rr = await c.get(f"{BASE}/api/orcid/publications")
                assert rr.status_code == 200
                pubs = rr.json()["results"]
                assert any(p["doi"] == doc["doi"] for p in pubs)
                # status counter reflects it
                st = await c.get(f"{BASE}/api/orcid/status")
                assert st.json()["publications_imported"] >= 1
            finally:
                await db.publications.delete_one({"_id": r.inserted_id})
        finally:
            client.close()
