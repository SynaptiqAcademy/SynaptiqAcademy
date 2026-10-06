"""Legal & Trust Phase 2 security review: the whole /api/admin surface is
deny-by-default. Before the gate, 40 admin endpoints (AI action logs,
self-improvement audit log, notification broadcast, sync queue, ...) only
required a signed-in member.

Runs in-process against the local MongoDB (skipped if none).
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId

pytest.importorskip("pymongo")

SAMPLE = [
    ("GET", "/api/admin/self-improvement/audit-log"),
    ("GET", "/api/admin/aos/timeline/recent"),
    ("GET", "/api/admin/publishing/overview"),
    ("POST", "/api/admin/aos/sync/process-queue"),
    ("POST", "/api/admin/aos/automation/install-defaults"),
    ("GET", "/api/admin/users"),
]


@pytest.fixture(scope="module")
def client_and_db():
    from pymongo import MongoClient
    try:
        mc = MongoClient(os.environ.get("MONGODB_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=800)
        mc.admin.command("ping")
    except Exception:
        pytest.skip("local MongoDB not available")
    from fastapi.testclient import TestClient
    import server
    # The same database the app resolves (db.py: MONGODB_DB_NAME, then DB_NAME).
    db = mc[(os.environ.get("MONGODB_DB_NAME", "").strip() or os.environ.get("DB_NAME", "synaptiq_local_qa"))]
    with TestClient(server.app) as c:
        yield c, db


def _as(client, db, role, email):
    from auth_utils import create_access_token
    uid = ObjectId()
    db.users.delete_many({"email": email})
    db.users.insert_one({"_id": uid, "email": email, "full_name": "Gate probe", "role": role,
                         "status": "active", "email_verified": True, "onboarded": True, "plan_code": "free"})
    client.cookies.clear()
    client.cookies.set("access_token", create_access_token(str(uid), email))
    client.cookies.set("csrf_token", "t")
    return uid


@pytest.mark.parametrize("method,path", SAMPLE)
def test_member_cannot_reach_admin_endpoints(client_and_db, method, path):
    c, db = client_and_db
    uid = _as(c, db, "researcher", "gate-member@example.org")
    try:
        r = c.request(method, path, headers={"X-CSRF-Token": "t"}, json={})
        assert r.status_code == 403, (path, r.status_code, r.text[:200])
    finally:
        db.users.delete_one({"_id": uid})


def test_anonymous_cannot_reach_admin_endpoints(client_and_db):
    c, _ = client_and_db
    c.cookies.clear()
    r = c.get("/api/admin/self-improvement/audit-log")
    assert r.status_code in (401, 403)


def test_gate_runs_before_the_zero_trust_skip_list():
    src = open("zt/middleware.py", encoding="utf-8").read()
    assert src.index("admin_gate(request)") < src.index("if any(path.startswith(p) for p in _SKIP_PATHS)")
