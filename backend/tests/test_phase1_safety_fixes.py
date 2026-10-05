"""Regression tests for the Phase 1 production-safety fixes:

  A. Discovery privacy — /api/profiles/directory and /api/network/people
     must not leak private profiles or email addresses.
  B. User purge cascade — grant_applications, grant_collaborations,
     grant_team_invitations, trust_scores, trust_badges, profile_showcases,
     profile_views, conference_team_invitations must all be swept, using the
     REAL field names each collection actually uses.
  C. grant_team_members — application-keyed and collaboration-keyed team
     records must not collide under the unique index.
  D. collaboration_requests — DB-level protection against duplicate pending
     sender/receiver pairs.

Users are created by inserting directly into the DB (not via
/api/auth/register) so these tests are independent of the public_registration
feature-flag state, which is owned by unrelated in-progress work in this
environment. Login (not gated by that flag) is used to obtain sessions.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId

import os

from auth_utils import hash_password
from db import get_db


def _oid() -> str:
    return str(ObjectId())


def _reset_db_client():
    """Work around the Motor cross-event-loop caching gap (db.py's self-heal
    only catches a *closed* loop, not one that's merely different but still
    open) when mixing sync TestClient calls with direct async get_db() use."""
    import db as _db_module
    _db_module._client = None
    _db_module._db = None
    _db_module._db_proxy = None


class _RawDB:
    """A throwaway Motor client independent of db.py's cached global client.

    Tests in this file interleave direct async DB writes (pytest-asyncio's
    per-test loop) with the sync TestClient, which drives the ASGI app on
    its own internal loop. Resetting db.py's shared client to follow one of
    the two loops just breaks the other. A private client sidesteps the
    conflict entirely — it only ever runs on the current test's loop.
    """
    def __init__(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        self._client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
        self.db = self._client[os.environ["MONGODB_DB_NAME"]]

    def close(self):
        self._client.close()


def _auth_header(client) -> dict[str, str]:
    """This environment's .env sets COOKIE_SECURE=1 (conftest.py does not
    override it), so login's Secure cookie is stored by httpx's TestClient
    but never re-sent over the plain-http test transport on later requests —
    the same class of gap documented on csrf_headers() above. Fall back to
    the Authorization header, which get_current_user() also accepts."""
    token = client.cookies.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _run(coro):
    """Run an async setup coroutine from a sync test function, on its own
    private event loop — kept fully separate from both pytest-asyncio's
    per-test loop and TestClient's internal loop."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _insert_user(raw: "_RawDB", full_name: str, email: str, password: str = "TestPass1!", **extra) -> str:
    db = raw.db
    doc = {
        "full_name": full_name,
        "email": email.lower(),
        "password_hash": hash_password(password),
        "role": "user",
        "status": "active",
        "email_verified": True,
        "connections": [],
        "created_at": datetime.now(timezone.utc),
        **extra,
    }
    res = await db.users.insert_one(doc)
    return str(res.inserted_id)


# ── A. Discovery privacy ────────────────────────────────────────────────────

class TestDiscoveryPrivacy:
    def test_directory_excludes_private_profiles(self, client):
        suffix = _oid()[:8]
        public_name = f"Directory Test Public {suffix}"
        private_name = f"Directory Test Private {suffix}"

        async def _setup():
            raw = _RawDB()
            try:
                await _insert_user(raw, public_name, f"dirpub-{_oid()}@synaptiq-test.io",
                                    profile_visibility="public")
                await _insert_user(raw, private_name, f"dirpriv-{_oid()}@synaptiq-test.io",
                                    profile_visibility="private")
            finally:
                raw.close()
        _run(_setup())

        r = client.get(f"/api/profiles/directory?limit=50&search={suffix}")
        assert r.status_code == 200, r.text
        names = {i["full_name"] for i in r.json()["items"]}
        assert public_name in names
        assert private_name not in names

    def test_network_people_never_returns_email_and_excludes_private(self, client):
        suffix = _oid()[:8]
        email = f"netviewer-{_oid()}@synaptiq-test.io"
        password = "TestPass1!"
        private_name = f"Network Private Person {suffix}"
        public_name = f"Network Public Person {suffix}"

        async def _setup():
            raw = _RawDB()
            try:
                await _insert_user(raw, "Network Viewer", email, password, plan_code="researcher")
                await _insert_user(raw, private_name, f"netpriv-{_oid()}@synaptiq-test.io",
                                    profile_visibility="private")
                await _insert_user(raw, public_name, f"netpub-{_oid()}@synaptiq-test.io",
                                    profile_visibility="public")
            finally:
                raw.close()
        _run(_setup())

        r = client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text

        r = client.get(f"/api/network/people?limit=50&q={suffix}", headers=_auth_header(client))
        assert r.status_code == 200, r.text
        results = r.json()["results"]
        for item in results:
            assert "email" not in item
        names = {i.get("name") for i in results}
        assert private_name not in names
        assert public_name in names

    def test_network_people_respects_show_in_discovery_and_blocks(self, client):
        suffix = _oid()[:8]
        viewer_email = f"netviewer2-{_oid()}@synaptiq-test.io"
        hidden_name = f"Opted Out Person {suffix}"
        blocker_name = f"Blocking Person {suffix}"
        password = "TestPass1!"

        async def _setup():
            raw = _RawDB()
            try:
                viewer_id = await _insert_user(raw, "Network Viewer Two", viewer_email, password, plan_code="researcher")
                hidden_id = await _insert_user(raw, hidden_name, f"hidden-{_oid()}@synaptiq-test.io")
                blocker_id = await _insert_user(raw, blocker_name, f"blocker-{_oid()}@synaptiq-test.io")
                await raw.db.network_settings.insert_one({"user_id": hidden_id, "show_in_discovery": False})
                await raw.db.network_settings.insert_one({"user_id": blocker_id, "blocked_users": [viewer_id]})
            finally:
                raw.close()
        _run(_setup())

        r = client.post("/api/auth/login", json={"email": viewer_email, "password": password})
        assert r.status_code == 200, r.text

        r = client.get(f"/api/network/people?limit=50&q={suffix}", headers=_auth_header(client))
        assert r.status_code == 200, r.text
        names = {i.get("name") for i in r.json()["results"]}
        assert hidden_name not in names
        assert blocker_name not in names


# ── B. Purge cascade ────────────────────────────────────────────────────────

class TestPurgeCascade:
    @pytest.mark.asyncio
    async def test_purge_removes_all_eight_target_collections(self):
        _reset_db_client()
        db = get_db()
        from routers.admin_data_governance import _purge_user_owned_data
        from repo.shim import DBProxy
        from repo.security_context import SecurityContext
        proxy = DBProxy(db, SecurityContext.system())
        uid = _oid()

        await db.grant_applications.insert_one({"pi_id": uid, "title": "t"})
        await db.grant_collaborations.insert_one({"lead_user_id": uid, "title": "t"})
        await db.grant_team_invitations.insert_one({"from_user_id": uid, "to_user_id": _oid()})
        await db.grant_team_invitations.insert_one({"from_user_id": _oid(), "to_user_id": uid})
        await db.trust_scores.insert_one({"user_id": uid, "score": 10})
        await db.trust_badges.insert_one({"user_id": uid, "badge_key": "x"})
        await db.profile_showcases.insert_one({"user_id": uid, "title": "x"})
        await db.profile_views.insert_one({"profile_user_id": uid, "viewer_hash": "h"})
        await db.conference_team_invitations.insert_one({"from_user_id": uid, "to_user_id": _oid()})
        await db.conference_team_invitations.insert_one({"from_user_id": _oid(), "to_user_id": uid})

        await _purge_user_owned_data(proxy, uid)

        assert await db.grant_applications.count_documents({"pi_id": uid}) == 0
        assert await db.grant_collaborations.count_documents({"lead_user_id": uid}) == 0
        assert await db.grant_team_invitations.count_documents(
            {"$or": [{"from_user_id": uid}, {"to_user_id": uid}]}) == 0
        assert await db.trust_scores.count_documents({"user_id": uid}) == 0
        assert await db.trust_badges.count_documents({"user_id": uid}) == 0
        assert await db.profile_showcases.count_documents({"user_id": uid}) == 0
        assert await db.profile_views.count_documents({"profile_user_id": uid}) == 0
        assert await db.conference_team_invitations.count_documents(
            {"$or": [{"from_user_id": uid}, {"to_user_id": uid}]}) == 0


# ── C. grant_team_members schema/index ──────────────────────────────────────

class TestGrantTeamMembersIndex:
    @pytest.mark.asyncio
    async def test_application_and_collaboration_keyed_docs_coexist(self):
        _reset_db_client()
        db = get_db()
        try:
            await db.grant_team_members.drop_index("application_id_1_user_id_1")
        except Exception:
            pass
        await db.grant_team_members.create_index(
            [("application_id", 1), ("user_id", 1)], unique=True,
            partialFilterExpression={"application_id": {"$exists": True}},
            name="unique_application_team_member",
        )
        await db.grant_team_members.create_index(
            [("collaboration_id", 1), ("user_id", 1)], unique=True,
            partialFilterExpression={"collaboration_id": {"$exists": True}},
            name="unique_collaboration_team_member",
        )

        uid = _oid()
        app_id = _oid()
        collab_id = _oid()
        await db.grant_team_members.delete_many({"user_id": uid})

        await db.grant_team_members.insert_one({"application_id": app_id, "user_id": uid, "status": "active"})
        # Same user_id on a DIFFERENT schema (collaboration-keyed) must NOT collide.
        await db.grant_team_members.insert_one({"collaboration_id": collab_id, "user_id": uid, "status": "active"})
        assert await db.grant_team_members.count_documents({"user_id": uid}) == 2

        # A second collaboration for the SAME user must also not collide with the first collaboration doc.
        collab_id_2 = _oid()
        await db.grant_team_members.insert_one({"collaboration_id": collab_id_2, "user_id": uid, "status": "active"})
        assert await db.grant_team_members.count_documents({"user_id": uid}) == 3

        # But a genuine duplicate within the SAME schema must still be rejected.
        from pymongo.errors import DuplicateKeyError
        with pytest.raises(DuplicateKeyError):
            await db.grant_team_members.insert_one({"application_id": app_id, "user_id": uid, "status": "active"})

        await db.grant_team_members.delete_many({"user_id": uid})


# ── D. collaboration_requests duplicate-pending guard ───────────────────────

class TestCollaborationRequestsUniqueIndex:
    @pytest.mark.asyncio
    async def test_duplicate_pending_request_rejected(self):
        """This index exists only for the duration of this test — it is NOT
        created by server.py's real startup (confirmed: production relies on
        the application-level find_one check in
        routers/collaboration_requests.py instead, which Phase 8E's
        context-scoped duplicate protection depends on). Previously this
        test created the index and never dropped it, leaving it to silently
        persist in the shared local test DB and break any later test in any
        file that inserts more than one collaboration_requests document for
        the same sender/receiver pair — exactly the kind of cross-test
        pollution this repo's is_demo/is_test hygiene work has been finding
        elsewhere. Always dropped in `finally`, regardless of outcome."""
        _reset_db_client()
        db = get_db()
        try:
            await db.collaboration_requests.drop_index("unique_pending_collaboration_request")
        except Exception:
            pass
        await db.collaboration_requests.create_index(
            [("sender_id", 1), ("receiver_id", 1)], unique=True,
            partialFilterExpression={"status": "pending"},
            name="unique_pending_collaboration_request",
        )

        try:
            sender, receiver = _oid(), _oid()
            await db.collaboration_requests.delete_many({"sender_id": sender, "receiver_id": receiver})
            await db.collaboration_requests.insert_one(
                {"sender_id": sender, "receiver_id": receiver, "status": "pending"})

            from pymongo.errors import DuplicateKeyError
            with pytest.raises(DuplicateKeyError):
                await db.collaboration_requests.insert_one(
                    {"sender_id": sender, "receiver_id": receiver, "status": "pending"})

            # A non-pending status for the same pair must be allowed (partial index).
            await db.collaboration_requests.insert_one(
                {"sender_id": sender, "receiver_id": receiver, "status": "declined"})

            await db.collaboration_requests.delete_many({"sender_id": sender, "receiver_id": receiver})
        finally:
            await db.collaboration_requests.drop_index("unique_pending_collaboration_request")
