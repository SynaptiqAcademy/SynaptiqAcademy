"""Monetization system — tiers, entitlements, credits, AI cost control, billing.

Unit tests need nothing; tests marked `db` use the local MongoDB that the
rest of the suite uses (synaptiq_test) and clean up after themselves.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path

import pytest
from bson import ObjectId
from fastapi import HTTPException

import plans_catalogue as pc
from plans_catalogue import (
    AI_OPERATIONS, CREDIT_COSTS, CREDIT_PACKS, PLAN_QUOTAS, STORAGE_LIMITS_BYTES,
    TIER_CAPABILITIES, get_plan,
)
from services import entitlements as ent
from services.monetization_middleware import match_rule, RULES

GB = 1024 ** 3
BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"


# ═════════════════════════════ catalogue ═════════════════════════════

class TestTierCatalogue:
    def test_three_individual_tiers_and_prices(self):
        assert [get_plan(c)["name"] for c in ("free", "researcher", "pro_researcher")] == ["Free", "Pro", "Pro Advanced"]
        assert get_plan("free")["price_eur_monthly"] == 0
        assert get_plan("researcher")["price_eur_monthly"] == 9.99
        assert get_plan("pro_researcher")["price_eur_monthly"] == 29.99

    def test_pro_early_access_future_price_recommended(self):
        pro = get_plan("researcher")
        assert pro["badge"] == "Early Access"
        assert pro["future_price_eur_monthly"] == 14.99
        assert pro["recommended"] is True
        assert pro["cta"] == "Choose Pro"
        adv = get_plan("pro_researcher")
        assert adv["cta"] == "Choose Pro Advanced"
        assert adv["features"][0] == "Everything in Pro"
        assert not any("Researcher" in f for f in adv["features"])

    def test_free_copy(self):
        free = get_plan("free")
        assert free["tagline"] == "Build your academic presence"
        assert free["cta"] == "Create Free Profile"

    def test_monthly_credits(self):
        assert [get_plan(c)["credits_per_month"] for c in ("free", "researcher", "pro_researcher")] == [0, 200, 750]

    def test_storage_limits(self):
        assert STORAGE_LIMITS_BYTES["free"] == 0
        assert STORAGE_LIMITS_BYTES["researcher"] == 10 * GB
        assert STORAGE_LIMITS_BYTES["pro_researcher"] == 50 * GB
        assert [get_plan(c)["limits"]["repository_gb"] for c in ("free", "researcher", "pro_researcher")] == [0, 10, 50]

    def test_project_and_workspace_limits(self):
        assert PLAN_QUOTAS["free"]["projects"] == 0 and PLAN_QUOTAS["free"]["workspaces"] == 0
        assert PLAN_QUOTAS["researcher"]["projects"] == -1 and PLAN_QUOTAS["researcher"]["workspaces"] == 10
        assert PLAN_QUOTAS["pro_researcher"]["projects"] == -1 and PLAN_QUOTAS["pro_researcher"]["workspaces"] == -1

    def test_operation_catalogue_exact(self):
        assert {op: m["credits"] for op, m in AI_OPERATIONS.items()} == {
            "QUICK_ACADEMIC_REWRITE": 1, "RESEARCH_QUESTIONS": 2, "ABSTRACT_ANALYSIS": 2,
            "AI_ASSISTANT_SIMPLE": 2, "JOURNAL_FIT": 5, "CONFERENCE_FIT": 5, "GRANT_FIT": 5,
            "MANUSCRIPT_SECTION_REVIEW": 10, "TEACHING_CONTENT_GENERATION": 10,
            "LITERATURE_SYNTHESIS": 15, "FULL_MANUSCRIPT_REVIEW": 30, "DEEP_RESEARCH": 40,
            "MULTI_PAPER_SYNTHESIS": 40, "ADVANCED_MANUSCRIPT_INTELLIGENCE": 50,
        }

    def test_legacy_actions_priced_by_their_operation(self):
        for action, op in pc.ACTION_OPERATION.items():
            assert CREDIT_COSTS[action] == AI_OPERATIONS[op]["credits"], action
        assert CREDIT_COSTS["ai_manuscript_review"] == 30
        assert CREDIT_COSTS["ai_journal_matching"] == 5

    def test_credit_packs(self):
        assert [(p["code"], p["credits"], p["price_eur"]) for p in CREDIT_PACKS] == [
            ("pack_100", 100, 4.99), ("pack_300", 300, 11.99), ("pack_750", 750, 24.99)]

    def test_no_hardcoded_stripe_ids_in_catalogue(self):
        src = (BACKEND / "plans_catalogue.py").read_text()
        # Real Stripe ids look like price_1Pq... / prod_Q... (mixed case + digits).
        assert not re.search(r"\b(price|prod)_(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Z])[A-Za-z0-9]{10,}", src)
        assert "STRIPE_PRICE_PRO_MONTHLY" in src and "STRIPE_PRICE_CREDITS_750" in src

    def test_operation_cost_override_validates(self, monkeypatch):
        saved = {k: dict(v) for k, v in AI_OPERATIONS.items()}
        try:
            monkeypatch.setenv("AI_OPERATION_COSTS_JSON", json.dumps({"JOURNAL_FIT": 6, "DEEP_RESEARCH": -5, "NOPE": 3}))
            pc._apply_operation_cost_overrides()
            assert AI_OPERATIONS["JOURNAL_FIT"]["credits"] == 6
            assert AI_OPERATIONS["DEEP_RESEARCH"]["credits"] == 40   # invalid value ignored
        finally:
            for k, v in saved.items():
                AI_OPERATIONS[k].update(v)

    def test_matrix_rows_derived_from_tables(self):
        rows = {r[0]: r[1:] for r in pc.FEATURE_MATRIX}
        assert rows["AI Credits / month"][:3] == ("0", "200", "750")
        assert rows["Storage"][:3] == ("Profile only", "10 GB", "50 GB")
        assert rows["Workspaces"][:3] == ("—", "10", "Unlimited")
        assert rows["Messaging"][:3] == (False, True, True)
        assert rows["Impact Dashboard"][:3] == (False, False, True)


# ═════════════════════════════ entitlements ═════════════════════════════

def _u(plan="free", **kw):
    return {"id": kw.pop("id", str(ObjectId())), "email": "x@synaptiq-test.io", "role": "user",
            "plan_code": plan, **kw}


class TestEntitlements:
    IDENTITY = {"can_edit_academic_profile", "can_publish_public_profile", "can_connect_orcid",
                "can_import_orcid_publications", "can_receive_collaboration_invites"}

    def test_free_is_identity_only(self):
        caps = ent.get_entitlements(_u("free"))["capabilities"]
        assert {c for c, v in caps.items() if v} == self.IDENTITY

    def test_free_numeric_limits(self):
        e = ent.get_entitlements(_u("free"))
        assert (e["monthly_ai_credits"], e["project_limit"], e["workspace_limit"], e["storage_limit_bytes"]) == (0, 0, 0, 0)

    def test_pro_capabilities(self):
        e = ent.get_entitlements(_u("researcher"))
        caps = e["capabilities"]
        for c in ("can_use_research_network", "can_message_researchers", "can_send_collaboration_request",
                  "can_accept_collaboration", "can_create_project", "can_create_workspace",
                  "can_use_journal_discovery", "can_use_conference_discovery", "can_use_grant_discovery",
                  "can_use_research_assistant", "can_use_manuscript_copilot", "can_use_teaching_ai",
                  "can_view_research_analytics", "can_purchase_ai_credits"):
            assert caps[c], c
        for c in ("can_use_collaboration_intelligence", "can_use_citation_monitoring",
                  "can_view_impact_dashboard", "can_use_advanced_ai"):
            assert not caps[c], c
        assert (e["monthly_ai_credits"], e["project_limit"], e["workspace_limit"], e["storage_limit_bytes"]) == (200, None, 10, 10 * GB)

    def test_pro_advanced_has_everything(self):
        e = ent.get_entitlements(_u("pro_researcher"))
        assert all(e["capabilities"].values())
        assert (e["monthly_ai_credits"], e["workspace_limit"], e["storage_limit_bytes"]) == (750, None, 50 * GB)

    def test_lapsed_subscription_is_free_but_past_due_is_grace(self):
        assert ent.tier_for(_u("researcher", subscription_status="unpaid")) == "FREE"
        assert ent.tier_for(_u("researcher", subscription_status="expired")) == "FREE"
        assert ent.tier_for(_u("researcher", subscription_status="past_due")) == "PRO"
        assert ent.tier_for(_u("researcher", subscription_status="active")) == "PRO"

    def test_client_cannot_supply_capabilities(self):
        # Only server-side plan_code/subscription_status/overrides matter.
        u = _u("free", capabilities={"can_use_advanced_ai": True}, tier="PRO_ADVANCED")
        assert not ent.has_capability(u, "can_use_advanced_ai")

    def test_admin_feature_override_grants_capability(self):
        u = _u("researcher", feature_overrides=[{"feature": "citation_monitoring"}])
        assert ent.has_capability(u, "can_use_citation_monitoring")

    def test_super_admin(self):
        assert ent.tier_for({"id": "1", "role": "super_admin", "plan_code": "free"}) == "PRO_ADVANCED"

    def test_upgrade_message_names_plan(self):
        exc = ent.capability_denied("can_accept_collaboration", _u("free"))
        assert exc.status_code == 402
        assert exc.detail["message"] == "Upgrade to Pro to respond to collaboration invitations."
        assert exc.detail["required_plan"] == "researcher"


# ═════════════════════════════ route policy ═════════════════════════════

class TestRoutePolicy:
    FREE_BLOCKED = [
        ("POST", "/api/collaboration-requests", "can_send_collaboration_request"),
        ("PATCH", "/api/collaboration-requests/abc", "can_accept_collaboration"),
        ("POST", "/api/conversations", "can_message_researchers"),
        ("POST", "/api/conversations/abc/messages", "can_message_researchers"),
        ("GET", "/api/network/people", "can_use_research_network"),
        ("GET", "/api/researchers/discover/sections", "can_use_research_network"),
        ("POST", "/api/projects", "can_create_project"),
        ("POST", "/api/workspaces", "can_create_workspace"),
        ("GET", "/api/journals", "can_use_journal_discovery"),
        ("GET", "/api/conferences", "can_use_conference_discovery"),
        ("GET", "/api/grants", "can_use_grant_discovery"),
        ("POST", "/api/teaching/lessons", "can_use_teaching_hub"),
        ("GET", "/api/analytics/me", "can_view_research_analytics"),
        ("GET", "/api/impact/me", "can_view_impact_dashboard"),
        ("GET", "/api/citation-monitoring/alerts", "can_use_citation_monitoring"),
        ("POST", "/api/billing/credit-pack-checkout", "can_purchase_ai_credits"),
    ]
    FREE_ALLOWED = [
        ("GET", "/api/collaboration-requests"),          # see invitations
        ("GET", "/api/conversations"),                   # read-only history
        ("GET", "/api/projects"), ("GET", "/api/workspaces"),
        ("DELETE", "/api/workspaces/0123456789abcdef01234567"),
        ("POST", "/api/workspaces/0123456789abcdef01234567/leave"),
        ("GET", "/api/users/me"), ("PATCH", "/api/users/me"), ("POST", "/api/orcid/sync"),
        ("GET", "/api/profiles/someone"), ("POST", "/api/billing/checkout-session"),
        ("GET", "/api/credits/balance"), ("POST", "/api/session/event"),
    ]

    @pytest.mark.parametrize("method,path,cap", FREE_BLOCKED)
    def test_free_blocked(self, method, path, cap):
        rule = match_rule(method, path)
        assert rule and rule.capability == cap
        assert not ent.has_capability(_u("free"), cap)
        assert ent.has_capability(_u("pro_researcher"), cap)

    @pytest.mark.parametrize("method,path", FREE_ALLOWED)
    def test_free_allowed(self, method, path):
        assert match_rule(method, path) is None

    def test_every_rule_matches_a_real_route(self):
        import logging
        logging.disable(logging.CRITICAL)
        from fastapi.routing import APIRoute
        from server import app
        routes = [(m, re.sub(r"\{[^}]+\}", "0123456789abcdef01234567", r.path))
                  for r in app.routes if isinstance(r, APIRoute) for m in r.methods]
        dead = [r.pattern.pattern for r in RULES
                if not any(m in r.methods and r.pattern.search(p) for m, p in routes)]
        assert not dead, dead


# ═════════════════════════════ pricing & guards ═════════════════════════════

class TestPricing:
    def test_prefix_match_and_cost(self):
        from services.ai.pricing import rates_for, estimate_cost_usd
        assert rates_for("claude-haiku-4-5-20251001") == rates_for("claude-haiku-4-5")
        assert estimate_cost_usd("claude-haiku-4-5-20251001", 1_000_000, 0) == rates_for("claude-haiku-4-5")["input"]
        cached = estimate_cost_usd("claude-sonnet-4-6", 0, 0, cache_read_tokens=1_000_000)
        assert cached == rates_for("claude-sonnet-4-6")["cache_read"]

    def test_unknown_model_never_underpriced(self):
        from services.ai.pricing import rates_for
        assert rates_for("some-new-model")["input"] >= 3.0

    def test_single_price_table(self):
        for path in ("gateway/cost_ledger.py", "services/ai/providers/anthropic_provider.py",
                     "services/ai/providers/openai_provider.py", "services/smart_router/config.py"):
            src = (BACKEND / path).read_text()
            assert "_PRICING: dict" not in src and "_PROVIDER_COSTS" not in src, path
            assert not re.search(r"ProviderCostConfig\(\"[^\"]+\",\s*[\d.]+", src), path


class _Req:
    def __init__(self, **kw):
        self.model = kw.get("model"); self.provider = kw.get("provider")
        self.max_tokens = kw.get("max_tokens", 2048); self.messages = kw.get("messages")
        self.user_id = kw.get("user_id")


class TestCostGuardPreflight:
    @pytest.fixture(autouse=True)
    def _ctx(self):
        from services.credits_service import open_request_context, close_request_context
        tok = open_request_context()
        yield
        close_request_context(tok)

    def _reserve(self, op, plan="researcher", uid=None):
        from services.credits_service import current_request_context
        current_request_context()["reservations"].append(
            {"id": str(ObjectId()), "user_id": uid or str(ObjectId()), "action": op,
             "operation": op, "credits": 1, "plan_code": plan})

    async def test_simple_operation_routes_to_cheap_model(self, monkeypatch):
        from services.ai import cost_guard
        monkeypatch.setattr(cost_guard, "_cloud_provider_is_anthropic", lambda r: True)
        monkeypatch.setattr(cost_guard, "_db", lambda: _NoCounters())
        self._reserve("QUICK_ACADEMIC_REWRITE")
        req = _Req()
        await cost_guard.preflight(req, "sys", "text")
        assert req.model.startswith("claude-haiku")

    async def test_output_clamped_and_input_limit(self, monkeypatch):
        from services.ai import cost_guard
        monkeypatch.setattr(cost_guard, "_db", lambda: _NoCounters())
        self._reserve("FULL_MANUSCRIPT_REVIEW")
        req = _Req(max_tokens=50_000)
        await cost_guard.preflight(req, "sys", "short")
        assert req.max_tokens == 4096
        with pytest.raises(HTTPException) as exc:
            await cost_guard.preflight(_Req(), "sys", "x" * 400_000)
        assert exc.value.status_code == 413
        assert exc.value.detail["code"] == "ai_input_too_large"

    async def test_daily_cost_ceiling(self, monkeypatch):
        from services.ai import cost_guard
        uid = str(ObjectId())
        self._reserve("AI_ASSISTANT_SIMPLE", uid=uid)
        day_id, _ = cost_guard._counter_ids(uid, __import__("datetime").datetime.now(__import__("datetime").timezone.utc))
        monkeypatch.setattr(cost_guard, "_db", lambda: _NoCounters({day_id: 999.0}))
        with pytest.raises(HTTPException) as exc:
            await cost_guard.preflight(_Req(), "sys", "hi")
        assert exc.value.status_code == 429 and exc.value.detail["code"] == "ai_daily_limit"


class _NoCounters:
    def __init__(self, spent=None):
        self.spent = spent or {}
        self.ai_user_cost_counters = self

    def find(self, q):
        ids = q["_id"]["$in"]
        docs = [{"_id": i, "cost_usd": self.spent[i]} for i in ids if i in self.spent]

        class _C:
            async def to_list(self, n):
                return docs
        return _C()


class TestCallLlmNeverReturnsFailureAsContent:
    async def _call(self, monkeypatch, **resp):
        from gateway.schemas import GatewayResponse
        import gateway.gateway as gw

        class _G:
            async def execute(self, request, db=None):
                return GatewayResponse(response="Synaptiq AI is temporarily unavailable.", **resp)
        monkeypatch.setattr(gw, "get_gateway", lambda: _G())
        from services.ai.llm import call_llm
        return await call_llm(system="s", user_msg="u")

    @pytest.mark.parametrize("provider", ["error_fallback", "budget_manager", "emergency_fallback"])
    async def test_provider_failure_raises(self, monkeypatch, provider):
        with pytest.raises(HTTPException) as exc:
            await self._call(monkeypatch, provider=provider)
        assert exc.value.status_code == 503

    async def test_gateway_error_raises(self, monkeypatch):
        with pytest.raises(HTTPException):
            await self._call(monkeypatch, provider="anthropic", validation_status="error")

    async def test_policy_rejection_raises_422(self, monkeypatch):
        with pytest.raises(HTTPException) as exc:
            await self._call(monkeypatch, provider="", validation_status="policy_rejected")
        assert exc.value.status_code == 422


# ═════════════════════════════ webhook helpers ═════════════════════════════

class TestWebhookHelpers:
    def test_sub_period_old_and_new_api(self):
        from routers.billing import _sub_period
        assert _sub_period({"current_period_start": 1, "current_period_end": 2}) == (1, 2)
        assert _sub_period({"items": {"data": [{"current_period_start": 3, "current_period_end": 4}]}}) == (3, 4)

    def test_invoice_subscription_id_shapes(self):
        from routers.billing import _invoice_subscription_id
        assert _invoice_subscription_id({"subscription": "sub_1"}) == "sub_1"
        assert _invoice_subscription_id({"parent": {"subscription_details": {"subscription": "sub_2"}}}) == "sub_2"

    def test_plan_from_price_beats_stale_metadata(self, monkeypatch):
        from routers import billing
        monkeypatch.setattr(billing, "get_plan_by_price_id",
                            lambda pid: ("pro_researcher", "monthly") if pid == "price_adv" else None)
        assert billing._resolve_plan("price_adv", {"plan_code": "researcher"})[0] == "pro_researcher"
        assert billing._resolve_plan("", {"plan_code": "researcher"})[0] == "researcher"
        assert billing._resolve_plan("", {"plan_code": "institution"})[0] is None


# ═════════════════════════════ database-backed ═════════════════════════════

@pytest.fixture
async def mdb(monkeypatch):
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
    db = client[os.environ["MONGODB_DB_NAME"]]
    for target in ("db.get_db", "services.credits_service.get_db", "routers.billing.get_db",
                   "services.product_analytics.get_db", "services.billing_history_service.get_db",
                   "services.audit.get_db", "services.permissions.get_db"):
        monkeypatch.setattr(target, lambda db=db: db)
    import rate_limit
    monkeypatch.setattr(rate_limit, "check_ai_rate_limit", lambda uid: None)
    monkeypatch.setattr("services.credits_service.check_ai_rate_limit", lambda uid: None)
    from services.credits_service import ensure_credit_indexes
    await ensure_credit_indexes(db)
    created: list[str] = []
    db._created = created
    yield db
    if created:
        await db.users.delete_many({"_id": {"$in": [ObjectId(u) for u in created]}})
        for coll in ("credit_reservations", "credit_transactions", "credit_purchases", "subscriptions",
                     "billing_history", "subscription_history", "session_events", "notifications"):
            await db[coll].delete_many({"user_id": {"$in": created}})
    await db.billing_events.delete_many({"stripe_event_id": {"$regex": "^evt_test_"}})
    client.close()


async def _mk_user(db, plan="researcher", sub=200, pack=0, **extra) -> str:
    uid = ObjectId()
    await db.users.insert_one({
        "_id": uid, "email": f"m-{str(uid)[-8:]}@synaptiq-test.io", "role": "user",
        "plan_code": plan, "credits_balance": sub, "credits_pack_balance": pack,
        "credits_monthly_allowance": get_plan(plan)["credits_per_month"],
        "credits_reset_at": "2999-01-01T00:00:00+00:00", **extra,
    })
    db._created.append(str(uid))
    return str(uid)


async def _bal(db, uid):
    u = await db.users.find_one({"_id": ObjectId(uid)})
    return u["credits_balance"], u["credits_pack_balance"]


class TestCreditsDb:
    async def test_free_cannot_use_ai_even_with_purchased_credits(self, mdb):
        from services.credits_service import consume_credits
        uid = await _mk_user(mdb, plan="free", sub=0, pack=120)
        with pytest.raises(HTTPException) as exc:
            await consume_credits(uid, "AI_ASSISTANT_SIMPLE")
        assert exc.value.status_code == 402 and exc.value.detail["code"] == "upgrade_required"
        assert await _bal(mdb, uid) == (0, 120)

    async def test_subscription_first_then_purchased(self, mdb):
        from services.credits_service import consume_credits
        uid = await _mk_user(mdb, sub=17, pack=120)
        r = await consume_credits(uid, "FULL_MANUSCRIPT_REVIEW")
        assert (r["from_monthly"], r["from_pack"], r["consumed"]) == (17, 13, 30)
        assert await _bal(mdb, uid) == (0, 107)
        res = await mdb.credit_reservations.find_one({"_id": ObjectId(r["reservation_id"])})
        assert res["status"] == "RESERVED" and res["operation"] == "FULL_MANUSCRIPT_REVIEW"

    async def test_insufficient_message(self, mdb):
        from services.credits_service import consume_credits
        uid = await _mk_user(mdb, sub=12, pack=0)
        with pytest.raises(HTTPException) as exc:
            await consume_credits(uid, "FULL_MANUSCRIPT_REVIEW")
        assert exc.value.status_code == 402
        assert exc.value.detail["message"] == "This analysis requires 30 AI Credits. You currently have 12."
        assert await _bal(mdb, uid) == (12, 0)

    async def test_concurrent_consumes_never_go_negative(self, mdb):
        from services.credits_service import consume_credits
        uid = await _mk_user(mdb, sub=200, pack=0)

        async def one():
            try:
                await consume_credits(uid, "FULL_MANUSCRIPT_REVIEW")
                return True
            except HTTPException:
                return False
        results = await asyncio.gather(*[one() for _ in range(20)])
        assert sum(results) == 6
        assert await _bal(mdb, uid) == (20, 0)

    async def test_release_is_exactly_once_and_restores_buckets(self, mdb):
        from services.credits_service import consume_credits, release_reservation
        uid = await _mk_user(mdb, sub=10, pack=100)
        r = await consume_credits(uid, "LITERATURE_SYNTHESIS")
        assert await _bal(mdb, uid) == (0, 95)
        results = await asyncio.gather(*[release_reservation(r["reservation_id"], "boom") for _ in range(5)])
        assert sum(results) == 1
        assert await _bal(mdb, uid) == (10, 100)
        refunds = await mdb.credit_transactions.count_documents({"reservation_id": r["reservation_id"], "ledger_type": "AI_REFUND"})
        assert refunds == 1

    async def test_request_finalization(self, mdb):
        from services.credits_service import (
            consume_credits, open_request_context, close_request_context,
            current_request_context, finalize_request_reservations,
        )
        uid = await _mk_user(mdb, sub=100)
        tok = open_request_context()
        try:
            ok = await consume_credits(uid, "AI_ASSISTANT_SIMPLE")
            bad = await consume_credits(uid, "JOURNAL_FIT")
            ctx = current_request_context()
            await finalize_request_reservations({"reservations": ctx["reservations"][:1]}, success=True)
            await finalize_request_reservations({"reservations": ctx["reservations"][1:]}, success=False, reason="http_503")
        finally:
            close_request_context(tok)
        s1 = await mdb.credit_reservations.find_one({"_id": ObjectId(ok["reservation_id"])})
        s2 = await mdb.credit_reservations.find_one({"_id": ObjectId(bad["reservation_id"])})
        assert (s1["status"], s2["status"]) == ("COMPLETED", "RELEASED")
        assert await _bal(mdb, uid) == (98, 0)

    async def test_legacy_refund_after_explicit_refund_is_noop(self, mdb):
        from services.credits_service import (consume_credits, refund_credits, open_request_context,
                                              close_request_context, current_request_context,
                                              finalize_request_reservations)
        uid = await _mk_user(mdb, sub=50)
        tok = open_request_context()
        try:
            await consume_credits(uid, "ai_rewriting")
            assert await refund_credits(uid, "ai_rewriting", reason="engine error") is True
            # Endpoint then fails with 5xx: middleware release must not refund twice.
            await finalize_request_reservations(current_request_context(), success=False)
        finally:
            close_request_context(tok)
        assert await _bal(mdb, uid) == (50, 0)

    async def test_idempotency_key_blocks_double_charge(self, mdb):
        from services.credits_service import consume_credits, release_reservation
        uid = await _mk_user(mdb, sub=100)
        key = "idem-" + str(ObjectId())
        first = await consume_credits(uid, "JOURNAL_FIT", idempotency_key=key)
        with pytest.raises(HTTPException) as exc:
            await consume_credits(uid, "JOURNAL_FIT", idempotency_key=key)
        assert exc.value.status_code == 409
        assert await _bal(mdb, uid) == (95, 0)
        await release_reservation(first["reservation_id"], "failed")
        await consume_credits(uid, "JOURNAL_FIT", idempotency_key=key)   # genuine retry after refund
        assert await _bal(mdb, uid) == (95, 0)

    async def test_renewal_resets_subscription_only_once_per_cycle(self, mdb):
        from services.credits_service import allocate_subscription_credits
        uid = await _mk_user(mdb, sub=17, pack=120)
        assert await allocate_subscription_credits(uid, plan_code="researcher", cycle_key="sub_x:100")
        assert await _bal(mdb, uid) == (200, 120)
        await mdb.users.update_one({"_id": ObjectId(uid)}, {"$set": {"credits_balance": 50}})
        assert not await allocate_subscription_credits(uid, plan_code="researcher", cycle_key="sub_x:100")
        assert await _bal(mdb, uid) == (50, 120)
        assert await allocate_subscription_credits(uid, plan_code="researcher", cycle_key="sub_x:200")
        assert await _bal(mdb, uid) == (200, 120)

    async def test_upgrade_downgrade_not_exploitable(self, mdb):
        from services.credits_service import allocate_subscription_credits, apply_plan_change_credits
        uid = await _mk_user(mdb, sub=0, pack=0)
        await allocate_subscription_credits(uid, plan_code="researcher", cycle_key="sub_y:1")
        await mdb.users.update_one({"_id": ObjectId(uid)}, {"$set": {"credits_balance": 17}})
        await apply_plan_change_credits(uid, from_plan="researcher", to_plan="pro_researcher", cycle_key="sub_y:1")
        assert (await _bal(mdb, uid))[0] == 17 + 550
        await apply_plan_change_credits(uid, from_plan="researcher", to_plan="pro_researcher", cycle_key="sub_y:1")
        assert (await _bal(mdb, uid))[0] == 567          # replay: no second top-up
        await apply_plan_change_credits(uid, from_plan="pro_researcher", to_plan="researcher", cycle_key="sub_y:1")
        assert (await _bal(mdb, uid))[0] == 200          # downgrade caps
        await apply_plan_change_credits(uid, from_plan="researcher", to_plan="pro_researcher", cycle_key="sub_y:1")
        assert (await _bal(mdb, uid))[0] == 200          # cycle already granted 750

    async def test_end_to_free_preserves_purchased(self, mdb):
        from services.credits_service import apply_plan_change_credits
        uid = await _mk_user(mdb, sub=150, pack=120)
        await apply_plan_change_credits(uid, from_plan="researcher", to_plan="free")
        assert await _bal(mdb, uid) == (0, 120)

    async def test_pack_grant_idempotent(self, mdb):
        from services.credits_service import grant_pack_credits
        uid = await _mk_user(mdb, sub=0, pack=0)
        sid = "cs_test_" + str(ObjectId())
        outs = await asyncio.gather(*[grant_pack_credits(uid, pack_code="pack_100", credits=100,
                                                         stripe_checkout_session_id=sid) for _ in range(3)])
        assert sum(o is not None for o in outs) == 1
        assert await _bal(mdb, uid) == (0, 100)


# ─────────────────────── webhook end-to-end (signed) ───────────────────────

WH_SECRET = "whsec_test_monetization"


def _signed_request(event: dict):
    from starlette.requests import Request
    body = json.dumps(event).encode()
    ts = str(int(time.time()))
    sig = hmac.new(WH_SECRET.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    headers = [(b"stripe-signature", f"t={ts},v1={sig}".encode()), (b"content-type", b"application/json")]
    sent = {"done": False}

    async def receive():
        if sent["done"]:
            return {"type": "http.disconnect"}
        sent["done"] = True
        return {"type": "http.request", "body": body, "more_body": False}
    return Request({"type": "http", "method": "POST", "path": "/api/billing/webhook",
                    "headers": headers, "query_string": b""}, receive)


@pytest.fixture
def webhook_env(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WH_SECRET)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    from routers import billing
    monkeypatch.setattr(billing, "get_plan_by_price_id",
                        lambda pid: {"price_pro": ("researcher", "monthly"),
                                     "price_adv": ("pro_researcher", "monthly")}.get(pid))
    return billing


def _evt(type_, obj):
    return {"id": "evt_test_" + str(ObjectId()), "type": type_, "data": {"object": obj}}


def _sub(uid, sub_id, price, start, status="active"):
    return {"id": sub_id, "status": status, "customer": "cus_test", "metadata": {"user_id": uid},
            "items": {"data": [{"price": {"id": price}, "current_period_start": start,
                                "current_period_end": start + 2_592_000}]}}


class TestWebhookDb:
    async def test_subscription_lifecycle(self, mdb, webhook_env):
        billing = webhook_env
        uid = await _mk_user(mdb, plan="free", sub=0, pack=120)
        sub_id = "sub_test_" + str(ObjectId())

        # Free -> Pro
        await billing.stripe_webhook(_signed_request(_evt("customer.subscription.created", _sub(uid, sub_id, "price_pro", 1000))))
        u = await mdb.users.find_one({"_id": ObjectId(uid)})
        assert u["plan_code"] == "researcher" and (u["credits_balance"], u["credits_pack_balance"]) == (200, 120)

        # Initial invoice for the same cycle: no second allocation
        await mdb.users.update_one({"_id": ObjectId(uid)}, {"$set": {"credits_balance": 17}})
        inv = {"id": "in_1", "subscription": sub_id, "billing_reason": "subscription_create", "amount_paid": 999,
               "lines": {"data": [{"type": "subscription", "price": {"id": "price_pro"}, "period": {"start": 1000, "end": 9000}}]}}
        await billing.stripe_webhook(_signed_request(_evt("invoice.paid", inv)))
        assert await _bal(mdb, uid) == (17, 120)

        # Renewal resets subscription credits (17 -> 200), purchased unchanged
        renewal = _evt("invoice.paid", {**inv, "id": "in_2", "billing_reason": "subscription_cycle",
                                        "lines": {"data": [{"type": "subscription", "price": {"id": "price_pro"},
                                                            "period": {"start": 2_593_000, "end": 5_185_000}}]}})
        await billing.stripe_webhook(_signed_request(renewal))
        assert await _bal(mdb, uid) == (200, 120)
        # Exact replay of the same event: ignored
        out = await billing.stripe_webhook(_signed_request(renewal))
        assert out.get("reason") == "duplicate"
        # Same invoice re-sent under a new event id: cycle key prevents a reset
        await mdb.users.update_one({"_id": ObjectId(uid)}, {"$set": {"credits_balance": 5}})
        await billing.stripe_webhook(_signed_request({**renewal, "id": "evt_test_" + str(ObjectId())}))
        assert await _bal(mdb, uid) == (5, 120)

        # Pro -> Pro Advanced mid-cycle: top-up to the cycle's 750 total
        await billing.stripe_webhook(_signed_request(_evt("customer.subscription.updated", _sub(uid, sub_id, "price_adv", 2_593_000))))
        u = await mdb.users.find_one({"_id": ObjectId(uid)})
        assert u["plan_code"] == "pro_researcher" and u["credits_balance"] == 5 + 550

        # Cancellation takes effect: Free, data + purchased credits kept
        await billing.stripe_webhook(_signed_request(_evt("customer.subscription.deleted", _sub(uid, sub_id, "price_adv", 2_593_000, "canceled"))))
        u = await mdb.users.find_one({"_id": ObjectId(uid)})
        assert u["plan_code"] == "free" and (u["credits_balance"], u["credits_pack_balance"]) == (0, 120)

    async def test_credit_pack_fulfilment(self, mdb, webhook_env):
        billing = webhook_env
        uid = await _mk_user(mdb, plan="researcher", sub=10, pack=0)
        sess = {"id": "cs_test_" + str(ObjectId()), "payment_status": "paid", "amount_total": 499,
                "metadata": {"user_id": uid, "kind": "credit_pack", "pack_code": "pack_100", "credits": "999999"}}
        await billing.stripe_webhook(_signed_request(_evt("checkout.session.completed", sess)))
        assert await _bal(mdb, uid) == (10, 100)          # catalogue credits, not metadata
        await billing.stripe_webhook(_signed_request(_evt("checkout.session.completed", sess)))
        assert await _bal(mdb, uid) == (10, 100)          # same session, new event id: no double grant

    async def test_unpaid_session_grants_nothing(self, mdb, webhook_env):
        billing = webhook_env
        uid = await _mk_user(mdb, plan="researcher", sub=10, pack=0)
        sess = {"id": "cs_test_" + str(ObjectId()), "payment_status": "unpaid",
                "metadata": {"user_id": uid, "kind": "credit_pack", "pack_code": "pack_750"}}
        await billing.stripe_webhook(_signed_request(_evt("checkout.session.completed", sess)))
        assert await _bal(mdb, uid) == (10, 0)

    async def test_forged_signature_rejected(self, mdb, webhook_env):
        billing = webhook_env
        req = _signed_request(_evt("checkout.session.completed", {}))
        req.scope["headers"] = [(b"stripe-signature", b"t=1,v1=deadbeef")]
        with pytest.raises(HTTPException) as exc:
            await billing.stripe_webhook(req)
        assert exc.value.status_code == 400


class TestPackCheckoutPaidOnly:
    async def test_free_user_cannot_start_pack_checkout(self):
        from routers.billing import create_credit_pack_checkout
        with pytest.raises(HTTPException) as exc:
            await create_credit_pack_checkout({"pack_code": "pack_100"}, user=_u("free"))
        assert exc.value.status_code == 402

    async def test_annual_billing_rejected(self):
        from routers.billing import create_checkout
        with pytest.raises(HTTPException) as exc:
            await create_checkout({"plan_code": "researcher", "billing_period": "annual"}, user=_u("free"))
        assert exc.value.status_code == 400


# ─────────────────────── middleware (ASGI) ───────────────────────

class TestMiddleware:
    async def _run(self, mw, method, path):
        out = {}

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(msg):
            if msg["type"] == "http.response.start":
                out["status"] = msg["status"]
            elif msg["type"] == "http.response.body":
                out["body"] = msg.get("body", b"")
        await mw({"type": "http", "method": method, "path": path, "headers": [], "query_string": b""}, receive, send)
        return out

    async def test_free_user_gets_402_and_app_not_called(self, monkeypatch):
        from services import monetization_middleware as mm
        called = []

        async def app(scope, receive, send):
            called.append(1)
        free_user = _u("free")

        async def _auth(scope, receive):
            return free_user
        monkeypatch.setattr(mm, "_authenticated_user", _auth)
        monkeypatch.setattr(mm, "_track_denied", lambda *a, **k: asyncio.sleep(0))
        out = await self._run(mm.MonetizationMiddleware(app), "POST", "/api/collaboration-requests")
        assert out["status"] == 402 and not called
        assert json.loads(out["body"])["detail"]["capability"] == "can_send_collaboration_request"

    async def test_failed_request_releases_reservation(self, mdb, monkeypatch):
        from services import monetization_middleware as mm
        from services.credits_service import consume_credits
        uid = await _mk_user(mdb, sub=40)

        async def app(scope, receive, send):
            await consume_credits(uid, "JOURNAL_FIT")
            await send({"type": "http.response.start", "status": 503, "headers": []})
            await send({"type": "http.response.body", "body": b"{}"})
        out = await self._run(mm.MonetizationMiddleware(app), "POST", "/api/ai/journal-fit")
        assert out["status"] == 503
        assert await _bal(mdb, uid) == (40, 0)

    async def test_successful_request_completes_reservation(self, mdb):
        from services import monetization_middleware as mm
        from services.credits_service import consume_credits
        uid = await _mk_user(mdb, sub=40)
        holder = {}

        async def app(scope, receive, send):
            holder["r"] = await consume_credits(uid, "JOURNAL_FIT")
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"{}"})
        await self._run(mm.MonetizationMiddleware(app), "POST", "/api/ai/journal-fit")
        res = await mdb.credit_reservations.find_one({"_id": ObjectId(holder["r"]["reservation_id"])})
        assert res["status"] == "COMPLETED"
        assert await _bal(mdb, uid) == (35, 0)


class TestQuotasDb:
    async def test_free_cannot_create_projects_or_workspaces(self, mdb):
        from services.permissions import assert_quota
        for res in ("projects", "workspaces"):
            with pytest.raises(HTTPException) as exc:
                await assert_quota(_u("free"), res)
            assert exc.value.status_code == 402 and exc.value.detail["code"] == "upgrade_required"

    async def test_free_has_no_general_storage(self, mdb):
        from services.permissions import assert_storage_quota
        with pytest.raises(HTTPException) as exc:
            await assert_storage_quota(_u("free"), 1)
        assert exc.value.status_code == 402

    async def test_workspace_lock_after_downgrade(self, mdb):
        from services.entitlements import locked_workspace_ids
        uid = str(ObjectId())
        ids = []
        for i in range(12):
            r = await mdb.workspaces.insert_one({"owner_id": uid, "name": f"w{i}", "created_at": f"2026-01-{i + 1:02d}"})
            ids.append(str(r.inserted_id))
        try:
            locked = await locked_workspace_ids(_u("researcher", id=uid), mdb)
            assert locked == set(ids[10:])                     # oldest 10 stay writable
            assert await locked_workspace_ids(_u("pro_researcher", id=uid), mdb) == set()
            assert await locked_workspace_ids(_u("free", id=uid), mdb) == set(ids)
            assert await mdb.workspaces.count_documents({"owner_id": uid}) == 12   # nothing deleted
        finally:
            await mdb.workspaces.delete_many({"owner_id": uid})


# ─────────────────────── frontend truth ───────────────────────

class TestFrontendNoHardcodedCosts:
    def test_ai_pages_use_catalogue(self):
        offenders = []
        for p in list((FRONTEND / "pages").rglob("*.jsx")) + list((FRONTEND / "components").rglob("*.jsx")):
            if "admin" in p.parts:
                continue
            # Ignore comment lines (docs may quote examples).
            src = "\n".join(ln for ln in p.read_text().splitlines()
                            if not ln.strip().startswith(("*", "//", "/*")))
            for m in re.finditer(r"(?<![\w€.])(\d{1,3}) (AI |Research )?Credits?\b(?! for €)", src):
                offenders.append(f"{p.relative_to(FRONTEND)}: {m.group(0)}")
        allowed = {"pages/Terms.jsx"}   # contractual text quoting pack sizes
        offenders = [o for o in offenders if o.split(":")[0] not in allowed]
        assert not offenders, offenders

    def test_pricing_page_reads_plans_from_api(self):
        src = (FRONTEND / "pages" / "Pricing.jsx").read_text()
        assert "STATIC_PLANS" not in src and "STATIC_PACKS" not in src
        assert 'api.get("/billing/plans")' in src
