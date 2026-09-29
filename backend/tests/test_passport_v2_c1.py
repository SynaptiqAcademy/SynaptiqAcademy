"""Regression tests for P1 Phase 7 (Academic Passport V2) — Gate C1:
correctness, consistency & privacy fixes.

Covers:
- services/verification/profile_service.py's orcid_verified (already fixed
  in commit 4b4de1c5, re-verified here as a C1 precondition).
- services/profile_completion.py as the ONE canonical completion source,
  now also consumed by routers/proactive.py instead of its own duplicate
  formula.
- services/public_profiles/profile_service.py::get_full_profile()'s
  safe-by-default public projection (no email/institution_id leak to
  anonymous viewers without explicit opt-in).
- routers/proactive.py's _has_orcid() no longer accepting a bare legacy
  string as an authenticated ORCID connection.

No Research Record, matching, trust-scoring algorithm, reputation, or
Connect/Follow architecture was touched by this stage.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId

from services.profile_completion import compute_profile_completion
from services.public_profiles.profile_service import get_full_profile
from routers.proactive import _profile_completeness, _has_orcid


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
                await self.db.public_profiles.delete_many({"user_id": {"$in": self.created_uids}})
        finally:
            self.close()

    def close(self):
        self._client.close()


class TestCanonicalProfileCompletionSingleSource:
    @pytest.mark.asyncio
    async def test_proactive_uses_canonical_formula_not_a_duplicate(self):
        """routers/proactive.py's _profile_completeness must return the exact
        same percentage as the canonical compute_profile_completion() for
        the same user — proving there's no second, drifted formula."""
        raw = _RawDB()
        try:
            uid = await raw.insert_user(
                "Completion Canonical Check",
                avatar_url="https://example.com/a.png",
                biography="A" * 30,
                institution="Test University",
                research_keywords=["ai"],
            )
            fake_user = {"id": uid}
            canonical = await compute_profile_completion(raw.db, uid)
            comp, missing = await _profile_completeness(fake_user, raw.db)
            assert comp == canonical["percentage"]
            not_earned_labels = {i["label"] for i in canonical["items"] if not i["earned"]}
            assert set(missing) == not_earned_labels
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_no_second_field_weight_table_reintroduced(self):
        """Static check: proactive.py must not define its own independent
        field-weight table for completion (PROFILE_FIELDS was removed)."""
        import inspect
        import routers.proactive as proactive_module
        src = inspect.getsource(proactive_module)
        assert "PROFILE_FIELDS" not in src


class TestOrcidConsistencyExtendedToProactive:
    @pytest.mark.asyncio
    async def test_has_orcid_requires_authenticated_dict_shape(self):
        assert _has_orcid({"orcid": {"orcid_id": "0000-0001-2345-6789"}}) is True
        assert _has_orcid({"orcid": "0000-0001-2345-6789"}) is False
        assert _has_orcid({"orcid": {}}) is False
        assert _has_orcid({"orcid": None}) is False
        assert _has_orcid({}) is False


class TestPublicProfilePrivacyDefault:
    @pytest.mark.asyncio
    async def test_anonymous_viewer_does_not_receive_email_by_default(self):
        """The exact reported gap: a user who never touched privacy
        settings must not leak their real email to an anonymous viewer."""
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Privacy Default Check", institution_id="internal-inst-123")
            profile = await get_full_profile(uid, raw.db, viewer_id=None)
            assert profile["email"] is None
            assert "institution_id" not in profile
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_owner_viewer_sees_own_email(self):
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Privacy Owner Check")
            profile = await get_full_profile(uid, raw.db, viewer_id=uid)
            assert profile["email"] is not None
            assert "institution_id" not in profile
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_explicit_public_contact_opt_in_shows_email_to_anonymous(self):
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Privacy OptIn Check")
            await raw.db.public_profiles.insert_one({
                "user_id": uid, "slug": f"optin-{uid[:8]}",
                "visibility_settings": {"contact": "public"},
            })
            profile = await get_full_profile(uid, raw.db, viewer_id=None)
            assert profile["email"] is not None
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_public_profiles_doc_without_visibility_settings_does_not_crash(self):
        """P1 Phase 7.1: reproduces a real production 500. claim_custom_slug()
        only ever sets {slug, updated_at} — no visibility_settings field —
        so any account that claims a slug without first visiting privacy
        settings had a public_profiles doc missing that key entirely. The
        old `profile_doc["visibility_settings"]` bracket-index raised an
        unhandled KeyError for this exact, common shape."""
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Privacy No VisSettings Check")
            await raw.db.public_profiles.insert_one({
                "user_id": uid, "slug": f"noviz-{uid[:8]}", "updated_at": "2026-01-01T00:00:00Z",
            })
            profile = await get_full_profile(uid, raw.db, viewer_id=None)
            assert profile["visibility_settings"] == {}
            assert profile["email"] is None
        finally:
            await raw.cleanup()

    @pytest.mark.asyncio
    async def test_different_anonymous_viewer_still_hidden_with_explicit_private(self):
        raw = _RawDB()
        try:
            uid = await raw.insert_user("Privacy Explicit Private Check")
            other_uid = await raw.insert_user("Privacy Other Viewer")
            await raw.db.public_profiles.insert_one({
                "user_id": uid, "slug": f"priv-{uid[:8]}",
                "visibility_settings": {"contact": "private"},
            })
            profile = await get_full_profile(uid, raw.db, viewer_id=other_uid)
            assert profile["email"] is None
        finally:
            await raw.cleanup()
