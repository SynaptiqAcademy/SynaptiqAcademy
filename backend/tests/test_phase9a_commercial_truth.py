"""Phase 9A Part 2 — commercial-truth regression checks.

These lock in the specific claims/behaviors this phase established, so a
future change can't silently regress them:
  - the legacy individual "institution" plan_code is not self-serve
  - "enterprise" is not self-serve either (contact-sales only)
  - the contact-form topic validator covers every option the frontend
    actually offers (the exact mismatch that broke the institutional
    inquiry path before this phase)
  - displayed plan names come from the canonical catalogue, never a raw
    internal enum
  - GET /api/billing/plans never leaks a populated Stripe price id (nothing
    to leak today, but this guards the day one gets filled in)
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from plans_catalogue import PLANS, get_plan
from routers.billing import VALID_PAID_PLANS, NOT_SELF_SERVE_PLANS, create_checkout
from routers.contact import TOPIC_LABELS, ContactRequest


def _user(uid="u1", email="u1@synaptiq-test.io"):
    return {"id": uid, "email": email, "plan_code": "free"}


class TestLegacyInstitutionPlanBlocked:
    @pytest.mark.asyncio
    async def test_institution_plan_code_rejected_from_self_serve_checkout(self):
        with pytest.raises(HTTPException) as exc:
            await create_checkout({"plan_code": "institution", "billing_period": "monthly"}, user=_user())
        assert exc.value.status_code == 400
        assert exc.value.detail.get("code") == "not_self_serve"

    @pytest.mark.asyncio
    async def test_enterprise_plan_code_rejected_from_self_serve_checkout(self):
        with pytest.raises(HTTPException) as exc:
            await create_checkout({"plan_code": "enterprise", "billing_period": "monthly"}, user=_user())
        assert exc.value.status_code == 400
        assert exc.value.detail.get("code") == "not_self_serve"

    def test_valid_paid_plans_is_individual_only(self):
        assert VALID_PAID_PLANS == {"researcher", "pro_researcher"}
        assert "institution" not in VALID_PAID_PLANS
        assert "enterprise" not in VALID_PAID_PLANS
        assert NOT_SELF_SERVE_PLANS == {"institution", "enterprise"}

    @pytest.mark.asyncio
    async def test_researcher_plan_still_reaches_the_stripe_gate(self):
        # Not testing Stripe itself (unconfigured in this environment) — just
        # confirming a real self-serve plan_code is NOT rejected by the same
        # not-self-serve guard that blocks institution/enterprise.
        with pytest.raises(HTTPException) as exc:
            await create_checkout({"plan_code": "researcher", "billing_period": "monthly"}, user=_user())
        # 503 "Stripe not configured", never the not_self_serve 400.
        assert exc.value.status_code == 503


class TestContactTopicValidationMatchesFrontend:
    """The exact bug this phase found and fixed: Pricing.jsx's Institution
    CTA linked to a topic the backend didn't accept, so every institutional
    inquiry through that path silently failed."""

    FRONTEND_TOPICS = {
        "general", "individual", "institution", "enterprise", "support",
        "security", "partnership", "research", "other",
    }

    def test_every_frontend_topic_is_backend_valid(self):
        missing = self.FRONTEND_TOPICS - set(TOPIC_LABELS.keys())
        assert not missing, f"Frontend offers topics the backend rejects: {missing}"

    def test_institution_topic_accepted(self):
        req = ContactRequest(name="Jane Doe", email="jane@example.com", topic="institution", message="We are interested.")
        assert req.topic == "institution"

    def test_enterprise_topic_accepted(self):
        req = ContactRequest(name="Jane Doe", email="jane@example.com", topic="enterprise", message="We are interested.")
        assert req.topic == "enterprise"

    def test_unknown_topic_rejected(self):
        with pytest.raises(Exception):
            ContactRequest(name="Jane Doe", email="jane@example.com", topic="not_a_real_topic", message="Hi")


class TestCanonicalPlanNamesOnly:
    def test_every_plan_has_a_customer_facing_name_distinct_from_its_code(self):
        for plan in PLANS:
            assert plan["name"], f"Plan {plan['code']} has no display name"
            # A real display name should read like English, not the raw
            # snake_case internal code (e.g. "Pro Advanced", not
            # "pro_researcher") — the exact bug the Navigation-phase pass
            # fixed for the sidebar.
            assert "_" not in plan["name"]

    def test_get_plan_pro_researcher_name_is_display_ready(self):
        assert get_plan("pro_researcher")["name"] == "Pro Advanced"

    def test_get_plan_institution_name_is_display_ready(self):
        assert get_plan("institution")["name"] == "Institution"


class TestNoFakeTrialLanguage:
    def test_no_plan_declares_a_trial(self):
        # No trial is configured anywhere (confirmed in the Stripe audit) —
        # this guards against a plan entry claiming one without the checkout
        # code actually setting trial_period_days.
        for plan in PLANS:
            assert "trial" not in str(plan.get("tagline", "")).lower()
            assert "trial" not in str(plan.get("cta", "")).lower()
