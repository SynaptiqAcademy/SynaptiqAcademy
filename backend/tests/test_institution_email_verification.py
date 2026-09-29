"""P1 Phase 7C4.4 §D Method 1 — institutional email verification.

Covers the confirm endpoint's DB effects directly (token→membership→
verification_profile), since it has no rate-limit decorator or auth
dependency (the signed JWT is the credential) and is safely callable as a
plain function. The domain-trust check and rate limiting in
start_institution_email_verification are exercised in production QA instead
(that handler is wrapped in @limiter.limit, which needs a live Request/
slowapi context this suite doesn't set up).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from routers.institutions import (
    _make_institution_email_token, confirm_institution_email_verification, router as institutions_router,
)


def test_verify_email_start_route_recognizes_body_param():
    """Regression guard: this router has `from __future__ import annotations`
    active, and combining a rate-limit decorator (@limiter.limit) with a
    locally-defined Pydantic BaseModel parameter silently broke FastAPI's
    body-param resolution — every real request 400'd with a spurious
    "query.payload Field required" error, confirmed live in production QA.
    Fixed by using an explicit Body(..., embed=True) str field instead of a
    model class. This checks the route's dependant actually has the body
    param FastAPI needs, so this exact class of bug can't silently return."""
    for r in institutions_router.routes:
        if "verify-email/start" in r.path:
            names = [p.name for p in r.dependant.body_params]
            assert "email" in names, f"body_params={r.dependant.body_params!r}"
            return
    pytest.fail("verify-email/start route not found")


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
    doc = {"full_name": "Institution Verify Test User",
           "email": f"instverify-{_oid()}@synaptiq-test.io",
           "email_verified": True, **extra}
    res = await db.users.insert_one(doc)
    return str(res.inserted_id)


async def _insert_institution(db, **extra) -> str:
    doc = {"name": "Test University", "email_domains": ["test-university.example"], **extra}
    res = await db.institutions.insert_one(doc)
    return str(res.inserted_id)


@pytest.mark.asyncio
async def test_confirm_creates_approved_membership_and_verifies_institution():
    from db import get_db
    import server  # noqa: F401 — ensures app/db lifecycle is initialised the same as other suites
    raw = _RawDB()
    uid = iid = None
    try:
        uid = await _insert_user(raw.db)
        iid = await _insert_institution(raw.db)
        email = "researcher@test-university.example"
        token, jti = _make_institution_email_token(uid, iid, email)
        await raw.db.institution_email_verifications.insert_one({
            "user_id": uid, "institution_id": iid, "email": email, "jti": jti,
            "used": False, "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
        })

        resp = await confirm_institution_email_verification(token=token)
        assert resp.status_code in (302, 307)
        assert "institution=verified" in resp.headers["location"]

        membership = await raw.db.institution_memberships.find_one({"institution_id": iid, "user_id": uid})
        assert membership is not None
        assert membership["status"] == "approved"
        assert membership["verified_via"] == "institutional_email"
        assert membership["verified_email"] == email

        user = await raw.db.users.find_one({"_id": ObjectId(uid)})
        assert user["institution_id"] == iid
        assert user["institution"] == "Test University"

        record = await raw.db.institution_email_verifications.find_one({"user_id": uid, "jti": jti})
        assert record["used"] is True

        from services.verification.profile_service import compute_verification_profile
        profile = await compute_verification_profile(uid, raw.db)
        assert profile["institution_verified"] is True
    finally:
        if uid:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.institution_memberships.delete_many({"user_id": uid})
            await raw.db.institution_email_verifications.delete_many({"user_id": uid})
            await raw.db.institution_audit.delete_many({"actor_id": uid})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
        if iid:
            await raw.db.institutions.delete_one({"_id": ObjectId(iid)})
        raw.close()


@pytest.mark.asyncio
async def test_confirm_rejects_reused_token():
    raw = _RawDB()
    uid = iid = None
    try:
        uid = await _insert_user(raw.db)
        iid = await _insert_institution(raw.db)
        email = "researcher@test-university.example"
        token, jti = _make_institution_email_token(uid, iid, email)
        await raw.db.institution_email_verifications.insert_one({
            "user_id": uid, "institution_id": iid, "email": email, "jti": jti,
            "used": True, "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
        })

        resp = await confirm_institution_email_verification(token=token)
        assert "institution_error=already_used" in resp.headers["location"]

        membership = await raw.db.institution_memberships.find_one({"institution_id": iid, "user_id": uid})
        assert membership is None
    finally:
        if uid:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.institution_memberships.delete_many({"user_id": uid})
            await raw.db.institution_email_verifications.delete_many({"user_id": uid})
        if iid:
            await raw.db.institutions.delete_one({"_id": ObjectId(iid)})
        raw.close()


@pytest.mark.asyncio
async def test_confirm_rejects_garbage_token():
    resp = await confirm_institution_email_verification(token="not-a-real-token")
    assert "institution_error=invalid_token" in resp.headers["location"]


@pytest.mark.asyncio
async def test_confirm_rejects_expired_token():
    raw = _RawDB()
    uid = iid = None
    try:
        uid = await _insert_user(raw.db)
        iid = await _insert_institution(raw.db)
        import jwt as pyjwt
        from auth_utils import JWT_ALGORITHM
        expired_payload = {
            "sub": uid, "jti": _oid(), "type": "institution_email_verification",
            "institution_id": iid, "email": "researcher@test-university.example",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        }
        token = pyjwt.encode(expired_payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)
        resp = await confirm_institution_email_verification(token=token)
        assert "institution_error=expired" in resp.headers["location"]
    finally:
        if uid:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
        if iid:
            await raw.db.institutions.delete_one({"_id": ObjectId(iid)})
        raw.close()


@pytest.mark.asyncio
async def test_confirm_does_not_touch_login_email():
    """Spec: 'Do not replace the user's primary account email unless
    explicitly requested.' The verified institutional email is a separate
    record, never written to users.email."""
    raw = _RawDB()
    uid = iid = None
    try:
        uid = await _insert_user(raw.db, email="original-login-email@example.com")
        iid = await _insert_institution(raw.db)
        email = "researcher@test-university.example"
        token, jti = _make_institution_email_token(uid, iid, email)
        await raw.db.institution_email_verifications.insert_one({
            "user_id": uid, "institution_id": iid, "email": email, "jti": jti,
            "used": False, "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
        })
        await confirm_institution_email_verification(token=token)
        user = await raw.db.users.find_one({"_id": ObjectId(uid)})
        assert user["email"] == "original-login-email@example.com"
    finally:
        if uid:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.institution_memberships.delete_many({"user_id": uid})
            await raw.db.institution_email_verifications.delete_many({"user_id": uid})
            await raw.db.institution_audit.delete_many({"actor_id": uid})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
        if iid:
            await raw.db.institutions.delete_one({"_id": ObjectId(iid)})
        raw.close()
