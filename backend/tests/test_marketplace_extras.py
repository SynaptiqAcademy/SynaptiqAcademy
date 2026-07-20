"""Extra smoke checks for Marketplace v2 + Reputation that complement test_marketplace_phase.py."""
from __future__ import annotations
import os
import pytest
import httpx

BASE = os.environ.get("BASE_URL", "http://localhost:8001")
ELENA = ("elena.varga@synaptiq.io", "demo123")
ADMIN = ("admin@synaptiq.io", "admin123")


async def _login(client, email: str, password: str):
    r = await client.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_marketplace_analytics_shape():
    async with httpx.AsyncClient(timeout=20) as c:
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/marketplace/analytics")
        assert r.status_code == 200
        d = r.json()
        for k in ("invitations_sent", "invitations_accepted"):
            assert k in d, f"missing {k}"


@pytest.mark.asyncio
async def test_reputation_me_has_weights_and_subscores():
    async with httpx.AsyncClient(timeout=20) as c:
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/reputation/me")
        assert r.status_code == 200
        d = r.json()
        for k in ("collaboration", "publication", "reviewer", "funding", "activity", "overall"):
            assert k in d
        # weights are commonly nested or top-level — accept either form
        assert "weights" in d or any(k.endswith("_weight") for k in d.keys())


@pytest.mark.asyncio
async def test_expertise_list_with_facets():
    async with httpx.AsyncClient(timeout=20) as c:
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/expertise")
        assert r.status_code == 200
        d = r.json()
        assert "results" in d
        assert "facets" in d, "expertise list should return facets"


@pytest.mark.asyncio
async def test_marketplace_search_returns_results():
    async with httpx.AsyncClient(timeout=20) as c:
        await _login(c, *ELENA)
        r = await c.post(f"{BASE}/api/marketplace/search", json={"limit": 5})
        assert r.status_code == 200
        d = r.json()
        assert d.get("count", 0) >= 1
        assert isinstance(d.get("results"), list)


@pytest.mark.asyncio
async def test_reputation_sync_openalex_no_500():
    """OpenAlex may legitimately 404 if no profile resolves — never 500."""
    async with httpx.AsyncClient(timeout=60) as c:
        await _login(c, *ELENA)
        r = await c.post(f"{BASE}/api/reputation/sync-openalex")
        assert r.status_code in (200, 404), f"unexpected: {r.status_code} {r.text[:300]}"


@pytest.mark.asyncio
async def test_marketplace_roles_complete():
    async with httpx.AsyncClient(timeout=20) as c:
        await _login(c, *ELENA)
        r = await c.get(f"{BASE}/api/marketplace/roles")
        assert r.status_code == 200
        roles = r.json()["roles"]
        expected = {"co_author", "statistician", "methodology", "reviewer",
                    "ai_specialist", "data_scientist", "editor", "sme"}
        missing = expected - set(roles)
        assert not missing, f"missing roles: {missing}"
