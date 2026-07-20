"""Research Analytics Router — real-data analytics for researchers.

All metrics originate from live platform data:
  publications, openalex_metrics, publication_citations,
  collaboration_requests, projects, grant_links, grant_applications,
  manuscripts, submissions, reputation_scores
"""
from __future__ import annotations

import asyncio
import csv
import io
import math
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from auth_utils import get_current_user
from db import get_db
from services.permissions import require_feature
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

_GATE = [Depends(require_feature("advanced_analytics"))]

_TO_USD: dict[str, float] = {
    "USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CHF": 1.11,
    "JPY": 0.0068, "CAD": 0.73, "AUD": 0.65, "SEK": 0.095,
}

_APP_STATUS: dict[str, str] = {
    "draft": "in_preparation", "in_preparation": "in_preparation",
    "internal_review": "in_preparation", "ready_for_submission": "in_preparation",
    "submitted": "submitted", "eligible": "submitted", "under_evaluation": "submitted",
    "funded": "awarded",
    "rejected": "rejected",
    "closed": "closed", "withdrawn": "closed",
}


def _budget_usd(amount, currency: str) -> float:
    return float(amount or 0) * _TO_USD.get((currency or "USD").upper().strip(), 1.0)


def _safe_year(v) -> Optional[int]:
    if not v:
        return None
    try:
        return int(str(v)[:4])
    except Exception:
        return None


# ─────────────────────────── shared helper ───────────────────────────────────

async def _pub_stats(db, uid: str) -> dict:
    """Real publication metrics from publications + openalex_metrics."""
    pub_count, openalex = await asyncio.gather(
        db.publications.count_documents({"user_id": uid}),
        db.openalex_metrics.find_one({"user_id": uid}),
    )
    h_index    = int((openalex or {}).get("h_index",        0) or 0)
    i10_index  = int((openalex or {}).get("i10_index",      0) or 0)
    total_cit  = int((openalex or {}).get("cited_by_count", 0) or 0)

    # Fallback: sum citations field across publications
    if not total_cit and pub_count:
        agg = await db.publications.aggregate([
            {"$match": {"user_id": uid}},
            {"$group": {"_id": None, "total": {"$sum": "$citations"}}},
        ]).to_list(1)
        total_cit = int((agg[0].get("total") if agg else 0) or 0)

    return {
        "pub_count":      pub_count,
        "h_index":        h_index,
        "i10_index":      i10_index,
        "total_citations": total_cit,
        "has_openalex":   bool(openalex),
    }


# ─────────────────────────── GET /me ─────────────────────────────────────────

@router.get("/me", dependencies=_GATE)
async def my_analytics(user: dict = Depends(get_current_user)):
    """Researcher summary analytics — all real data, no derivations."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    (pub_stats, rep_doc, active_projects,
     active_collab, completed_collab, pending_apps) = await asyncio.gather(
        _pub_stats(db, uid),
        db.reputation_scores.find_one({"user_id": uid}),
        db.projects.count_documents(
            {"$or": [{"owner_id": uid}, {"members": uid}]}
        ),
        db.collaboration_requests.count_documents(
            {"$or": [{"sender_id": uid}, {"receiver_id": uid}], "status": "accepted"}
        ),
        db.collaboration_requests.count_documents(
            {"$or": [{"sender_id": uid}, {"receiver_id": uid}], "status": "declined"}
        ),
        db.collaboration_requests.count_documents(
            {"receiver_id": uid, "status": "pending"}
        ),
    )

    rep            = rep_doc or {}
    collab_score   = ((rep.get("collaboration") or {}).get("score") or 0)
    pub_score      = ((rep.get("publication")   or {}).get("score") or 0)
    expertise_score = ((rep.get("expertise")    or {}).get("score") or 0)
    community_score = ((rep.get("community")    or {}).get("score") or 0)

    return {
        "active_projects":           active_projects,
        "active_collaborations":     active_collab,
        "completed_collaborations":  completed_collab,
        "pending_applications":      pending_apps,
        "accepted_applications":     active_collab,
        "publications":              pub_stats["pub_count"],
        "citations":                 pub_stats["total_citations"],
        "h_index":                   pub_stats["h_index"],
        "i10_index":                 pub_stats["i10_index"],
        "collaboration_score":       collab_score,
        "publication_score":         pub_score,
        "expertise_score":           expertise_score,
        "community_score":           community_score,
        "has_openalex_data":         pub_stats["has_openalex"],
        "has_reputation_data":       bool(rep_doc),
    }


# ─────────────────────────── GET /grants ─────────────────────────────────────

@router.get("/grants", dependencies=_GATE)
async def grant_analytics(user: dict = Depends(get_current_user)):
    """Grant analytics from grant_links (ORCID) and grant_applications (platform)."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    links, apps = await asyncio.gather(
        db.grant_links.find({"user_id": uid}).to_list(500),
        db.grant_applications.find({"pi_id": uid}).to_list(500),
    )

    by_status: dict[str, int] = {}
    by_year:   dict[int, int] = {}
    by_funder: dict[str, int] = {}
    total_funding_usd = 0.0

    for g in links:
        status = g.get("status") or "in_preparation"
        by_status[status] = by_status.get(status, 0) + 1
        if status == "awarded":
            total_funding_usd += _budget_usd(g.get("amount"), g.get("currency"))
        yr = _safe_year(g.get("year_start") or g.get("start_year"))
        if yr:
            by_year[yr] = by_year.get(yr, 0) + 1
        funder = g.get("funder_name") or g.get("funder")
        if funder:
            by_funder[str(funder)] = by_funder.get(str(funder), 0) + 1

    for g in apps:
        raw    = g.get("status") or "in_preparation"
        status = _APP_STATUS.get(raw, "in_preparation")
        by_status[status] = by_status.get(status, 0) + 1
        if status == "awarded":
            total_funding_usd += _budget_usd(g.get("requested_budget"), g.get("currency"))
        yr = _safe_year(g.get("created_at") or g.get("submitted_at"))
        if yr:
            by_year[yr] = by_year.get(yr, 0) + 1

    total     = len(links) + len(apps)
    awarded   = by_status.get("awarded", 0)
    rejected  = by_status.get("rejected", 0)
    with_outcome = awarded + rejected
    success_rate = round(awarded / max(1, with_outcome) * 100, 1) if with_outcome else 0.0

    return {
        "total_grants":         total,
        "awarded":              awarded,
        "submitted":            by_status.get("submitted", 0),
        "in_preparation":       by_status.get("in_preparation", 0),
        "rejected":             rejected,
        "closed":               by_status.get("closed", 0),
        "success_rate":         success_rate,
        "total_funding_usd":    round(total_funding_usd),
        "by_year":              sorted(
            [{"year": k, "count": v} for k, v in by_year.items()],
            key=lambda x: x["year"],
        ),
        "by_funder":            sorted(
            [{"funder": k, "count": v} for k, v in by_funder.items()],
            key=lambda x: -x["count"],
        )[:10],
        "by_status":            [
            {"status": k, "count": v}
            for k, v in sorted(by_status.items(), key=lambda x: -x[1])
        ],
        "grant_links_count":    len(links),
        "platform_apps_count":  len(apps),
    }


# ─────────────────────────── GET /manuscripts ────────────────────────────────

@router.get("/manuscripts", dependencies=_GATE)
async def manuscript_analytics(user: dict = Depends(get_current_user)):
    """Manuscript submission analytics from manuscripts + submissions collections."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    manuscripts = await db.manuscripts.find({"authors": uid}).to_list(300)
    ms_ids = [str(m["_id"]) for m in manuscripts]

    submissions: list[dict] = []
    if ms_ids:
        submissions = await db.submissions.find(
            {"manuscript_id": {"$in": ms_ids}}
        ).to_list(1000)

    stage_counts: dict[str, int] = {}
    for s in submissions:
        stage = s.get("stage") or s.get("status") or "unknown"
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    accepted      = stage_counts.get("accepted", 0) + stage_counts.get("published", 0)
    rejected      = stage_counts.get("rejected", 0)
    withdrawn     = stage_counts.get("withdrawn", 0)
    under_review  = stage_counts.get("under_review", 0)
    revision      = stage_counts.get("revision_requested", 0)

    total_completed = accepted + rejected + withdrawn
    acceptance_rate = (
        round(accepted / max(1, total_completed) * 100, 1) if total_completed else 0.0
    )

    active_ms_statuses = {
        "draft", "internal_review", "ready_for_submission",
        "submitted", "revision_requested", "accepted",
    }
    active = sum(
        1 for m in manuscripts
        if (m.get("status") or "draft") in active_ms_statuses
    )

    by_venue: dict[str, int] = {}
    for s in submissions:
        v = s.get("venue_name") or s.get("venue_id") or "Unknown"
        by_venue[str(v)] = by_venue.get(str(v), 0) + 1

    # Revision cycles: count revision_requested feedbacks per submission
    revision_counts: list[int] = []
    for s in submissions:
        feedbacks  = s.get("feedback") or []
        rev_count  = sum(1 for f in feedbacks if "revision" in (f.get("type") or "").lower())
        if rev_count:
            revision_counts.append(rev_count)
    avg_revisions = (
        round(sum(revision_counts) / len(revision_counts), 1) if revision_counts else 0.0
    )

    by_month: dict[str, int] = {}
    for s in submissions:
        dt = s.get("submitted_at") or s.get("created_at")
        if dt:
            try:
                mo = dt[:7] if isinstance(dt, str) else dt.strftime("%Y-%m")
                by_month[mo] = by_month.get(mo, 0) + 1
            except Exception:
                pass

    return {
        "total_manuscripts":   len(manuscripts),
        "active":              active,
        "total_submissions":   len(submissions),
        "accepted":            accepted,
        "rejected":            rejected,
        "withdrawn":           withdrawn,
        "under_review":        under_review,
        "revision_requested":  revision,
        "acceptance_rate":     acceptance_rate,
        "avg_revision_cycles": avg_revisions,
        "stage_counts":        [
            {"stage": k, "count": v}
            for k, v in sorted(stage_counts.items(), key=lambda x: -x[1])
        ],
        "top_venues":          sorted(
            [{"venue": k, "count": v} for k, v in by_venue.items()],
            key=lambda x: -x["count"],
        )[:8],
        "by_month":            sorted(
            [{"month": k, "count": v} for k, v in by_month.items()]
        ),
    }


# ─────────────────────────── GET /career-timeline ────────────────────────────

@router.get("/career-timeline", dependencies=_GATE)
async def career_timeline(user: dict = Depends(get_current_user)):
    """Research career timeline — publications, citations, projects, grants by year."""
    db        = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid       = user["id"]
    now_year  = datetime.now(timezone.utc).year

    pubs, projects, grant_links, grant_apps = await asyncio.gather(
        db.publications.find(
            {"user_id": uid}, {"year": 1, "citations": 1, "title": 1}
        ).to_list(1000),
        db.projects.find(
            {"$or": [{"owner_id": uid}, {"members": uid}]},
            {"title": 1, "created_at": 1},
        ).to_list(200),
        db.grant_links.find(
            {"user_id": uid},
            {"status": 1, "year_start": 1, "start_year": 1, "title": 1, "funder_name": 1},
        ).to_list(200),
        db.grant_applications.find(
            {"pi_id": uid}, {"status": 1, "created_at": 1, "title": 1}
        ).to_list(200),
    )

    by_year: dict[int, dict] = {}

    def _ensure(y: int) -> None:
        if y not in by_year:
            by_year[y] = {
                "year": y, "publications": 0, "citations": 0,
                "projects": 0, "grants_awarded": 0, "milestones": [],
            }

    for p in pubs:
        yr = p.get("year")
        if yr and isinstance(yr, (int, float)) and 1970 <= int(yr) <= now_year:
            y = int(yr)
            _ensure(y)
            by_year[y]["publications"] += 1
            by_year[y]["citations"]    += int(p.get("citations") or 0)

    for proj in projects:
        y = _safe_year(proj.get("created_at"))
        if y and 1970 <= y <= now_year:
            _ensure(y)
            by_year[y]["projects"] += 1

    for g in grant_links:
        y = _safe_year(g.get("year_start") or g.get("start_year"))
        if y and 1970 <= y <= now_year and g.get("status") == "awarded":
            _ensure(y)
            by_year[y]["grants_awarded"] += 1
            label = g.get("title") or g.get("funder_name") or "Grant"
            by_year[y]["milestones"].append(f"Grant awarded: {label}")

    for g in grant_apps:
        y = _safe_year(g.get("created_at"))
        if y and 1970 <= y <= now_year and _APP_STATUS.get(g.get("status", "")) == "awarded":
            _ensure(y)
            by_year[y]["grants_awarded"] += 1
            by_year[y]["milestones"].append(f"Grant funded: {g.get('title') or 'Platform grant'}")

    timeline = sorted(by_year.values(), key=lambda x: x["year"])
    pub_years = [p.get("year") for p in pubs if p.get("year")]
    first_pub = min(pub_years) if pub_years else None

    return {
        "timeline":               timeline,
        "first_publication_year": first_pub,
        "current_year":           now_year,
        "total_publications":     len(pubs),
        "years_active":           len(timeline),
    }


# ─────────────────────────── GET /network ────────────────────────────────────

@router.get("/network", dependencies=_GATE)
async def collaboration_network(user: dict = Depends(get_current_user)):
    """Co-author and institution network from publications + collaboration_requests."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    pubs, collab_reqs = await asyncio.gather(
        db.publications.find(
            {"user_id": uid}, {"coauthors": 1, "year": 1}
        ).to_list(500),
        db.collaboration_requests.find(
            {"$or": [{"sender_id": uid}, {"receiver_id": uid}], "status": "accepted"},
            {"sender_id": 1, "receiver_id": 1},
        ).to_list(500),
    )

    coauthor_freq:    dict[str, int] = {}
    institution_freq: dict[str, int] = {}

    for pub in pubs:
        for ca in (pub.get("coauthors") or []):
            if isinstance(ca, str):
                name = ca.strip()
            elif isinstance(ca, dict):
                name = (ca.get("display_name") or ca.get("name") or "").strip()
                inst = (ca.get("institution") or ca.get("institution_name") or "").strip()
                if inst:
                    institution_freq[inst] = institution_freq.get(inst, 0) + 1
            else:
                name = ""
            if name:
                coauthor_freq[name] = coauthor_freq.get(name, 0) + 1

    partner_ids: set[str] = set()
    for r in collab_reqs:
        pid = r["receiver_id"] if r.get("sender_id") == uid else r.get("sender_id")
        if pid and pid != uid:
            partner_ids.add(pid)

    partner_profiles: list[dict] = []
    if partner_ids:
        valid_ids = [ObjectId(p) for p in partner_ids if len(p) == 24]
        if valid_ids:
            docs = await db.users.find(
                {"_id": {"$in": valid_ids}},
                {"full_name": 1, "institution": 1, "academic_role": 1, "country": 1},
            ).to_list(50)
            for d in docs:
                partner_profiles.append({
                    "id":          str(d["_id"]),
                    "name":        d.get("full_name") or "Unknown",
                    "institution": d.get("institution"),
                    "role":        d.get("academic_role"),
                    "country":     d.get("country"),
                })

    country_freq: dict[str, int] = {}
    for p in partner_profiles:
        c = (p.get("country") or "").strip()
        if c:
            country_freq[c] = country_freq.get(c, 0) + 1

    return {
        "total_unique_coauthors": len(coauthor_freq),
        "top_coauthors":          sorted(
            [{"name": k, "count": v} for k, v in coauthor_freq.items()],
            key=lambda x: -x["count"],
        )[:30],
        "top_institutions":       sorted(
            [{"institution": k, "count": v} for k, v in institution_freq.items()],
            key=lambda x: -x["count"],
        )[:15],
        "collaboration_partners": partner_profiles[:20],
        "country_distribution":   sorted(
            [{"country": k, "count": v} for k, v in country_freq.items()],
            key=lambda x: -x["count"],
        )[:10],
        "international_partners": len([p for p in partner_profiles if p.get("country")]),
        "total_partners":         len(partner_ids),
    }


# ─────────────────────────── GET /productivity ───────────────────────────────

@router.get("/productivity", dependencies=_GATE)
async def productivity_score(user: dict = Depends(get_current_user)):
    """Transparent research productivity score — formula exposed, all inputs real."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    (pub_stats, rep_doc, collab_count, project_count,
     grant_count, ms_count) = await asyncio.gather(
        _pub_stats(db, uid),
        db.reputation_scores.find_one({"user_id": uid}),
        db.collaboration_requests.count_documents(
            {"$or": [{"sender_id": uid}, {"receiver_id": uid}], "status": "accepted"}
        ),
        db.projects.count_documents(
            {"$or": [{"owner_id": uid}, {"members": uid}]}
        ),
        db.grant_links.count_documents({"user_id": uid, "status": "awarded"}),
        db.manuscripts.count_documents({"authors": uid}),
    )

    pubs = pub_stats["pub_count"]
    cits = pub_stats["total_citations"]
    h    = pub_stats["h_index"]

    # Each component 0–100, log-scaled where appropriate
    cit_score   = round(min(100, math.log1p(cits)         / math.log1p(300) * 100), 1)
    pub_score   = round(min(100, math.log1p(pubs)         / math.log1p(50)  * 100), 1)
    h_score     = round(min(100, h * 5.0),                                           1)
    col_score   = round(min(100, collab_count  * 10.0),                              1)
    proj_score  = round(min(100, project_count * 12.0),                              1)
    grant_score = round(min(100, grant_count   * 25.0),                              1)
    ms_score    = round(min(100, ms_count      * 8.0),                               1)

    raw = round(
        0.25 * cit_score + 0.20 * pub_score + 0.15 * h_score +
        0.15 * col_score + 0.10 * proj_score + 0.10 * grant_score + 0.05 * ms_score,
        1,
    )

    rep         = rep_doc or {}
    rep_overall = int(((rep.get("overall") or {}).get("score") or 0))
    final       = round(0.8 * raw + 0.2 * rep_overall, 1) if rep_overall else raw

    return {
        "score":    int(final),
        "formula":  (
            "Score = 25%×CitationScore + 20%×PublicationScore + 15%×HIndexScore "
            "+ 15%×CollaborationScore + 10%×ProjectScore + 10%×GrantScore + 5%×ManuscriptScore"
        ),
        "components": [
            {"key": "citations",     "label": "Citation Impact",    "score": cit_score,
             "weight": 0.25, "value": cits,          "formula": "log(citations+1)/log(301)×100"},
            {"key": "publications",  "label": "Publication Output", "score": pub_score,
             "weight": 0.20, "value": pubs,          "formula": "log(publications+1)/log(51)×100"},
            {"key": "h_index",       "label": "H-index",           "score": h_score,
             "weight": 0.15, "value": h,             "formula": "h_index×5, cap 100"},
            {"key": "collaboration", "label": "Collaboration",      "score": col_score,
             "weight": 0.15, "value": collab_count,  "formula": "collaborations×10, cap 100"},
            {"key": "projects",      "label": "Research Projects",  "score": proj_score,
             "weight": 0.10, "value": project_count, "formula": "projects×12, cap 100"},
            {"key": "grants",        "label": "Grant Success",      "score": grant_score,
             "weight": 0.10, "value": grant_count,   "formula": "awarded_grants×25, cap 100"},
            {"key": "manuscripts",   "label": "Manuscript Activity","score": ms_score,
             "weight": 0.05, "value": ms_count,      "formula": "manuscripts×8, cap 100"},
        ],
        "reputation_blended":  bool(rep_overall),
        "data_sources": (
            "publications · openalex_metrics · collaboration_requests · "
            "projects · grant_links · manuscripts · reputation_scores"
        ),
    }


# ─────────────────────────── GET /export ─────────────────────────────────────

@router.get("/export", dependencies=_GATE)
async def export_analytics(
    report: str = Query(
        "publications",
        enum=["publications", "grants", "manuscripts", "network", "summary"],
    ),
    user: dict = Depends(get_current_user),
):
    """Download analytics data as CSV."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]

    buf    = io.StringIO()
    writer = csv.writer(buf)

    if report == "publications":
        pubs = await db.publications.find(
            {"user_id": uid},
            {"title": 1, "year": 1, "journal": 1, "citations": 1, "type": 1, "doi": 1},
        ).sort("year", -1).to_list(1000)
        writer.writerow(["Title", "Year", "Journal", "Type", "Citations", "DOI"])
        for p in pubs:
            writer.writerow([
                p.get("title"), p.get("year"), p.get("journal"),
                p.get("type"), p.get("citations", 0), p.get("doi"),
            ])
        filename = "publications.csv"

    elif report == "grants":
        links, apps = await asyncio.gather(
            db.grant_links.find({"user_id": uid}).to_list(500),
            db.grant_applications.find({"pi_id": uid}).to_list(500),
        )
        writer.writerow(["Source", "Title", "Funder", "Status", "Amount", "Currency", "Year"])
        for g in links:
            writer.writerow([
                "orcid", g.get("title"), g.get("funder_name"), g.get("status"),
                g.get("amount"), g.get("currency"), g.get("year_start"),
            ])
        for g in apps:
            writer.writerow([
                "platform", g.get("title"), None,
                _APP_STATUS.get(g.get("status", ""), g.get("status")),
                g.get("requested_budget"), g.get("currency"),
                _safe_year(g.get("created_at")),
            ])
        filename = "grants.csv"

    elif report == "manuscripts":
        mss = await db.manuscripts.find(
            {"authors": uid}, {"title": 1, "status": 1, "created_at": 1}
        ).to_list(300)
        ms_ids = [str(m["_id"]) for m in mss]
        subs: list[dict] = []
        if ms_ids:
            subs = await db.submissions.find(
                {"manuscript_id": {"$in": ms_ids}},
                {"manuscript_id": 1, "stage": 1, "venue_name": 1, "submitted_at": 1},
            ).to_list(1000)
        ms_title: dict[str, str] = {str(m["_id"]): m.get("title") or "" for m in mss}
        writer.writerow(["Manuscript", "Venue", "Stage", "Submitted"])
        for s in subs:
            writer.writerow([
                ms_title.get(s.get("manuscript_id"), "Unknown"),
                s.get("venue_name"), s.get("stage"),
                (s.get("submitted_at") or "")[:10] if s.get("submitted_at") else "",
            ])
        filename = "manuscripts.csv"

    elif report == "network":
        pubs = await db.publications.find(
            {"user_id": uid}, {"coauthors": 1}
        ).to_list(500)
        freq: dict[str, int] = {}
        for p in pubs:
            for ca in (p.get("coauthors") or []):
                name = ca if isinstance(ca, str) else (ca.get("display_name") or ca.get("name") or "")
                if name:
                    freq[str(name)] = freq.get(str(name), 0) + 1
        writer.writerow(["Co-author", "Shared Publications"])
        for name, count in sorted(freq.items(), key=lambda x: -x[1]):
            writer.writerow([name, count])
        filename = "collaboration_network.csv"

    else:  # summary
        pub_stats, rep_doc = await asyncio.gather(
            _pub_stats(db, uid),
            db.reputation_scores.find_one({"user_id": uid}),
        )
        rep = rep_doc or {}
        writer.writerow(["Metric", "Value", "Source"])
        writer.writerow(["Publications",       pub_stats["pub_count"],      "publications collection"])
        writer.writerow(["Total Citations",     pub_stats["total_citations"], "openalex_metrics / publications"])
        writer.writerow(["H-index",             pub_stats["h_index"],        "openalex_metrics"])
        writer.writerow(["i10-index",           pub_stats["i10_index"],      "openalex_metrics"])
        writer.writerow(["Collaboration Score", ((rep.get("collaboration") or {}).get("score") or 0), "reputation_scores"])
        writer.writerow(["Publication Score",   ((rep.get("publication")   or {}).get("score") or 0), "reputation_scores"])
        writer.writerow(["Expertise Score",     ((rep.get("expertise")     or {}).get("score") or 0), "reputation_scores"])
        writer.writerow(["Community Score",     ((rep.get("community")     or {}).get("score") or 0), "reputation_scores"])
        filename = "analytics_summary.csv"

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
