"""Journals — Discovery Suite read API.

Endpoints
---------
GET /api/journals                Faceted search + pagination
GET /api/journals/facets         Available subject + quartile + OA facets
GET /api/journals/{id}           Full journal record (rich profile)
"""
from __future__ import annotations

from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user
from db import get_db
from services.permissions import check_discovery_quota
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/journals", tags=["journals"])


def _ser(d):
    if not d: return None
    x = dict(d); x["id"] = str(x.pop("_id")); return x


@router.get("")
async def list_journals(
    q: Optional[str] = Query(None, description="Full-text query"),
    subject: Optional[str] = None,
    quartile: Optional[str] = None,
    open_access: Optional[bool] = None,
    apc_max: Optional[int] = Query(None, ge=0),
    publisher: Optional[str] = None,
    country: Optional[str] = None,
    sort: str = Query("popularity", regex="^(popularity|works|citations|recent|relevance)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    await check_discovery_quota(user, "journal")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    query: dict = {}
    if q: query["$text"] = {"$search": q}
    if subject: query["subjects"] = subject
    if quartile: query["quartile"] = quartile
    if open_access is not None: query["open_access"] = open_access
    if apc_max is not None:
        query["$or"] = [{"apc_usd": {"$lte": apc_max}}, {"apc_usd": None}, {"apc_usd": {"$exists": False}}]
    if publisher:
        import re as _re
        query["publisher"] = {"$regex": f"^{_re.escape(publisher)}", "$options": "i"}
    if country: query["country"] = country.upper()

    # Sort
    if sort == "relevance" and q:
        cursor = db.journals.find(query, {"score": {"$meta": "textScore"}})
        cursor = cursor.sort([("score", {"$meta": "textScore"}), ("popularity_score", -1)])
    elif sort == "works":
        cursor = db.journals.find(query).sort([("works_count", -1)])
    elif sort == "citations":
        cursor = db.journals.find(query).sort([("cited_by_count", -1)])
    elif sort == "recent":
        cursor = db.journals.find(query).sort([("updated_at", -1)])
    else:
        cursor = db.journals.find(query).sort([("popularity_score", -1), ("works_count", -1)])

    total = await db.journals.count_documents(query)
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
async def journal_facets(q: Optional[str] = None, _user: dict = Depends(get_current_user)):
    """Returns top filter values for the current query (subjects, publishers, countries, quartiles)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    match: dict = {}
    if q: match["$text"] = {"$search": q}
    pipeline = [
        {"$match": match},
        {"$facet": {
            "subjects": [
                {"$unwind": "$subjects"},
                {"$group": {"_id": "$subjects", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}, {"$limit": 30},
            ],
            "publishers": [
                {"$group": {"_id": "$publisher", "count": {"$sum": 1}}},
                {"$match": {"_id": {"$ne": ""}}},
                {"$sort": {"count": -1}}, {"$limit": 25},
            ],
            "countries": [
                {"$group": {"_id": "$country", "count": {"$sum": 1}}},
                {"$match": {"_id": {"$ne": None}}},
                {"$sort": {"count": -1}}, {"$limit": 25},
            ],
            "quartile": [
                {"$group": {"_id": "$quartile", "count": {"$sum": 1}}},
                {"$match": {"_id": {"$ne": None}}},
                {"$sort": {"_id": 1}},
            ],
            "open_access": [
                {"$group": {"_id": "$open_access", "count": {"$sum": 1}}},
            ],
        }},
    ]
    out = await db.journals.aggregate(pipeline).to_list(1)
    return out[0] if out else {"subjects": [], "publishers": [], "countries": [], "quartile": [], "open_access": []}


@router.get("/{journal_id}")
async def get_journal(journal_id: str, _user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try: oid = ObjectId(journal_id)
    except Exception: raise HTTPException(status_code=404, detail="Not found")
    doc = await db.journals.find_one({"_id": oid})
    if not doc: raise HTTPException(status_code=404, detail="Not found")
    return _ser(doc)
