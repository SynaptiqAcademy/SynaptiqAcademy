"""Phase 9A Part 3, §8 — Department Management gate fix.

Every department route used to call assert_institution_plan(iid) before its
real membership check — a paid institutions.plan_code gate that no
institution could ever satisfy (organization-level billing doesn't exist;
every institution is permanently "institution_free"). That made Department
Management completely dead for every real institution, regardless of
membership. Fixed by removing the dead billing gate; real membership
(assert_dept_membership / assert_dept_admin) is the actual, sufficient
protection — this locks that in.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId
from fastapi import HTTPException

from routers.departments import list_departments


def _oid() -> str:
    return str(ObjectId())


class _RawDB:
    def __init__(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        self._client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
        self.db = self._client[os.environ["MONGODB_DB_NAME"]]

    def close(self):
        self._client.close()


async def _insert_institution(db, name: str, plan_code: str = "institution_free") -> str:
    res = await db.institutions.insert_one({
        "name": name, "country": "AT", "type": "university",
        "plan_code": plan_code, "email_domains": [], "admin_ids": [],
    })
    return str(res.inserted_id)


async def _insert_membership(db, institution_id: str, user_id: str, *, role="researcher", status="approved") -> None:
    await db.institution_memberships.insert_one({
        "institution_id": institution_id, "user_id": user_id, "role": role,
        "status": status, "joined_at": "2026-01-01T00:00:00+00:00",
    })


async def _insert_user(db, full_name: str) -> str:
    # ObjectId's first 8 hex chars are its unix-timestamp component — IDENTICAL
    # for any two ids minted in the same second, so slicing from the tail
    # (the random+counter bytes) instead is what actually makes this unique
    # across the many objects a fast test run creates within one second.
    doc = {"full_name": full_name, "email": f"{full_name.lower()}-{_oid()[-8:]}@synaptiq-test.io", "is_demo": False}
    res = await db.users.insert_one(doc)
    return str(res.inserted_id)


def _user(uid: str) -> dict:
    return {"id": uid, "role": "user"}


class TestDepartmentGateNoLongerRequiresImpossibleBillingState:
    @pytest.mark.asyncio
    async def test_approved_member_of_institution_free_can_list_departments(self, monkeypatch):
        """The critical case: a REAL approved member of an institution whose
        plan_code is "institution_free" (i.e. every institution that has
        ever existed) must be able to use Department Management."""
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.departments.get_db", lambda: raw.db)
            monkeypatch.setattr("services.institutions.department_service.get_db", lambda: raw.db)
            iid = await _insert_institution(raw.db, f"Free Plan Inst {_oid()[:8]}", plan_code="institution_free")
            member = await _insert_user(raw.db, "DeptMember")
            await _insert_membership(raw.db, iid, member, role="researcher", status="approved")

            result = await list_departments(iid, q=None, user=_user(member))
            assert isinstance(result, list)  # did not raise 402
        finally:
            await raw.db.users.delete_many({"full_name": "DeptMember"})
            raw.close()

    @pytest.mark.asyncio
    async def test_non_member_still_rejected(self, monkeypatch):
        """Removing the dead billing gate must not weaken the real check —
        a stranger still gets 403, not accidental access."""
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.departments.get_db", lambda: raw.db)
            monkeypatch.setattr("services.institutions.department_service.get_db", lambda: raw.db)
            iid = await _insert_institution(raw.db, f"Inst {_oid()[:8]}")
            stranger = await _insert_user(raw.db, "Stranger")

            with pytest.raises(HTTPException) as exc:
                await list_departments(iid, q=None, user=_user(stranger))
            assert exc.value.status_code == 403
        finally:
            await raw.db.users.delete_many({"full_name": "Stranger"})
            raw.close()

    @pytest.mark.asyncio
    async def test_pending_member_still_rejected(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.departments.get_db", lambda: raw.db)
            monkeypatch.setattr("services.institutions.department_service.get_db", lambda: raw.db)
            iid = await _insert_institution(raw.db, f"Inst {_oid()[:8]}")
            pending = await _insert_user(raw.db, "Pending")
            await _insert_membership(raw.db, iid, pending, status="pending")

            with pytest.raises(HTTPException) as exc:
                await list_departments(iid, q=None, user=_user(pending))
            assert exc.value.status_code == 403
        finally:
            await raw.db.users.delete_many({"full_name": "Pending"})
            raw.close()
