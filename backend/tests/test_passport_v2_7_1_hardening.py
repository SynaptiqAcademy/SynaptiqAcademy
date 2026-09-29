"""Regression tests for P1 Phase 7.1 (Academic Passport post-deploy security
hardening).

Covers:
- services/trust/passport_service.py::sanitize_historical_verified_orcid()
  — idempotent migration of legacy object-shaped verified_orcid values.
- services/passport/fingerprint.py with a real configured
  PASSPORT_FINGERPRINT_SECRET (determinism, no source-identifier leakage).
- frontend ORCID-helper strictness is covered by frontend/src/lib/orcid.js's
  existing usage; here we cover the backend-observable consequences (the
  sanitization never touches users.orcid or any other collection).

No token/secret values are ever asserted against literal strings that would
need to appear in this file — only shape/type assertions.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId

from services.trust.passport_service import sanitize_historical_verified_orcid
from services.passport.fingerprint import compute_fingerprint


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
        finally:
            self.close()

    def close(self):
        self._client.close()


class TestHistoricalOrcidSanitization:
    @pytest.mark.asyncio
    async def test_object_with_valid_orcid_id_migrates_to_string(self):
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Sanitize Valid")
            await raw.db.trust_passports.insert_one({
                "user_id": uid,
                "verified_orcid": {"orcid_id": "0000-0001-2345-6789", "access_token": {"ciphertext": "x"}},
            })
            result = await sanitize_historical_verified_orcid(raw.db)
            assert result["migrated_to_string"] >= 1
            assert result["remaining_object_type_after"] == 0

            doc = await raw.db.trust_passports.find_one({"user_id": uid})
            assert doc["verified_orcid"] == "0000-0001-2345-6789"
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_object_without_valid_orcid_id_becomes_null(self):
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Sanitize Invalid")
            await raw.db.trust_passports.insert_one({
                "user_id": uid,
                "verified_orcid": {"access_token": {"ciphertext": "x"}},  # no orcid_id at all
            })
            result = await sanitize_historical_verified_orcid(raw.db)
            assert result["nulled_no_valid_id"] >= 1

            doc = await raw.db.trust_passports.find_one({"user_id": uid})
            assert doc["verified_orcid"] is None
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_malformed_orcid_id_format_also_becomes_null(self):
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Sanitize Malformed")
            await raw.db.trust_passports.insert_one({
                "user_id": uid,
                "verified_orcid": {"orcid_id": "not-a-real-orcid-id"},
            })
            await sanitize_historical_verified_orcid(raw.db)
            doc = await raw.db.trust_passports.find_one({"user_id": uid})
            assert doc["verified_orcid"] is None
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_idempotent_second_run_is_a_noop(self):
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Sanitize Idempotent")
            await raw.db.trust_passports.insert_one({
                "user_id": uid,
                "verified_orcid": {"orcid_id": "0000-0001-2345-6789"},
            })
            first = await sanitize_historical_verified_orcid(raw.db)
            second = await sanitize_historical_verified_orcid(raw.db)
            assert first["migrated_to_string"] >= 1
            assert second["documents_found_as_object"] == 0
            assert second["migrated_to_string"] == 0
            assert second["nulled_no_valid_id"] == 0
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_string_and_null_verified_orcid_untouched(self):
        raw = _RawDB()
        try:
            uid_str = await raw.insert_user("Sanitize AlreadyString", )
            uid_null = await raw.insert_user("Sanitize AlreadyNull")
            await raw.db.trust_passports.insert_one({"user_id": uid_str, "verified_orcid": "0000-0001-2345-6789"})
            await raw.db.trust_passports.insert_one({"user_id": uid_null, "verified_orcid": None})
            await sanitize_historical_verified_orcid(raw.db)
            d1 = await raw.db.trust_passports.find_one({"user_id": uid_str})
            d2 = await raw.db.trust_passports.find_one({"user_id": uid_null})
            assert d1["verified_orcid"] == "0000-0001-2345-6789"
            assert d2["verified_orcid"] is None
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_migration_never_touches_users_collection(self):
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Sanitize No Users Touch", orcid={"orcid_id": "0000-0001-2345-6789", "access_token": "enc"})
            await raw.db.trust_passports.insert_one({
                "user_id": uid,
                "verified_orcid": {"orcid_id": "0000-0001-2345-6789", "access_token": "enc"},
            })
            before = await raw.db.users.find_one({"_id": ObjectId(uid)})
            await sanitize_historical_verified_orcid(raw.db)
            after = await raw.db.users.find_one({"_id": ObjectId(uid)})
            assert before == after
        finally:
            await raw.cleanup()


class TestFingerprintWithConfiguredSecret:
    def test_deterministic_with_current_production_secret(self):
        """Uses whatever PASSPORT_FINGERPRINT_SECRET is actually configured
        in this environment (falls back gracefully if unset locally) —
        proves determinism holds regardless of which secret is active."""
        uid = str(ObjectId())
        a = compute_fingerprint(uid)
        b = compute_fingerprint(uid)
        assert a == b
        assert a["full"]
        assert a["display"].startswith("SYN")

    def test_fingerprint_output_never_contains_secret_or_user_id(self):
        uid = str(ObjectId())
        secret = os.environ.get("PASSPORT_FINGERPRINT_SECRET", "")
        fp = compute_fingerprint(uid)
        blob = fp["full"] + fp["display"]
        assert uid not in blob
        if secret:
            assert secret not in blob
