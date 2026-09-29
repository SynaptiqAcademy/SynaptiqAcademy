"""Regression tests for the ORCID status inconsistency fix.

Root cause: services/verification/profile_service.py's orcid_verified
computation treated ANY non-empty users.orcid value — a real OAuth-
authenticated dict ({orcid_id, access_token, verified_at, ...}, written by
routers/orcid.py's /callback) OR a bare, never-authenticated string (legacy
data / seed accounts) — as "verified". Every other consumer in the codebase
(GET /api/orcid/status, services/profile_completion.py, routers/citations.py,
routers/users.py) already correctly required the dict shape with a real
orcid_id. This meant an account holding only a string ORCID value showed
"ORCID Connected" / "ORCID Connection: Verified" on the Academic Passport and
Verification Center (driven by verification_profiles.orcid_verified), while
the Research Integrations / OrcidSettings card (driven by the canonical
GET /api/orcid/status) correctly showed "not connected" — the exact
contradiction reported.

Fix: orcid_verified now requires isinstance(users.orcid, dict) and a truthy
orcid_id, matching the canonical check everywhere else. No Research Record,
publication sync, DOI system, trust_passports/trust_verifications, or
reputation/matching/AI-credit/Connect architecture was touched.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId

from services.verification.profile_service import compute_verification_profile


class _RawDB:
    def __init__(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        self._client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
        self.db = self._client[os.environ["MONGODB_DB_NAME"]]
        self.created_uids: list[str] = []

    async def insert_user(self, full_name: str, orcid, **extra) -> str:
        doc = {
            "full_name": full_name,
            "email": f"{full_name.lower().replace(' ', '')}-{str(ObjectId())[:8]}@synaptiq-test.io",
            "orcid": orcid,
            "is_demo": False,
            **extra,
        }
        res = await self.db.users.insert_one(doc)
        uid = str(res.inserted_id)
        self.created_uids.append(uid)
        return uid

    async def cleanup(self):
        try:
            if self.created_uids:
                oids = [ObjectId(u) for u in self.created_uids]
                await self.db.users.delete_many({"_id": {"$in": oids}})
                await self.db.verification_profiles.delete_many({"user_id": {"$in": self.created_uids}})
                await self.db.verification_history.delete_many({"user_id": {"$in": self.created_uids}})
                await self.db.verification_audits.delete_many({"user_id": {"$in": self.created_uids}})
                await self.db.verification_badges.delete_many({"user_id": {"$in": self.created_uids}})
        finally:
            self.close()

    def close(self):
        self._client.close()


class TestOrcidVerifiedRequiresAuthenticatedConnection:
    @pytest.mark.asyncio
    async def test_dict_shape_with_orcid_id_is_verified(self):
        """Real OAuth connection (the shape routers/orcid.py persists) —
        Career/Passport/Verification must all agree this is connected."""
        raw = _RawDB()
        try:
            uid = await raw.insert_user(
                "Orcid Dict Connected",
                orcid={"orcid_id": "0000-0001-2345-6789", "access_token": "enc", "verified_at": "2026-01-01T00:00:00Z"},
            )
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["orcid_verified"] is True
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_bare_string_orcid_is_not_verified(self):
        """The exact bug case: a never-authenticated, self-reported ORCID
        string must NOT be treated as a verified/connected state."""
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Orcid String Legacy", orcid="0000-0001-2345-6789")
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["orcid_verified"] is False
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_dict_without_orcid_id_is_not_verified(self):
        """A malformed/partial orcid dict (no orcid_id yet) must not verify."""
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Orcid Dict Incomplete", orcid={"access_token": "enc"})
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["orcid_verified"] is False
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_absent_orcid_is_not_verified(self):
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Orcid Absent", orcid=None)
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["orcid_verified"] is False
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_empty_string_orcid_is_not_verified(self):
        """The signup-default placeholder (routers/auth.py sets orcid: "")
        must not verify — this was already correctly false before the fix,
        confirming the fix doesn't change never-connected behavior."""
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Orcid Empty Default", orcid="")
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["orcid_verified"] is False
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_orcid_verified_matches_canonical_status_endpoint_semantics(self):
        """orcid_verified must agree with the same dict+orcid_id rule that
        GET /api/orcid/status (routers/orcid.py) already canonically uses —
        this is the actual cross-consumer consistency the bug violated."""
        raw = _RawDB()
        try:
            cases = [
                ("Orcid Match A", {"orcid_id": "0000-0001-2345-6789"}, True),
                ("Orcid Match B", "0000-0001-2345-6789", False),
                ("Orcid Match C", {}, False),
                ("Orcid Match D", None, False),
            ]
            for name, orcid_value, expected in cases:
                uid = await raw.insert_user(name, orcid=orcid_value)
                profile = await compute_verification_profile(uid, raw.db)

                # Same rule GET /api/orcid/status applies (routers/orcid.py):
                # orcid = orcid_value if isinstance(orcid_value, dict) else {}
                # connected = bool(orcid.get("orcid_id"))
                canonical_orcid = orcid_value if isinstance(orcid_value, dict) else {}
                canonical_connected = bool(canonical_orcid.get("orcid_id"))

                assert profile["orcid_verified"] == canonical_connected == expected, name
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_identity_verified_no_longer_falsely_triggered_by_bare_orcid_string(self):
        """identity_verified = email_verified and (institution_verified or
        orcid_verified) — a bare ORCID string alone must not be enough to
        flip identity_verified true either (it was, via the same bug)."""
        raw = _RawDB()
        try:
            uid = await raw.insert_user(
                "Orcid Identity Check", orcid="0000-0001-2345-6789", email_verified=True,
            )
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["orcid_verified"] is False
            assert profile["identity_verified"] is False
        finally:
            await raw.cleanup()
