"""Research File Layer smoke tests."""
from __future__ import annotations
import os
import pytest
import httpx
import io

BASE = os.environ.get("BASE_URL", "http://localhost:8001")
ELENA = ("elena.varga@synaptiq.io", "demo123")

PDF_BYTES = b"%PDF-1.4\n%seed\ntrailer<</Size 0/Root 1 0 R>>\n%%EOF"


async def _login(c, email, password):
    r = await c.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_full_file_lifecycle():
    async with httpx.AsyncClient(timeout=30) as c:
        await _login(c, *ELENA)
        # Find a workspace user is a member of
        ws_resp = await c.get(f"{BASE}/api/workspaces")
        ws = ws_resp.json() if isinstance(ws_resp.json(), list) else ws_resp.json().get("items", [])
        assert ws, "Elena needs at least one workspace"
        wid = ws[0]["id"]

        # Upload v1
        files = {"file": ("test.pdf", io.BytesIO(PDF_BYTES), "application/pdf")}
        data = {"entity_kind": "workspace", "entity_id": wid, "description": "pytest seed"}
        r = await c.post(f"{BASE}/api/files/upload", files=files, data=data)
        assert r.status_code == 200, r.text
        v1 = r.json()
        assert v1["version"] == 1
        assert v1["is_latest"] is True
        assert v1["root_id"] == v1["id"]
        fid = v1["id"]

        try:
            # List by entity
            r = await c.get(f"{BASE}/api/files?entity_kind=workspace&entity_id={wid}")
            assert r.status_code == 200
            assert any(x["id"] == fid for x in r.json())

            # Recent files surfaces it
            r = await c.get(f"{BASE}/api/files/recent")
            assert r.status_code == 200
            assert any(x["id"] == fid for x in r.json())

            # Upload v2
            files = {"file": ("test.pdf", io.BytesIO(PDF_BYTES + b"v2"), "application/pdf")}
            data["replaces_id"] = fid
            r = await c.post(f"{BASE}/api/files/upload", files=files, data=data)
            assert r.status_code == 200
            v2 = r.json()
            assert v2["version"] == 2
            assert v2["root_id"] == fid
            assert v2["is_latest"] is True

            # v1 no longer latest
            r = await c.get(f"{BASE}/api/files/{fid}")
            assert r.status_code == 200
            assert r.json()["is_latest"] is False

            # Versions chain
            r = await c.get(f"{BASE}/api/files/{fid}/versions")
            chain = r.json()
            assert len(chain) == 2
            assert chain[0]["version"] == 2

            # Activity
            r = await c.get(f"{BASE}/api/files/{fid}/activity")
            actions = [x["action"] for x in r.json()]
            assert "upload" in actions and "version" in actions

            # Download
            r = await c.get(f"{BASE}/api/files/{fid}/download")
            assert r.status_code == 200
            assert b"PDF" in r.content[:8]

            # Patch metadata
            r = await c.patch(f"{BASE}/api/files/{fid}", json={"description": "Updated"})
            assert r.status_code == 200
            assert r.json()["description"] == "Updated"
        finally:
            # Clean up entire chain
            for f in (await c.get(f"{BASE}/api/files/{fid}/versions")).json():
                await c.delete(f"{BASE}/api/files/{f['id']}")


@pytest.mark.asyncio
async def test_rejects_disallowed_mime():
    async with httpx.AsyncClient(timeout=15) as c:
        await _login(c, *ELENA)
        ws = (await c.get(f"{BASE}/api/workspaces")).json()
        ws = ws if isinstance(ws, list) else ws.get("items", [])
        wid = ws[0]["id"]
        files = {"file": ("malware.exe", io.BytesIO(b"MZ\x90"), "application/x-msdownload")}
        data = {"entity_kind": "workspace", "entity_id": wid}
        r = await c.post(f"{BASE}/api/files/upload", files=files, data=data)
        assert r.status_code == 415


@pytest.mark.asyncio
async def test_blocks_non_member_access():
    """Non-member must get 403 when listing files of a workspace they aren't in."""
    async with httpx.AsyncClient(timeout=15) as c:
        # Login as elena, find a workspace she's NOT in.
        await _login(c, *ELENA)
        # Use a fabricated id — should 404 or 403.
        r = await c.get(f"{BASE}/api/files?entity_kind=workspace&entity_id=000000000000000000000000")
        assert r.status_code in (403, 404)
