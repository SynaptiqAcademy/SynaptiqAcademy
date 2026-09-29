"""Regression tests for P1 Phase 7 C3's changes to
services/trust/passport_service.py::build_passport() — Academic Fingerprint
inclusion, and the discovered verified_orcid token-leak fix.

No trust-scoring algorithm was touched — trust_score/trust_level values
themselves are read as-is from trust_scores; only the fingerprint field and
verified_orcid's shape changed.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId

from services.trust.passport_service import build_passport


class _RawDB:
    def __init__(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        self._client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
        self.db = self._client[os.environ["MONGODB_DB_NAME"]]
        self.created_uids: list[str] = []

    async def insert_user(self, full_name: str, **extra) -> str:
        doc = {
            "full_name": full_name,
            "email": f"{full_name.lower().replace(' ', '')}-{str(ObjectId())[:8]}@synaptiq-test.io",
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
                await self.db.trust_passports.delete_many({"user_id": {"$in": self.created_uids}})
                await self.db.trust_verifications.delete_many({"user_id": {"$in": self.created_uids}})
                await self.db.trust_badges.delete_many({"user_id": {"$in": self.created_uids}})
        finally:
            self.close()

    def close(self):
        self._client.close()


class TestBuildPassportIncludesFingerprint:
    @pytest.mark.asyncio
    async def test_passport_includes_academic_fingerprint(self):
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Passport Fingerprint Check")
            passport = await build_passport(uid, raw.db)
            assert "academic_fingerprint" in passport
            assert passport["academic_fingerprint"]["full"]
            assert passport["academic_fingerprint"]["display"].startswith("SYN")
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_fingerprint_is_stable_across_repeated_builds(self):
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Passport Fingerprint Stable")
            p1 = await build_passport(uid, raw.db)
            p2 = await build_passport(uid, raw.db)
            assert p1["academic_fingerprint"] == p2["academic_fingerprint"]
        finally:
            await raw.cleanup()


class TestVerifiedOrcidNoLongerLeaksTokens:
    @pytest.mark.asyncio
    async def test_verified_orcid_is_plain_id_not_raw_dict(self):
        raw = _RawDB()
        try:
            uid = await raw.insert_user(
                "Passport Orcid Safety Check",
                orcid={
                    "orcid_id": "0000-0001-2345-6789",
                    "access_token": {"ciphertext": "should-never-appear", "iv": "x", "tag": "y"},
                    "refresh_token": {"ciphertext": "should-never-appear-either", "iv": "x", "tag": "y"},
                    "verified_at": "2026-01-01T00:00:00Z",
                },
            )
            await raw.db.trust_verifications.insert_one({
                "user_id": uid, "verification_type": "orcid", "status": "verified",
            })
            passport = await build_passport(uid, raw.db)
            assert passport["verified_orcid"] == "0000-0001-2345-6789"
            assert "should-never-appear" not in str(passport)
            assert "access_token" not in str(passport["verified_orcid"])
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_unverified_orcid_stays_none(self):
        raw = _RawDB()
        try:
            uid = await raw.insert_user(
                "Passport Orcid Unverified Check",
                orcid={"orcid_id": "0000-0001-2345-6789", "access_token": {}},
            )
            passport = await build_passport(uid, raw.db)
            assert passport["verified_orcid"] is None
        finally:
            await raw.cleanup()
