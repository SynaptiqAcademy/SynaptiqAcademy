"""Institution access-control fix (Navigation/Entitlements redesign, §23-26).

Audit found several institution-scoped routes granted access to ANY
authenticated user regardless of real organization membership (a genuine
IDOR — institutions.py's /analytics* routes and institution_hub.py's 10
member routes had no membership check at all), plus a separate bug where
the routers that DID attempt a membership check queried
institution_memberships for status="active", a value that database never
actually contains (real values are pending/approved/denied/revoked/
pending_invite) — which locked out every real institution admin/member and
left only the platform-admin bypass working.

This file covers the fix: services.permissions.require_institution_member /
require_institution_admin / get_my_institution_context, and their adoption
in routers/institutions.py's analytics endpoints and routers/
institution_hub.py's member + admin-console endpoints.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId
from fastapi import HTTPException

from services.permissions import (
    require_institution_member,
    require_institution_admin,
    get_my_institution_context,
    access_summary,
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


async def _insert_institution(db, name: str) -> str:
    res = await db.institutions.insert_one({
        "name": name, "country": "AT", "type": "university",
        "plan_code": "institution_free", "email_domains": [], "admin_ids": [],
    })
    return str(res.inserted_id)


async def _insert_membership(db, institution_id: str, user_id: str, *, role="researcher", status="approved") -> None:
    await db.institution_memberships.insert_one({
        "institution_id": institution_id, "user_id": user_id, "role": role,
        "status": status, "joined_at": "2026-01-01T00:00:00+00:00",
    })


async def _insert_user(db, full_name: str, **extra) -> str:
    doc = {
        "full_name": full_name,
        "email": f"{full_name.lower().replace(' ', '')}-{_oid()[:8]}@synaptiq-test.io",
        "is_demo": False,
        **extra,
    }
    res = await db.users.insert_one(doc)
    return str(res.inserted_id)


def _user(uid: str, role: str = "user") -> dict:
    return {"id": uid, "role": role, "full_name": "Test", "email": "t@synaptiq-test.io"}


class TestRequireInstitutionMember:
    @pytest.mark.asyncio
    async def test_non_member_rejected(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            iid = await _insert_institution(raw.db, f"Inst {_oid()[:8]}")
            stranger = await _insert_user(raw.db, "Stranger")
            with pytest.raises(HTTPException) as exc:
                await require_institution_member(iid, _user(stranger))
            assert exc.value.status_code == 403
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_approved_member_allowed(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            iid = await _insert_institution(raw.db, f"Inst {_oid()[:8]}")
            member = await _insert_user(raw.db, "Member")
            await _insert_membership(raw.db, iid, member, role="researcher", status="approved")
            m = await require_institution_member(iid, _user(member))
            assert m["role"] == "researcher"
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_pending_member_rejected(self, monkeypatch):
        """A pending (not-yet-approved) applicant must NOT get member access."""
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            iid = await _insert_institution(raw.db, f"Inst {_oid()[:8]}")
            pending = await _insert_user(raw.db, "Pending")
            await _insert_membership(raw.db, iid, pending, role="researcher", status="pending")
            with pytest.raises(HTTPException) as exc:
                await require_institution_member(iid, _user(pending))
            assert exc.value.status_code == 403
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_revoked_member_rejected(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            iid = await _insert_institution(raw.db, f"Inst {_oid()[:8]}")
            revoked = await _insert_user(raw.db, "Revoked")
            await _insert_membership(raw.db, iid, revoked, role="researcher", status="revoked")
            with pytest.raises(HTTPException) as exc:
                await require_institution_member(iid, _user(revoked))
            assert exc.value.status_code == 403
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_member_of_a_different_institution_rejected(self, monkeypatch):
        """Confirms per-institution scoping — membership at Inst A must not grant access to Inst B."""
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            iid_a = await _insert_institution(raw.db, f"Inst A {_oid()[:8]}")
            iid_b = await _insert_institution(raw.db, f"Inst B {_oid()[:8]}")
            member_of_a = await _insert_user(raw.db, "MemberOfA")
            await _insert_membership(raw.db, iid_a, member_of_a, role="researcher", status="approved")
            with pytest.raises(HTTPException) as exc:
                await require_institution_member(iid_b, _user(member_of_a))
            assert exc.value.status_code == 403
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_platform_admin_bypasses(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            iid = await _insert_institution(raw.db, f"Inst {_oid()[:8]}")
            admin_uid = await _insert_user(raw.db, "PlatformAdmin", role="super_admin")
            m = await require_institution_member(iid, _user(admin_uid, role="super_admin"))
            assert m["role"] == "platform_admin"
        finally:
            raw.close()


class TestRequireInstitutionAdmin:
    @pytest.mark.asyncio
    async def test_plain_member_rejected_from_admin_check(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            iid = await _insert_institution(raw.db, f"Inst {_oid()[:8]}")
            member = await _insert_user(raw.db, "PlainMember")
            await _insert_membership(raw.db, iid, member, role="researcher", status="approved")
            with pytest.raises(HTTPException) as exc:
                await require_institution_admin(iid, _user(member))
            assert exc.value.status_code == 403
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_real_institution_admin_allowed(self, monkeypatch):
        """This is the case that was broken: a genuine institution admin
        (status="approved", role="admin") used to be rejected everywhere the
        old status="active" check was used."""
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            iid = await _insert_institution(raw.db, f"Inst {_oid()[:8]}")
            admin_user = await _insert_user(raw.db, "InstAdmin")
            await _insert_membership(raw.db, iid, admin_user, role="admin", status="approved")
            m = await require_institution_admin(iid, _user(admin_user))
            assert m["role"] == "admin"
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_owner_role_allowed(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            iid = await _insert_institution(raw.db, f"Inst {_oid()[:8]}")
            owner = await _insert_user(raw.db, "Owner")
            await _insert_membership(raw.db, iid, owner, role="owner", status="approved")
            m = await require_institution_admin(iid, _user(owner))
            assert m["role"] == "owner"
        finally:
            raw.close()


class TestGetMyInstitutionContext:
    @pytest.mark.asyncio
    async def test_non_member_returns_is_member_false(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            stranger = await _insert_user(raw.db, "Stranger2")
            ctx = await get_my_institution_context(_user(stranger))
            assert ctx == {"is_member": False}
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_member_returns_institution_name_and_role(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            iid = await _insert_institution(raw.db, f"Real University {_oid()[:8]}")
            member = await _insert_user(raw.db, "RealMember")
            await _insert_membership(raw.db, iid, member, role="researcher", status="approved")
            ctx = await get_my_institution_context(_user(member))
            assert ctx["is_member"] is True
            assert ctx["institution_id"] == iid
            assert ctx["institution_name"].startswith("Real University")
            assert ctx["role"] == "researcher"
            assert ctx["is_admin"] is False
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_admin_role_sets_is_admin_true(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            iid = await _insert_institution(raw.db, f"Admin's Inst {_oid()[:8]}")
            admin_user = await _insert_user(raw.db, "AdminCtx")
            await _insert_membership(raw.db, iid, admin_user, role="admin", status="approved")
            ctx = await get_my_institution_context(_user(admin_user))
            assert ctx["is_admin"] is True
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_institution_verified_or_professional_role_alone_grants_nothing(self, monkeypatch):
        """Regression guard for the exact hypothesis the spec called out: neither
        institution_verified, ORCID affiliation, nor professional_role should ever
        substitute for a real institution_memberships row."""
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            verified_but_not_member = await _insert_user(
                raw.db, "VerifiedNotMember",
                institution_verified=True, professional_role="Professor",
                institution="Some University", orcid="0000-0000-0000-0001",
            )
            ctx = await get_my_institution_context(_user(verified_but_not_member))
            assert ctx == {"is_member": False}
        finally:
            raw.close()


class TestAccessSummaryIncludesInstitution:
    @pytest.mark.asyncio
    async def test_access_summary_embeds_institution_context_and_plan_name(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            monkeypatch.setattr("services.credits_service.get_db", lambda: raw.db)
            uid = await _insert_user(raw.db, "SummaryUser", plan_code="pro_researcher")
            summary = await access_summary({**_user(uid), "plan_code": "pro_researcher"})
            assert summary["institution"] == {"is_member": False}
            assert summary["plan_name"] == "Pro Researcher"
        finally:
            raw.close()


class TestInstitutionsRouterAnalyticsIDOR:
    """The confirmed-severe finding: /api/institutions/{iid}/analytics* had no
    membership check at all — any authenticated user could pull any
    institution's analytics by iid. Exercises the real router functions."""

    @pytest.mark.asyncio
    async def test_analytics_overview_rejects_non_member(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.institutions.get_db", lambda: raw.db)
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            from routers.institutions import analytics_overview
            iid = await _insert_institution(raw.db, f"Victim Inst {_oid()[:8]}")
            attacker = await _insert_user(raw.db, "Attacker")
            with pytest.raises(HTTPException) as exc:
                await analytics_overview(iid, _user(attacker))
            assert exc.value.status_code == 403
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_analytics_overview_allows_real_member(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.institutions.get_db", lambda: raw.db)
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            monkeypatch.setattr("services.institutions.analytics.get_db", lambda: raw.db)
            from routers.institutions import analytics_overview
            iid = await _insert_institution(raw.db, f"Home Inst {_oid()[:8]}")
            member = await _insert_user(raw.db, "HomeMember")
            await _insert_membership(raw.db, iid, member, role="researcher", status="approved")
            result = await analytics_overview(iid, _user(member))
            assert isinstance(result, dict)
        finally:
            raw.close()


class TestInstitutionHubMemberRoutesRequireMembership:
    @pytest.mark.asyncio
    async def test_timeline_rejects_non_member(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.institution_hub.get_db", lambda: raw.db)
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            from routers.institution_hub import get_timeline
            iid = await _insert_institution(raw.db, f"TL Inst {_oid()[:8]}")
            stranger = await _insert_user(raw.db, "TLStranger")
            with pytest.raises(HTTPException) as exc:
                await get_timeline(iid, _user(stranger))
            assert exc.value.status_code == 403
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_timeline_allows_real_member(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.institution_hub.get_db", lambda: raw.db)
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            from routers.institution_hub import get_timeline
            iid = await _insert_institution(raw.db, f"TL Home {_oid()[:8]}")
            member = await _insert_user(raw.db, "TLMember")
            await _insert_membership(raw.db, iid, member, role="researcher", status="approved")
            result = await get_timeline(iid, _user(member))
            assert "timeline" in result
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_admin_console_now_reachable_by_a_real_approved_admin(self, monkeypatch):
        """Confirms the status="active" -> "approved" fix: a real institution
        admin can now reach their own admin console, which previously always
        403'd for everyone except the platform-admin bypass."""
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.institution_hub.get_db", lambda: raw.db)
            monkeypatch.setattr("services.permissions.get_db", lambda: raw.db)
            from routers.institution_hub import _require_institution_admin
            iid = await _insert_institution(raw.db, f"Admin Console Inst {_oid()[:8]}")
            admin_user = await _insert_user(raw.db, "ConsoleAdmin")
            await _insert_membership(raw.db, iid, admin_user, role="admin", status="approved")
            await _require_institution_admin(iid, _user(admin_user))  # must not raise
        finally:
            raw.close()
