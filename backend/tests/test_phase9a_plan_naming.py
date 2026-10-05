"""Phase 9A final commercial decisions — customer-facing plan naming.

Backend codes stay `researcher` / `pro_researcher`; customers see "Pro" and
"Pro Advanced". This file locks in: the display mapping (backend + the one
frontend mirror), the owner-approved entitlement bundles per tier, that no
individual plan grants Institution, that the public pages carry no old
persona-style plan names / public Institutional price / popularity badge /
annual purchase toggle, and that the credits row in the comparison matrix
is derived from the canonical catalogue rather than a second hardcoded copy.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from bson import ObjectId
from fastapi import HTTPException

from plans_catalogue import PLANS, FEATURE_MIN_PLAN, PLAN_QUOTAS, FEATURE_MATRIX, get_plan
from services.permissions import (
    require_plan,
    require_institution_member,
    get_my_institution_context,
)

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"


# ───────────────────────────── display names ─────────────────────────────

class TestCanonicalDisplayNames:
    def test_researcher_code_displays_as_pro(self):
        assert get_plan("researcher")["name"] == "Pro"

    def test_pro_researcher_code_displays_as_pro_advanced(self):
        assert get_plan("pro_researcher")["name"] == "Pro Advanced"

    def test_backend_codes_unchanged(self):
        assert [p["code"] for p in PLANS] == ["free", "researcher", "pro_researcher", "institution", "enterprise"]

    def test_frontend_mapping_mirrors_backend_names(self):
        src = (FRONTEND / "lib" / "planNames.js").read_text()
        mapping = dict(re.findall(r'^\s*(\w+):\s*"([^"]+)",', src, re.M))
        for plan in PLANS:
            assert mapping.get(plan["code"]) == plan["name"], plan["code"]

    @pytest.mark.asyncio
    async def test_upgrade_gate_message_uses_display_name_not_code(self):
        dep = require_plan("pro_researcher")
        with pytest.raises(HTTPException) as exc:
            await dep(user={"id": "u1", "email": "u1@synaptiq-test.io", "plan_code": "free", "role": "user"})
        msg = exc.value.detail["message"]
        assert "Pro Advanced" in msg
        assert "Researcher" not in msg
        # The raw code still travels separately for the frontend mapping to use.
        assert exc.value.detail["required_plan"] == "pro_researcher"


# ───────────────────────────── entitlement bundles ─────────────────────────────

class TestEntitlementBundles:
    """Bundles as set by the owner's monetization decision (Free = identity
    only; Pro = network, collaboration, discovery, AI; Pro Advanced = advanced
    intelligence). Locked here so a later naming/copy pass can't move them."""

    def test_pro_bundle(self):
        pro = {k for k, v in FEATURE_MIN_PLAN.items() if v == "researcher"}
        assert pro == {
            "network", "messaging", "basic_discovery", "project_create", "workspace_create",
            "collaboration_request", "teaching_hub", "credit_purchase",
            "ai_assistant", "ai_manuscript_copilot", "publication_tracking", "advanced_analytics",
            "full_discovery", "ai_journal_matching", "ai_conference_matching", "ai_grant_matching",
            "ai_manuscript_review", "ai_methodology_builder", "ai_research_assistant",
            "ai_rewriting", "ai_abstract_generator",
        }

    def test_pro_advanced_bundle(self):
        adv = {k for k, v in FEATURE_MIN_PLAN.items() if v == "pro_researcher"}
        assert adv == {
            "ai_advanced_assistant", "ai_literature_review", "ai_statistical_review",
            "ai_research_design_advisor", "ai_research_gap_finder", "collaboration_intelligence",
            "research_analytics_suite", "citation_monitoring", "research_impact_dashboard",
            "premium_collaboration", "advanced_manuscript_intelligence", "advanced_ai_teaching",
        }

    def test_free_is_identity_only(self):
        free = {k for k, v in FEATURE_MIN_PLAN.items() if v == "free"}
        assert free == {"academic_profile", "orcid", "public_profile"}

    def test_quotas_prices_and_credits(self):
        assert PLAN_QUOTAS["free"] == {"projects": 0, "workspaces": 0, "manuscripts": 0}
        assert PLAN_QUOTAS["researcher"] == {"projects": -1, "workspaces": 10, "manuscripts": -1}
        assert PLAN_QUOTAS["pro_researcher"] == {"projects": -1, "workspaces": -1, "manuscripts": -1}
        assert get_plan("free")["price_eur_monthly"] == 0
        assert get_plan("researcher")["price_eur_monthly"] == 9.99
        assert get_plan("pro_researcher")["price_eur_monthly"] == 29.99
        assert [get_plan(c)["credits_per_month"] for c in ("free", "researcher", "pro_researcher")] == [0, 200, 750]

    def test_matrix_credits_row_derived_from_catalogue(self):
        row = next(r for r in FEATURE_MATRIX if r[0] == "AI Credits / month")
        expected = [f"{get_plan(c)['credits_per_month']:,}" for c in ("free", "researcher", "pro_researcher", "institution")]
        assert list(row[1:5]) == expected


# ───────────────────────────── no individual plan grants Institution ─────────────────────────────

class _RawDB:
    def __init__(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        self._client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
        self.db = self._client[os.environ["MONGODB_DB_NAME"]]

    def close(self):
        self._client.close()


class TestPaidIndividualPlansDoNotGrantInstitution:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("plan_code", ["researcher", "pro_researcher"])
    async def test_paid_plan_without_membership_has_no_institution(self, monkeypatch, plan_code):
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            iid = str((await raw.db.institutions.insert_one({"name": f"Inst {str(ObjectId())[-8:]}"})).inserted_id)
            user = {"id": str(ObjectId()), "role": "user", "plan_code": plan_code}

            assert await get_my_institution_context(user) == {"is_member": False}
            with pytest.raises(HTTPException) as exc:
                await require_institution_member(iid, user)
            assert exc.value.status_code == 403
        finally:
            await raw.db.institutions.delete_many({"_id": ObjectId(iid)})
            raw.close()


# ───────────────────────────── public surfaces ─────────────────────────────

PUBLIC_PRICING_FILES = [
    FRONTEND / "pages" / "Pricing.jsx",
    FRONTEND / "pages" / "Landing.jsx",
    FRONTEND / "components" / "landing" / "content.js",
    FRONTEND / "components" / "landing" / "Sections.jsx",
]


def _customer_pages():
    for p in (FRONTEND / "pages").rglob("*.jsx"):
        if "admin" in p.parts:
            continue  # internal staff tooling, not customer-facing
        yield p
    yield from (FRONTEND / "components").rglob("*.jsx")


class TestPublicCommercialTruth:
    @pytest.mark.parametrize("path", PUBLIC_PRICING_FILES, ids=lambda p: p.name)
    def test_no_public_institutional_price_or_popularity_badge(self, path):
        src = path.read_text()
        assert "€299" not in src
        assert "Most Popular" not in src and "Most popular" not in src and "MOST POPULAR" not in src

    def test_no_customer_facing_old_plan_names(self):
        offenders = []
        for p in _customer_pages():
            src = p.read_text()
            for bad in ("Pro Researcher", "Researcher plan", "Researcher Plan", "Upgrade to Researcher", "Choose Researcher"):
                if bad in src:
                    offenders.append(f"{p.relative_to(FRONTEND)}: {bad}")
        assert not offenders, offenders

    def test_landing_preview_has_no_researcher_plan_card(self):
        src = (FRONTEND / "components" / "landing" / "content.js").read_text()
        tiers = src[src.index("export const PLAN_PREVIEW"):src.index("export const FAQ")]
        names = re.findall(r'name:\s*"([^"]+)"', tiers)
        assert names == ["Free", "Pro", "Pro Advanced", "Institutional"]

    def test_landing_paid_ctas_do_not_hit_checkout(self):
        src = (FRONTEND / "components" / "landing" / "content.js").read_text()
        tiers = src[src.index("export const PLAN_PREVIEW"):src.index("export const FAQ")]
        assert "checkout" not in tiers
        assert 'href: "/contact?topic=institution"' in tiers

    def test_annual_billing_not_offered_as_purchasable(self):
        src = (FRONTEND / "pages" / "Pricing.jsx").read_text()
        assert "Pay yearly" not in src
        assert "Save up to 20%" not in src
        assert "const annual = false;" in src

    def test_institution_catalogue_features_carry_no_fixed_price(self):
        feats = " ".join(get_plan("institution")["features"])
        assert "€" not in feats and "299" not in feats
        assert get_plan("institution")["cta"] == "Contact Sales"


class TestPublicPlansApi:
    @pytest.mark.asyncio
    async def test_public_plans_api_publishes_no_institutional_price(self):
        from routers.billing import list_plans
        plans = {p["code"]: p for p in await list_plans()}
        for code in ("institution", "enterprise"):
            assert plans[code]["price_eur_monthly"] is None
            assert plans[code]["price_eur_annual"] is None
        assert plans["researcher"]["price_eur_monthly"] == 9.99
        assert plans["pro_researcher"]["price_eur_monthly"] == 29.99
        assert plans["researcher"]["name"] == "Pro" and plans["pro_researcher"]["name"] == "Pro Advanced"
