"""P1 Phase 8B QA-hygiene follow-up.

Covers: the available_for_collaboration absent/null/false/true semantics
fix (display + discovery filter alignment), the new admin mark-demo /
unmark-demo endpoints and their is_demo discovery-exclusion effect, and the
local production-DB connection guard in db.py. Regression checks confirm
self-exclusion, show_in_discovery, and blocking remain intact.
"""
from __future__ import annotations

import os
import types

import pytest
from bson import ObjectId

from services.network.discovery_engine import search_people, _serialize_person
from auth_utils import serialize_user, serialize_public_user
from routers.admin_users_mgmt import mark_user_demo, unmark_user_demo, _parse_oid


def _oid() -> str:
    return str(ObjectId())


class _RawDB:
    def __init__(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        self._client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
        self.db = self._client[os.environ["MONGODB_DB_NAME"]]

    def close(self):
        self._client.close()


async def _insert_user(db, full_name: str, **extra) -> str:
    doc = {
        "full_name": full_name,
        "email": f"{full_name.lower().replace(' ', '')}-{_oid()[:8]}@synaptiq-test.io",
        "is_demo": False,
        "profile_visibility": "public",
        **extra,
    }
    res = await db.users.insert_one(doc)
    return str(res.inserted_id)


class _FakeRequest:
    """Minimal stand-in for FastAPI's Request — only what request_meta() reads."""
    class _Headers(dict):
        def get(self, k, default=""):
            return dict.get(self, k, default)

    class _Client:
        host = "127.0.0.1"

    def __init__(self):
        self.headers = self._Headers()
        self.client = self._Client()


class TestAvailableForCollaborationSemantics:
    """Part B — canonical semantic: absent/null means available (True);
    only an explicit False means unavailable. Applies to
    available_for_collaboration only, not the other three availability
    fields (their own canonical default is False when unset)."""

    def test_explicit_true_serializes_true(self):
        user = {"_id": ObjectId(), "full_name": "X", "available_for_collaboration": True}
        assert serialize_public_user(user)["available_for_collaboration"] is True
        assert serialize_user(dict(user))["available_for_collaboration"] is True

    def test_explicit_false_serializes_false(self):
        user = {"_id": ObjectId(), "full_name": "X", "available_for_collaboration": False}
        assert serialize_public_user(user)["available_for_collaboration"] is False
        assert serialize_user(dict(user))["available_for_collaboration"] is False

    def test_absent_serializes_true(self):
        user = {"_id": ObjectId(), "full_name": "X"}
        assert serialize_public_user(user)["available_for_collaboration"] is True
        assert serialize_user(dict(user))["available_for_collaboration"] is True

    def test_null_serializes_true_same_as_absent(self):
        user = {"_id": ObjectId(), "full_name": "X", "available_for_collaboration": None}
        assert serialize_public_user(user)["available_for_collaboration"] is True
        assert serialize_user(dict(user))["available_for_collaboration"] is True

    def test_serialize_person_display_matches_same_default(self):
        assert _serialize_person({"_id": ObjectId(), "full_name": "X"})["available_for_collaboration"] is True
        assert _serialize_person(
            {"_id": ObjectId(), "full_name": "X", "available_for_collaboration": False}
        )["available_for_collaboration"] is False
        assert _serialize_person(
            {"_id": ObjectId(), "full_name": "X", "available_for_collaboration": True}
        )["available_for_collaboration"] is True

    @pytest.mark.asyncio
    async def test_filter_true_includes_absent_and_explicit_true(self):
        raw = _RawDB()
        uid_absent = uid_true = uid_false = None
        try:
            suffix = _oid()[:8]
            uid_absent = await _insert_user(raw.db, f"CollabAbsent {suffix}")
            uid_true = await _insert_user(raw.db, f"CollabTrue {suffix}", available_for_collaboration=True)
            uid_false = await _insert_user(raw.db, f"CollabFalse {suffix}", available_for_collaboration=False)
            result = await search_people(
                raw.db, {"q": suffix, "available_for_collaboration": True}, viewer_id=None
            )
            ids = {r["id"] for r in result["results"]}
            assert uid_absent in ids
            assert uid_true in ids
            assert uid_false not in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^Collab"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_filter_false_matches_only_explicit_false(self):
        raw = _RawDB()
        uid_absent = uid_false = None
        try:
            suffix = _oid()[:8]
            uid_absent = await _insert_user(raw.db, f"CollabFAbsent {suffix}")
            uid_false = await _insert_user(raw.db, f"CollabFFalse {suffix}", available_for_collaboration=False)
            result = await search_people(
                raw.db, {"q": suffix, "available_for_collaboration": False}, viewer_id=None
            )
            ids = {r["id"] for r in result["results"]}
            assert uid_false in ids
            assert uid_absent not in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^CollabF"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_null_stored_value_behaves_like_absent_in_filter(self):
        raw = _RawDB()
        uid_null = None
        try:
            suffix = _oid()[:8]
            uid_null = await _insert_user(raw.db, f"CollabNull {suffix}", available_for_collaboration=None)
            result = await search_people(
                raw.db, {"q": suffix, "available_for_collaboration": True}, viewer_id=None
            )
            ids = {r["id"] for r in result["results"]}
            assert uid_null in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^CollabNull"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_other_availability_filters_unaffected_still_exact_match(self):
        """available_for_reviewing/supervision/consulting keep their own
        default-False-when-absent semantic — absent must NOT match a
        filter for True, unlike available_for_collaboration."""
        raw = _RawDB()
        uid_absent = uid_true = None
        try:
            suffix = _oid()[:8]
            uid_absent = await _insert_user(raw.db, f"RevAbsent {suffix}")
            uid_true = await _insert_user(raw.db, f"RevTrue {suffix}", available_for_reviewing=True)
            result = await search_people(
                raw.db, {"q": suffix, "available_for_reviewing": True}, viewer_id=None
            )
            ids = {r["id"] for r in result["results"]}
            assert uid_true in ids
            assert uid_absent not in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^Rev"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_self_exclusion_still_intact(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"SelfCheck {suffix}", available_for_collaboration=True)
            result = await search_people(
                raw.db, {"q": suffix, "available_for_collaboration": True}, viewer_id=uid
            )
            ids = {r["id"] for r in result["results"]}
            assert uid not in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^SelfCheck"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_show_in_discovery_still_intact(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"OptOutCheck {suffix}", available_for_collaboration=True)
            await raw.db.network_settings.insert_one({"user_id": uid, "show_in_discovery": False})
            result = await search_people(
                raw.db, {"q": suffix, "available_for_collaboration": True}, viewer_id=None
            )
            ids = {r["id"] for r in result["results"]}
            assert uid not in ids
        finally:
            await raw.db.network_settings.delete_many({"user_id": {"$exists": True}, "show_in_discovery": False})
            await raw.db.users.delete_many({"full_name": {"$regex": "^OptOutCheck"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_blocking_still_intact(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            viewer_id = await _insert_user(raw.db, f"Blocker {suffix}")
            blocked_id = await _insert_user(raw.db, f"Blocked {suffix}", available_for_collaboration=True)
            await raw.db.network_settings.insert_one({"user_id": viewer_id, "blocked_users": [blocked_id]})
            result = await search_people(
                raw.db, {"q": suffix, "available_for_collaboration": True}, viewer_id=viewer_id
            )
            ids = {r["id"] for r in result["results"]}
            assert blocked_id not in ids
        finally:
            await raw.db.network_settings.delete_many({"user_id": {"$exists": True}})
            await raw.db.users.delete_many({"full_name": {"$regex": "^Block"}})
            raw.close()


class TestAdminMarkDemo:
    @pytest.mark.asyncio
    async def test_mark_demo_sets_flag_and_excludes_from_discovery(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"MarkDemo {suffix}")

            async def _fake_get_db():
                return raw.db
            monkeypatch.setattr("routers.admin_users_mgmt.get_db", lambda: raw.db)
            monkeypatch.setattr("services.admin_audit.get_db", lambda: raw.db)

            admin = {"id": _oid(), "role": "super_admin", "email": "admin@synaptiq.academy"}
            out = await mark_user_demo(uid, _FakeRequest(), admin=admin)
            assert out == {"ok": True, "is_demo": True}

            doc = await raw.db.users.find_one({"_id": _parse_oid(uid)})
            assert doc["is_demo"] is True

            result = await search_people(raw.db, {"q": suffix}, viewer_id=None)
            ids = {r["id"] for r in result["results"]}
            assert uid not in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^MarkDemo"}})
            await raw.db.audit_log.delete_many({"target_email": {"$regex": "@synaptiq-test.io$"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_unmark_demo_restores_visibility(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"UnmarkDemo {suffix}", is_demo=True)
            monkeypatch.setattr("routers.admin_users_mgmt.get_db", lambda: raw.db)
            monkeypatch.setattr("services.admin_audit.get_db", lambda: raw.db)

            admin = {"id": _oid(), "role": "super_admin", "email": "admin@synaptiq.academy"}
            out = await unmark_user_demo(uid, _FakeRequest(), admin=admin)
            assert out == {"ok": True, "is_demo": False}

            doc = await raw.db.users.find_one({"_id": _parse_oid(uid)})
            assert doc["is_demo"] is False
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^UnmarkDemo"}})
            await raw.db.audit_log.delete_many({"target_email": {"$regex": "@synaptiq-test.io$"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_mark_demo_response_has_no_private_fields(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"SafeResp {suffix}")
            monkeypatch.setattr("routers.admin_users_mgmt.get_db", lambda: raw.db)
            monkeypatch.setattr("services.admin_audit.get_db", lambda: raw.db)
            admin = {"id": _oid(), "role": "super_admin", "email": "admin@synaptiq.academy"}
            out = await mark_user_demo(uid, _FakeRequest(), admin=admin)
            assert set(out.keys()) == {"ok", "is_demo"}
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^SafeResp"}})
            await raw.db.audit_log.delete_many({"target_email": {"$regex": "@synaptiq-test.io$"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_mark_demo_refuses_equal_or_higher_role_target(self, monkeypatch):
        """Hierarchy guard: an admin cannot demo-mark another admin/mod."""
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"PeerAdmin {suffix}", role="moderator")
            monkeypatch.setattr("routers.admin_users_mgmt.get_db", lambda: raw.db)
            admin = {"id": _oid(), "role": "moderator", "email": "mod@synaptiq.academy"}
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await mark_user_demo(uid, _FakeRequest(), admin=admin)
            assert exc.value.status_code == 403
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^PeerAdmin"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_mark_demo_unknown_user_404(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.admin_users_mgmt.get_db", lambda: raw.db)
            admin = {"id": _oid(), "role": "super_admin", "email": "admin@synaptiq.academy"}
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await mark_user_demo(_oid(), _FakeRequest(), admin=admin)
            assert exc.value.status_code == 404
        finally:
            raw.close()


class TestLocalProdDbGuard:
    """db.py's _assert_safe_db_target — never runs against a real connection,
    pure logic check on the three inputs it reads."""

    def _reload_guard(self):
        import importlib
        import db as db_module
        importlib.reload(db_module)
        return db_module

    def test_non_prod_uri_never_blocked(self, monkeypatch):
        db_module = self._reload_guard()
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
        monkeypatch.delenv("ALLOW_PROD_DB_LOCAL", raising=False)
        db_module._assert_safe_db_target("mongodb://localhost:27017/")  # must not raise

    def test_prod_uri_local_process_blocked(self, monkeypatch):
        db_module = self._reload_guard()
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
        monkeypatch.delenv("ALLOW_PROD_DB_LOCAL", raising=False)
        with pytest.raises(RuntimeError):
            db_module._assert_safe_db_target("mongodb+srv://u:p@synaptiq-prod.ici39nk.mongodb.net/")

    def test_prod_uri_on_railway_allowed(self, monkeypatch):
        db_module = self._reload_guard()
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        monkeypatch.delenv("ALLOW_PROD_DB_LOCAL", raising=False)
        db_module._assert_safe_db_target("mongodb+srv://u:p@synaptiq-prod.ici39nk.mongodb.net/")  # must not raise
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)

    def test_prod_uri_with_explicit_opt_in_allowed(self, monkeypatch):
        db_module = self._reload_guard()
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
        monkeypatch.setenv("ALLOW_PROD_DB_LOCAL", "1")
        db_module._assert_safe_db_target("mongodb+srv://u:p@synaptiq-prod.ici39nk.mongodb.net/")  # must not raise
        monkeypatch.delenv("ALLOW_PROD_DB_LOCAL", raising=False)
