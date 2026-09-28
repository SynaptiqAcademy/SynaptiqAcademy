"""Academic Publishing Intelligence — Smart Journal Matcher.

Six match strategies re-ranking the real-data JournalFitScore list from
journal_analyzer.py. Phase 0: strategies that depended on invented figures
(predicted acceptance probability, desk-rejection risk, a numeric "Impact
Factor" no free source publishes) now rank on the closest real proxy
available, or are limited to journals that actually carry the needed field.
"""
from __future__ import annotations

from .models import JournalFitScore, MatchType, SmartJournalMatch
from .journal_analyzer import analyze_journal_fit

_DESCRIPTIONS: dict[MatchType, str] = {
    MatchType.BEST:            "Best-fit journals by subject overlap and citation strength",
    MatchType.SAFE:            "Journals with a published acceptance rate on record",
    MatchType.HIGH_IMPACT:     "Highest h-index / citation-count journals in scope (OpenAlex)",
    MatchType.FAST_PUB:        "Not available — no connected source publishes review-time data",
    MatchType.OPEN_ACCESS:     "Full open-access journals for maximum discoverability",
    MatchType.BUDGET_FRIENDLY: "Free or low-cost publication options with a known APC",
}

_LABELS: dict[MatchType, str] = {
    MatchType.BEST:            "Best Overall",
    MatchType.SAFE:            "Published Acceptance Rate",
    MatchType.HIGH_IMPACT:     "High Citation Impact",
    MatchType.FAST_PUB:        "Fast Publication",
    MatchType.OPEN_ACCESS:     "Open Access",
    MatchType.BUDGET_FRIENDLY: "Budget-Friendly",
}


def _rank_best(fits: list[JournalFitScore]) -> list[JournalFitScore]:
    return sorted(fits, key=lambda f: -f.overall_fit)


def _rank_safe(fits: list[JournalFitScore]) -> list[JournalFitScore]:
    # Only journals with a real, published acceptance rate qualify.
    with_rate = [f for f in fits if f.journal.acceptance_rate is not None]
    return sorted(with_rate, key=lambda f: -(f.journal.acceptance_rate or 0))


def _rank_high_impact(fits: list[JournalFitScore]) -> list[JournalFitScore]:
    with_h = [f for f in fits if f.journal.h_index]
    return sorted(with_h, key=lambda f: -(f.journal.h_index or 0))


def _rank_fast(fits: list[JournalFitScore]) -> list[JournalFitScore]:
    # No connected source publishes review/time-to-publication data today.
    return []


def _rank_open_access(fits: list[JournalFitScore]) -> list[JournalFitScore]:
    oa = [f for f in fits if f.journal.open_access]
    return sorted(oa, key=lambda f: -f.overall_fit)


def _rank_budget(fits: list[JournalFitScore]) -> list[JournalFitScore]:
    budget = [f for f in fits if f.journal.apc_usd is not None and f.journal.apc_usd <= 1000]
    return sorted(budget, key=lambda f: (f.journal.apc_usd or 0, -f.overall_fit))


_RANKERS = {
    MatchType.BEST:            _rank_best,
    MatchType.SAFE:            _rank_safe,
    MatchType.HIGH_IMPACT:     _rank_high_impact,
    MatchType.FAST_PUB:        _rank_fast,
    MatchType.OPEN_ACCESS:     _rank_open_access,
    MatchType.BUDGET_FRIENDLY: _rank_budget,
}


async def match_journals(
    text: str,
    discipline: str,
    manuscript_quality: float,
    match_types: list[MatchType] | None = None,
    db=None,
) -> list[SmartJournalMatch]:
    """Return one SmartJournalMatch per requested match type."""
    if match_types is None:
        match_types = list(MatchType)

    base_fits = await analyze_journal_fit(text, discipline, manuscript_quality, db=db)

    results: list[SmartJournalMatch] = []
    for mtype in match_types:
        ranker = _RANKERS[mtype]
        ranked = ranker(base_fits)[:6]
        for fs in ranked:
            fs.match_type = mtype

        top = ranked[0] if ranked else None
        results.append(SmartJournalMatch(
            match_type=mtype,
            label=_LABELS[mtype],
            description=_DESCRIPTIONS[mtype],
            fits=ranked,
            top_pick=top,
        ))

    return results
