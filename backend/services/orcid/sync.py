"""ORCID profile + works synchronization.

After OAuth, `sync_profile(user_id)` pulls personal details, biography, keywords,
researcher URLs, employments, educations, fundings, and works. Profile fields
populate the User document; works are persisted to a dedicated `publications`
collection as the canonical source-of-truth. Manuscripts are cross-linked via
DOI / normalized-title match.

OpenAlex enrichment runs as a second pass to add citation counts, concepts,
topics, co-authors, and resolved institutions.
"""
from __future__ import annotations
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from db import get_db
from services.orcid.oauth import fetch_record
from services.reputation.openalex import _normalize_orcid  # reuse the helper
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.orcid.sync")

WORK_TYPE_MAP = {
    "journal-article": "journal_article", "conference-paper": "conference_paper",
    "book": "book", "book-chapter": "book_chapter", "report": "report",
    "preprint": "preprint", "review": "review", "data-set": "dataset", "other": "other",
}


def _safe(d, *path, default=None):
    cur = d
    for p in path:
        if cur is None: return default
        cur = cur.get(p) if isinstance(cur, dict) else None
    return cur if cur is not None else default


def _norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").lower().strip())


def _extract_doi(work_summary: dict) -> Optional[str]:
    ids = _safe(work_summary, "external-ids", "external-id", default=[]) or []
    for x in ids:
        if (x.get("external-id-type") or "").lower() == "doi":
            val = (x.get("external-id-value") or "").strip()
            if val: return val.lower()
    return None


def _profile_from_record(record: dict) -> dict:
    person = record.get("person") or {}
    activities = record.get("activities-summary") or {}
    name = (person.get("name") or {})
    given = _safe(name, "given-names", "value")
    family = _safe(name, "family-name", "value")
    full_name = " ".join([p for p in [given, family] if p]).strip() or None
    bio = _safe(person, "biography", "content")
    keywords = [kw.get("content") for kw in _safe(person, "keywords", "keyword", default=[]) or [] if kw.get("content")]
    research_urls = []
    for ru in _safe(person, "researcher-urls", "researcher-url", default=[]) or []:
        url = _safe(ru, "url", "value"); name_url = ru.get("url-name")
        if url: research_urls.append({"url": url, "name": name_url})
    country = _safe(person, "addresses", "address", 0, "country", "value") if isinstance(_safe(person, "addresses", "address"), list) else None

    def _affil(group, key):
        out = []
        for entry in _safe(activities, group, default=[]) or []:
            for summary in (entry.get(key + "-summary") or []):
                org = summary.get("organization") or {}
                out.append({
                    "institution": org.get("name"),
                    "role":        summary.get("role-title"),
                    "department":  summary.get("department-name"),
                    "start_year":  _safe(summary, "start-date", "year", "value"),
                    "end_year":    _safe(summary, "end-date", "year", "value"),
                    "city":        _safe(org, "address", "city"),
                    "country":     _safe(org, "address", "country"),
                })
        return out
    employments_groups = activities.get("employments") or {}
    educations_groups  = activities.get("educations") or {}

    def _affil_flat(groups, key):
        out = []
        for entry in groups.get(key + "-summary", []) or []:
            org = entry.get("organization") or {}
            out.append({
                "institution": org.get("name"),
                "role":        entry.get("role-title"),
                "department":  entry.get("department-name"),
                "start_year":  _safe(entry, "start-date", "year", "value"),
                "end_year":    _safe(entry, "end-date", "year", "value"),
                "city":        _safe(org, "address", "city"),
                "country":     _safe(org, "address", "country"),
            })
        for grp in groups.get("affiliation-group", []) or []:
            for entry in grp.get("summaries", []) or []:
                emp = entry.get(key + "-summary") or {}
                if not emp: continue
                org = emp.get("organization") or {}
                out.append({
                    "institution": org.get("name"),
                    "role":        emp.get("role-title"),
                    "department":  emp.get("department-name"),
                    "start_year":  _safe(emp, "start-date", "year", "value"),
                    "end_year":    _safe(emp, "end-date", "year", "value"),
                    "city":        _safe(org, "address", "city"),
                    "country":     _safe(org, "address", "country"),
                })
        return out
    employments = _affil_flat(employments_groups, "employment")
    educations  = _affil_flat(educations_groups, "education")

    fundings = []
    for fg in _safe(activities, "fundings", "group", default=[]) or []:
        for fs in fg.get("funding-summary", []) or []:
            fundings.append({
                "title":  _safe(fs, "title", "title", "value"),
                "type":   fs.get("type"),
                "organization": _safe(fs, "organization", "name"),
                "start_year": _safe(fs, "start-date", "year", "value"),
                "end_year":   _safe(fs, "end-date", "year", "value"),
            })

    return {
        "full_name": full_name,
        "biography": bio,
        "keywords":  keywords,
        "research_urls": research_urls,
        "country": country,
        "employments": employments,
        "educations": educations,
        "fundings": fundings,
    }


def _works_from_record(record: dict) -> list[dict]:
    activities = record.get("activities-summary") or {}
    works_out: list[dict] = []
    for wg in _safe(activities, "works", "group", default=[]) or []:
        # ORCID groups works; the first work-summary in a group is canonical.
        ws_list = wg.get("work-summary") or []
        if not ws_list: continue
        ws = ws_list[0]
        title = _safe(ws, "title", "title", "value")
        if not title: continue
        works_out.append({
            "title":     title,
            "subtitle":  _safe(ws, "title", "subtitle", "value"),
            "journal":   _safe(ws, "journal-title", "value"),
            "year":      _safe(ws, "publication-date", "year", "value"),
            "month":     _safe(ws, "publication-date", "month", "value"),
            "type":      WORK_TYPE_MAP.get((ws.get("type") or "").lower(), "other"),
            "put_code":  ws.get("put-code"),
            "doi":       _extract_doi(ws),
            "url":       _safe(ws, "url", "value"),
        })
    return works_out


# ============================= MAIN SYNC ===================================
async def sync_user(user_id: str, *, trigger: str = "manual") -> dict:
    """Fetch ORCID record + persist profile changes + upsert publications.

    Returns a sync report.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    u = await db.users.find_one({"_id": ObjectId(user_id)})
    if not u: raise ValueError("User not found")
    orcid = u.get("orcid") or {}
    orcid_id = orcid.get("orcid_id")
    if not orcid_id:
        raise ValueError("User has no linked ORCID iD")

    started = datetime.now(timezone.utc).isoformat()
    errors: list[str] = []
    pub_imported = pub_updated = pub_linked = 0

    try:
        from services.encryption_service import decrypt_field
        raw_access_token = decrypt_field(orcid.get("access_token"))
        record = await fetch_record(orcid_id, raw_access_token or None)
    except Exception as e:
        errors.append(f"fetch_record: {e}")
        record = None

    profile_update: dict = {}
    if record:
        prof = _profile_from_record(record)
        if prof.get("full_name") and not u.get("full_name"):
            profile_update["full_name"] = prof["full_name"]
        if prof.get("biography") and not u.get("biography"):
            profile_update["biography"] = prof["biography"]
        if prof.get("country") and not u.get("country"):
            profile_update["country"] = prof["country"]
        if prof.get("keywords"):
            existing = set(u.get("research_keywords") or [])
            profile_update["research_keywords"] = list(existing | set(prof["keywords"]))
        if prof.get("research_urls"):
            existing_urls = u.get("research_urls") or []
            profile_update["research_urls"] = (existing_urls + prof["research_urls"])[:20]
        # Affiliations + fundings stored on user as imported snapshots
        if prof.get("employments"): profile_update["orcid_employments"] = prof["employments"][:20]
        if prof.get("educations"):  profile_update["orcid_educations"]  = prof["educations"][:20]
        if prof.get("fundings"):    profile_update["orcid_fundings"]    = prof["fundings"][:20]
        if profile_update:
            await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": profile_update})

        # ----- Works → publications collection (canonical) -----
        works = _works_from_record(record)
        for w in works:
            try:
                doc = {
                    "owner_id":        user_id,
                    "orcid_put_code":  str(w.get("put_code") or ""),
                    "source":          "orcid",
                    "title":           w["title"],
                    "title_norm":      _norm_title(w["title"]),
                    "subtitle":        w.get("subtitle"),
                    "journal":         w.get("journal"),
                    "year":            int(w["year"]) if w.get("year") and str(w["year"]).isdigit() else None,
                    "month":           w.get("month"),
                    "type":            w.get("type"),
                    "doi":             w.get("doi"),
                    "url":             w.get("url"),
                    "authors":         [{"orcid_id": orcid_id, "user_id": user_id}],
                    "imported_via":    "orcid",
                    "synced_at":       datetime.now(timezone.utc).isoformat(),
                }
                # Idempotent upsert
                key = {"owner_id": user_id,
                       "$or": [
                           {"doi": doc["doi"]} if doc["doi"] else {"_no": True},
                           {"orcid_put_code": doc["orcid_put_code"]} if doc["orcid_put_code"] else {"_no": True},
                           {"title_norm": doc["title_norm"]},
                       ]}
                # Filter $or to drop synthetic no-matchers
                key["$or"] = [c for c in key["$or"] if "_no" not in c]
                existing = await db.publications.find_one(key)
                if existing:
                    await db.publications.update_one({"_id": existing["_id"]}, {"$set": doc})
                    pub_updated += 1
                else:
                    doc["created_at"] = datetime.now(timezone.utc).isoformat()
                    r = await db.publications.insert_one(doc)
                    pub_imported += 1
                    # Cross-link to manuscript when title/DOI matches
                    linked = await _link_to_manuscript(str(r.inserted_id), doc, user_id)
                    if linked: pub_linked += 1
            except Exception as e:
                errors.append(f"work[{w.get('title','?')[:40]}]: {e}")

    # ----- Record sync history -----
    history = {
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "trigger": trigger,
        "publications_imported": pub_imported,
        "publications_updated":  pub_updated,
        "publications_linked":   pub_linked,
        "profile_fields_updated": list(profile_update.keys()),
        "errors": errors,
        "ok": len(errors) == 0,
    }
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$push": {"orcid.sync_history": {"$each": [history], "$slice": -25}},
         "$set":  {"orcid.last_sync_at": history["finished_at"]}}
    )
    return history


async def _link_to_manuscript(pub_id: str, pub: dict, user_id: str) -> bool:
    """Match an imported publication to an existing manuscript by DOI/title."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    candidate = None
    if pub.get("doi"):
        candidate = await db.manuscripts.find_one({"doi": pub["doi"]})
    if not candidate and pub.get("title_norm"):
        candidate = await db.manuscripts.find_one({
            "author_ids": user_id,
            "$expr": {"$eq": [{"$toLower": "$title"}, pub["title_norm"]]}
        })
    if not candidate: return False
    mid = str(candidate["_id"])
    await db.publications.update_one({"_id": ObjectId(pub_id)},
                                       {"$set": {"manuscript_id": mid}})
    await db.manuscripts.update_one({"_id": candidate["_id"]},
                                      {"$set": {"orcid_publication_id": pub_id}})
    return True


# ============================= OPENALEX ENRICHMENT =========================
async def enrich_publications_with_openalex(user_id: str, *, limit: int = 50) -> dict:
    """Pass through publications missing citation/concept data; enrich via OpenAlex."""
    import httpx
    from services.reputation.openalex import HEADERS, OPENALEX_BASE
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    pubs = await db.publications.find(
        {"owner_id": user_id, "openalex_enriched_at": {"$exists": False}, "doi": {"$ne": None}}
    ).limit(limit).to_list(limit)
    enriched = errors = 0
    async with httpx.AsyncClient(timeout=10, headers=HEADERS) as cli:
        for p in pubs:
            try:
                r = await cli.get(f"{OPENALEX_BASE}/works/doi:{p['doi']}")
                if r.status_code != 200:
                    errors += 1; continue
                work = r.json()
                concepts = [c.get("display_name") for c in (work.get("concepts") or [])[:6] if c.get("display_name")]
                topics   = [t.get("display_name") for t in (work.get("topics")   or [])[:6] if t.get("display_name")]
                authors  = [{"name": a.get("author", {}).get("display_name"),
                             "orcid": a.get("author", {}).get("orcid"),
                             "institution": (a.get("institutions") or [{}])[0].get("display_name")}
                            for a in (work.get("authorships") or [])[:20]]
                update = {
                    "openalex_id":         work.get("id"),
                    "citations":           int(work.get("cited_by_count") or 0),
                    "concepts":            concepts,
                    "topics":              topics,
                    "coauthors":           authors,
                    "openalex_enriched_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.publications.update_one({"_id": p["_id"]}, {"$set": update})
                enriched += 1
            except Exception as e:
                logger.warning("OpenAlex enrich failed for %s: %s", p.get("doi"), e)
                errors += 1
    return {"enriched": enriched, "errors": errors, "total_candidates": len(pubs)}
