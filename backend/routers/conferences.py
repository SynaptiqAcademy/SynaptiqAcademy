"""Conferences — Discovery Suite read API.

Endpoints
---------
GET /api/conferences            Faceted search + pagination + deadline state
GET /api/conferences/facets     Top research areas / countries / ranks for the query
GET /api/conferences/{id}       Rich profile
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user
from db import get_db
from services.permissions import check_discovery_quota
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/conferences", tags=["conferences"])


def _today_iso() -> str: return date.today().isoformat()
def _plus(days: int) -> str: return (date.today() + timedelta(days=days)).isoformat()


def _enrich_deadline(d: dict) -> dict:
    today = _today_iso(); soon = _plus(30)
    state = "unknown"
    sd = d.get("submission_deadline")
    if sd:
        if sd < today: state = "closed"
        elif sd <= soon: state = "closing_soon"
        else: state = "open"
    d["deadline_state"] = state
    return d


def _ser(d):
    if not d: return None
    x = dict(d); x["id"] = str(x.pop("_id"))
    return _enrich_deadline(x)


@router.get("")
async def list_conferences(
    q: Optional[str] = None,
    research_area: Optional[str] = None,
    rank: Optional[str] = None,
    country: Optional[str] = None,
    deadline_state: Optional[str] = Query(None, regex="^(open|closing_soon|closed|any)$"),
    format: Optional[str] = Query(None, regex="^(in-person|virtual|hybrid)$"),
    sort: str = Query("deadline_asc", regex="^(deadline_asc|deadline_desc|recent|relevance)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    await check_discovery_quota(user, "conference")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    query: dict = {}
    if q: query["$text"] = {"$search": q}
    if research_area: query["research_areas"] = research_area
    if rank: query["rank"] = rank
    if country: query["country"] = country.upper()
    if format: query["format"] = format
    today = _today_iso(); soon = _plus(30)
    if deadline_state == "open":
        query["submission_deadline"] = {"$gt": soon}
    elif deadline_state == "closing_soon":
        query["submission_deadline"] = {"$gte": today, "$lte": soon}
    elif deadline_state == "closed":
        query["submission_deadline"] = {"$lt": today}

    if sort == "relevance" and q:
        cursor = db.conferences.find(query, {"score": {"$meta": "textScore"}})
        cursor = cursor.sort([("score", {"$meta": "textScore"}), ("submission_deadline", 1)])
    elif sort == "deadline_desc":
        cursor = db.conferences.find(query).sort([("submission_deadline", -1)])
    elif sort == "recent":
        cursor = db.conferences.find(query).sort([("updated_at", -1)])
    elif sort == "deadline_asc":
        # Only filter by non-null deadline when an explicit deadline_state filter is set.
        # Otherwise sort ascending but include rows without deadlines so users see all.
        if deadline_state in ("open", "closing_soon", "closed"):
            pass  # query already filters to a specific deadline state
        cursor = db.conferences.find(query).sort([("submission_deadline", 1), ("start_date", 1)])
    else:
        cursor = db.conferences.find(query).sort([("updated_at", -1)])

    total = await db.conferences.count_documents(query)
    skip = (page - 1) * page_size
    docs = await cursor.skip(skip).limit(page_size).to_list(page_size)
    return {
        "items": [_ser(d) for d in docs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": skip + len(docs) < total,
    }


@router.get("/facets")
async def conference_facets(q: Optional[str] = None, _user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    match: dict = {}
    if q: match["$text"] = {"$search": q}
    today = _today_iso(); soon = _plus(30)
    pipeline = [
        {"$match": match},
        {"$facet": {
            "research_areas": [
                {"$unwind": "$research_areas"},
                {"$group": {"_id": "$research_areas", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}, {"$limit": 25},
            ],
            "rank": [
                {"$group": {"_id": "$rank", "count": {"$sum": 1}}},
                {"$match": {"_id": {"$ne": None}}}, {"$sort": {"_id": 1}},
            ],
            "deadline_state": [
                {"$project": {
                    "state": {"$switch": {
                        "branches": [
                            {"case": {"$or": [{"$eq": ["$submission_deadline", None]}, {"$not": ["$submission_deadline"]}]}, "then": "unknown"},
                            {"case": {"$lt": ["$submission_deadline", today]}, "then": "closed"},
                            {"case": {"$lte": ["$submission_deadline", soon]}, "then": "closing_soon"},
                        ], "default": "open"}}
                }},
                {"$group": {"_id": "$state", "count": {"$sum": 1}}},
            ],
            "countries": [
                {"$group": {"_id": "$country", "count": {"$sum": 1}}},
                {"$match": {"_id": {"$ne": None}}}, {"$sort": {"count": -1}}, {"$limit": 25},
            ],
        }},
    ]
    out = await db.conferences.aggregate(pipeline).to_list(1)
    return out[0] if out else {}


@router.get("/{conf_id}")
async def get_conference(conf_id: str, _user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try: oid = ObjectId(conf_id)
    except Exception: raise HTTPException(status_code=404, detail="Not found")
    doc = await db.conferences.find_one({"_id": oid})
    if not doc: raise HTTPException(status_code=404, detail="Not found")
    return _ser(doc)
