"""Network Settings visibility must keep its promise.

"Network — visible to group/community members only" previously left the
member in the anonymous researcher directory and on an anonymous public page
(only "private" was ever excluded). Now:

  Public   public page, directory, discovery and member search.
  Network  none of the general surfaces; visible in Network discovery and on
           their member profile only to people sharing a group or community.
  Private  nowhere.

Throwaway records in the local MongoDB (skipped if none); never production.
"""
from __future__ import annotations

import os
import uuid

import pytest
from bson import ObjectId

pymongo = pytest.importorskip("pymongo")
MONGO = os.environ.get("LIFECYCLE_TEST_MONGO", "mongodb://localhost:27017")


def test_choice_maps_to_the_general_surface_value():
    from services.discovery_preferences import discovery_visibility as dv
    assert dv({"profile_visibility": "public"}) == "public"
    assert dv({"profile_visibility": "network"}) == "private"
    assert dv({"profile_visibility": "private"}) == "private"
    assert dv({"profile_visibility": "public", "show_in_discovery": False}) == "private"


@pytest.fixture(scope="module")
def world():
    client = pymongo.MongoClient(MONGO, serverSelectionTimeoutMS=800)
    try:
        client.admin.command("ping")
    except Exception:
        pytest.skip("local MongoDB not available")
    from fastapi.testclient import TestClient
    from auth_utils import create_access_token
    import server
    db = client[(os.environ.get("MONGODB_DB_NAME", "").strip() or os.environ.get("DB_NAME", "synaptiq_local_qa"))]
    tag = uuid.uuid4().hex[:6]
    ids = {k: ObjectId() for k in ("member", "comember", "stranger")}
    for k, oid in ids.items():
        db.users.insert_one({"_id": oid, "full_name": f"Nv {k} {tag}", "email": f"{k}{tag}@example.org",
                             "role": "researcher", "status": "active", "onboarded": True,
                             "email_verified": True, "profile_visibility": "public", "plan_code": "researcher"})
    db.public_profiles.insert_one({"user_id": str(ids["member"]), "slug": f"nv-{tag}", "visibility_settings": {}})
    gid = f"g-{tag}"
    db.network_group_members.insert_many([{"group_id": gid, "user_id": str(ids["member"])},
                                          {"group_id": gid, "user_id": str(ids["comember"])}])
    tokens = {k: create_access_token(str(v), f"{k}{tag}@example.org") for k, v in ids.items()}
    with TestClient(server.app) as c:
        yield c, db, tag, ids, tokens
    db.users.delete_many({"_id": {"$in": list(ids.values())}})
    db.public_profiles.delete_many({"slug": f"nv-{tag}"})
    db.network_group_members.delete_many({"group_id": gid})
    db.network_settings.delete_many({"user_id": {"$in": [str(v) for v in ids.values()]}})


def _as(c, tokens, who):
    c.cookies.clear()
    if who:
        c.cookies.set("access_token", tokens[who])
        c.cookies.set("csrf_token", "t")


def _set(c, tokens, value):
    _as(c, tokens, "member")
    r = c.put("/api/network/settings", headers={"X-CSRF-Token": "t"},
              json={"profile_visibility": value, "show_in_discovery": True})
    assert r.status_code == 200, r.text


def _surfaces(c, tag, ids, tokens):
    name = f"Nv member {tag}"
    _as(c, tokens, None)
    directory = any(i["full_name"] == name for i in c.get("/api/profiles/directory", params={"search": name}).json()["items"])
    public_page = c.get(f"/api/profiles/researcher/nv-{tag}").status_code
    out = {"directory": directory, "public_page": public_page}
    for viewer in ("stranger", "comember"):
        _as(c, tokens, viewer)
        people = c.get("/api/network/people", params={"q": name}).json()
        found = [p for p in (people.get("results") or people.get("items") or []) if (p.get("name") or p.get("full_name")) == name]
        search = c.get("/api/users", params={"q": name}).json()
        listed = search if isinstance(search, list) else (search.get("items") or search.get("results") or [])
        out[viewer] = {
            "network_discovery": bool(found),
            "member_search": any(u.get("full_name") == name for u in listed),
            "profile": c.get(f"/api/users/{ids['member']}").status_code,
            "email_leak": any("email" in p for p in found),
        }
    return out


def test_public(world):
    c, db, tag, ids, tokens = world
    _set(c, tokens, "public")
    s = _surfaces(c, tag, ids, tokens)
    assert s["directory"] and s["public_page"] == 200
    assert s["stranger"]["network_discovery"] and s["stranger"]["member_search"] and s["stranger"]["profile"] == 200


def test_network_is_limited_to_group_and_community_members(world):
    c, db, tag, ids, tokens = world
    _set(c, tokens, "network")
    s = _surfaces(c, tag, ids, tokens)
    assert not s["directory"] and s["public_page"] == 404                       # nothing anonymous
    assert not s["stranger"]["network_discovery"] and not s["stranger"]["member_search"]
    assert s["stranger"]["profile"] == 404
    assert s["comember"]["network_discovery"] and s["comember"]["profile"] == 200
    assert not s["comember"]["member_search"]                                   # general search stays closed
    assert not s["comember"]["email_leak"]


def test_private(world):
    c, db, tag, ids, tokens = world
    _set(c, tokens, "private")
    s = _surfaces(c, tag, ids, tokens)
    assert not s["directory"] and s["public_page"] == 404
    for viewer in ("stranger", "comember"):
        assert not s[viewer]["network_discovery"] and not s[viewer]["member_search"] and s[viewer]["profile"] == 404


@pytest.mark.parametrize("seq", [("public", "network"), ("network", "public"), ("network", "private"), ("private", "network")])
def test_transitions_take_effect_immediately(world, seq):
    c, db, tag, ids, tokens = world
    for value in seq:
        _set(c, tokens, value)
    s = _surfaces(c, tag, ids, tokens)
    final = seq[-1]
    assert s["directory"] is (final == "public")
    assert (s["public_page"] == 200) is (final == "public")
    assert s["stranger"]["network_discovery"] is (final == "public")
    assert s["comember"]["network_discovery"] is (final in ("public", "network"))


def test_existing_network_members_are_corrected_by_the_startup_sync(world):
    import asyncio
    import motor.motor_asyncio as m
    from services.discovery_preferences import sync_all
    c, db, tag, ids, tokens = world
    db.network_settings.update_one({"user_id": str(ids["stranger"])},
                                   {"$set": {"profile_visibility": "network", "show_in_discovery": True}}, upsert=True)
    db.users.update_one({"_id": ids["stranger"]}, {"$set": {"profile_visibility": "network"}})   # legacy derived value

    async def go():
        client = m.AsyncIOMotorClient(MONGO)
        await sync_all(client[db.name])
        client.close()
    asyncio.new_event_loop().run_until_complete(go())
    assert db.users.find_one({"_id": ids["stranger"]})["profile_visibility"] == "private"
    src = open("services/cleanup_service.py", encoding="utf-8").read()
    assert '"discovery_preferences":   await _run_with_label("discovery_preferences", _sync_discovery_preferences())' in src
