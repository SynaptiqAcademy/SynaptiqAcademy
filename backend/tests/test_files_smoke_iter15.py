"""Iter15 file lifecycle smoke + security via public URL as elena."""
import os, io, requests, pytest

BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8001").rstrip("/")
ELENA = {"email": "elena.varga@synaptiq.io", "password": "demo123"}

TINY_PDF = b"%PDF-1.4\n%seed\n%%EOF"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{BASE_URL}/api/auth/login", json=ELENA)
    assert r.status_code == 200, r.text
    return sess


@pytest.fixture(scope="module")
def workspace_id(s):
    r = s.get(f"{BASE_URL}/api/workspaces")
    assert r.status_code == 200, r.text
    ws_list = r.json()
    assert ws_list, "elena has no workspaces"
    # Pick the first one she's in
    return ws_list[0]["id"]


def test_upload_v1(s, workspace_id):
    files = {"file": ("tinyA.pdf", TINY_PDF, "application/pdf")}
    data = {"entity_kind": "workspace", "entity_id": workspace_id, "description": "iter15 v1"}
    r = s.post(f"{BASE_URL}/api/files/upload", files=files, data=data)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["version"] == 1
    assert j["root_id"] == j["id"]
    assert j["is_latest"] is True
    pytest.fid_v1 = j["id"]


def test_list_includes_uploaded(s, workspace_id):
    r = s.get(f"{BASE_URL}/api/files", params={"entity_kind": "workspace", "entity_id": workspace_id})
    assert r.status_code == 200
    items = r.json()
    ids = [it["id"] for it in items]
    assert pytest.fid_v1 in ids


def test_upload_v2_replaces(s, workspace_id):
    files = {"file": ("tinyB.pdf", TINY_PDF + b"\n%v2\n", "application/pdf")}
    data = {"entity_kind": "workspace", "entity_id": workspace_id, "replaces_id": pytest.fid_v1}
    r = s.post(f"{BASE_URL}/api/files/upload", files=files, data=data)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["version"] == 2
    assert j["root_id"] == pytest.fid_v1
    assert j["is_latest"] is True
    pytest.fid_v2 = j["id"]

    # Original now is_latest:false
    r2 = s.get(f"{BASE_URL}/api/files/{pytest.fid_v1}")
    assert r2.status_code == 200
    assert r2.json()["is_latest"] is False


def test_versions(s):
    r = s.get(f"{BASE_URL}/api/files/{pytest.fid_v1}/versions")
    assert r.status_code == 200
    chain = r.json()
    assert len(chain) == 2
    assert chain[0]["version"] == 2  # desc
    assert chain[1]["version"] == 1


def test_activity_has_upload_and_version(s):
    r = s.get(f"{BASE_URL}/api/files/{pytest.fid_v1}/activity")
    assert r.status_code == 200
    actions = {a["action"] for a in r.json()}
    assert "upload" in actions
    assert "version" in actions


def test_download_v1(s):
    r = s.get(f"{BASE_URL}/api/files/{pytest.fid_v1}/download")
    assert r.status_code == 200
    assert "attachment" in r.headers.get("Content-Disposition", "")
    assert len(r.content) > 0


def test_patch_meta(s):
    r = s.patch(f"{BASE_URL}/api/files/{pytest.fid_v1}", json={"description": "updated"})
    assert r.status_code == 200
    body = r.json()
    # patch returns full doc; check description
    if "description" in body:
        assert body["description"] == "updated"


def test_delete_v1_keeps_v2_latest(s):
    r = s.delete(f"{BASE_URL}/api/files/{pytest.fid_v1}")
    assert r.status_code == 200
    # v2 still exists and latest
    r2 = s.get(f"{BASE_URL}/api/files/{pytest.fid_v2}")
    assert r2.status_code == 200
    assert r2.json()["is_latest"] is True


# ============ SECURITY ============

def test_reject_exe(s, workspace_id):
    files = {"file": ("evil.exe", b"MZ\x90\x00", "application/x-msdownload")}
    data = {"entity_kind": "workspace", "entity_id": workspace_id}
    r = s.post(f"{BASE_URL}/api/files/upload", files=files, data=data)
    assert r.status_code == 415, r.text


def test_reject_non_member(s):
    files = {"file": ("t.pdf", TINY_PDF, "application/pdf")}
    data = {"entity_kind": "workspace", "entity_id": "000000000000000000000000"}
    r = s.post(f"{BASE_URL}/api/files/upload", files=files, data=data)
    assert r.status_code in (403, 404), r.text


def test_reject_oversize(s, workspace_id):
    big = os.urandom(51 * 1024 * 1024)  # 51 MB
    files = {"file": ("big.pdf", big, "application/pdf")}
    data = {"entity_kind": "workspace", "entity_id": workspace_id}
    r = s.post(f"{BASE_URL}/api/files/upload", files=files, data=data)
    assert r.status_code == 413, f"Expected 413, got {r.status_code}"


# ============ MARKETPLACE ENRICHMENT NO-REGRESSION ============

def test_marketplace_search_no_regression(s):
    r = s.post(f"{BASE_URL}/api/marketplace/search", json={"limit": 10})
    assert r.status_code == 200, r.text
    body = r.json()
    candidates = body.get("candidates") or body.get("results") or []
    assert isinstance(candidates, list)
    if candidates:
        c0 = candidates[0]
        assert "shared_keywords" in c0 or "matched_keywords" in c0 or "score" in c0


# ============ CLEANUP ============

def test_cleanup_v2(s):
    if hasattr(pytest, "fid_v2"):
        r = s.delete(f"{BASE_URL}/api/files/{pytest.fid_v2}")
        assert r.status_code in (200, 404)
