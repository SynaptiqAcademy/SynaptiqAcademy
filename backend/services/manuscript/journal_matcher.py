"""Field-aware journal recommender.

Phase 0 rewrite: candidate journals come from the live `journals` collection
(real OpenAlex/Crossref/DOAJ ingestion), not a hardcoded list. AI-suggested
journals (`ai_journal_dicts`, from the manuscript-review LLM pass) are only
kept if they match a real record in that collection by title — an LLM can
otherwise hallucinate a journal name or its impact factor, and Phase 0
requires every published claim to trace to a real source. Unmatched AI
suggestions are dropped, not shown.
"""
from __future__ import annotations

from db import get_db
from repo.security_context import SecurityContext
from repo.shim import DBProxy
from .models import JournalMatch


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

_DISC_SIGNALS: dict[str, list[str]] = {
    "medicine": ["patient", "clinical", "diagnosis", "treatment", "disease", "drug",
                 "surgery", "therapy", "hospital", "epidemiology", "prevalence"],
    "psychology": ["behaviour", "behavior", "cognitive", "anxiety", "depression",
                   "personality", "emotion", "perception", "memory", "attitude"],
    "education": ["student", "learning", "teaching", "curriculum", "pedagogy",
                  "classroom", "school", "university", "academic achievement", "higher education"],
    "AI": ["neural network", "machine learning", "deep learning", "algorithm",
            "natural language processing", "computer vision", "reinforcement learning",
            "transformer", "llm", "large language model", "classification"],
    "management": ["organisation", "organization", "leadership", "strategy", "firm",
                   "managerial", "corporate", "employee", "performance", "governance"],
    "sustainability": ["sustainable", "green", "carbon", "climate change", "renewable",
                       "circular economy", "environmental", "ESG", "net zero"],
    "science": ["experiment", "hypothesis", "laboratory", "biology", "chemistry",
                "physics", "genome", "protein", "cell", "enzyme"],
}


def infer_discipline(text_lower: str, ai_discipline: str = "") -> str:
    if ai_discipline:
        return ai_discipline
    scores: dict[str, int] = {d: 0 for d in _DISC_SIGNALS}
    for disc, signals in _DISC_SIGNALS.items():
        for sig in signals:
            if sig in text_lower:
                scores[disc] += 1
    if not any(v > 0 for v in scores.values()):
        return "general"
    return max(scores, key=lambda k: scores[k])


def _journal_match_from_doc(j: dict, scope: float) -> JournalMatch:
    return JournalMatch(
        name=j.get("title") or j.get("name") or "",
        publisher=j.get("publisher", ""),
        quartile=j.get("quartile") or "",
        scope_match=round(scope, 3),
        acceptance_probability=None,
        impact_factor=None,  # no legitimate free source publishes this
        submission_notes=(
            f"Quartile is {'an OpenAlex citation-based estimate' if j.get('quartile_source') == 'openalex_estimate' else 'as reported by source'}."
            if j.get("quartile") else "No quartile data available."
        ),
        open_access=bool(j.get("open_access", False)),
    )


async def recommend_journals(
    text: str,
    discipline: str,
    overall_score: float,
    ai_journal_dicts: list[dict] | None = None,
    db=None,
) -> list[JournalMatch]:
    """Return up to 6 ranked journal matches from real, sourced records.
    `overall_score` is accepted for API compatibility but no longer perturbs
    the score — see services/publishing/journal_analyzer.py for the
    rationale (no real basis for a quality-adjusted acceptance estimate)."""
    if db is None:
        db = DBProxy(get_db(), SecurityContext.system())

    text_lower = text.lower()
    docs = await db.journals.find({"is_seed": {"$ne": True}}).limit(300).to_list(300)

    matched: list[tuple[float, JournalMatch]] = []
    by_title: dict[str, dict] = {}
    for j in docs:
        title = (j.get("title") or j.get("name") or "")
        if not title:
            continue
        by_title[title.lower()] = j
        tags = _as_list(j.get("subjects")) + _as_list(j.get("research_areas")) + _as_list(j.get("scope_keywords"))
        if not tags:
            continue
        relevance = sum(1 for t in tags if t and (t.lower() in text_lower or t.lower() in discipline.lower()))
        if relevance == 0:
            continue
        scope = min(1.0, relevance / max(len(tags) * 0.5, 1))
        matched.append((scope, _journal_match_from_doc(j, scope)))

    matched.sort(key=lambda x: -x[0])
    results: list[JournalMatch] = [m for _, m in matched[:4]]

    # ── Merge AI-suggested journals, but only if they match a real record ──
    seen = {j.name.lower() for j in results}
    if ai_journal_dicts:
        for jd in ai_journal_dicts:
            name = (jd.get("name") or "").strip()
            if not name or name.lower() in seen:
                continue
            real = by_title.get(name.lower())
            if not real:
                continue  # LLM-suggested journal not found in real data — drop, don't fabricate
            results.append(_journal_match_from_doc(real, scope=0.7))
            seen.add(name.lower())

    q_order = {"Q1": 0, "Q2": 1, "Q3": 2, "Q4": 3}
    results.sort(key=lambda j: (q_order.get(j.quartile, 9), -j.scope_match))
    return results[:6]
