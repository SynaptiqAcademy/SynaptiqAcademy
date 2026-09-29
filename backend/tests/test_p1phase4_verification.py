"""Regression tests for the P1 Phase 4 (Verification System) audit fixes.

Covers: GET /api/verification/me now recomputes instead of returning a
frozen default; the recompute is idempotent (no write when nothing
changed); identity_verified's composite rule is unchanged; and Expertise
verification's publication count now derives from the canonical Research
Record (publication_authors, with an owner_id fallback for ORCID-imported
legacy publications that never get a publication_authors row).

No changes to trust_verifications, Research Record schema, matching, or
People Discovery.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId

from services.verification.profile_service import compute_verification_profile
from services.research_record.authors import (
    count_publications_for_user, link_user_to_publication,
)


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
    # email_verified defaults True — a realistic confirmed test account.
    # P1 Phase 7C4.4 fixed compute_verification_profile's email_verified to
    # check this real, JWT-link-confirmed field instead of mere presence of
    # an email string (the old bug this suite's fixtures used to encode);
    # these composite-identity tests care about orcid/institution/identity
    # logic, not email confirmation itself, so the default keeps that intent
    # unchanged. Pass email_verified=False explicitly to test that case.
    doc = {
        "full_name": "Verification Test User",
        "email": f"verify-{_oid()}@synaptiq-test.io",
        "email_verified": True,
        **extra,
    }
    res = await db.users.insert_one(doc)
    return str(res.inserted_id)


class TestIdentityVerifiedComposite:
    @pytest.mark.asyncio
    async def test_email_only_verified_but_identity_not(self):
        raw = _RawDB()
        try:
            uid = await _insert_user(raw.db)  # email set, nothing else
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["email_verified"] is True
            assert profile["identity_verified"] is False
        finally:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
            raw.close()

    @pytest.mark.asyncio
    async def test_email_plus_orcid_makes_identity_verified(self):
        raw = _RawDB()
        try:
            uid = await _insert_user(raw.db, orcid={"orcid_id": "0000-0001-2345-6789"})
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["orcid_verified"] is True
            assert profile["identity_verified"] is True
        finally:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
            raw.close()

    @pytest.mark.asyncio
    async def test_email_plus_institution_makes_identity_verified(self):
        raw = _RawDB()
        try:
            uid = await _insert_user(raw.db, institution="Test University",
                                      institution_id=_oid())
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["institution_verified"] is True
            assert profile["identity_verified"] is True
        finally:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
            raw.close()

    @pytest.mark.asyncio
    async def test_neither_institution_nor_orcid_identity_not_verified(self):
        raw = _RawDB()
        try:
            uid = await _insert_user(raw.db)
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["orcid_verified"] is False
            assert profile["institution_verified"] is False
            assert profile["identity_verified"] is False
        finally:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
            raw.close()


class TestRecomputeIdempotency:
    @pytest.mark.asyncio
    async def test_get_me_recomputes_current_state(self):
        """Simulates the fixed GET /api/verification/me: a fresh account
        must show email_verified=true immediately, not a frozen False
        default (the exact bug reported)."""
        raw = _RawDB()
        try:
            uid = await _insert_user(raw.db)
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["email_verified"] is True  # not stuck at the old default
        finally:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
            raw.close()

    @pytest.mark.asyncio
    async def test_repeated_calls_do_not_rewrite_unchanged_profile(self):
        raw = _RawDB()
        try:
            uid = await _insert_user(raw.db)
            first = await compute_verification_profile(uid, raw.db)
            first_updated_at = first["updated_at"]

            second = await compute_verification_profile(uid, raw.db)
            # Nothing about the underlying user changed between calls, so
            # the stored updated_at must not have moved (no unnecessary write).
            assert second["updated_at"] == first_updated_at
            assert second["email_verified"] == first["email_verified"]

            # A real change (ORCID connected) must still trigger a write.
            await raw.db.users.update_one(
                {"_id": ObjectId(uid)}, {"$set": {"orcid": {"orcid_id": "0000-0001-2345-6789"}}})
            third = await compute_verification_profile(uid, raw.db)
            assert third["orcid_verified"] is True
            assert third["updated_at"] != first_updated_at
        finally:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
            raw.close()


class TestEmailVerifiedRequiresRealConfirmation:
    """P1 Phase 7C4.4 §B: email_verified must reflect the real, JWT-link-
    confirmed users.email_verified field, not mere presence of an email
    string — the presence-only check falsely told users their email
    ownership was confirmed when it had never been."""

    @pytest.mark.asyncio
    async def test_email_present_but_unconfirmed_is_not_verified(self):
        raw = _RawDB()
        try:
            uid = await _insert_user(raw.db, email_verified=False)
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["email_verified"] is False
            assert profile["identity_verified"] is False
        finally:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
            raw.close()

    @pytest.mark.asyncio
    async def test_email_confirmed_is_verified(self):
        raw = _RawDB()
        try:
            uid = await _insert_user(raw.db, email_verified=True)
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["email_verified"] is True
        finally:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
            raw.close()


class TestInstitutionVerifiedPaths:
    """P1 Phase 7C4.4 §D/§K audit: institution_verified must become true via
    every real evidence path — an approved institution_memberships row (the
    status value is "approved", never "active" — the dead check this fixes)
    and an approved manual verification_requests institution request (the
    admin-approval path that was previously silently discarded by the very
    recompute call that followed it)."""

    @pytest.mark.asyncio
    async def test_approved_membership_with_status_approved_verifies(self):
        raw = _RawDB()
        try:
            uid = await _insert_user(raw.db, institution="Test University")
            await raw.db.institution_memberships.insert_one(
                {"institution_id": _oid(), "user_id": uid, "status": "approved"})
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["institution_verified"] is True
        finally:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.institution_memberships.delete_many({"user_id": uid})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
            raw.close()

    @pytest.mark.asyncio
    async def test_pending_membership_does_not_verify(self):
        raw = _RawDB()
        try:
            uid = await _insert_user(raw.db, institution="Test University")
            await raw.db.institution_memberships.insert_one(
                {"institution_id": _oid(), "user_id": uid, "status": "pending"})
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["institution_verified"] is False
        finally:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.institution_memberships.delete_many({"user_id": uid})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
            raw.close()

    @pytest.mark.asyncio
    async def test_approved_manual_verification_request_verifies(self):
        """The confirmed root-cause case: an admin approving a
        verification_requests institution request (routers/verification.py's
        POST /admin/request/{rid}/decide) must actually result in
        institution_verified=True on the next recompute, not silently
        revert to False."""
        raw = _RawDB()
        try:
            uid = await _insert_user(raw.db, institution="Test University")
            await raw.db.verification_requests.insert_one({
                "user_id": uid, "request_type": "institution", "status": "approved",
                "details": {"institution_name": "Test University"},
            })
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["institution_verified"] is True
        finally:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.verification_requests.delete_many({"user_id": uid})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
            raw.close()

    @pytest.mark.asyncio
    async def test_pending_manual_verification_request_does_not_verify(self):
        raw = _RawDB()
        try:
            uid = await _insert_user(raw.db, institution="Test University")
            await raw.db.verification_requests.insert_one({
                "user_id": uid, "request_type": "institution", "status": "pending",
                "details": {"institution_name": "Test University"},
            })
            profile = await compute_verification_profile(uid, raw.db)
            assert profile["institution_verified"] is False
        finally:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.verification_requests.delete_many({"user_id": uid})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
            raw.close()


class TestOrcidTriggersRecompute:
    @pytest.mark.asyncio
    async def test_setting_orcid_then_recomputing_flips_orcid_verified(self):
        """Exercises the same call the fixed ORCID OAuth callback now makes
        (compute_verification_profile right after users.orcid is set) —
        the callback integration itself is a single try/except wrapping
        this exact call (routers/orcid.py), so the meaningful behavior to
        test is that the call correctly reflects a freshly-set ORCID id."""
        raw = _RawDB()
        try:
            uid = await _insert_user(raw.db)
            before = await compute_verification_profile(uid, raw.db)
            assert before["orcid_verified"] is False

            await raw.db.users.update_one(
                {"_id": ObjectId(uid)}, {"$set": {"orcid": {"orcid_id": "0000-0001-2345-6789"}}})
            after = await compute_verification_profile(uid, raw.db)
            assert after["orcid_verified"] is True
        finally:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
            raw.close()


class TestExpertiseCanonicalPublicationCount:
    @pytest.mark.asyncio
    async def test_one_publication_one_author_counts_one(self):
        raw = _RawDB()
        try:
            uid = _oid()
            pub_id = str((await raw.db.publications.insert_one({"title": "P1"})).inserted_id)
            await link_user_to_publication(raw.db, pub_id, uid, role="author", source="manual")

            count = await count_publications_for_user(raw.db, uid)
            assert count == 1
        finally:
            await raw.db.publications.delete_one({"title": "P1"})
            await raw.db.publication_authors.delete_many({"synaptiq_user_id": uid})
            raw.close()

    @pytest.mark.asyncio
    async def test_one_publication_two_authors_each_counts_one_not_two(self):
        raw = _RawDB()
        try:
            user_a, user_b = _oid(), _oid()
            pub_id = str((await raw.db.publications.insert_one({"title": "P2"})).inserted_id)
            await link_user_to_publication(raw.db, pub_id, user_a, role="author", source="manual")
            await link_user_to_publication(raw.db, pub_id, user_b, role="author", source="manual")

            assert await count_publications_for_user(raw.db, user_a) == 1
            assert await count_publications_for_user(raw.db, user_b) == 1
        finally:
            await raw.db.publications.delete_one({"title": "P2"})
            await raw.db.publication_authors.delete_many({"synaptiq_user_id": {"$in": [user_a, user_b]}})
            raw.close()

    @pytest.mark.asyncio
    async def test_multiple_publications_correct_distinct_count(self):
        raw = _RawDB()
        try:
            uid = _oid()
            pub_ids = []
            for i in range(3):
                pid = str((await raw.db.publications.insert_one({"title": f"Multi {i} {uid[:6]}"})).inserted_id)
                pub_ids.append(pid)
                await link_user_to_publication(raw.db, pid, uid, role="author", source="manual")

            assert await count_publications_for_user(raw.db, uid) == 3
        finally:
            await raw.db.publications.delete_many({"_id": {"$in": [ObjectId(p) for p in pub_ids]}})
            await raw.db.publication_authors.delete_many({"synaptiq_user_id": uid})
            raw.close()

    @pytest.mark.asyncio
    async def test_duplicate_authorship_row_cannot_inflate_count(self):
        raw = _RawDB()
        try:
            uid = _oid()
            pub_id = str((await raw.db.publications.insert_one({"title": "P3"})).inserted_id)
            await link_user_to_publication(raw.db, pub_id, uid, role="author", source="manual")
            # Re-linking the same (publication, user) pair is idempotent by
            # design (see services/research_record/authors.py) — must not
            # create a second row or inflate the count.
            await link_user_to_publication(raw.db, pub_id, uid, role="owner", source="orcid")

            rows = await raw.db.publication_authors.count_documents(
                {"publication_id": pub_id, "synaptiq_user_id": uid})
            assert rows == 1
            assert await count_publications_for_user(raw.db, uid) == 1
        finally:
            await raw.db.publications.delete_one({"title": "P3"})
            await raw.db.publication_authors.delete_many({"synaptiq_user_id": uid})
            raw.close()

    @pytest.mark.asyncio
    async def test_legacy_owner_id_only_publication_still_counted(self):
        """The primary real writer of `publications` (services/orcid/sync.py)
        sets owner_id directly and never creates a publication_authors row —
        this is the exact legacy-compatibility case the fix must handle."""
        raw = _RawDB()
        try:
            uid = _oid()
            await raw.db.publications.insert_one({"title": "Legacy ORCID Import", "owner_id": uid})
            # Deliberately NO publication_authors row for this one.

            count = await count_publications_for_user(raw.db, uid)
            assert count == 1
        finally:
            await raw.db.publications.delete_many({"owner_id": uid})
            raw.close()

    @pytest.mark.asyncio
    async def test_same_publication_via_both_paths_not_double_counted(self):
        raw = _RawDB()
        try:
            uid = _oid()
            pub_id_obj = (await raw.db.publications.insert_one(
                {"title": "Both Paths", "owner_id": uid})).inserted_id
            # Same publication also has an explicit publication_authors row
            # (e.g. after an explicit manuscript-publish action).
            await link_user_to_publication(raw.db, str(pub_id_obj), uid, role="owner", source="synaptiq")

            count = await count_publications_for_user(raw.db, uid)
            assert count == 1  # not 2
        finally:
            await raw.db.publications.delete_one({"_id": pub_id_obj})
            await raw.db.publication_authors.delete_many({"synaptiq_user_id": uid})
            raw.close()

    @pytest.mark.asyncio
    async def test_expertise_verified_reflects_real_publication_count(self):
        """End-to-end: 5+ real publications via the canonical relationship
        now actually flips expert_verified (previously impossible — see
        the audit)."""
        raw = _RawDB()
        try:
            uid = await _insert_user(raw.db, orcid={"orcid_id": "0000-0001-2345-6789"})
            pub_ids = []
            for i in range(5):
                pid = str((await raw.db.publications.insert_one(
                    {"title": f"Expertise Pub {i} {uid[:6]}"})).inserted_id)
                pub_ids.append(pid)
                await link_user_to_publication(raw.db, pid, uid, role="author", source="manual")

            profile = await compute_verification_profile(uid, raw.db)
            assert profile["expert_verified"] is True
        finally:
            await raw.db.users.delete_one({"_id": ObjectId(uid)})
            await raw.db.verification_profiles.delete_one({"user_id": uid})
            await raw.db.publications.delete_many({"_id": {"$in": [ObjectId(p) for p in pub_ids]}})
            await raw.db.publication_authors.delete_many({"synaptiq_user_id": uid})
            raw.close()
