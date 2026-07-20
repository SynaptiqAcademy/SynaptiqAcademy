"""Background synchronization — pulls existing MongoDB collections into the AKG.

Incremental: only processes records updated after last sync timestamp.
Event-driven: called after key mutations.
Safe: never deletes existing relationships without explicit admin trigger.
"""
from __future__ import annotations
import asyncio
import hashlib
from datetime import datetime, timezone

from .graph_adapter import get_adapter
from .entity_registry import ENTITY_TYPES


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _eid(entity_type: str, label: str) -> str:
    return hashlib.md5(f"{entity_type}:{label.lower().strip()}".encode()).hexdigest()


def _user_eid(user_id: str) -> str:
    return f"user:{user_id}"


def _inst_eid(inst_name: str) -> str:
    return _eid("institution", inst_name)


async def _log_sync(db, source: str, synced: int, message: str = ""):
    await db["akg_sync_log"].insert_one({
        "source": source, "synced": synced, "message": message, "at": _now()
    })


async def _get_last_sync(db, source: str) -> str:
    doc = await db["akg_sync_log"].find_one({"source": source}, sort=[("at", -1)])
    return doc["at"] if doc else "2000-01-01T00:00:00+00:00"


async def sync_users(db) -> int:
    adapter = get_adapter()
    last_sync = await _get_last_sync(db, "users")
    query = {"updated_at": {"$gt": last_sync}} if last_sync else {}
    cursor = db["users"].find(query).limit(2000)
    users = await cursor.to_list(2000)

    count = 0
    for u in users:
        uid = str(u.get("_id", ""))
        if not uid:
            continue
        name = u.get("name", "") or u.get("email", uid)
        career_stage = u.get("career_stage", "researcher")
        entity_type = "educator" if career_stage in ("professor", "associate_professor", "lecturer") else "student" if career_stage == "phd_student" else "researcher"

        entity_id = _user_eid(uid)
        props = {
            "user_id":          uid,
            "email":            u.get("email", ""),
            "career_stage":     career_stage,
            "institution":      u.get("institution", ""),
            "department":       u.get("department", ""),
            "country":          u.get("country", ""),
            "research_interests": u.get("research_interests", []),
            "expertise":        u.get("expertise", []),
            "research_area":    u.get("academic_field", ""),
            "verification_level": u.get("verification_level", 0),
            "trust_score":      u.get("trust_score", 0),
            "description":      u.get("bio", ""),
        }
        await adapter.upsert_entity(entity_id, entity_type, name, props, db)

        # Affiliation edge
        institution = u.get("institution", "")
        if institution:
            inst_eid = _inst_eid(institution)
            await adapter.upsert_entity(inst_eid, "institution", institution, {"name": institution}, db)
            await adapter.upsert_relationship(entity_id, inst_eid, "WORKS_AT", {}, db)

        # Research interest edges
        for ri in (u.get("research_interests", []) or [])[:5]:
            topic_eid = _eid("topic", ri)
            await adapter.upsert_entity(topic_eid, "topic", ri, {}, db)
            await adapter.upsert_relationship(entity_id, topic_eid, "SPECIALIZES_IN", {}, db)

        count += 1

    await _log_sync(db, "users", count, f"Synced {count} users to AKG")
    return count


async def sync_institutions(db) -> int:
    adapter = get_adapter()
    last_sync = await _get_last_sync(db, "institutions")
    query = {"updated_at": {"$gt": last_sync}} if last_sync else {}
    cursor = db["institutions"].find(query).limit(500)
    institutions = await cursor.to_list(500)

    count = 0
    for inst in institutions:
        name = inst.get("name", "")
        if not name:
            continue
        inst_eid = _inst_eid(name)
        props = {
            "website":       inst.get("website", ""),
            "country":       inst.get("country", ""),
            "city":          inst.get("city", ""),
            "type":          inst.get("type", "university"),
            "research_focus": inst.get("research_focus", []),
            "description":   inst.get("description", ""),
        }
        await adapter.upsert_entity(inst_eid, "institution", name, props, db)

        # Country edge
        country = inst.get("country", "")
        if country:
            ctry_eid = _eid("country", country)
            await adapter.upsert_entity(ctry_eid, "country", country, {}, db)
            await adapter.upsert_relationship(inst_eid, ctry_eid, "LOCATED_IN", {}, db)

        count += 1

    await _log_sync(db, "institutions", count)
    return count


async def sync_projects(db) -> int:
    adapter = get_adapter()
    cursor = db["projects"].find({}).limit(1000)
    projects = await cursor.to_list(1000)
    count = 0
    for p in projects:
        pid = str(p.get("_id", ""))
        title = p.get("title", pid)
        proj_eid = _eid("research_group", title)
        props = {
            "description": p.get("description", ""),
            "status":      p.get("status", ""),
            "keywords":    p.get("keywords", []),
        }
        await adapter.upsert_entity(proj_eid, "research_group", title, props, db)
        owner_id = str(p.get("owner_id", "") or p.get("user_id", ""))
        if owner_id:
            await adapter.upsert_relationship(_user_eid(owner_id), proj_eid, "LEADS", {}, db)
        count += 1
    await _log_sync(db, "projects", count)
    return count


async def sync_grants(db) -> int:
    adapter = get_adapter()
    cursor = db["grant_applications"].find({}).limit(1000)
    grants = await cursor.to_list(1000)
    count = 0
    for g in grants:
        gid = str(g.get("_id", ""))
        title = g.get("title", "") or g.get("grant_title", gid)
        grant_eid = _eid("grant", title)
        props = {
            "funder":    g.get("funder", ""),
            "amount":    g.get("amount", 0),
            "status":    g.get("status", ""),
            "keywords":  g.get("keywords", []),
        }
        await adapter.upsert_entity(grant_eid, "grant", title, props, db)
        user_id = str(g.get("user_id", ""))
        if user_id:
            await adapter.upsert_relationship(_user_eid(user_id), grant_eid, "PARTICIPATES_IN", {}, db)
        funder = g.get("funder", "")
        if funder:
            funder_eid = _eid("funding_agency", funder)
            await adapter.upsert_entity(funder_eid, "funding_agency", funder, {}, db)
            await adapter.upsert_relationship(grant_eid, funder_eid, "FUNDED_BY", {}, db)
        count += 1
    await _log_sync(db, "grant_applications", count)
    return count


async def sync_marketplace_services(db) -> int:
    adapter = get_adapter()
    cursor = db["mkt_services"].find({"status": "active"}).limit(500)
    services = await cursor.to_list(500)
    count = 0
    for svc in services:
        sid = str(svc.get("_id", ""))
        title = svc.get("title", sid)
        svc_eid = _eid("marketplace_service", title)
        props = {
            "category":     svc.get("category", ""),
            "tags":         svc.get("tags", []),
            "description":  svc.get("description", ""),
            "keywords":     svc.get("tags", []),
        }
        await adapter.upsert_entity(svc_eid, "marketplace_service", title, props, db)
        provider_uid = svc.get("provider_user_id", "")
        if provider_uid:
            await adapter.upsert_relationship(_user_eid(provider_uid), svc_eid, "PRODUCES", {}, db)
        count += 1
    await _log_sync(db, "mkt_services", count)
    return count


async def sync_communities(db) -> int:
    adapter = get_adapter()
    cursor = db["network_communities"].find({}).limit(500)
    communities = await cursor.to_list(500)
    count = 0
    for c in communities:
        cid = str(c.get("_id", ""))
        name = c.get("name", cid)
        comm_eid = _eid("community", name)
        props = {
            "topic":       c.get("topic", ""),
            "description": c.get("description", ""),
            "member_count":c.get("member_count", 0),
            "keywords":    [c.get("topic", "")],
        }
        await adapter.upsert_entity(comm_eid, "community", name, props, db)
        count += 1
    await _log_sync(db, "network_communities", count)
    return count


async def run_full_sync(db) -> dict:
    """Run all sync tasks sequentially (safe for background task)."""
    results = {}
    for fn, label in [
        (sync_users,                "users"),
        (sync_institutions,         "institutions"),
        (sync_projects,             "projects"),
        (sync_grants,               "grants"),
        (sync_marketplace_services, "marketplace_services"),
        (sync_communities,          "communities"),
    ]:
        try:
            n = await fn(db)
            results[label] = n
        except Exception as e:
            results[label] = f"error: {e}"

    return {"synced": results, "completed_at": _now()}


async def get_sync_status(db) -> list[dict]:
    cursor = db["akg_sync_log"].find({}).sort("at", -1).limit(50)
    docs = await cursor.to_list(50)
    for d in docs:
        d.pop("_id", None)
    return docs
