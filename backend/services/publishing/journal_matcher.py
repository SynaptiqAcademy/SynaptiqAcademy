"""Academic Publishing Intelligence — Smart Journal Matcher (Phase XII).

Six match strategies: Best, Safe, HighImpact, FastPublication, OpenAccess,
BudgetFriendly. Each strategy re-ranks the pre-scored JournalFitScore list.
"""
from __future__ import annotations

from .models import JournalFitScore, MatchType, SmartJournalMatch
from .journal_analyzer import analyze_journal_fit

_DESCRIPTIONS: dict[MatchType, str] = {
    MatchType.BEST:            "Best-fit journals balancing scope, IF, and acceptance probability",
    MatchType.SAFE:            "High-acceptance journals that reduce rejection risk",
    MatchType.HIGH_IMPACT:     "Q1 and top-Q2 journals with the highest impact factors",
    MatchType.FAST_PUB:        "Fastest review-to-publication pipelines",
    MatchType.OPEN_ACCESS:     "Full open-access journals for maximum discoverability",
    MatchType.BUDGET_FRIENDLY: "Free or low-cost publication options",
}

_LABELS: dict[MatchType, str] = {
    MatchType.BEST:            "Best Overall",
    MatchType.SAFE:            "Safe Choice",
    MatchType.HIGH_IMPACT:     "High Impact",
    MatchType.FAST_PUB:        "Fast Publication",
    MatchType.OPEN_ACCESS:     "Open Access",
    MatchType.BUDGET_FRIENDLY: "Budget-Friendly",
}


def _rank_best(fits: list[JournalFitScore]) -> list[JournalFitScore]:
    return sorted(fits, key=lambda f: -f.overall_fit)


def _rank_safe(fits: list[JournalFitScore]) -> list[JournalFitScore]:
    # Weight acceptance probability heavily; penalise very low-IF journals
    return sorted(
        fits,
        key=lambda f: -(
            0.55 * f.acceptance_probability
            + 0.25 * f.scope_match
            + 0.10 * (1 - f.desk_rejection_risk)
            + 0.10 * min(1.0, f.journal.impact_factor / 10)
        ),
    )


def _rank_high_impact(fits: list[JournalFitScore]) -> list[JournalFitScore]:
    hi = [f for f in fits if f.journal.quartile in ("Q1", "Q2")]
    return sorted(hi, key=lambda f: -f.journal.impact_factor)


def _rank_fast(fits: list[JournalFitScore]) -> list[JournalFitScore]:
    return sorted(
        fits,
        key=lambda f: (
            f.journal.review_duration_weeks,
            f.journal.time_to_publication_weeks,
            -f.scope_match,
        ),
    )


def _rank_open_access(fits: list[JournalFitScore]) -> list[JournalFitScore]:
    oa = [f for f in fits if f.journal.open_access]
    return sorted(oa, key=lambda f: -(f.overall_fit * 0.7 + f.acceptance_probability * 0.3))


def _rank_budget(fits: list[JournalFitScore]) -> list[JournalFitScore]:
    budget = [f for f in fits if f.journal.apc_usd <= 1000]
    return sorted(budget, key=lambda f: (f.journal.apc_usd, -f.overall_fit))


_RANKERS = {
    MatchType.BEST:            _rank_best,
    MatchType.SAFE:            _rank_safe,
    MatchType.HIGH_IMPACT:     _rank_high_impact,
    MatchType.FAST_PUB:        _rank_fast,
    MatchType.OPEN_ACCESS:     _rank_open_access,
    MatchType.BUDGET_FRIENDLY: _rank_budget,
}


def match_journals(
    text: str,
    discipline: str,
    manuscript_quality: float,
    match_types: list[MatchType] | None = None,
) -> list[SmartJournalMatch]:
    """Return one SmartJournalMatch per requested match type."""
    if match_types is None:
        match_types = list(MatchType)

    base_fits = analyze_journal_fit(text, discipline, manuscript_quality)

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
