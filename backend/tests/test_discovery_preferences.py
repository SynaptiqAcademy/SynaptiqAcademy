"""Network Settings privacy choices must reach every discovery surface.

/discover, the researcher directory and member search filter on
users.profile_visibility; the choices were only saved to network_settings,
so "Private" and "don't show me in discovery" had no effect there.
"""
from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from bson import ObjectId

from services.discovery_preferences import discovery_visibility, sync_all

motor = pytest.importorskip("motor.motor_asyncio")
_LOOP = asyncio.new_event_loop()


def test_choice_maps_to_discovery_visibility():
    assert discovery_visibility({"show_in_discovery": False, "profile_visibility": "public"}) == "private"
    assert discovery_visibility({"show_in_discovery": True, "profile_visibility": "private"}) == "private"
    assert discovery_visibility({"show_in_discovery": True, "profile_visibility": "public"}) == "public"
    assert discovery_visibility({}) == "public"
    assert discovery_visibility({"profile_visibility": "nonsense"}) == "public"


def test_settings_endpoint_mirrors_to_user_record():
    src = open("routers/network.py", encoding="utf-8").read()
    i = src.index("async def update_network_settings")
    assert "discovery_visibility(settings)" in src[i:i + 1500]


def test_sync_applies_saved_choices():
    async def go():
        client = motor.AsyncIOMotorClient(os.environ.get("LIFECYCLE_TEST_MONGO", "mongodb://localhost:27017"),
                                          serverSelectionTimeoutMS=800)
        try:
            await client.admin.command("ping")
        except Exception:
            pytest.skip("local MongoDB not available")
        db = client[f"synaptiq_discovery_{uuid.uuid4().hex[:8]}"]
        a, b, c = ObjectId(), ObjectId(), ObjectId()
        await db.users.insert_many([{"_id": a}, {"_id": b}, {"_id": c, "profile_visibility": "private"}])
        await db.network_settings.insert_many([
            {"user_id": str(a), "show_in_discovery": False, "profile_visibility": "public"},
            {"user_id": str(b), "show_in_discovery": True, "profile_visibility": "private"},
            {"user_id": str(c), "show_in_discovery": True, "profile_visibility": "public"},
        ])
        await sync_all(db)
        got = {d["_id"]: d.get("profile_visibility") async for d in db.users.find({})}
        await client.drop_database(db.name)
        client.close()
        return got, a, b, c
    got, a, b, c = _LOOP.run_until_complete(go())
    assert got[a] == "private" and got[b] == "private" and got[c] == "public"


# ── Public Passport: privacy by default ──────────────────────────────────────

def test_unpublished_work_and_email_are_opt_in():
    from services.public_profiles.visibility import DEFAULT_VISIBILITY, section_visibility
    for k in ("projects", "grants", "collaborations", "contact"):
        assert DEFAULT_VISIBILITY[k] == "private"
        assert section_visibility({}, k) == "private"
    assert section_visibility({}, "publications") == "public"
    assert section_visibility({"grants": "public"}, "grants") == "public"


def test_public_passport_respects_private_choice_and_lists_only_public_projects():
    from routers.public_profiles import _owner_chose_private
    from services.public_profiles.profile_service import get_projects_for_profile
    from services.public_profiles.visibility import apply_defaults_to_untouched

    async def go():
        client = motor.AsyncIOMotorClient(os.environ.get("LIFECYCLE_TEST_MONGO", "mongodb://localhost:27017"),
                                          serverSelectionTimeoutMS=800)
        try:
            await client.admin.command("ping")
        except Exception:
            pytest.skip("local MongoDB not available")
        db = client[f"synaptiq_passport_{uuid.uuid4().hex[:8]}"]
        a, b = ObjectId(), ObjectId()
        await db.users.insert_many([{"_id": a, "profile_visibility": "private"}, {"_id": b}])
        await db.projects.insert_many([
            {"owner_id": str(b), "title": "secret", "visibility": "private", "created_at": "1"},
            {"owner_id": str(b), "title": "open", "visibility": "public", "created_at": "2"},
        ])
        await db.public_profiles.insert_many([
            {"user_id": str(a), "visibility_settings": {"grants": "public", "contact": "public"},
             "created_at": "t0", "updated_at": "t0"},
            {"user_id": str(b), "visibility_settings": {"grants": "public"},
             "created_at": "t0", "updated_at": "t1"},
        ])
        out = {
            "a_private": await _owner_chose_private(str(a), db),
            "b_private": await _owner_chose_private(str(b), db),
            "projects": [p["title"] for p in await get_projects_for_profile(str(b), db)],
        }
        await apply_defaults_to_untouched(db)
        out["untouched"] = (await db.public_profiles.find_one({"user_id": str(a)}))["visibility_settings"]
        out["configured"] = (await db.public_profiles.find_one({"user_id": str(b)}))["visibility_settings"]
        await client.drop_database(db.name)
        client.close()
        return out
    out = _LOOP.run_until_complete(go())
    assert out["a_private"] is True and out["b_private"] is False
    assert out["projects"] == ["open"]
    assert out["untouched"]["grants"] == "private" and out["untouched"]["contact"] == "private"
    assert out["configured"]["grants"] == "public"   # a member's own choice is kept
