from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/funding", tags=["funding"])


def _ser(d):
    if not d:
        return None
    x = dict(d)
    x["id"] = str(x.pop("_id"))
    return x


@router.get("")
async def list_funding(
    q: Optional[str] = None,
    research_area: Optional[str] = None,
    agency: Optional[str] = None,
    limit: int = 80,
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    query = {}
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"agency": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    if research_area:
        query["research_areas"] = research_area
    if agency:
        query["agency"] = {"$regex": agency, "$options": "i"}
    docs = await db.grants.find(query).sort("deadline", 1).limit(limit).to_list(limit)
    return [_ser(d) for d in docs]


@router.get("/{funding_id}")
async def get_funding(funding_id: str):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        doc = await db.grants.find_one({"_id": ObjectId(funding_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _ser(doc)
