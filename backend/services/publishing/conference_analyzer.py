"""Academic Publishing Intelligence — Conference analyzer.

Phase 0 rewrite: scores conferences against a manuscript using only the live
`conferences` collection (WikiCFP ingestion via services/discovery). No
hardcoded conference database, no invented acceptance rate, registration
fee, or "networking/career value" scores — see AUDIT_PHASE0.md. Seed/demo
conference records (`is_seed: true`) are excluded, as are conferences whose
submission deadline has already passed.
"""
from __future__ import annotations

from datetime import date

from db import get_db
from repo.security_context import SecurityContext
from repo.shim import DBProxy
from .models import ConferenceFit


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


def _scope_hit(text_lower: str, discipline_lower: str, tags: list[str]) -> float:
    if not tags:
        return 0.0
    tags_lower = [t.lower() for t in tags if t]
    hits = sum(1 for t in tags_lower if t in text_lower or t in discipline_lower)
    return round(min(1.0, hits / max(len(tags_lower) * 0.4, 1)), 3)


def _to_fit(c: dict, scope: float) -> ConferenceFit:
    tags = _as_list(c.get("topics")) + _as_list(c.get("research_areas"))
    fit = ConferenceFit(
        name=c.get("name", ""),
        acronym=c.get("acronym") or "",
        publisher=c.get("organizer") or "",
        ranking=c.get("rank") or "",
        topics=tags,
        is_indexed=bool(c.get("rank")),  # only claim "indexed" if a source actually ranked it
        submission_deadline=c.get("submission_deadline") or "",
        notification_date=c.get("notification_date") or "",
        event_date=c.get("start_date") or "",
        location=c.get("location") or "",
    )
    fit.research_fit = scope
    fit.overall_score = scope
    caveats = []
    if not c.get("submission_deadline"):
        caveats.append("no submission deadline on record")
    if not c.get("rank"):
        caveats.append("no ranking source")
    fit.rationale = (
        f"{fit.name} shares {scope:.0%} of its indexed topics with this manuscript"
        + (f" ({'; '.join(caveats)})" if caveats else "")
        + "."
    )
    return fit


async def get_all_profiles(db=None, limit: int = _MAX_CANDIDATES) -> list[dict]:
    if db is None:
        db = DBProxy(get_db(), SecurityContext.system())
    today = date.today().isoformat()
    docs = await db.conferences.find({
        "is_seed": {"$ne": True},
        "$or": [{"submission_deadline": None}, {"submission_deadline": {"$gte": today}}],
    }).limit(limit).to_list(limit)
    return docs


async def analyze_conference_fit(
    text: str,
    discipline: str,
    manuscript_quality: float,
    db=None,
) -> list[ConferenceFit]:
    """`manuscript_quality` is accepted for API compatibility but no longer
    perturbs the score — see journal_analyzer.py for the same rationale."""
    if db is None:
        db = DBProxy(get_db(), SecurityContext.system())

    text_lower = (text or "").lower()
    discipline_lower = (discipline or "").lower()

    conferences = await get_all_profiles(db=db)
    scored: list[tuple[float, ConferenceFit]] = []

    for c in conferences:
        tags = _as_list(c.get("topics")) + _as_list(c.get("research_areas"))
        scope = _scope_hit(text_lower, discipline_lower, tags)
        if scope == 0.0:
            continue
        fit = _to_fit(c, scope)
        scored.append((scope, fit))

    scored.sort(key=lambda x: -x[0])
    return [f for _, f in scored]
