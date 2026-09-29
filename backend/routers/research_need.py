"""P1 Phase 8C — Research Need Intelligence.

Research question -> structured Research Need -> required expertise ->
real Synaptiq people -> explainable match. Two endpoints, cleanly split so
only the AI interpretation step can ever cost credits — retrieval/matching
is always free, same invariant as Phase 8B's basic discovery.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from repo.shim import make_db_proxy
from plans_catalogue import CREDIT_COSTS
from services.credits_service import consume_credits, refund_credits
from services.research_need.interpreter import interpret_research_need, CREDIT_ACTION
from services.research_need.models import ResearchNeed
from services.research_need.relevance import find_relevant_people

router = APIRouter(prefix="/api/research-need", tags=["research-need"])


def _uid(user) -> str:
    return str(user["id"])


class InterpretRequest(BaseModel):
    query: str
    use_ai: bool = True


class MatchRequest(BaseModel):
    need: ResearchNeed
    # Real backend controls (§22 of Phase 8D) — each maps straight into
    # discovery_engine's own filter handling or relevance.py's grouping
    # logic; none of these is decorative.
    country: Optional[str] = None
    language: Optional[str] = None
    available_for_collaboration: Optional[bool] = None
    include_methods: bool = True
    prioritize: Optional[str] = None  # "directly_relevant" | "complementary_expertise" | ...


@router.get("/cost")
async def interpret_cost():
    """So the frontend can show the cost BEFORE the user commits to AI
    interpretation, per §5 — no auth needed, this is a static price."""
    return {"action": CREDIT_ACTION, "cost": CREDIT_COSTS.get(CREDIT_ACTION, 0)}


@router.post("/interpret")
async def interpret(
    payload: InterpretRequest,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """AI (or, if declined/unavailable, deterministic) interpretation of a
    free-text research question into a structured, user-editable
    ResearchNeed. Credits are charged only when a real AI call is actually
    attempted, and refunded immediately if it falls back — never charged for
    something that didn't happen.
    """
    db = make_db_proxy(db, user)
    uid = _uid(user)

    charged = None
    if payload.use_ai:
        charged = await consume_credits(uid, CREDIT_ACTION, metadata={"query_len": len(payload.query or "")})

    need, meta = await interpret_research_need(payload.query, use_ai=payload.use_ai, user_id=uid, db=db)

    if payload.use_ai and meta["source"] != "ai":
        # Not a valid AI operation (unavailable/malformed/error) — refund.
        await refund_credits(uid, CREDIT_ACTION, reason=meta.get("reason") or "ai_interpretation_fallback")
        charged = None

    return {
        "need": need.model_dump(),
        "source": meta["source"],
        "credits_consumed": charged["consumed"] if charged else 0,
        "credits_balance": charged["balance"] if charged else None,
    }


@router.post("/match")
async def match(
    payload: MatchRequest,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Deterministic, zero-credit retrieval + relevance grouping against the
    (possibly user-edited) ResearchNeed. Reuses discovery_engine.search_people
    directly — every Phase 8B eligibility/privacy rule applies for free.
    """
    db = make_db_proxy(db, user)
    result = await find_relevant_people(
        db, payload.need, viewer_id=_uid(user),
        country=payload.country, language=payload.language,
        available_for_collaboration=payload.available_for_collaboration,
        include_methods=payload.include_methods, prioritize=payload.prioritize,
    )
    return result
