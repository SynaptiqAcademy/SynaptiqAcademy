"""/pricing: the commercial source of truth. Plan values come from the
catalogue via the public API; every promise maps to an enforced capability;
no checkout is offered unless it can be completed and fulfilled."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from plans_catalogue import get_plan, PLAN_QUOTAS, STORAGE_LIMITS_BYTES, FEATURE_MATRIX, FEATURE_MIN_PLAN, TIER_CAPABILITIES
from tests.test_landing_commercial_truth import FABRICATION, UNSAFE, GENERIC, _visible_text

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "frontend" / "src" / "pages" / "Pricing.jsx").read_text()
TEXT = _visible_text(SRC)
GB = 1024 ** 3


# ── canonical plan values ────────────────────────────────────────────────
def test_free():
    p = get_plan("free")
    assert p["name"] == "Free" and p["price_eur_monthly"] == 0 and p["credits_per_month"] == 0
    assert PLAN_QUOTAS["free"]["workspaces"] == 0 and STORAGE_LIMITS_BYTES["free"] == 0


def test_pro():
    p = get_plan("researcher")
    assert (p["name"], p["price_eur_monthly"], p["future_price_eur_monthly"], p["credits_per_month"]) == ("Pro", 9.99, 14.99, 200)
    assert p["badge"] == "Early Access"
    assert PLAN_QUOTAS["researcher"]["workspaces"] == 10 and PLAN_QUOTAS["researcher"]["projects"] == -1
    assert STORAGE_LIMITS_BYTES["researcher"] == 10 * GB


def test_pro_advanced():
    p = get_plan("pro_researcher")
    assert (p["name"], p["price_eur_monthly"], p["credits_per_month"]) == ("Pro Advanced", 29.99, 750)
    assert PLAN_QUOTAS["pro_researcher"]["workspaces"] == -1 and STORAGE_LIMITS_BYTES["pro_researcher"] == 50 * GB


def test_institutional_is_custom_contact_sales():
    p = get_plan("institution")
    assert p["name"] == "Institutional" and p["cta"] == "Contact Sales"
    assert "Contact Sales" in SRC and "/for-institutions#inquiry" in SRC and "Custom" in SRC


# ── public API never leaks internal commercial values ───────────────────
@pytest.mark.asyncio
async def test_public_plans_api_redacts_custom_plans_and_flags_checkout():
    from routers.billing import list_plans
    plans = {p["code"]: p for p in await list_plans()}
    for code in ("institution", "enterprise"):
        assert plans[code]["price_eur_monthly"] is None and plans[code]["credits_per_month"] is None
        assert plans[code]["limits"] == {} and plans[code]["checkout_available"] is False
    assert plans["free"]["checkout_available"] is False


@pytest.mark.asyncio
async def test_checkout_needs_webhook_secret(monkeypatch):
    from services import stripe_service
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_MODE", "test")
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    assert stripe_service.is_configured() and not stripe_service.checkout_ready()
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "dummy-webhook-secret-for-tests")
    assert stripe_service.checkout_ready()


@pytest.mark.asyncio
async def test_webhook_without_secret_is_not_acknowledged(monkeypatch):
    from fastapi import HTTPException
    from starlette.requests import Request
    from routers.billing import stripe_webhook
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)

    async def receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}
    req = Request({"type": "http", "method": "POST", "headers": []}, receive)
    with pytest.raises(HTTPException) as e:
        await stripe_webhook(req)
    assert e.value.status_code == 503      # Stripe retries instead of dropping the event


# ── every advertised feature is a real, enforced capability ─────────────
def test_matrix_has_no_unimplemented_rows():
    labels = {r[0] for r in FEATURE_MATRIX}
    for gone in ("Advanced Analytics", "Advanced Manuscript Intelligence", "Advanced AI Teaching", "Support"):
        assert gone not in labels
    feats = " ".join(get_plan("researcher")["features"] + get_plan("pro_researcher")["features"])
    for gone in ("Priority", "Advanced Research Analytics", "Advanced Manuscript Intelligence", "Advanced AI Teaching"):
        assert gone not in feats, gone


def test_pro_advanced_tools_are_gated_to_pro_advanced():
    for f in ("ai_literature_review", "ai_research_gap_finder", "ai_research_design_advisor", "ai_statistical_review"):
        assert FEATURE_MIN_PLAN[f] == "pro_researcher", f
    adv, pro = TIER_CAPABILITIES["PRO_ADVANCED"], TIER_CAPABILITIES["PRO"]
    for cap in ("can_use_collaboration_intelligence", "can_view_impact_dashboard", "can_use_citation_monitoring"):
        assert adv[cap] and not pro.get(cap), cap


def test_individual_plans_never_grant_institution_access():
    perms = (ROOT / "backend" / "services" / "permissions.py").read_text()
    block = perms[perms.index("async def get_institution_membership"):perms.index("async def require_institution_member")]
    assert "plan_code" not in block and '"status": "approved"' in block
    assert "not from an individual plan" in SRC


# ── page copy ────────────────────────────────────────────────────────────
BANNED = [r"€ ?299", r"[Mm]ost [Pp]opular", r"[Bb]est [Vv]alue", r"\b[Rr]ecommended\b", r"[Ss]ave \d", r"\d+% off",
          r"[Ff]ree trial", r"\d+-day", r"[Tt]ry Pro", r"[Ll]imited time", r"[Ee]nds soon", r"[Ll]ock in", r"[Gg]randfather",
          r"[Cc]ancel anytime", r"[Mm]oney-back", r"[Nn]o credit card", r"VAT included", r"[Pp]riority",
          r"Pro Researcher", r"Researcher [Pp]lan", r"Institution plan", r"pro_researcher\"\s*>", r"--\s*credits",
          r"<s>|line-through", r"20,?000"]


@pytest.mark.parametrize("pattern", FABRICATION + UNSAFE + GENERIC + BANNED)
def test_no_dark_patterns_or_unsupported_claims(pattern):
    assert not re.search(pattern, TEXT), pattern


def test_page_renders_from_server_catalogue_and_gates_checkout():
    assert 'api.get("/billing/plans")' in SRC and 'api.get("/billing/feature-matrix")' in SRC
    assert "plan.checkout_available" in SRC
    assert "registrationOpen === false" in SRC
    for n in ("9.99", "29.99", "14.99", "200", "750"):
        assert not re.search(rf"(?<![\d.]){re.escape(n)}(?![\d])", TEXT), f"hardcoded {n}"


def test_analytics_carry_no_personal_data():
    for call in re.findall(r"track(?:MonetizationEvent)?\(([^)]*)\)", SRC):
        assert not re.search(r"email|name\b|card|token|user\.", call), call
