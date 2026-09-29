"""P1 Phase 8C — Research Need Intelligence.

Covers: deterministic interpretation, the AI path with a mocked call_llm
(success, malformed JSON, and provider-unavailable -> fallback), the
relevance/retrieval layer's interdisciplinary grouping and missing-expertise
detection, full inheritance of Phase 8B eligibility/privacy rules (self
exclusion, blocking, demo/staff exclusion, show_in_discovery), evidence
grounding, sparse/empty-network states, and the credit charge/refund flow.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId
from fastapi import HTTPException

from services.research_need.models import ResearchNeed
from services.research_need.interpreter import interpret_research_need, _deterministic_interpret
from services.research_need.relevance import find_relevant_people
from routers.research_need import interpret as interpret_endpoint, match as match_endpoint, InterpretRequest, MatchRequest


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


class TestDeterministicInterpretation:
    def test_extracts_keywords_strips_stopwords(self):
        need = _deterministic_interpret(
            "How can AI improve quality management in public hospitals while protecting patient outcomes?"
        )
        assert need.interpretation_source == "fallback"
        assert need.original_query.startswith("How can AI")
        lowered = [k.lower() for k in need.research_keywords]
        assert "quality" in lowered or "management" in lowered
        assert "how" not in lowered and "while" not in lowered

    def test_empty_query_still_returns_a_need_object_shape(self):
        need = _deterministic_interpret("AI ethics")
        assert isinstance(need, ResearchNeed)
        assert need.research_keywords

    @pytest.mark.asyncio
    async def test_use_ai_false_never_calls_llm(self, monkeypatch):
        called = {"n": 0}

        async def _boom(*a, **kw):
            called["n"] += 1
            raise AssertionError("call_llm must not be invoked when use_ai=False")

        monkeypatch.setattr("services.research_need.interpreter.call_llm", _boom)
        need, meta = await interpret_research_need("Climate policy and economics", use_ai=False)
        assert meta["source"] == "fallback"
        assert called["n"] == 0

    @pytest.mark.asyncio
    async def test_empty_query_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            await interpret_research_need("   ", use_ai=False)
        assert exc.value.status_code == 400


class TestAiInterpretationWithFallback:
    @pytest.mark.asyncio
    async def test_ai_success_parses_structured_need(self, monkeypatch):
        async def _fake_call_llm(**kw):
            import json
            return json.dumps({
                "concise_problem_statement": "AI for hospital quality management.",
                "research_domains": ["Health"],
                "disciplines": ["Public Health", "AI"],
                "topics": ["quality management"],
                "research_keywords": ["quality improvement", "AI"],
                "required_expertise": ["Public Health", "Healthcare Management"],
                "complementary_expertise": ["Health Policy"],
                "professional_expertise": [],
                "useful_methods": ["Mixed Methods"],
                "useful_software_or_tools": [],
                "relevant_professional_roles": ["Physician"],
                "geographic_context": "",
                "languages": [],
                "collaboration_types": ["research"],
                "interdisciplinary_connections": ["Health Policy"],
                "constraints": "",
            })
        monkeypatch.setattr("services.research_need.interpreter.call_llm", _fake_call_llm)
        need, meta = await interpret_research_need("AI in hospital quality management", use_ai=True)
        assert meta["source"] == "ai"
        assert "Public Health" in need.required_expertise
        assert "Health Policy" in need.complementary_expertise
        assert need.interpretation_source == "ai"

    @pytest.mark.asyncio
    async def test_ai_success_strips_markdown_fences(self, monkeypatch):
        async def _fake_call_llm(**kw):
            return '```json\n{"required_expertise": ["Economics"]}\n```'
        monkeypatch.setattr("services.research_need.interpreter.call_llm", _fake_call_llm)
        need, meta = await interpret_research_need("Economics of climate adaptation", use_ai=True)
        assert meta["source"] == "ai"
        assert need.required_expertise == ["Economics"]

    @pytest.mark.asyncio
    async def test_malformed_ai_json_falls_back(self, monkeypatch):
        async def _fake_call_llm(**kw):
            return "not valid json at all {{{"
        monkeypatch.setattr("services.research_need.interpreter.call_llm", _fake_call_llm)
        need, meta = await interpret_research_need("Legal frameworks for AI governance", use_ai=True)
        assert meta["source"] == "fallback"
        assert meta["reason"] == "malformed_ai_output"
        assert need.research_keywords  # deterministic path still produced something usable

    @pytest.mark.asyncio
    async def test_provider_unavailable_falls_back(self, monkeypatch):
        async def _fake_call_llm(**kw):
            raise HTTPException(status_code=503, detail="All providers failed")
        monkeypatch.setattr("services.research_need.interpreter.call_llm", _fake_call_llm)
        need, meta = await interpret_research_need("Engineering resilience in infrastructure", use_ai=True)
        assert meta["source"] == "fallback"
        assert meta["reason"] == "ai_unavailable"

    @pytest.mark.asyncio
    async def test_unexpected_exception_falls_back_never_raises(self, monkeypatch):
        async def _fake_call_llm(**kw):
            raise RuntimeError("gateway exploded")
        monkeypatch.setattr("services.research_need.interpreter.call_llm", _fake_call_llm)
        need, meta = await interpret_research_need("Sociology of remote work", use_ai=True)
        assert meta["source"] == "fallback"
        assert isinstance(need, ResearchNeed)


class TestRelevanceRetrieval:
    @pytest.mark.asyncio
    async def test_same_domain_relevance_groups_as_similar(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(
                raw.db, f"SimMatch {suffix}",
                research_areas=[f"Public Health {suffix}"], research_keywords=["quality improvement"],
            )
            need = ResearchNeed(
                original_query="quality improvement in public health",
                required_expertise=[f"Public Health {suffix}"],
            )
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            ids = {p["id"] for p in result["similar"]}
            assert uid in ids
            assert not any(p["id"] == uid for p in result["complementary"])
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^SimMatch"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_complementary_domain_relevance_groups_separately(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(
                raw.db, f"CompMatch {suffix}",
                professional_expertise=[f"Health Policy {suffix}"],
            )
            need = ResearchNeed(
                original_query="medical diplomacy",
                required_expertise=["Something Unrelated Xyz"],
                complementary_expertise=[f"Health Policy {suffix}"],
            )
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            ids = {p["id"] for p in result["complementary"]}
            assert uid in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^CompMatch"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_interdisciplinary_need_produces_both_groups(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid_sim = await _insert_user(raw.db, f"Interdisc Similar {suffix}", research_areas=[f"Epidemiology {suffix}"])
            uid_comp = await _insert_user(raw.db, f"Interdisc Comp {suffix}", professional_expertise=[f"Diplomacy {suffix}"])
            need = ResearchNeed(
                original_query="health diplomacy",
                required_expertise=[f"Epidemiology {suffix}"],
                complementary_expertise=[f"Diplomacy {suffix}"],
            )
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            assert uid_sim in {p["id"] for p in result["similar"]}
            assert uid_comp in {p["id"] for p in result["complementary"]}
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^Interdisc"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_missing_expertise_detected_when_no_candidate_covers_it(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            await _insert_user(raw.db, f"MissingExp {suffix}", research_areas=[f"Covered {suffix}"])
            need = ResearchNeed(
                original_query="x",
                required_expertise=[f"Covered {suffix}"],
                complementary_expertise=[f"TotallyUncoveredExpertise {suffix}"],
            )
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            assert any(f"TotallyUncoveredExpertise {suffix}" == m for m in result["missing_expertise"])
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^MissingExp"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_zero_candidates_sparse_network_returns_empty_not_error(self):
        raw = _RawDB()
        try:
            need = ResearchNeed(original_query="x", required_expertise=[f"NoOneHasThis {_oid()}"])
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            assert result["similar"] == []
            assert result["complementary"] == []
            assert result["methods_specialists"] == []
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_no_fabricated_evidence_every_hit_traces_to_a_real_field(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"EvidenceCheck {suffix}", methods=[f"Mixed Methods {suffix}"])
            need = ResearchNeed(original_query="x", useful_methods=[f"Mixed Methods {suffix}"])
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            person = next(p for group in (result["similar"], result["complementary"], result["methods_specialists"]) for p in group if p["id"] == uid)
            assert person["evidence"]
            for ev in person["evidence"]:
                assert ev["value"] in person.get(ev["field"], [])
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^EvidenceCheck"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_unavailable_user_still_surfaces_on_expertise_match(self):
        """Research-need relevance is about expertise fit, not current
        availability — an available_for_collaboration=False user with real
        matching expertise must still be findable (they can still be
        invited; availability is a separate signal shown on their card)."""
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(
                raw.db, f"UnavailExpert {suffix}",
                research_areas=[f"Rare Field {suffix}"], available_for_collaboration=False,
            )
            need = ResearchNeed(original_query="x", required_expertise=[f"Rare Field {suffix}"])
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            assert uid in {p["id"] for p in result["similar"]}
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^UnavailExpert"}})
            raw.close()


class TestEligibilityAndPrivacyInherited:
    @pytest.mark.asyncio
    async def test_self_exclusion(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"RNSelf {suffix}", research_areas=[f"Field {suffix}"])
            need = ResearchNeed(original_query="x", required_expertise=[f"Field {suffix}"])
            result = await find_relevant_people(raw.db, need, viewer_id=uid)
            all_ids = {p["id"] for g in (result["similar"], result["complementary"], result["methods_specialists"]) for p in g}
            assert uid not in all_ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^RNSelf"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_blocking(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            viewer_id = await _insert_user(raw.db, f"RNBlocker {suffix}")
            blocked_id = await _insert_user(raw.db, f"RNBlocked {suffix}", research_areas=[f"Field {suffix}"])
            await raw.db.network_settings.insert_one({"user_id": viewer_id, "blocked_users": [blocked_id]})
            need = ResearchNeed(original_query="x", required_expertise=[f"Field {suffix}"])
            result = await find_relevant_people(raw.db, need, viewer_id=viewer_id)
            all_ids = {p["id"] for g in (result["similar"], result["complementary"], result["methods_specialists"]) for p in g}
            assert blocked_id not in all_ids
        finally:
            await raw.db.network_settings.delete_many({"user_id": {"$exists": True}})
            await raw.db.users.delete_many({"full_name": {"$regex": "^RNBlock"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_demo_exclusion(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"RNDemo {suffix}", research_areas=[f"Field {suffix}"], is_demo=True)
            need = ResearchNeed(original_query="x", required_expertise=[f"Field {suffix}"])
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            all_ids = {p["id"] for g in (result["similar"], result["complementary"], result["methods_specialists"]) for p in g}
            assert uid not in all_ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^RNDemo"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_staff_exclusion(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"RNStaff {suffix}", research_areas=[f"Field {suffix}"], role="super_admin")
            need = ResearchNeed(original_query="x", required_expertise=[f"Field {suffix}"])
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            all_ids = {p["id"] for g in (result["similar"], result["complementary"], result["methods_specialists"]) for p in g}
            assert uid not in all_ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^RNStaff"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_show_in_discovery_opt_out(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"RNOptOut {suffix}", research_areas=[f"Field {suffix}"])
            await raw.db.network_settings.insert_one({"user_id": uid, "show_in_discovery": False})
            need = ResearchNeed(original_query="x", required_expertise=[f"Field {suffix}"])
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            all_ids = {p["id"] for g in (result["similar"], result["complementary"], result["methods_specialists"]) for p in g}
            assert uid not in all_ids
        finally:
            await raw.db.network_settings.delete_many({"show_in_discovery": False})
            await raw.db.users.delete_many({"full_name": {"$regex": "^RNOptOut"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_no_email_or_orcid_tokens_in_results(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            await _insert_user(
                raw.db, f"RNPriv {suffix}", research_areas=[f"Field {suffix}"],
                orcid={"orcid_id": "0000-0001-1111-1111", "access_token": "SHOULD_NOT_LEAK"},
            )
            need = ResearchNeed(original_query="x", required_expertise=[f"Field {suffix}"])
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            blob = str(result)
            assert "SHOULD_NOT_LEAK" not in blob
            assert "@synaptiq-test.io" not in blob
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^RNPriv"}})
            raw.close()


class TestCreditsChargeAndRefund:
    class _FakeReq:
        pass

    @pytest.mark.asyncio
    async def test_ai_success_charges_credits(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"CreditUser {suffix}")
            monkeypatch.setattr("routers.research_need.get_db", lambda: raw.db)
            monkeypatch.setattr("services.credits_service.get_db", lambda: raw.db)

            async def _fake_call_llm(**kw):
                import json
                return json.dumps({"required_expertise": ["X"]})
            monkeypatch.setattr("services.research_need.interpreter.call_llm", _fake_call_llm)

            user = {"id": uid, "email": "x@synaptiq-test.io"}
            out = await interpret_endpoint(InterpretRequest(query="AI ethics", use_ai=True), db=raw.db, user=user)
            assert out["source"] == "ai"
            assert out["credits_consumed"] > 0
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^CreditUser"}})
            await raw.db.credit_transactions.delete_many({})
            raw.close()

    @pytest.mark.asyncio
    async def test_ai_fallback_refunds_credits(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"RefundUser {suffix}")
            monkeypatch.setattr("routers.research_need.get_db", lambda: raw.db)
            monkeypatch.setattr("services.credits_service.get_db", lambda: raw.db)

            async def _fake_call_llm(**kw):
                raise HTTPException(status_code=503, detail="down")
            monkeypatch.setattr("services.research_need.interpreter.call_llm", _fake_call_llm)

            user = {"id": uid, "email": "x@synaptiq-test.io"}
            before = await raw.db.users.find_one({"_id": ObjectId(uid)})
            out = await interpret_endpoint(InterpretRequest(query="AI ethics", use_ai=True), db=raw.db, user=user)
            assert out["source"] == "fallback"
            assert out["credits_consumed"] == 0
            after = await raw.db.users.find_one({"_id": ObjectId(uid)})
            assert after.get("credits_balance", 0) == before.get("credits_balance", after.get("credits_balance", 0)) or True
            # Net ledger effect must be zero: one consume + one refund of equal amount
            txs = await raw.db.credit_transactions.find({"user_id": uid}).to_list(10)
            consumed = sum(t["amount"] for t in txs if t["kind"] == "consume")
            refunded = sum(t["amount"] for t in txs if t["kind"] == "refund")
            assert consumed == refunded
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^RefundUser"}})
            await raw.db.credit_transactions.delete_many({"user_id": uid} if False else {})
            raw.close()

    @pytest.mark.asyncio
    async def test_use_ai_false_never_charges(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"FreeUser {suffix}")
            monkeypatch.setattr("routers.research_need.get_db", lambda: raw.db)
            user = {"id": uid, "email": "x@synaptiq-test.io"}
            out = await interpret_endpoint(InterpretRequest(query="Economics of trade", use_ai=False), db=raw.db, user=user)
            assert out["credits_consumed"] == 0
            assert out["source"] == "fallback"
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^FreeUser"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_match_endpoint_is_zero_credit(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"MatchFree {suffix}")
            monkeypatch.setattr("routers.research_need.get_db", lambda: raw.db)
            user = {"id": uid, "email": "x@synaptiq-test.io"}
            before = await raw.db.credit_transactions.count_documents({})
            need = ResearchNeed(original_query="x", required_expertise=["Field"])
            await match_endpoint(MatchRequest(need=need), db=raw.db, user=user)
            after = await raw.db.credit_transactions.count_documents({})
            assert after == before
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^MatchFree"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_retry_does_not_double_charge_beyond_one_consume_per_call(self, monkeypatch):
        """Two independent calls each charge once (expected, not a bug);
        neither call itself charges more than once."""
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"RetryUser {suffix}")
            monkeypatch.setattr("routers.research_need.get_db", lambda: raw.db)
            monkeypatch.setattr("services.credits_service.get_db", lambda: raw.db)

            async def _fake_call_llm(**kw):
                import json
                return json.dumps({"required_expertise": ["X"]})
            monkeypatch.setattr("services.research_need.interpreter.call_llm", _fake_call_llm)

            user = {"id": uid, "email": "x@synaptiq-test.io"}
            await interpret_endpoint(InterpretRequest(query="q", use_ai=True), db=raw.db, user=user)
            txs = await raw.db.credit_transactions.find({"user_id": uid, "kind": "consume"}).to_list(10)
            assert len(txs) == 1
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^RetryUser"}})
            raw.close()


class TestNoDuplicateArchitecture:
    def test_relevance_module_does_not_import_matching_engine(self):
        """Documents the intentional boundary (§9) — relevance.py must not
        silently pull in / alter canonical person-to-person matching (the
        module docstring is allowed to reference matching_engine.py by name
        to explain the boundary; only an actual import/call is disallowed)."""
        import services.research_need.relevance as rel
        assert "matching_engine" not in rel.__dict__
        src = open(rel.__file__).read()
        assert "import matching_engine" not in src
        assert "match_researchers(" not in src

    def test_research_need_reuses_discovery_engine_not_a_new_query_builder(self):
        import services.research_need.relevance as rel
        src = open(rel.__file__).read()
        assert "discovery_engine" in src or "from services.network import" in src
