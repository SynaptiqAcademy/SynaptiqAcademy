"""/for-institutions release audit: tenant isolation, member privacy, role
safety and the Contact Sales path. Each test exercises a real route handler
against the isolated test database (see tests/conftest.py)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from bson import ObjectId
from fastapi import HTTPException


def _oid() -> str:
    return str(ObjectId())


class _RawDB:
    def __init__(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        self._client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
        self.db = self._client[os.environ["MONGODB_DB_NAME"]]

    def close(self):
        self._client.close()


async def _inst(db, name="Illustrative University", domains=()):
    r = await db.institutions.insert_one({"name": f"{name} {_oid()[-8:]}", "plan_code": "institution_free",
                                          "email_domains": list(domains), "seats": {"total": 5}})
    return str(r.inserted_id)


async def _user(db, name="Researcher", email=None):
    r = await db.users.insert_one({"full_name": f"{name} {_oid()[-8:]}", "is_demo": False,
                                   "email": email or f"r-{_oid()[-10:]}@synaptiq-test.io"})
    return str(r.inserted_id)


async def _member(db, iid, uid, role="researcher", status="approved", **extra):
    await db.institution_memberships.insert_one({"institution_id": iid, "user_id": uid, "role": role,
                                                 "status": status, "joined_at": "2026-01-01T00:00:00+00:00",
                                                 "unit_ids": [], **extra})


def _u(uid, email="x@synaptiq-test.io", role="user"):
    return {"id": uid, "role": role, "email": email, "full_name": "T"}


@pytest.fixture
def raw():
    r = _RawDB()
    yield r.db
    r.close()


# ── member list ──────────────────────────────────────────────────────────────
class TestMemberList:
    @pytest.mark.asyncio
    async def test_non_member_cannot_list_another_institutions_members(self, raw):
        from routers.institutions import list_members
        a, b = await _inst(raw), await _inst(raw)
        outsider = await _user(raw)
        await _member(raw, a, outsider)                     # member of A only
        with pytest.raises(HTTPException) as e:
            await list_members(b, user=_u(outsider))
        assert e.value.status_code == 403

    @pytest.mark.asyncio
    async def test_member_sees_approved_only_without_email(self, raw):
        from routers.institutions import list_members
        iid = await _inst(raw)
        me, other, pending = await _user(raw), await _user(raw), await _user(raw)
        await _member(raw, iid, me)
        await _member(raw, iid, other, evidence_url="https://example.org/letter")
        await _member(raw, iid, pending, status="pending")
        rows = await list_members(iid, status="pending", user=_u(me))
        assert {r["status"] for r in rows} == {"approved"}
        assert all("email" not in (r["user"] or {}) and "evidence_url" not in r for r in rows)

    @pytest.mark.asyncio
    async def test_admin_sees_pending_and_email(self, raw):
        from routers.institutions import list_members
        iid = await _inst(raw)
        admin, pending = await _user(raw), await _user(raw)
        await _member(raw, iid, admin, role="admin")
        await _member(raw, iid, pending, status="pending")
        rows = await list_members(iid, status="pending", user=_u(admin))
        assert len(rows) == 1 and rows[0]["user"]["email"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", ["pending", "pending_invite", "denied", "revoked"])
    async def test_non_approved_states_have_no_member_access(self, raw, status):
        from routers.institutions import list_members, list_units
        iid = await _inst(raw)
        uid = await _user(raw)
        await _member(raw, iid, uid, status=status)
        for call in (lambda: list_members(iid, user=_u(uid)), lambda: list_units(iid, user=_u(uid))):
            with pytest.raises(HTTPException) as e:
                await call()
            assert e.value.status_code == 403


# ── units / departments ──────────────────────────────────────────────────────
class TestUnits:
    @pytest.mark.asyncio
    async def test_unit_detail_requires_membership_of_its_institution(self, raw):
        from routers.institutions import get_unit
        a, b = await _inst(raw), await _inst(raw)
        unit = str((await raw.units.insert_one({"institution_id": b, "name": "Department B", "type": "department"})).inserted_id)
        uid = await _user(raw)
        await _member(raw, a, uid, role="admin")            # admin of A
        with pytest.raises(HTTPException) as e:
            await get_unit(unit, user=_u(uid))
        assert e.value.status_code == 403

    @pytest.mark.asyncio
    async def test_department_admin_cannot_link_another_tenants_private_project(self, raw):
        from routers.departments import link_project, ProjectLinkIn
        a, b = await _inst(raw), await _inst(raw)
        admin, stranger = await _user(raw), await _user(raw)
        await _member(raw, a, admin, role="admin")
        await _member(raw, b, stranger)
        did = str((await raw.units.insert_one({"institution_id": a, "name": "Dept A", "type": "department"})).inserted_id)
        pid = str((await raw.projects.insert_one({"title": "Private B project", "owner_id": stranger,
                                                  "members": [stranger], "visibility": "private"})).inserted_id)
        with pytest.raises(HTTPException) as e:
            await link_project(did, ProjectLinkIn(project_id=pid), user=_u(admin))
        assert e.value.status_code == 404
        assert not await raw.department_projects.find_one({"department_id": did, "project_id": pid})

    @pytest.mark.asyncio
    async def test_department_admin_cannot_demote_institution_admin(self, raw):
        from routers.departments import update_member_role, RoleIn
        iid = await _inst(raw)
        did = str((await raw.units.insert_one({"institution_id": iid, "name": "Dept", "type": "department"})).inserted_id)
        dept_admin, inst_admin = await _user(raw), await _user(raw)
        await _member(raw, iid, dept_admin, role="unit_admin", unit_ids=[did])
        await raw.units.update_one({"_id": ObjectId(did)}, {"$set": {"admin_ids": [dept_admin]}})
        await _member(raw, iid, inst_admin, role="admin", unit_ids=[did])
        with pytest.raises(HTTPException) as e:
            await update_member_role(did, inst_admin, RoleIn(role="researcher"), user=_u(dept_admin))
        assert e.value.status_code == 403
        m = await raw.institution_memberships.find_one({"institution_id": iid, "user_id": inst_admin})
        assert m["role"] == "admin"


# ── roles and membership transitions ────────────────────────────────────────
class TestRolesAndClaims:
    @pytest.mark.asyncio
    async def test_owner_role_cannot_be_changed_by_admin(self, raw):
        from routers.institutions import assign_role, RoleIn
        iid = await _inst(raw)
        owner, admin = await _user(raw), await _user(raw)
        await _member(raw, iid, owner, role="owner")
        await _member(raw, iid, admin, role="admin")
        with pytest.raises(HTTPException) as e:
            await assign_role(iid, owner, RoleIn(role="researcher"), user=_u(admin))
        assert e.value.status_code == 400

    @pytest.mark.asyncio
    async def test_invite_cannot_grant_ownership(self, raw):
        from routers.institutions import invite_member, InviteIn
        iid = await _inst(raw)
        admin = await _user(raw)
        await _member(raw, iid, admin, role="admin")
        with pytest.raises(HTTPException) as e:
            await invite_member(iid, InviteIn(email="new@synaptiq-test.io", role="owner"), user=_u(admin))
        assert e.value.status_code == 400

    @pytest.mark.asyncio
    async def test_revoked_member_with_matching_domain_goes_back_to_review(self, raw):
        from routers.institutions import claim_institution, ClaimIn
        iid = await _inst(raw, domains=["synaptiq-test.io"])
        uid = await _user(raw)
        await _member(raw, iid, uid, status="revoked")
        out = await claim_institution(iid, ClaimIn(), user=_u(uid, email="me@synaptiq-test.io"))
        assert out["status"] == "pending"

    @pytest.mark.asyncio
    async def test_accepting_an_invitation_approves_with_invited_role(self, raw):
        from routers.institutions import claim_institution, ClaimIn
        iid = await _inst(raw)
        uid = await _user(raw)
        await _member(raw, iid, uid, role="research_lead", status="pending_invite")
        out = await claim_institution(iid, ClaimIn(), user=_u(uid, email="me@elsewhere-test.io"))
        assert out["status"] == "approved" and out["verified_via"] == "admin_invite"
        m = await raw.institution_memberships.find_one({"institution_id": iid, "user_id": uid})
        assert m["role"] == "research_lead"


# ── analytics scope, directory privacy, public leaderboard ──────────────────
class TestScopeAndPrivacy:
    @pytest.mark.asyncio
    async def test_analytics_scope_ignores_institution_id_without_membership(self, raw):
        from routers.institutional_analytics import _resolve_institution
        a = await _inst(raw)
        uid = await _user(raw)
        with pytest.raises(HTTPException) as e:
            await _resolve_institution({**_u(uid), "institution_id": a})
        assert e.value.status_code == 403

    @pytest.mark.asyncio
    async def test_directory_hides_colleague_email_from_members(self, raw):
        from routers.institution_hub import get_research_directory
        iid = await _inst(raw)
        me, other = await _user(raw), await _user(raw)
        await _member(raw, iid, me)
        await _member(raw, iid, other)
        out = await get_research_directory(iid, user=_u(me))
        assert out["members"] and all(m["email"] is None for m in out["members"])
        assert all(m["name"] for m in out["members"])        # full_name, not the missing "name" field

    def test_public_leaderboard_never_falls_back_to_email(self):
        src = (Path(__file__).resolve().parents[1] / "services" / "institution_hub" / "leaderboard_engine.py").read_text()
        block = src[src.index("async def get_top_researchers_global"):]
        assert 'u.get("email")' not in block and '"email": 1' not in block
        assert '"profile_visibility": {"$ne": "private"}' in block and "_discovery_exclusions" in block


# ── Contact Sales ────────────────────────────────────────────────────────────
class TestContactSales:
    @pytest.mark.asyncio
    async def test_inquiry_is_stored_escaped_and_rate_limited_by_real_ip(self, raw, monkeypatch):
        import routers.contact as contact
        from starlette.requests import Request
        sent = {}

        async def fake_send(**kw):
            sent.update(kw)
            return {"ok": True, "mode": "live"}
        monkeypatch.setattr(contact, "send_email", fake_send)
        contact._rate_store.clear()
        marker = f"inq-{_oid()}"
        body = contact.ContactRequest(name="<b>Head</b> of Research", email="lead@synaptiq-test.io", topic="institution",
                                      message=f"<script>x</script> {marker}", organization="Illustrative Institute", role="Research office")
        req = Request({"type": "http", "headers": [(b"x-real-ip", b"203.0.113.50")], "client": ("10.0.0.1", 1)})
        assert (await contact.submit_contact(body, req))["ok"]
        assert "<script>" not in sent["html"] and "&lt;script&gt;" in sent["html"]
        assert "Illustrative Institute" in sent["html"]
        assert await raw.contact_inquiries.find_one({"message": {"$regex": marker}})
        # The proxy address is not the rate-limit key.
        assert "203.0.113.50" in contact._rate_store and "10.0.0.1" not in contact._rate_store
