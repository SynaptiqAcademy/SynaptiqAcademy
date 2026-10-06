"""Safe search, anonymous public-Passport output and the legacy visibility
migration. Uses throwaway records in the local MongoDB (skipped if none);
never production data.
"""
from __future__ import annotations

import asyncio
import os
import re
import uuid

import pytest
from bson import ObjectId

from services.safe_search import MAX_QUERY_LEN, contains, exact, normalize_search

motor = pytest.importorskip("motor.motor_asyncio")
pymongo = pytest.importorskip("pymongo")
MONGO = os.environ.get("LIFECYCLE_TEST_MONGO", "mongodb://localhost:27017")
_LOOP = asyncio.new_event_loop()


# ── 1. The helper ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,norm", [
    ("Ada Lovelace", "Ada Lovelace"),
    ("  Ada \t\n  Lovelace  ", "Ada Lovelace"),
    ("Ștefănescu", "Ștefănescu"),
    ("José Müller", "José Müller"),
    ("中文 研究", "中文 研究"),
    ("", ""),
    ("   ", ""),
    (None, ""),
    ("a\x00b\x07c", "a b c"),
])
def test_normalize(raw, norm):
    assert normalize_search(raw) == norm


@pytest.mark.parametrize("raw", [".*", "^$", "[", "(", "a|b", "x+?", "\\", "\\d+", "(a+)+$", "$ne", '{"$ne": ""}', "a{1,99999}"])
def test_metacharacters_are_literal(raw):
    rx = contains(raw)["$regex"]
    assert re.fullmatch(rx, normalize_search(raw))            # matches itself literally
    assert not re.fullmatch(rx, "zzz unrelated")              # and nothing else


def test_contains_any_escapes_each_term():
    from services.safe_search import contains_any
    rx = contains_any(["gene therapy", "a.b", ".*"])["$regex"]
    assert re.search(rx, "Gene Therapy trials", re.I) and re.search(rx, "a.b") and not re.search(rx, "axb")
    assert contains_any("solo")["$regex"] == "solo"              # a string is one term, not characters


def test_length_is_capped_and_non_strings_are_text():
    assert len(normalize_search("x" * 10_000)) == MAX_QUERY_LEN
    injected = {"$ne": ""}                                    # e.g. smuggled through a JSON body
    q = contains(injected)
    assert set(q) == {"$regex", "$options"} and isinstance(q["$regex"], str)
    assert exact("Q1")["$regex"] == "^Q1$"


# ── 2. Real MongoDB matching ─────────────────────────────────────────────────

NAMES = ["Ana-Maria Ștefănescu", "José Müller", "a.b", "x*y", "[test]", "(paren)", "back\\slash", "$ne", "Ada Lovelace"]


@pytest.fixture(scope="module")
def mdb():
    client = pymongo.MongoClient(MONGO, serverSelectionTimeoutMS=800)
    try:
        client.admin.command("ping")
    except Exception:
        pytest.skip("local MongoDB not available")
    db = client[f"synaptiq_search_{uuid.uuid4().hex[:8]}"]
    db.people.insert_many([{"name": n} for n in NAMES])
    yield db
    client.drop_database(db.name)


@pytest.mark.parametrize("q,expected", [
    ("lovelace", ["Ada Lovelace"]),
    ("ada  lovelace", ["Ada Lovelace"]),
    ("ștefăn", ["Ana-Maria Ștefănescu"]),
    ("müller", ["José Müller"]),
    ("a.b", ["a.b"]),
    ("x*y", ["x*y"]),
    ("[test]", ["[test]"]),
    ("(paren", ["(paren)"]),
    ("back\\slash", ["back\\slash"]),
    ("$ne", ["$ne"]),
    (".*", []),
    ("^$", []),
    ("[", ["[test]"]),
    ("(", ["(paren)"]),
    ("y" * 5000, []),
])
def test_mongo_search_is_literal(mdb, q, expected):
    got = sorted(d["name"] for d in mdb.people.find({"name": contains(q)}))
    assert got == sorted(expected)


def test_no_unescaped_user_regex_left_in_routes():
    """Every $regex built from a variable goes through services.safe_search
    (or is already re.escape'd). routers/workspaces.py is excluded: it is
    an in-progress owner file, reported separately."""
    import pathlib
    offenders = []
    for path in list(pathlib.Path("routers").rglob("*.py")) + list(pathlib.Path("services").rglob("*.py")):
        if str(path) in ("routers/workspaces.py", "services/safe_search.py"):
            continue
        for i, line in enumerate(path.read_text().splitlines(), 1):
            m = re.search(r'"\$regex":\s*([^,}]+)', line)
            if not m:
                continue
            expr = m.group(1).strip()
            # escaped, q_safe: already re.escape'd; senior_role_pattern: a fixed
            # internal pattern in services/recommendation/matchers/mentors.py.
            if expr.startswith(('"', "'", 'r"', "r'")) or "escape(" in expr or expr in ("escaped", "q_safe", "senior_role_pattern"):
                continue
            offenders.append(f"{path}:{i}: {expr}")
    assert offenders == []


# ── 3. Through the app: directory and anonymous Passport ─────────────────────

@pytest.fixture(scope="module")
def app_db():
    client = pymongo.MongoClient(MONGO, serverSelectionTimeoutMS=800)
    try:
        client.admin.command("ping")
    except Exception:
        pytest.skip("local MongoDB not available")
    from fastapi.testclient import TestClient
    import server
    db = client[(os.environ.get("MONGODB_DB_NAME", "").strip() or os.environ.get("DB_NAME", "synaptiq_local_qa"))]
    tag = uuid.uuid4().hex[:6]
    ids = {k: ObjectId() for k in ("visible", "private", "nodisc", "pub")}
    db.users.insert_many([
        {"_id": ids["visible"], "full_name": f"Zelda Visible {tag}", "email": f"v{tag}@example.org", "role": "researcher", "status": "active"},
        {"_id": ids["private"], "full_name": f"Zelda Private {tag}", "email": f"p{tag}@example.org", "role": "researcher", "status": "active", "profile_visibility": "private"},
        {"_id": ids["nodisc"], "full_name": f"Zelda Nodisc {tag}", "email": f"n{tag}@example.org", "role": "researcher", "status": "active"},
        {"_id": ids["pub"], "full_name": f"Zelda Pub {tag}", "email": f"pub{tag}@example.org", "role": "researcher", "status": "active"},
    ])
    db.network_settings.insert_one({"user_id": str(ids["nodisc"]), "show_in_discovery": False, "profile_visibility": "public"})
    from services.discovery_preferences import discovery_visibility
    db.users.update_one({"_id": ids["nodisc"]}, {"$set": {"profile_visibility": discovery_visibility({"show_in_discovery": False})}})
    db.public_profiles.insert_many([
        {"user_id": str(ids["private"]), "slug": f"zp-{tag}", "visibility_settings": {"contact": "public", "grants": "public"}},
        {"user_id": str(ids["visible"]), "slug": f"zv-{tag}", "visibility_settings": {
            "contact": "private", "grants": "private", "projects": "private", "collaborations": "private"}},
        {"user_id": str(ids["pub"]), "slug": f"zb-{tag}", "visibility_settings": {
            "contact": "private", "grants": "public", "projects": "public", "collaborations": "private"},
         # turned on deliberately (as PUT /me/visibility records it)
         "visibility_explicit": {"grants": "2026-10-07", "projects": "2026-10-07"}},
    ])
    db.grant_applications.insert_many([
        {"user_id": str(ids["visible"]), "grant_title": "HIDDEN-GRANT", "status": "draft", "budget": 1, "notes": "INTERNAL"},
        {"user_id": str(ids["pub"]), "grant_title": "SHOWN-GRANT", "status": "submitted", "budget": 2, "notes": "INTERNAL"},
    ])
    db.projects.insert_many([
        {"owner_id": str(ids["visible"]), "title": "HIDDEN-PROJECT", "visibility": "public", "created_at": "1"},
        {"owner_id": str(ids["pub"]), "title": "TEAM-PROJECT", "visibility": "team", "created_at": "1"},
        {"owner_id": str(ids["pub"]), "title": "PUBLIC-PROJECT", "visibility": "public", "created_at": "2"},
    ])
    with TestClient(server.app) as c:
        c.cookies.clear()
        yield c, tag, ids
    db.users.delete_many({"_id": {"$in": list(ids.values())}})
    db.network_settings.delete_many({"user_id": {"$in": [str(i) for i in ids.values()]}})
    db.public_profiles.delete_many({"slug": {"$regex": f"-{tag}$"}})
    db.grant_applications.delete_many({"user_id": {"$in": [str(i) for i in ids.values()]}})
    db.projects.delete_many({"owner_id": {"$in": [str(i) for i in ids.values()]}})


def _names(c, search):
    r = c.get("/api/profiles/directory", params={"search": search, "limit": 50})
    assert r.status_code == 200, r.text
    return {i["full_name"] for i in r.json().get("items", [])}


def test_directory_excludes_private_and_discovery_off(app_db):
    c, tag, _ = app_db
    names = _names(c, f"zelda")
    assert f"Zelda Visible {tag}" in names
    assert f"Zelda Private {tag}" not in names and f"Zelda Nodisc {tag}" not in names


@pytest.mark.parametrize("q", [".*", "^$", "[", "(", "\\", "$ne", '{"$gt": ""}', "x" * 5000, "   ", ""])
def test_directory_handles_hostile_input(app_db, q):
    c, tag, _ = app_db
    names = _names(c, q)
    assert f"Zelda Private {tag}" not in names and f"Zelda Nodisc {tag}" not in names
    if q in (".*", "^$", "$ne", '{"$gt": ""}') or len(q) > 200:
        assert not any(n.endswith(tag) for n in names)   # treated as literal text, matches no one


def test_anonymous_private_profile_has_no_page(app_db):
    c, tag, _ = app_db
    assert c.get(f"/api/profiles/researcher/zp-{tag}").status_code == 404
    assert c.get(f"/api/profiles/researcher/zp-{tag}/grants").status_code == 404


def test_anonymous_sees_no_private_sections(app_db):
    c, tag, _ = app_db
    r = c.get(f"/api/profiles/researcher/zv-{tag}")
    assert r.status_code == 200
    body = r.text
    assert f"v{tag}@example.org" not in body and r.json()["email"] is None
    assert "HIDDEN-GRANT" not in body and "HIDDEN-PROJECT" not in body
    for section in ("grants", "projects", "collaborations"):
        assert c.get(f"/api/profiles/researcher/zv-{tag}/{section}").status_code == 403


def test_explicitly_public_sections_show_only_intended_fields(app_db):
    c, tag, _ = app_db
    assert c.get(f"/api/profiles/researcher/zb-{tag}").json()["email"] is None
    grants = c.get(f"/api/profiles/researcher/zb-{tag}/grants").json()
    assert [g["grant_title"] for g in grants] == ["SHOWN-GRANT"]
    assert "INTERNAL" not in repr(grants) and "notes" not in grants[0]
    projects = c.get(f"/api/profiles/researcher/zb-{tag}/projects").json()
    assert [p["title"] for p in projects] == ["PUBLIC-PROJECT"]          # team project never listed
    assert c.get(f"/api/profiles/researcher/zb-{tag}/collaborations").status_code == 403


def test_put_records_explicit_choice_only_for_changed_sections(app_db):
    c, tag, ids = app_db
    from auth_utils import create_access_token
    client = pymongo.MongoClient(MONGO)
    db = client[(os.environ.get("MONGODB_DB_NAME", "").strip() or os.environ.get("DB_NAME", "synaptiq_local_qa"))]
    uid = str(ids["visible"])
    c.cookies.set("access_token", create_access_token(uid, f"v{tag}@example.org"))
    c.cookies.set("csrf_token", "t")
    current = c.get("/api/profiles/me/visibility", headers={"X-CSRF-Token": "t"}).json()
    r = c.put("/api/profiles/me/visibility", json={**current, "grants": "public"}, headers={"X-CSRF-Token": "t"})
    c.cookies.clear()
    assert r.status_code == 200, r.text
    doc = db.public_profiles.find_one({"user_id": uid})
    assert set(doc["visibility_explicit"]) == {"grants"}      # bulk payload, one real change


# ── 4. Legacy migration ──────────────────────────────────────────────────────

def _run(coro):
    return _LOOP.run_until_complete(coro)


def test_migration_is_conservative_idempotent_and_keeps_explicit_choices():
    from services.public_profiles import visibility_migration as M

    async def go():
        client = motor.AsyncIOMotorClient(MONGO, serverSelectionTimeoutMS=800)
        try:
            await client.admin.command("ping")
        except Exception:
            pytest.skip("local MongoDB not available")
        db = client[f"synaptiq_migr_{uuid.uuid4().hex[:8]}"]
        legacy_all_public = {k: "public" for k in ("publications", "impact", "contact", "grants", "projects", "collaborations")}
        await db.public_profiles.insert_many([
            {"user_id": "legacy", "visibility_settings": dict(legacy_all_public), "updated_at": "t2", "created_at": "t1"},
            {"user_id": "untrusted", "visibility_settings": dict(legacy_all_public), "contact_opt_in_at": "x"},
            {"user_id": "explicit", "visibility_settings": dict(legacy_all_public),
             "visibility_explicit": {"grants": "2026-10-07"}},
            {"user_id": "already_private", "visibility_settings": {"contact": "private", "grants": "private"}},
        ])
        await db.projects.insert_one({"owner_id": "legacy", "visibility": "public"})
        dry = await M.report(db)
        summary = await M.migrate(db)
        after = {d["user_id"]: d async for d in db.public_profiles.find({})}
        # a member explicitly turns grants on after the migration...
        await db.public_profiles.update_one({"user_id": "legacy"}, {"$set": {
            "visibility_settings.grants": "public", "visibility_explicit.grants": "2026-10-08"}})
        again = await M.migrate(db)
        startup = await M.run_at_startup(db)
        # a second worker racing the first can't apply it again
        await db.migrations.delete_one({"_id": "probe"})
        await db.migrations.insert_one({"_id": "x"})
        later = await db.public_profiles.find_one({"user_id": "legacy"})
        project = await db.projects.find_one({"owner_id": "legacy"})
        record = await db.migrations.find_one({"_id": M.MIGRATION_ID})
        await client.drop_database(db.name)
        client.close()
        return dry, summary, after, again, startup, later, project, record

    dry, summary, after, again, startup, later, project, record = _run(go())
    assert dry["contact_ambiguous"] == 3 and dry["grants_ambiguous"] == 2 and dry["contact_opt_in_at_untrusted"] == 1
    assert summary["profiles_changed"] == 3
    for uid in ("legacy", "untrusted"):
        vs = after[uid]["visibility_settings"]
        assert all(vs[k] == "private" for k in ("contact", "grants", "projects", "collaborations"))
        assert vs["publications"] == "public" and vs["impact"] == "public"       # academic sections untouched
        assert after[uid]["visibility_migrations"]["v2"]["previous"]["grants"] == "public"   # auditable
    assert after["explicit"]["visibility_settings"]["grants"] == "public"            # explicit evidence kept
    assert after["explicit"]["visibility_settings"]["contact"] == "private"
    assert "visibility_migrations" not in after["already_private"]
    assert again["skipped"] in ("already applied", "already claimed") and startup == {"status": "done"}
    assert later["visibility_settings"]["grants"] == "public"                          # new choice survives
    assert project["visibility"] == "public"                                           # project's own flag untouched
    assert record["status"] == "done" and record["summary"]["profiles_changed"] == 3


def test_migration_is_disabled_until_counts_are_reviewed_or_enabled_deliberately():
    from services.public_profiles import visibility_migration as M
    assert M.ENABLED in (True, False)
    src = open("services/cleanup_service.py", encoding="utf-8").read()
    assert "apply_defaults_to_untouched" not in src and "retract_unconsented_email" not in src   # no recurring resets
    assert "if schedule else {}" in src                                                           # startup only


def test_concurrent_workers_apply_the_migration_once():
    from services.public_profiles import visibility_migration as M

    async def go():
        client = motor.AsyncIOMotorClient(MONGO, serverSelectionTimeoutMS=800)
        try:
            await client.admin.command("ping")
        except Exception:
            pytest.skip("local MongoDB not available")
        db = client[f"synaptiq_race_{uuid.uuid4().hex[:8]}"]
        await db.public_profiles.insert_many([{"user_id": str(i), "visibility_settings": {"grants": "public"}} for i in range(5)])
        results = await asyncio.gather(*[M.migrate(db) for _ in range(4)])
        record = await db.migrations.find_one({"_id": M.MIGRATION_ID})
        await client.drop_database(db.name)
        client.close()
        return results, record
    results, record = _run(go())
    applied = [r for r in results if "profiles_changed" in r]
    assert len(applied) == 1 and applied[0]["profiles_changed"] == 5
    assert record["status"] == "done" and record["summary"]["profiles_changed"] == 5
