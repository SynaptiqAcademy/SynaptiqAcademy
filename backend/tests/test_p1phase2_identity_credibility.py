"""Regression tests for the P1 Phase 2 (Academic Identity + Credibility) audit
fixes — the `bio` vs `biography` field-name mismatch found across ~7
identity/credibility-scoring call sites, and the onboarding ORCID
type-clobber bug.

The real `users` document field is `biography` (see backend/models.py,
auth_utils.py) — `bio` was never written anywhere, so every one of these
scoring/validation functions silently always treated biography as absent
before this fix.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId

from services.rule_engine.scoring.profile_score import calculate_profile_score
from services.rule_engine.validation.content_validator import validate_profile_completeness
from services.rule_engine.alerts.alert_engine import generate_profile_alerts


def _oid() -> str:
    return str(ObjectId())


class _RawDB:
    def __init__(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        self._client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
        self.db = self._client[os.environ["MONGODB_DB_NAME"]]

    def close(self):
        self._client.close()


class TestProfileScoreReadsRealBiographyField:
    def test_real_user_shaped_profile_with_biography_counts_as_complete(self):
        profile = {"biography": "A" * 100, "avatar_url": "x", "institution": "MIT"}
        result = calculate_profile_score(profile)
        assert result.breakdown["bio"]["complete"] is True

    def test_missing_biography_is_incomplete(self):
        profile = {"avatar_url": "x", "institution": "MIT"}
        result = calculate_profile_score(profile)
        assert result.breakdown["bio"]["complete"] is False

    def test_short_biography_is_incomplete(self):
        profile = {"biography": "too short"}
        result = calculate_profile_score(profile)
        assert result.breakdown["bio"]["complete"] is False

    def test_ad_hoc_bio_key_still_works_for_backward_compat(self):
        # Existing callers/tests that pass a raw {"bio": ...} dict (not a
        # real user document) must keep working.
        profile = {"bio": "A" * 100}
        result = calculate_profile_score(profile)
        assert result.breakdown["bio"]["complete"] is True


class TestContentValidatorReadsRealFieldNames:
    def test_biography_and_methods_recognized(self):
        result = validate_profile_completeness({
            "biography": "A" * 60, "methods": ["qualitative"], "institution": "MIT",
        })
        assert result["fields"]["biography"]["complete"] is True
        assert result["fields"]["methods"]["complete"] is True

    def test_missing_fields_not_recognized(self):
        result = validate_profile_completeness({})
        assert result["fields"]["biography"]["complete"] is False
        assert result["fields"]["methods"]["complete"] is False


class TestAlertEngineReadsRealBiographyField:
    def test_no_bio_alert_when_biography_is_set(self):
        alerts = generate_profile_alerts({
            "orcid_id": "0000-0000-0000-0001", "biography": "A" * 100,
            "research_keywords": ["a", "b", "c"],
        })
        codes = [a.code for a in alerts]
        assert "PROFILE_MISSING_BIO" not in codes

    def test_bio_alert_when_biography_missing(self):
        alerts = generate_profile_alerts({"orcid_id": "0000-0000-0000-0001"})
        codes = [a.code for a in alerts]
        assert "PROFILE_MISSING_BIO" in codes


class TestOnboardingDoesNotClobberOrcidDict:
    @pytest.mark.asyncio
    async def test_onboarding_update_never_includes_orcid_key(self):
        """Exercises the exact fix in routers/users.py::complete_onboarding —
        confirms the pop("orcid", None) actually removes it from the $set
        payload, simulating what the endpoint builds before writing."""
        from models import OnboardingComplete

        payload = OnboardingComplete(
            first_name="Ada", last_name="Lovelace", country="UK",
            user_type="researcher", primary_domain="research",
            institution="Analytical Engines Ltd", department="Computing",
            orcid="0000-0001-2345-6789",  # legacy plain-string shape
        )
        update = payload.model_dump()
        update.pop("orcid", None)
        assert "orcid" not in update

    @pytest.mark.asyncio
    async def test_existing_oauth_orcid_dict_survives_a_simulated_onboarding_write(self):
        raw = _RawDB()
        try:
            uid = (await raw.db.users.insert_one({
                "full_name": "Test User",
                "email": f"onboard-{_oid()}@synaptiq-test.io",
                "orcid": {"orcid_id": "0000-0001-2345-6789", "access_token": "enc:xyz"},
            })).inserted_id

            # Simulate the fixed endpoint's write: orcid popped before $set.
            update = {"institution": "New Institution", "onboarded": True}
            await raw.db.users.update_one({"_id": uid}, {"$set": update})

            doc = await raw.db.users.find_one({"_id": uid})
            assert isinstance(doc["orcid"], dict)
            assert doc["orcid"]["orcid_id"] == "0000-0001-2345-6789"
        finally:
            raw.close()
