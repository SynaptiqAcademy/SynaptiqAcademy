"""Academic Publishing Intelligence — Grant analyzer.

Phase 0 rewrite: scores grants against a manuscript/proposal using only the
live `grants` collection (NIH RePORTER / OpenAIRE / UKRI ingestion via
services/discovery). No hardcoded grant database, no invented
"funding probability" or "proposal readiness" score — see AUDIT_PHASE0.md.
Seed/demo grant records (`is_seed: true`) are excluded, as are grants whose
deadline has already passed.
"""
from __future__ import annotations

from datetime import date

from db import get_db
from repo.security_context import SecurityContext
from repo.shim import DBProxy
from .models import GrantFit


def _as_list(v) -> list[str]:
    """Defensive normalization — some legacy/seed records store a
    comma-separated string where the schema expects a list."""
    if not v:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x]
    if isinstance(v, str):
        return [s.strip() for s in v.split(",") if s.strip()]
    return []

_MAX_CANDIDATES = 300


def _topic_overlap(text_lower: str, discipline_lower: str, topics: list[str]) -> float:
    if not topics:
        return 0.0
    topics_lower = [t.lower() for t in topics if t]
    hits = sum(1 for t in topics_lower if t in text_lower or t in discipline_lower)
    return round(min(1.0, hits / max(len(topics_lower) * 0.4, 1)), 3)


def _amount_usd(g: dict) -> int:
    fa = g.get("funding_amount") or {}
    amt = fa.get("amount")
    try:
        return int(amt) if amt else 0
    except (TypeError, ValueError):
        return 0


def _to_fit(g: dict, topic_fit: float) -> GrantFit:
    topics = _as_list(g.get("research_areas")) + _as_list(g.get("keywords"))
    fit = GrantFit(
        title=g.get("title", ""),
        funder=g.get("sponsor", ""),
        amount_usd=_amount_usd(g),
        deadline=g.get("deadline") or "",
        eligibility=[g.get("eligibility")] if g.get("eligibility") else [],
        topics=topics,
    )
    fit.topic_fit = topic_fit
    caveats = []
    if not g.get("deadline"):
        caveats.append("no deadline on record")
    if not fit.amount_usd:
        caveats.append("no funding amount on record")
    fit.rationale = (
        f"{fit.title} shares {topic_fit:.0%} of its indexed research areas with this project"
        + (f" ({'; '.join(caveats)})" if caveats else "")
        + f". Source: {g.get('source', 'unknown')}."
    )
    return fit


async def get_all_profiles(db=None, limit: int = _MAX_CANDIDATES) -> list[dict]:
    if db is None:
        db = DBProxy(get_db(), SecurityContext.system())
    today = date.today().isoformat()
    docs = await db.grants.find({
        "is_seed": {"$ne": True},
        "$or": [{"deadline": None}, {"deadline": {"$gte": today}}],
    }).limit(limit).to_list(limit)
    return docs


async def analyze_grant_fit(
    text: str,
    discipline: str,
    manuscript_quality: float,
    user_profile: dict | None = None,
    db=None,
) -> list[GrantFit]:
    """`manuscript_quality` is accepted for API compatibility but no longer
    perturbs the score — there is no real basis for a predicted funding
    probability, so none is produced (see journal_analyzer.py)."""
    if db is None:
        db = DBProxy(get_db(), SecurityContext.system())

    text_lower = (text or "").lower()
    discipline_lower = (discipline or "").lower()

    grants = await get_all_profiles(db=db)
    scored: list[tuple[float, GrantFit]] = []

    for g in grants:
        topics = _as_list(g.get("research_areas")) + _as_list(g.get("keywords"))
        topic_fit = _topic_overlap(text_lower, discipline_lower, topics)
        if topic_fit == 0.0:
            continue
        fit = _to_fit(g, topic_fit)
        scored.append((topic_fit, fit))

    scored.sort(key=lambda x: -x[0])
    return [f for _, f in scored]
