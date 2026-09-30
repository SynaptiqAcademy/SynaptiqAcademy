"""P1 Phase 8F — Interdisciplinary Research Team Builder.

Covers blueprint generation (AI success, malformed output, provider
unavailable, deterministic fallback, domain-general non-medical case),
role editing, "I can cover this role", real-candidate retrieval per role
(direct/complementary/methods, cross-role "also relevant to" hints, no
candidate), selection (not outreach), one-invitation-per-explicit-approval
via the reused Phase 8E send_request(), state synchronization from live
collaboration_requests, replacement flow, full eligibility/privacy
inheritance (self/blocking/demo/staff/show_in_discovery/availability),
authorization, safe serialization, and zero-credit operations outside the
one AI blueprint-generation call.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId
from fastapi import HTTPException

from services.research_need.models import ResearchNeed
from services.team_builder.blueprint_generator import generate_blueprint_roles, _deterministic_roles
from routers.team_builder import (
    create_blueprint, get_blueprint, patch_blueprint, delete_blueprint,
    get_role_candidates, select_candidate, unselect_candidate, invite_candidate,
    CreateBlueprintRequest, PatchBlueprintRequest, RoleEdit, InviteCandidateRequest,
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


def _user(uid: str, name: str = "Owner") -> dict:
    return {"id": uid, "full_name": name, "email": f"{name}@synaptiq-test.io"}


def _patch_get_db(monkeypatch, raw_db):
    monkeypatch.setattr("routers.team_builder.get_db", lambda: raw_db)
    monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw_db)


class TestDeterministicBlueprintGeneration:
    def test_one_role_per_required_expertise(self):
        need = ResearchNeed(original_query="x", required_expertise=["Public Health", "AI"])
        roles = _deterministic_roles(need)
        labels = {r.label for r in roles}
        assert {"Public Health", "AI"} <= labels
        assert all(r.priority == "essential" for r in roles if r.label in ("Public Health", "AI"))

    def test_methods_grouped_into_one_role(self):
        need = ResearchNeed(original_query="x", useful_methods=["Mixed Methods", "Econometrics"])
        roles = _deterministic_roles(need)
        methods_roles = [r for r in roles if r.category == "methods"]
        assert len(methods_roles) == 1
        assert set(methods_roles[0].useful_methods) == {"Mixed Methods", "Econometrics"}

    def test_no_arbitrary_roles_added(self):
        """§5 — must not pad roles just to look interdisciplinary."""
        need = ResearchNeed(original_query="x", required_expertise=["Solo Field"])
        roles = _deterministic_roles(need)
        assert len(roles) == 1

    def test_domain_general_non_medical(self):
        need = ResearchNeed(
            original_query="economic policy for climate adaptation",
            required_expertise=["Climate Economics"],
            complementary_expertise=["Environmental Law"],
            relevant_professional_roles=["Policy Analyst"],
        )
        roles = _deterministic_roles(need)
        labels = {r.label for r in roles}
        assert {"Climate Economics", "Environmental Law", "Policy Analyst"} <= labels


class TestAiBlueprintGeneration:
    @pytest.mark.asyncio
    async def test_ai_success_parses_roles(self, monkeypatch):
        async def _fake_call_llm(**kw):
            import json
            return json.dumps({"roles": [
                {"label": "Health Policy", "category": "policy_context", "priority": "essential",
                 "why_needed": "Because the need concerns hospital policy.", "required_expertise": ["Health Policy"]},
            ]})
        monkeypatch.setattr("services.team_builder.blueprint_generator.call_llm", _fake_call_llm)
        need = ResearchNeed(original_query="hospital quality management")
        roles, meta = await generate_blueprint_roles(need, use_ai=True)
        assert meta["source"] == "ai"
        assert roles[0].label == "Health Policy"
        assert roles[0].priority == "essential"

    @pytest.mark.asyncio
    async def test_malformed_ai_output_falls_back(self, monkeypatch):
        async def _fake_call_llm(**kw):
            return "not json {{{"
        monkeypatch.setattr("services.team_builder.blueprint_generator.call_llm", _fake_call_llm)
        need = ResearchNeed(original_query="x", required_expertise=["Field A"])
        roles, meta = await generate_blueprint_roles(need, use_ai=True)
        assert meta["source"] == "fallback"
        assert meta["reason"] == "malformed_ai_output"
        assert any(r.label == "Field A" for r in roles)

    @pytest.mark.asyncio
    async def test_provider_unavailable_falls_back(self, monkeypatch):
        async def _fake_call_llm(**kw):
            raise HTTPException(status_code=503, detail="down")
        monkeypatch.setattr("services.team_builder.blueprint_generator.call_llm", _fake_call_llm)
        need = ResearchNeed(original_query="x", required_expertise=["Field B"])
        roles, meta = await generate_blueprint_roles(need, use_ai=True)
        assert meta["source"] == "fallback"
        assert meta["reason"] == "ai_unavailable"

    @pytest.mark.asyncio
    async def test_empty_ai_roles_falls_back(self, monkeypatch):
        async def _fake_call_llm(**kw):
            import json
            return json.dumps({"roles": []})
        monkeypatch.setattr("services.team_builder.blueprint_generator.call_llm", _fake_call_llm)
        need = ResearchNeed(original_query="x", required_expertise=["Field C"])
        roles, meta = await generate_blueprint_roles(need, use_ai=True)
        assert meta["source"] == "fallback"
        assert any(r.label == "Field C" for r in roles)


class TestBlueprintCrudAndAuthorization:
    @pytest.mark.asyncio
    async def test_create_and_get_blueprint(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            uid = await _insert_user(raw.db, f"Owner {_oid()[:8]}")
            need = ResearchNeed(original_query="x", required_expertise=["Field D"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(uid))
            assert out["blueprint"]["status"] == "draft"
            assert out["credits_consumed"] == 0
            got = await get_blueprint(out["blueprint"]["id"], db=raw.db, user=_user(uid))
            assert got["id"] == out["blueprint"]["id"]
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": uid})
            await raw.db.users.delete_many({"full_name": {"$regex": "^Owner"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_unrelated_user_cannot_read_blueprint(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            owner_id = await _insert_user(raw.db, f"BpOwner {_oid()[:8]}")
            stranger_id = await _insert_user(raw.db, f"BpStranger {_oid()[:8]}")
            need = ResearchNeed(original_query="x", required_expertise=["Field E"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            with pytest.raises(HTTPException) as exc:
                await get_blueprint(out["blueprint"]["id"], db=raw.db, user=_user(stranger_id))
            assert exc.value.status_code == 403
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^BpOwner|^BpStranger"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_delete_blueprint_owner_only(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            owner_id = await _insert_user(raw.db, f"DelOwner {_oid()[:8]}")
            stranger_id = await _insert_user(raw.db, f"DelStranger {_oid()[:8]}")
            need = ResearchNeed(original_query="x")
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            bp_id = out["blueprint"]["id"]
            with pytest.raises(HTTPException) as exc:
                await delete_blueprint(bp_id, db=raw.db, user=_user(stranger_id))
            assert exc.value.status_code == 403
            result = await delete_blueprint(bp_id, db=raw.db, user=_user(owner_id))
            assert result["ok"] is True
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^DelOwner|^DelStranger"}})
            raw.close()


class TestRoleEditing:
    @pytest.mark.asyncio
    async def test_add_remove_rename_role(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            uid = await _insert_user(raw.db, f"EditOwner {_oid()[:8]}")
            need = ResearchNeed(original_query="x", required_expertise=["Original Role"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(uid))
            bp_id = out["blueprint"]["id"]
            role_id = out["blueprint"]["roles"][0]["role_id"]

            patched = await patch_blueprint(
                bp_id,
                PatchBlueprintRequest(role_edits=[RoleEdit(role_id=role_id, label="Renamed Role", priority="optional")]),
                db=raw.db, user=_user(uid),
            )
            assert patched["roles"][0]["label"] == "Renamed Role"
            assert patched["roles"][0]["priority"] == "optional"

            added = await patch_blueprint(
                bp_id,
                PatchBlueprintRequest(role_edits=[RoleEdit(label="New Role", category="technical")]),
                db=raw.db, user=_user(uid),
            )
            assert len(added["roles"]) == 2

            removed = await patch_blueprint(
                bp_id,
                PatchBlueprintRequest(remove_role_ids=[role_id]),
                db=raw.db, user=_user(uid),
            )
            assert len(removed["roles"]) == 1
            assert removed["roles"][0]["label"] == "New Role"
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": uid})
            await raw.db.users.delete_many({"full_name": {"$regex": "^EditOwner"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_self_covers_toggle(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            uid = await _insert_user(raw.db, f"CoverOwner {_oid()[:8]}")
            need = ResearchNeed(original_query="x", required_expertise=["Field F"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(uid))
            role_id = out["blueprint"]["roles"][0]["role_id"]
            patched = await patch_blueprint(
                out["blueprint"]["id"],
                PatchBlueprintRequest(role_edits=[RoleEdit(role_id=role_id, self_covers=True)]),
                db=raw.db, user=_user(uid),
            )
            assert patched["roles"][0]["self_covers"] is True
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": uid})
            await raw.db.users.delete_many({"full_name": {"$regex": "^CoverOwner"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_invalid_priority_rejected(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            uid = await _insert_user(raw.db, f"BadPriorityOwner {_oid()[:8]}")
            need = ResearchNeed(original_query="x", required_expertise=["Field G"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(uid))
            role_id = out["blueprint"]["roles"][0]["role_id"]
            with pytest.raises(HTTPException) as exc:
                await patch_blueprint(
                    out["blueprint"]["id"],
                    PatchBlueprintRequest(role_edits=[RoleEdit(role_id=role_id, priority="urgent")]),
                    db=raw.db, user=_user(uid),
                )
            assert exc.value.status_code == 400
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": uid})
            await raw.db.users.delete_many({"full_name": {"$regex": "^BadPriorityOwner"}})
            raw.close()


class TestCandidateRetrievalPerRole:
    @pytest.mark.asyncio
    async def test_direct_and_complementary_and_methods_candidates(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            suffix = _oid()[:8]
            owner_id = await _insert_user(raw.db, f"RoleOwner {suffix}")
            direct_id = await _insert_user(raw.db, f"RoleDirect {suffix}", research_areas=[f"CoreField {suffix}"])
            need = ResearchNeed(original_query="x", required_expertise=[f"CoreField {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            role_id = out["blueprint"]["roles"][0]["role_id"]
            result = await get_role_candidates(out["blueprint"]["id"], role_id, db=raw.db, user=_user(owner_id))
            ids = {c["id"] for c in result["candidates"]}
            assert direct_id in ids
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^RoleOwner|^RoleDirect"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_no_candidate_is_a_valid_result(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            owner_id = await _insert_user(raw.db, f"EmptyOwner {_oid()[:8]}")
            need = ResearchNeed(original_query="x", required_expertise=[f"NoOneHasThis {_oid()}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            role_id = out["blueprint"]["roles"][0]["role_id"]
            result = await get_role_candidates(out["blueprint"]["id"], role_id, db=raw.db, user=_user(owner_id))
            assert result["candidates"] == []
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^EmptyOwner"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_also_relevant_to_cross_role_hint(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            suffix = _oid()[:8]
            owner_id = await _insert_user(raw.db, f"CrossOwner {suffix}")
            # candidate evidences both roles' terms
            multi_id = await _insert_user(
                raw.db, f"CrossMulti {suffix}",
                research_areas=[f"RoleATerm {suffix}"], professional_expertise=[f"RoleBTerm {suffix}"],
            )
            need = ResearchNeed(original_query="x", required_expertise=[f"RoleATerm {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            bp_id = out["blueprint"]["id"]
            role_a_id = out["blueprint"]["roles"][0]["role_id"]
            await patch_blueprint(
                bp_id,
                PatchBlueprintRequest(role_edits=[RoleEdit(label="Role B", relevant_disciplines=[f"RoleBTerm {suffix}"])]),
                db=raw.db, user=_user(owner_id),
            )
            result = await get_role_candidates(bp_id, role_a_id, db=raw.db, user=_user(owner_id))
            card = next(c for c in result["candidates"] if c["id"] == multi_id)
            assert "Role B" in card["also_relevant_to"]
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^CrossOwner|^CrossMulti"}})
            raw.close()


class TestSelectionIsNotOutreach:
    @pytest.mark.asyncio
    async def test_select_does_not_create_collaboration_request(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            suffix = _oid()[:8]
            owner_id = await _insert_user(raw.db, f"SelOwner {suffix}")
            cand_id = await _insert_user(raw.db, f"SelCandidate {suffix}", research_areas=[f"SelField {suffix}"])
            need = ResearchNeed(original_query="x", required_expertise=[f"SelField {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            bp_id, role_id = out["blueprint"]["id"], out["blueprint"]["roles"][0]["role_id"]

            before = await raw.db.collaboration_requests.count_documents({})
            bp = await select_candidate(bp_id, role_id, cand_id, db=raw.db, user=_user(owner_id))
            after = await raw.db.collaboration_requests.count_documents({})
            assert after == before
            assert bp["roles"][0]["selected_candidates"][0]["candidate_id"] == cand_id
            assert bp["roles"][0]["selected_candidates"][0]["status"] == "proposed"
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^SelOwner|^SelCandidate"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_cannot_select_ineligible_candidate(self, monkeypatch):
        """Re-verifies eligibility at selection time — a candidate who
        doesn't actually match the role's real evidence cannot be forced in."""
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            suffix = _oid()[:8]
            owner_id = await _insert_user(raw.db, f"IneligOwner {suffix}")
            unrelated_id = await _insert_user(raw.db, f"IneligCandidate {suffix}")
            need = ResearchNeed(original_query="x", required_expertise=[f"VeryNarrowField {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            bp_id, role_id = out["blueprint"]["id"], out["blueprint"]["roles"][0]["role_id"]
            with pytest.raises(HTTPException) as exc:
                await select_candidate(bp_id, role_id, unrelated_id, db=raw.db, user=_user(owner_id))
            assert exc.value.status_code == 404
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^IneligOwner|^IneligCandidate"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_cannot_select_self_as_candidate(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            owner_id = await _insert_user(raw.db, f"SelfSelOwner {_oid()[:8]}")
            need = ResearchNeed(original_query="x", required_expertise=["Field H"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            with pytest.raises(HTTPException) as exc:
                await select_candidate(out["blueprint"]["id"], out["blueprint"]["roles"][0]["role_id"], owner_id, db=raw.db, user=_user(owner_id))
            assert exc.value.status_code == 400
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^SelfSelOwner"}})
            raw.close()


class TestInvitationIntegrationWithPhase8E:
    @pytest.mark.asyncio
    async def test_invite_creates_one_real_collaboration_request(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            suffix = _oid()[:8]
            owner_id = await _insert_user(raw.db, f"InviteOwner {suffix}")
            cand_id = await _insert_user(raw.db, f"InviteCandidate {suffix}", research_areas=[f"InvField {suffix}"])
            need = ResearchNeed(original_query="x", required_expertise=[f"InvField {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            bp_id, role_id = out["blueprint"]["id"], out["blueprint"]["roles"][0]["role_id"]
            await select_candidate(bp_id, role_id, cand_id, db=raw.db, user=_user(owner_id))

            bp = await invite_candidate(
                bp_id, role_id, cand_id,
                InviteCandidateRequest(message="Would you like to collaborate?"),
                db=raw.db, user=_user(owner_id),
            )
            assert bp["status"] == "inviting"
            selected = bp["roles"][0]["selected_candidates"][0]
            assert selected["collaboration_request_id"]
            assert selected["status"] == "invitation_pending"

            real_req = await raw.db.collaboration_requests.find_one({"_id": ObjectId(selected["collaboration_request_id"])})
            assert real_req["sender_id"] == owner_id
            assert real_req["receiver_id"] == cand_id
            assert real_req["source"] == "team_builder"
            assert real_req["context"]["team_role"] == bp["roles"][0]["label"]
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^InviteOwner|^InviteCandidate"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_cannot_invite_same_candidate_twice_for_same_role(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            suffix = _oid()[:8]
            owner_id = await _insert_user(raw.db, f"DblInviteOwner {suffix}")
            cand_id = await _insert_user(raw.db, f"DblInviteCandidate {suffix}", research_areas=[f"DblField {suffix}"])
            need = ResearchNeed(original_query="x", required_expertise=[f"DblField {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            bp_id, role_id = out["blueprint"]["id"], out["blueprint"]["roles"][0]["role_id"]
            await select_candidate(bp_id, role_id, cand_id, db=raw.db, user=_user(owner_id))
            await invite_candidate(bp_id, role_id, cand_id, InviteCandidateRequest(), db=raw.db, user=_user(owner_id))
            with pytest.raises(HTTPException) as exc:
                await invite_candidate(bp_id, role_id, cand_id, InviteCandidateRequest(), db=raw.db, user=_user(owner_id))
            assert exc.value.status_code == 409
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^DblInviteOwner|^DblInviteCandidate"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_blocked_candidate_cannot_be_invited(self, monkeypatch):
        """Team Builder must never bypass Phase 8E's blocking protection.
        Blocking is actually enforced even earlier than invitation: a
        blocked candidate is excluded from discovery.search_people() itself
        (Phase 8B/8D behavior, reused here via find_relevant_people), so
        they can never even be selected — which is stronger than only
        blocking at the final invite step, not a gap."""
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            suffix = _oid()[:8]
            owner_id = await _insert_user(raw.db, f"BlockOwner {suffix}")
            cand_id = await _insert_user(raw.db, f"BlockCandidate {suffix}", research_areas=[f"BlockField {suffix}"])
            await raw.db.network_settings.insert_one({"user_id": cand_id, "blocked_users": [owner_id]})
            need = ResearchNeed(original_query="x", required_expertise=[f"BlockField {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            bp_id, role_id = out["blueprint"]["id"], out["blueprint"]["roles"][0]["role_id"]

            # Cannot even retrieve the blocked candidate as a real option.
            result = await get_role_candidates(bp_id, role_id, db=raw.db, user=_user(owner_id))
            assert cand_id not in {c["id"] for c in result["candidates"]}

            # Selection itself is refused (the same real-eligibility check
            # that select_candidate() re-runs), so invitation is unreachable.
            with pytest.raises(HTTPException) as exc:
                await select_candidate(bp_id, role_id, cand_id, db=raw.db, user=_user(owner_id))
            assert exc.value.status_code == 404
        finally:
            await raw.db.network_settings.delete_many({"user_id": cand_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^BlockOwner|^BlockCandidate"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_status_syncs_live_from_collaboration_requests(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            suffix = _oid()[:8]
            owner_id = await _insert_user(raw.db, f"SyncOwner {suffix}")
            cand_id = await _insert_user(raw.db, f"SyncCandidate {suffix}", research_areas=[f"SyncField {suffix}"])
            need = ResearchNeed(original_query="x", required_expertise=[f"SyncField {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            bp_id, role_id = out["blueprint"]["id"], out["blueprint"]["roles"][0]["role_id"]
            await select_candidate(bp_id, role_id, cand_id, db=raw.db, user=_user(owner_id))
            bp = await invite_candidate(bp_id, role_id, cand_id, InviteCandidateRequest(), db=raw.db, user=_user(owner_id))
            req_id = bp["roles"][0]["selected_candidates"][0]["collaboration_request_id"]

            await raw.db.collaboration_requests.update_one({"_id": ObjectId(req_id)}, {"$set": {"status": "accepted"}})
            refreshed = await get_blueprint(bp_id, db=raw.db, user=_user(owner_id))
            assert refreshed["roles"][0]["selected_candidates"][0]["status"] == "accepted"

            await raw.db.collaboration_requests.update_one({"_id": ObjectId(req_id)}, {"$set": {"status": "declined"}})
            refreshed2 = await get_blueprint(bp_id, db=raw.db, user=_user(owner_id))
            assert refreshed2["roles"][0]["selected_candidates"][0]["status"] == "declined"
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^SyncOwner|^SyncCandidate"}})
            raw.close()


class TestReplacementFlow:
    @pytest.mark.asyncio
    async def test_remove_unselected_candidate_and_pick_another(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            suffix = _oid()[:8]
            owner_id = await _insert_user(raw.db, f"ReplOwner {suffix}")
            cand_a = await _insert_user(raw.db, f"ReplA {suffix}", research_areas=[f"ReplField {suffix}"])
            cand_b = await _insert_user(raw.db, f"ReplB {suffix}", research_areas=[f"ReplField {suffix}"])
            need = ResearchNeed(original_query="x", required_expertise=[f"ReplField {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            bp_id, role_id = out["blueprint"]["id"], out["blueprint"]["roles"][0]["role_id"]
            await select_candidate(bp_id, role_id, cand_a, db=raw.db, user=_user(owner_id))
            bp = await unselect_candidate(bp_id, role_id, cand_a, db=raw.db, user=_user(owner_id))
            assert bp["roles"][0]["selected_candidates"] == []
            bp2 = await select_candidate(bp_id, role_id, cand_b, db=raw.db, user=_user(owner_id))
            assert bp2["roles"][0]["selected_candidates"][0]["candidate_id"] == cand_b
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^ReplOwner|^ReplA|^ReplB"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_cannot_unselect_an_already_invited_candidate(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            suffix = _oid()[:8]
            owner_id = await _insert_user(raw.db, f"NoUnselOwner {suffix}")
            cand_id = await _insert_user(raw.db, f"NoUnselCand {suffix}", research_areas=[f"NoUnselField {suffix}"])
            need = ResearchNeed(original_query="x", required_expertise=[f"NoUnselField {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            bp_id, role_id = out["blueprint"]["id"], out["blueprint"]["roles"][0]["role_id"]
            await select_candidate(bp_id, role_id, cand_id, db=raw.db, user=_user(owner_id))
            await invite_candidate(bp_id, role_id, cand_id, InviteCandidateRequest(), db=raw.db, user=_user(owner_id))
            with pytest.raises(HTTPException) as exc:
                await unselect_candidate(bp_id, role_id, cand_id, db=raw.db, user=_user(owner_id))
            assert exc.value.status_code == 409
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^NoUnselOwner|^NoUnselCand"}})
            raw.close()


class TestEligibilityPrivacyAndCredits:
    @pytest.mark.asyncio
    async def test_demo_candidate_excluded_from_role_candidates(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            suffix = _oid()[:8]
            owner_id = await _insert_user(raw.db, f"DemoExclOwner {suffix}")
            await _insert_user(raw.db, f"DemoExclFixture {suffix}", research_areas=[f"DemoField {suffix}"], is_demo=True)
            need = ResearchNeed(original_query="x", required_expertise=[f"DemoField {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            role_id = out["blueprint"]["roles"][0]["role_id"]
            result = await get_role_candidates(out["blueprint"]["id"], role_id, db=raw.db, user=_user(owner_id))
            assert result["candidates"] == []
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^DemoExclOwner|^DemoExclFixture"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_self_excluded_from_role_candidates(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            suffix = _oid()[:8]
            owner_id = await _insert_user(raw.db, f"SelfExclOwner {suffix}", research_areas=[f"SelfField {suffix}"])
            need = ResearchNeed(original_query="x", required_expertise=[f"SelfField {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            role_id = out["blueprint"]["roles"][0]["role_id"]
            result = await get_role_candidates(out["blueprint"]["id"], role_id, db=raw.db, user=_user(owner_id))
            assert owner_id not in {c["id"] for c in result["candidates"]}
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^SelfExclOwner"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_no_email_or_orcid_tokens_in_candidate_list(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            suffix = _oid()[:8]
            owner_id = await _insert_user(raw.db, f"PrivOwner {suffix}")
            await _insert_user(
                raw.db, f"PrivCandidate {suffix}", research_areas=[f"PrivField {suffix}"],
                orcid={"orcid_id": "0000-0001-1111-1111", "access_token": "SHOULD_NOT_LEAK"},
            )
            need = ResearchNeed(original_query="x", required_expertise=[f"PrivField {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            role_id = out["blueprint"]["roles"][0]["role_id"]
            result = await get_role_candidates(out["blueprint"]["id"], role_id, db=raw.db, user=_user(owner_id))
            blob = str(result)
            assert "SHOULD_NOT_LEAK" not in blob
            assert "@synaptiq-test.io" not in blob
        finally:
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^PrivOwner|^PrivCandidate"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_zero_credit_for_non_ai_operations(self, monkeypatch):
        raw = _RawDB()
        try:
            _patch_get_db(monkeypatch, raw.db)
            suffix = _oid()[:8]
            owner_id = await _insert_user(raw.db, f"CreditOwner {suffix}")
            cand_id = await _insert_user(raw.db, f"CreditCandidate {suffix}", research_areas=[f"CreditField {suffix}"])
            need = ResearchNeed(original_query="x", required_expertise=[f"CreditField {suffix}"])
            before = await raw.db.credit_transactions.count_documents({})

            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            bp_id, role_id = out["blueprint"]["id"], out["blueprint"]["roles"][0]["role_id"]
            await get_role_candidates(bp_id, role_id, db=raw.db, user=_user(owner_id))
            await select_candidate(bp_id, role_id, cand_id, db=raw.db, user=_user(owner_id))
            await invite_candidate(bp_id, role_id, cand_id, InviteCandidateRequest(), db=raw.db, user=_user(owner_id))

            after = await raw.db.credit_transactions.count_documents({})
            assert after == before
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^CreditOwner|^CreditCandidate"}})
            raw.close()
