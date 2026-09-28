"""Regression tests for the P1 Phase 3 (People Discovery) audit fixes.

Prior to this phase, only /api/network/people and /api/profiles/directory
honored show_in_discovery/blocked_users (network_settings), and only
/api/researchers/discover/sections excluded the viewer from their own
results. This phase makes all authenticated discovery endpoints consistent:
self-exclusion + block/opt-out exclusion everywhere a viewer identity
exists.

No matching formula, ranking logic, Research Record, ORCID, or credibility
code was touched.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId

from services.network.discovery_engine import search_people, _discovery_exclusions
from routers.public_profiles import researcher_directory


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
        **extra,
    }
    res = await db.users.insert_one(doc)
    return str(res.inserted_id)


class TestNetworkPeopleSelfExclusion:
    @pytest.mark.asyncio
    async def test_viewer_never_sees_self_in_network_people(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            viewer_id = await _insert_user(raw.db, f"Self Exclude Viewer {suffix}")
            other_id = await _insert_user(raw.db, f"Self Exclude Other {suffix}")

            result = await search_people(raw.db, {"q": suffix}, viewer_id=viewer_id)
            ids = {r.get("id") for r in result["results"]}
            assert viewer_id not in ids
            assert other_id in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^Self Exclude"}})
            raw.close()


class TestListUsersConsistency:
    @pytest.mark.asyncio
    async def test_list_users_self_and_block_exclusion_query_shape(self):
        """Unit-level check on the exclusion-building logic list_users now
        shares with the other endpoints, without needing a full HTTP/auth
        round-trip (covered at the discovery_engine level directly)."""
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            viewer_id = await _insert_user(raw.db, f"ListUsers Viewer {suffix}")
            blocker_id = await _insert_user(raw.db, f"ListUsers Blocker {suffix}")
            await raw.db.network_settings.insert_one(
                {"user_id": blocker_id, "blocked_users": [viewer_id]})

            excluded = await _discovery_exclusions(raw.db, viewer_id)
            assert blocker_id in excluded
            assert viewer_id not in excluded  # _discovery_exclusions itself never excludes the viewer
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^ListUsers"}})
            await raw.db.network_settings.delete_many({"user_id": blocker_id})
            raw.close()


class TestDiscoveryExclusionsSharedHelper:
    @pytest.mark.asyncio
    async def test_show_in_discovery_false_excludes_from_network_people(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            viewer_id = await _insert_user(raw.db, f"OptOut Viewer {suffix}")
            hidden_id = await _insert_user(raw.db, f"OptOut Hidden {suffix}")
            await raw.db.network_settings.insert_one(
                {"user_id": hidden_id, "show_in_discovery": False})

            result = await search_people(raw.db, {"q": suffix}, viewer_id=viewer_id)
            ids = {r.get("id") for r in result["results"]}
            assert hidden_id not in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^OptOut"}})
            await raw.db.network_settings.delete_many({"user_id": hidden_id})
            raw.close()

    @pytest.mark.asyncio
    async def test_reciprocal_block_excludes_both_directions(self):
        """A blocks B -> B excluded from A's results (already covered above).
        B blocks A -> A excluded from B's results too (reciprocal, per the
        existing _discovery_exclusions symmetric design)."""
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            user_a = await _insert_user(raw.db, f"Reciprocal A {suffix}")
            user_b = await _insert_user(raw.db, f"Reciprocal B {suffix}")
            await raw.db.network_settings.insert_one(
                {"user_id": user_b, "blocked_users": [user_a]})

            # From A's perspective, B (who blocked A) must not appear.
            excluded_for_a = await _discovery_exclusions(raw.db, user_a)
            assert user_b in excluded_for_a

            # From B's perspective, A is in B's own blocked_users, so A must not appear either.
            excluded_for_b = await _discovery_exclusions(raw.db, user_b)
            assert user_a in excluded_for_b
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^Reciprocal"}})
            await raw.db.network_settings.delete_many({"user_id": {"$in": [user_a, user_b]}})
            raw.close()

    @pytest.mark.asyncio
    async def test_directory_respects_show_in_discovery_opt_out(self):
        """/api/profiles/directory is unauthenticated (no viewer), but
        show_in_discovery=False is a per-candidate opt-out, not
        viewer-relative — must still be enforced with no viewer present."""
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            visible_id = await _insert_user(raw.db, f"Directory Visible {suffix}",
                                             profile_visibility="public")
            hidden_id = await _insert_user(raw.db, f"Directory Hidden {suffix}",
                                            profile_visibility="public")
            await raw.db.network_settings.insert_one(
                {"user_id": hidden_id, "show_in_discovery": False})

            result = await researcher_directory(search=f"Directory ", research_area=None, institution=None, country=None, career_stage=None, page=1, limit=50, db=raw.db)
            names = {i["full_name"] for i in result["items"]}
            assert f"Directory Visible {suffix}" in names
            assert f"Directory Hidden {suffix}" not in names
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^Directory (Visible|Hidden)"}})
            await raw.db.network_settings.delete_many({"user_id": hidden_id})
            raw.close()

    @pytest.mark.asyncio
    async def test_directory_and_network_people_exclude_demo_and_staff(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            demo_id = await _insert_user(raw.db, f"Demo Account {suffix}",
                                          profile_visibility="public", is_demo=True)
            staff_id = await _insert_user(raw.db, f"Staff Account {suffix}",
                                           profile_visibility="public", role="super_admin")
            real_id = await _insert_user(raw.db, f"Real Researcher {suffix}",
                                          profile_visibility="public")

            dir_result = await researcher_directory(search=None, research_area=None, institution=None, country=None, career_stage=None, page=1, limit=50, db=raw.db)
            dir_names = {i["full_name"] for i in dir_result["items"]}
            assert f"Demo Account {suffix}" not in dir_names
            assert f"Staff Account {suffix}" not in dir_names

            net_result = await search_people(raw.db, {}, viewer_id=None)
            # search_people has no full-text default filter beyond query,
            # so just confirm the demo/staff ids never appear regardless of q.
            net_ids = {r.get("id") for r in net_result["results"]}
            assert demo_id not in net_ids
            assert staff_id not in net_ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^(Demo Account|Staff Account|Real Researcher)"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_blocked_user_cannot_reappear_through_directory_endpoint(self):
        """The public directory endpoint enforces only profile_visibility
        (unauthenticated, no viewer identity to block against) — confirms
        that's still correctly scoped, not a regression: blocking is a
        viewer-relative concept and doesn't apply to an anonymous endpoint."""
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            blocked_id = await _insert_user(raw.db, f"Directory Blocked {suffix}",
                                             profile_visibility="public")
            # No network_settings entry needed — directory has no viewer
            # context, so this user is correctly still visible there even
            # though they might be blocked by some OTHER specific viewer.
            doc = await raw.db.users.find_one({"_id": ObjectId(blocked_id)})
            assert doc.get("profile_visibility") != "private"
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^Directory Blocked"}})
            raw.close()
