"""P1 Phase 7C4.4 §E — GET /api/verification/me/institution-status.

Read-only aggregation over the real institution-verification state (no new
verification model — see routers/verification.py's docstring on this
endpoint). Callable directly: its Depends() are just default-value markers,
so passing user/db explicitly bypasses FastAPI's DI cleanly, matching this
suite's established pattern for other router-level tests.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId

from routers.verification import get_my_institution_status


def _oid() -> str:
    return str(ObjectId())


class _RawDB:
    def __init__(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        self._client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
        self.db = self._client[os.environ["MONGODB_DB_NAME"]]

    def close(self):
        self._client.close()


async def _insert_user(db, **extra) -> str:
    doc = {"full_name": "Institution Status Test User",
           "email": f"inststatus-{_oid()}@synaptiq-test.io",
           "email_verified": True, **extra}
    res = await db.users.insert_one(doc)
    return str(res.inserted_id)


@pytest.mark.asyncio
async def test_no_state_is_not_verified():
    raw = _RawDB()
    uid = None
    try:
        uid = await _insert_user(raw.db, institution="Some University")
        result = await get_my_institution_status(user={"id": uid}, db=raw.db)
        assert result["state"] == "not_verified"
        assert result["institution_name"] == "Some University"
    finally:
        if uid:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
        raw.close()


@pytest.mark.asyncio
async def test_approved_membership_is_verified():
    raw = _RawDB()
    uid = iid = None
    try:
        iid = _oid()
        await raw.db.institutions.insert_one({"_id": ObjectId(iid), "name": "Verified University"})
        uid = await _insert_user(raw.db, institution="Verified University", institution_id=iid)
        await raw.db.institution_memberships.insert_one({
            "institution_id": iid, "user_id": uid, "status": "approved",
            "verified_via": "institutional_email", "joined_at": "2026-01-01T00:00:00+00:00",
        })
        result = await get_my_institution_status(user={"id": uid}, db=raw.db)
        assert result["state"] == "verified"
        assert result["institution_name"] == "Verified University"
        assert result["verified_via"] == "institutional_email"
    finally:
        if uid:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.institution_memberships.delete_many({"user_id": uid})
        if iid:
            await raw.db.institutions.delete_one({"_id": ObjectId(iid)})
        raw.close()


@pytest.mark.asyncio
async def test_pending_membership_is_in_progress():
    raw = _RawDB()
    uid = iid = None
    try:
        iid = _oid()
        await raw.db.institutions.insert_one({"_id": ObjectId(iid), "name": "Pending University"})
        uid = await _insert_user(raw.db)
        await raw.db.institution_memberships.insert_one({
            "institution_id": iid, "user_id": uid, "status": "pending", "joined_at": "2026-01-01T00:00:00+00:00",
        })
        result = await get_my_institution_status(user={"id": uid}, db=raw.db)
        assert result["state"] == "in_progress"
        assert result["institution_name"] == "Pending University"
    finally:
        if uid:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.institution_memberships.delete_many({"user_id": uid})
        if iid:
            await raw.db.institutions.delete_one({"_id": ObjectId(iid)})
        raw.close()


@pytest.mark.asyncio
async def test_denied_membership_is_rejected():
    raw = _RawDB()
    uid = iid = None
    try:
        iid = _oid()
        await raw.db.institutions.insert_one({"_id": ObjectId(iid), "name": "Denied University"})
        uid = await _insert_user(raw.db)
        await raw.db.institution_memberships.insert_one({
            "institution_id": iid, "user_id": uid, "status": "denied",
            "joined_at": "2026-01-01T00:00:00+00:00", "decided_at": "2026-01-02T00:00:00+00:00",
        })
        result = await get_my_institution_status(user={"id": uid}, db=raw.db)
        assert result["state"] == "rejected"
    finally:
        if uid:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.institution_memberships.delete_many({"user_id": uid})
        if iid:
            await raw.db.institutions.delete_one({"_id": ObjectId(iid)})
        raw.close()


@pytest.mark.asyncio
async def test_pending_legacy_verification_request_is_in_progress():
    raw = _RawDB()
    uid = None
    try:
        uid = await _insert_user(raw.db)
        await raw.db.verification_requests.insert_one({
            "user_id": uid, "request_type": "institution", "status": "pending",
            "details": {"institution_name": "Not Yet Catalogued University"},
            "created_at": "2026-01-01T00:00:00+00:00",
        })
        result = await get_my_institution_status(user={"id": uid}, db=raw.db)
        assert result["state"] == "in_progress"
        assert result["institution_name"] == "Not Yet Catalogued University"
    finally:
        if uid:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.verification_requests.delete_many({"user_id": uid})
        raw.close()
