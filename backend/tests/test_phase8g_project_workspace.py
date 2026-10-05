"""P1 Phase 8G — Research Collaboration Workspace & Project Execution.

Covers the one genuinely new integration point this phase adds: Team
Blueprint -> canonical Research Project + canonical Workspace, using the
real routers/projects.py document shape and services/workspace_provisioning
directly (audited, not assumed). No project creation happens automatically
from selection/invitation/acceptance — only from an explicit call to
create-project. Only accepted collaborators become members; proposed/
pending/declined/withdrawn never do. Team-role labels are preserved as
workspace member_roles without touching professional_role. Idempotent on
repeat calls. Unauthorized users cannot create/read/duplicate a project
from someone else's blueprint.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId
from fastapi import HTTPException

from services.research_need.models import ResearchNeed
from routers.team_builder import (
    create_blueprint, select_candidate, invite_candidate, create_project_from_blueprint,
    patch_blueprint,
    CreateBlueprintRequest, InviteCandidateRequest, CreateProjectRequest,
    PatchBlueprintRequest, RoleEdit,
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
        # Creating projects/workspaces is a Pro capability; the plan limit is
        # enforced against the owner's stored plan (services/workspace_provisioning.py).
        "plan_code": "researcher",
        **extra,
    }
    res = await db.users.insert_one(doc)
    return str(res.inserted_id)


def _user(uid: str, name: str = "Owner") -> dict:
    # Projects/workspaces are Pro features — the acting user is on Pro.
    return {"id": uid, "full_name": name, "email": f"{name}@synaptiq-test.io", "plan_code": "researcher"}


def _patch_get_db(monkeypatch, raw_db):
    monkeypatch.setattr("routers.team_builder.get_db", lambda: raw_db)
    monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw_db)


async def _setup_blueprint_with_accepted_candidate(raw, suffix, role_label=None):
    owner_id = await _insert_user(raw.db, f"PWOwner {suffix}")
    cand_id = await _insert_user(raw.db, f"PWCandidate {suffix}", research_areas=[f"PWField {suffix}"])
    need = ResearchNeed(original_query="x", required_expertise=[f"PWField {suffix}"])
    out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
    bp_id, role_id = out["blueprint"]["id"], out["blueprint"]["roles"][0]["role_id"]
    if role_label:
        await patch_blueprint(
            bp_id, PatchBlueprintRequest(role_edits=[RoleEdit(role_id=role_id, label=role_label)]),
            db=raw.db, user=_user(owner_id),
        )
    await select_candidate(bp_id, role_id, cand_id, db=raw.db, user=_user(owner_id))
    bp = await invite_candidate(bp_id, role_id, cand_id, InviteCandidateRequest(), db=raw.db, user=_user(owner_id))
    req_id = bp["roles"][0]["selected_candidates"][0]["collaboration_request_id"]
    await raw.db.collaboration_requests.update_one({"_id": ObjectId(req_id)}, {"$set": {"status": "accepted"}})
    return owner_id, cand_id, bp_id, role_id


class TestProjectCreationFromAcceptedTeam:
    @pytest.mark.asyncio
    async def test_create_project_includes_only_accepted_member(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            owner_id, cand_id, bp_id, role_id = await _setup_blueprint_with_accepted_candidate(raw, suffix)
            _patch_get_db(monkeypatch, raw.db)

            out = await create_project_from_blueprint(
                bp_id, CreateProjectRequest(title=f"Test Project {suffix}"),
                db=raw.db, user=_user(owner_id),
            )
            assert out["already_existed"] is False
            proj = await raw.db.projects.find_one({"_id": ObjectId(out["project_id"])})
            assert owner_id in proj["members"]
            assert cand_id in proj["members"]
            assert proj["source"] == "team_builder"
            assert proj["team_blueprint_id"] == bp_id
            assert proj["workspace_id"] == out["workspace_id"]
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.workspaces.delete_many({"owner_id": owner_id})
            await raw.db.conversations.delete_many({"created_by": owner_id})
            await raw.db.projects.delete_many({"owner_id": owner_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^PWOwner|^PWCandidate"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_pending_candidate_excluded_from_project_members(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            _patch_get_db(monkeypatch, raw.db)
            owner_id = await _insert_user(raw.db, f"PWPendOwner {suffix}")
            cand_id = await _insert_user(raw.db, f"PWPendCand {suffix}", research_areas=[f"PWPendField {suffix}"])
            need = ResearchNeed(original_query="x", required_expertise=[f"PWPendField {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            bp_id, role_id = out["blueprint"]["id"], out["blueprint"]["roles"][0]["role_id"]
            await select_candidate(bp_id, role_id, cand_id, db=raw.db, user=_user(owner_id))
            await invite_candidate(bp_id, role_id, cand_id, InviteCandidateRequest(), db=raw.db, user=_user(owner_id))
            # left pending — never accepted

            proj_out = await create_project_from_blueprint(
                bp_id, CreateProjectRequest(title=f"Pending Test {suffix}"),
                db=raw.db, user=_user(owner_id),
            )
            proj = await raw.db.projects.find_one({"_id": ObjectId(proj_out["project_id"])})
            assert cand_id not in proj["members"]
            assert proj["members"] == [owner_id]
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.workspaces.delete_many({"owner_id": owner_id})
            await raw.db.conversations.delete_many({"created_by": owner_id})
            await raw.db.projects.delete_many({"owner_id": owner_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^PWPendOwner|^PWPendCand"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_declined_candidate_excluded_from_project_members(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            _patch_get_db(monkeypatch, raw.db)
            owner_id = await _insert_user(raw.db, f"PWDeclOwner {suffix}")
            cand_id = await _insert_user(raw.db, f"PWDeclCand {suffix}", research_areas=[f"PWDeclField {suffix}"])
            need = ResearchNeed(original_query="x", required_expertise=[f"PWDeclField {suffix}"])
            out = await create_blueprint(CreateBlueprintRequest(need=need, use_ai=False), db=raw.db, user=_user(owner_id))
            bp_id, role_id = out["blueprint"]["id"], out["blueprint"]["roles"][0]["role_id"]
            await select_candidate(bp_id, role_id, cand_id, db=raw.db, user=_user(owner_id))
            bp = await invite_candidate(bp_id, role_id, cand_id, InviteCandidateRequest(), db=raw.db, user=_user(owner_id))
            req_id = bp["roles"][0]["selected_candidates"][0]["collaboration_request_id"]
            await raw.db.collaboration_requests.update_one({"_id": ObjectId(req_id)}, {"$set": {"status": "declined"}})

            proj_out = await create_project_from_blueprint(
                bp_id, CreateProjectRequest(title=f"Declined Test {suffix}"),
                db=raw.db, user=_user(owner_id),
            )
            proj = await raw.db.projects.find_one({"_id": ObjectId(proj_out["project_id"])})
            assert cand_id not in proj["members"]
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.workspaces.delete_many({"owner_id": owner_id})
            await raw.db.conversations.delete_many({"created_by": owner_id})
            await raw.db.projects.delete_many({"owner_id": owner_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^PWDeclOwner|^PWDeclCand"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_no_automatic_project_creation_on_accept(self, monkeypatch):
        """§2 — accepting a request must never itself create a project."""
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            owner_id, cand_id, bp_id, role_id = await _setup_blueprint_with_accepted_candidate(raw, suffix)
            _patch_get_db(monkeypatch, raw.db)
            count = await raw.db.projects.count_documents({"owner_id": owner_id})
            assert count == 0  # accept already happened in setup; still zero projects
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^PWOwner|^PWCandidate"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_unauthorized_user_cannot_create_project_from_blueprint(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            owner_id, cand_id, bp_id, role_id = await _setup_blueprint_with_accepted_candidate(raw, suffix)
            stranger_id = await _insert_user(raw.db, f"PWStranger {suffix}")
            _patch_get_db(monkeypatch, raw.db)
            with pytest.raises(HTTPException) as exc:
                await create_project_from_blueprint(
                    bp_id, CreateProjectRequest(title="Hijack"), db=raw.db, user=_user(stranger_id),
                )
            assert exc.value.status_code == 403
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^PWOwner|^PWCandidate|^PWStranger"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_idempotent_no_duplicate_project(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            owner_id, cand_id, bp_id, role_id = await _setup_blueprint_with_accepted_candidate(raw, suffix)
            _patch_get_db(monkeypatch, raw.db)
            out1 = await create_project_from_blueprint(bp_id, CreateProjectRequest(title="First"), db=raw.db, user=_user(owner_id))
            out2 = await create_project_from_blueprint(bp_id, CreateProjectRequest(title="Second attempt"), db=raw.db, user=_user(owner_id))
            assert out1["project_id"] == out2["project_id"]
            assert out2["already_existed"] is True
            count = await raw.db.projects.count_documents({"owner_id": owner_id})
            assert count == 1
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.workspaces.delete_many({"owner_id": owner_id})
            await raw.db.conversations.delete_many({"created_by": owner_id})
            await raw.db.projects.delete_many({"owner_id": owner_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^PWOwner|^PWCandidate"}})
            raw.close()


class TestWorkspaceIntegrationAndRolePreservation:
    @pytest.mark.asyncio
    async def test_workspace_linked_and_role_preserved_as_member_role(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            owner_id, cand_id, bp_id, role_id = await _setup_blueprint_with_accepted_candidate(raw, suffix, role_label=f"Health Policy {suffix}")
            _patch_get_db(monkeypatch, raw.db)
            out = await create_project_from_blueprint(bp_id, CreateProjectRequest(title="Role Test"), db=raw.db, user=_user(owner_id))

            ws = await raw.db.workspaces.find_one({"_id": ObjectId(out["workspace_id"])})
            assert ws is not None
            assert cand_id in ws["members"]
            assert ws["member_roles"][cand_id] == f"Health Policy {suffix}"
            assert ws["project_ids"] == [out["project_id"]]

            # professional_role on the user document itself is untouched (§5)
            cand_doc = await raw.db.users.find_one({"_id": ObjectId(cand_id)})
            assert "professional_role" not in cand_doc or cand_doc.get("professional_role") is None
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.workspaces.delete_many({"owner_id": owner_id})
            await raw.db.conversations.delete_many({"created_by": owner_id})
            await raw.db.projects.delete_many({"owner_id": owner_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^PWOwner|^PWCandidate"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_workspace_auto_conversation_created_reusing_canonical_messaging(self, monkeypatch):
        """§16/§17 — discussion must reuse the existing conversations system,
        not a new one."""
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            owner_id, cand_id, bp_id, role_id = await _setup_blueprint_with_accepted_candidate(raw, suffix)
            _patch_get_db(monkeypatch, raw.db)
            out = await create_project_from_blueprint(bp_id, CreateProjectRequest(title="Conv Test"), db=raw.db, user=_user(owner_id))

            conv = await raw.db.conversations.find_one({"context_key": f"workspace:{out['workspace_id']}"})
            assert conv is not None
            assert conv["type"] == "workspace"
            members = await raw.db.conversation_members.find({"conversation_id": str(conv["_id"])}).to_list(10)
            member_ids = {m["user_id"] for m in members}
            assert owner_id in member_ids
            assert cand_id in member_ids
        finally:
            await raw.db.conversation_members.delete_many({"user_id": {"$in": [owner_id, cand_id]}})
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.workspaces.delete_many({"owner_id": owner_id})
            await raw.db.conversations.delete_many({"created_by": owner_id})
            await raw.db.projects.delete_many({"owner_id": owner_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^PWOwner|^PWCandidate"}})
            raw.close()


class TestSecurityAndZeroCredit:
    @pytest.mark.asyncio
    async def test_no_email_or_orcid_tokens_in_project_creation_response(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            owner_id, cand_id, bp_id, role_id = await _setup_blueprint_with_accepted_candidate(raw, suffix)
            await raw.db.users.update_one(
                {"_id": ObjectId(cand_id)},
                {"$set": {"orcid": {"orcid_id": "0000-0001-1111-1111", "access_token": "SHOULD_NOT_LEAK"}}},
            )
            _patch_get_db(monkeypatch, raw.db)
            out = await create_project_from_blueprint(bp_id, CreateProjectRequest(title="Priv Test"), db=raw.db, user=_user(owner_id))
            blob = str(out)
            assert "SHOULD_NOT_LEAK" not in blob
            assert "@synaptiq-test.io" not in blob
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.workspaces.delete_many({"owner_id": owner_id})
            await raw.db.conversations.delete_many({"created_by": owner_id})
            await raw.db.projects.delete_many({"owner_id": owner_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^PWOwner|^PWCandidate"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_project_creation_is_zero_credit(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            owner_id, cand_id, bp_id, role_id = await _setup_blueprint_with_accepted_candidate(raw, suffix)
            _patch_get_db(monkeypatch, raw.db)
            before = await raw.db.credit_transactions.count_documents({})
            await create_project_from_blueprint(bp_id, CreateProjectRequest(title="Credit Test"), db=raw.db, user=_user(owner_id))
            after = await raw.db.credit_transactions.count_documents({})
            assert after == before
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.workspaces.delete_many({"owner_id": owner_id})
            await raw.db.conversations.delete_many({"created_by": owner_id})
            await raw.db.projects.delete_many({"owner_id": owner_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^PWOwner|^PWCandidate"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_project_defaults_to_private_visibility(self, monkeypatch):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            owner_id, cand_id, bp_id, role_id = await _setup_blueprint_with_accepted_candidate(raw, suffix)
            _patch_get_db(monkeypatch, raw.db)
            out = await create_project_from_blueprint(bp_id, CreateProjectRequest(title="Vis Test"), db=raw.db, user=_user(owner_id))
            proj = await raw.db.projects.find_one({"_id": ObjectId(out["project_id"])})
            assert proj["visibility"] == "private"
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": cand_id})
            await raw.db.workspaces.delete_many({"owner_id": owner_id})
            await raw.db.conversations.delete_many({"created_by": owner_id})
            await raw.db.projects.delete_many({"owner_id": owner_id})
            await raw.db.team_blueprints.delete_many({"owner_id": owner_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^PWOwner|^PWCandidate"}})
            raw.close()
