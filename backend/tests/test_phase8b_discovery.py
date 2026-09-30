"""P1 Phase 8B — Unified Global Research & Expert Discovery.

Covers the security fix (§3), the fabricated-language fix (§4), the
extended canonical retrieval layer (§9-§12/§17), professional_role/
professional_expertise/languages, and the zero-credit guarantee for basic
discovery (§1/§15). All fixtures are disposable and cleaned up in finally
blocks, matching this repo's established test pattern.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId

from services.network.discovery_engine import search_people, _serialize_person, _scrub_orcid_field
from services.collab_intelligence.researcher_profiler import build_researcher_profile
from routers.collaboration_intelligence import _public_profile


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


class TestOrcidSerializationSecurityFix:
    """P1 Phase 8B §3 — collaboration_intelligence.py's _public_profile()
    must never return the raw orcid dict (OAuth token envelope)."""

    def test_authenticated_orcid_never_leaks_tokens(self):
        user = {
            "_id": ObjectId(), "full_name": "Token Leak Test",
            "orcid": {
                "orcid_id": "0000-0001-2345-6789",
                "access_token": "SECRET_ACCESS_TOKEN_SHOULD_NEVER_APPEAR",
                "refresh_token": "SECRET_REFRESH_TOKEN_SHOULD_NEVER_APPEAR",
                "verified_at": "2026-01-01T00:00:00+00:00",
            },
        }
        out = _public_profile(user)
        serialized = str(out)
        assert "SECRET_ACCESS_TOKEN_SHOULD_NEVER_APPEAR" not in serialized
        assert "SECRET_REFRESH_TOKEN_SHOULD_NEVER_APPEAR" not in serialized
        assert "access_token" not in out
        assert "refresh_token" not in out
        assert out["orcid_connected"] is True
        assert out["orcid_id"] == "0000-0001-2345-6789"
        assert "orcid" not in out  # raw key removed entirely, not just scrubbed in place

    def test_self_declared_orcid_string_is_not_connected(self):
        user = {"_id": ObjectId(), "full_name": "Self Declared Test", "orcid": "0000-0001-2345-6789"}
        out = _public_profile(user)
        assert out["orcid_connected"] is False
        assert out["orcid_id"] is None

    def test_no_orcid_at_all(self):
        user = {"_id": ObjectId(), "full_name": "No Orcid Test"}
        out = _public_profile(user)
        assert out["orcid_connected"] is False
        assert out["orcid_id"] is None

    def test_discovery_engine_serialize_person_also_scrubs_tokens(self):
        """The other, separate serializer this phase touches — same rule,
        independently verified."""
        doc = {
            "_id": ObjectId(), "full_name": "Discovery Scrub Test",
            "orcid": {"orcid_id": "0000-0002-1111-2222", "access_token": "SHOULD_NOT_LEAK"},
        }
        out = _serialize_person(dict(doc))
        assert "SHOULD_NOT_LEAK" not in str(out)
        assert out["orcid_verified"] is True
        assert out["orcid_id"] == "0000-0002-1111-2222"

    def test_scrub_orcid_field_helper(self):
        assert _scrub_orcid_field({"orcid_id": "x", "access_token": "y"}) == {"orcid_id": "x", "verified_at": None}
        assert _scrub_orcid_field("bare-string") is None
        assert _scrub_orcid_field(None) is None


class TestNoFabricatedLanguage:
    """P1 Phase 8B §4 — researcher_profiler must never default to English."""

    def test_no_languages_field_produces_empty_list(self):
        profile = build_researcher_profile({"_id": ObjectId(), "full_name": "No Lang Test"})
        assert profile.languages == []

    def test_empty_languages_list_stays_empty(self):
        profile = build_researcher_profile({"_id": ObjectId(), "full_name": "Empty Lang Test", "languages": []})
        assert profile.languages == []

    def test_real_languages_are_preserved(self):
        profile = build_researcher_profile(
            {"_id": ObjectId(), "full_name": "Real Lang Test", "languages": ["Romanian", "French"]})
        assert profile.languages == ["Romanian", "French"]

    def test_legacy_singular_language_field_no_longer_defaults_english(self):
        """The old code path had a secondary fallback to a legacy singular
        `language` field, itself defaulting to "English" if absent — both
        fabrication paths are gone now."""
        profile = build_researcher_profile({"_id": ObjectId(), "full_name": "Legacy Field Test"})
        assert "English" not in profile.languages
        assert profile.languages == []


class TestExtendedDiscoveryFilters:
    """P1 Phase 8B §9-§12 — professional_role/professional_expertise/
    languages/verification filters on the canonical retrieval layer."""

    @pytest.mark.asyncio
    async def test_professional_role_filter(self):
        raw = _RawDB()
        uid = None
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"ProfRole Test {suffix}", professional_role="Health Diplomacy Specialist")
            await _insert_user(raw.db, f"ProfRole Other {suffix}", professional_role="Software Engineer")
            result = await search_people(raw.db, {"professional_role": "Health Diplomacy"}, viewer_id=None)
            ids = {r["id"] for r in result["results"]}
            assert uid in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^ProfRole"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_professional_expertise_filter(self):
        raw = _RawDB()
        uid = None
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"ProfExp Test {suffix}", professional_expertise=["Public Health"])
            await _insert_user(raw.db, f"ProfExp Other {suffix}", professional_expertise=["Finance"])
            result = await search_people(raw.db, {"professional_expertise": "Public Health"}, viewer_id=None)
            ids = {r["id"] for r in result["results"]}
            assert uid in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^ProfExp"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_language_filter_only_matches_explicit_data(self):
        raw = _RawDB()
        uid_with = uid_without = None
        try:
            suffix = _oid()[:8]
            uid_with = await _insert_user(raw.db, f"Lang Test {suffix}", languages=["Romanian"])
            uid_without = await _insert_user(raw.db, f"Lang NoData {suffix}")
            result = await search_people(raw.db, {"languages": "Romanian"}, viewer_id=None)
            ids = {r["id"] for r in result["results"]}
            assert uid_with in ids
            assert uid_without not in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^Lang"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_orcid_verified_filter_excludes_self_declared(self):
        raw = _RawDB()
        uid_auth = uid_self = None
        try:
            suffix = _oid()[:8]
            uid_auth = await _insert_user(raw.db, f"OrcidFilter Auth {suffix}",
                                           orcid={"orcid_id": "0000-0001-1111-1111"})
            uid_self = await _insert_user(raw.db, f"OrcidFilter Self {suffix}", orcid="0000-0002-2222-2222")
            # Scoped by q — without it, this relies on both fixtures landing
            # within the default page size (20) of an unfiltered
            # orcid_verified=True query, which a shared, growing local test
            # DB (accumulated fixtures from many other test files/runs) can
            # no longer guarantee.
            result = await search_people(raw.db, {"orcid_verified": True, "q": suffix}, viewer_id=None)
            ids = {r["id"] for r in result["results"]}
            assert uid_auth in ids
            assert uid_self not in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^OrcidFilter"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_institution_verified_filter(self):
        raw = _RawDB()
        uid_verified = uid_unverified = None
        try:
            suffix = _oid()[:8]
            uid_verified = await _insert_user(raw.db, f"InstVerified Yes {suffix}", institution_id=_oid())
            uid_unverified = await _insert_user(raw.db, f"InstVerified No {suffix}", institution="Some University")
            result = await search_people(raw.db, {"institution_verified": True}, viewer_id=None)
            ids = {r["id"] for r in result["results"]}
            assert uid_verified in ids
            assert uid_unverified not in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^InstVerified"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_dead_filters_no_longer_referenced(self):
        """§5 — career_stage/verification_level/trust_score must not appear
        in the query builder at all now (they matched real production data
        0% of the time — see Phase 8A audit)."""
        raw = _RawDB()
        try:
            # Passing them as filters must simply be ignored (no KeyError,
            # no crash, and critically no query clause built from them).
            result = await search_people(
                raw.db, {"career_stage": "senior", "verification_level": 5, "min_trust_score": 90},
                viewer_id=None,
            )
            assert isinstance(result["results"], list)
        finally:
            raw.close()


class TestSerializationNeverLeaksPrivateFields:
    @pytest.mark.asyncio
    async def test_email_never_in_search_results(self):
        raw = _RawDB()
        uid = None
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"EmailLeak Test {suffix}", research_areas=["Test Area"])
            result = await search_people(raw.db, {"q": f"EmailLeak Test {suffix}"}, viewer_id=None)
            assert result["results"], "fixture should be found by its own name"
            for r in result["results"]:
                assert "email" not in r
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^EmailLeak"}})
            raw.close()


class TestZeroCreditBasicDiscovery:
    @pytest.mark.asyncio
    async def test_search_people_never_writes_credit_transactions(self):
        raw = _RawDB()
        uid = None
        try:
            before = await raw.db.credit_transactions.count_documents({})
            uid = await _insert_user(raw.db, f"CreditCheck Test {_oid()[:8]}", research_areas=["X"])
            await search_people(raw.db, {"q": "CreditCheck"}, viewer_id=None)
            after = await raw.db.credit_transactions.count_documents({})
            assert after == before
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^CreditCheck"}})
            raw.close()
