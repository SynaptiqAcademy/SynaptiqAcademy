"""Academic Publishing Intelligence — Publication strategy builder (Phase XII)."""
from __future__ import annotations

from .models import (
    JournalFitScore, PublicationStrategy, StrategyType, StrategicOption,
)
from .journal_analyzer import analyze_journal_fit


def _build_tiered_strategy(fits: list[JournalFitScore]) -> StrategicOption:
    top   = fits[0].journal.name if len(fits) > 0 else "top target journal"
    safe  = fits[1].journal.name if len(fits) > 1 else "backup journal"
    safer = fits[2].journal.name if len(fits) > 2 else "safe fallback journal"
    return StrategicOption(
        strategy_type=StrategyType.TIERED,
        title="Tiered Submission Strategy",
        description="Submit to journals in order: aim high, work down through backups.",
        steps=[
            f"Submit to {top} (highest-fit, competitive journal)",
            f"If rejected, submit to {safe} (well-matched backup)",
            f"If rejected again, submit to {safer} (high-acceptance fallback)",
            "Revise manuscript based on peer review feedback between submissions",
        ],
        estimated_weeks=30,
        success_probability=round(
            1 - (
                (1 - fits[0].acceptance_probability) *
                (1 - fits[1].acceptance_probability if len(fits) > 1 else 0.5)
            ),
            3,
        ) if fits else 0.7,
        risks=["Each rejection adds 3–6 months to timeline"],
        rewards=["Maximises prestige — starts with your best shot at a top journal"],
        recommended=True,
    )


def _build_parallel_strategy(fits: list[JournalFitScore]) -> StrategicOption:
    return StrategicOption(
        strategy_type=StrategyType.PARALLEL,
        title="Parallel Submission Strategy",
        description=(
            "Prepare multiple journal-specific versions simultaneously. "
            "Note: simultaneous submission to most journals is prohibited — "
            "use only for conferences + journal combinations."
        ),
        steps=[
            "Identify 1 journal + 2 conference targets with non-overlapping timelines",
            "Submit to conference first (faster review cycle)",
            "Expand conference paper for journal submission post-conference",
            "Leverage conference feedback to strengthen journal submission",
        ],
        estimated_weeks=20,
        success_probability=0.75,
        risks=["Dual submission to two journals simultaneously violates most ethics policies"],
        rewards=["Faster path to first publication; conference paper builds visibility"],
        recommended=False,
    )


def _build_conference_first(journal_name: str) -> StrategicOption:
    return StrategicOption(
        strategy_type=StrategyType.CONFERENCE_FIRST,
        title="Conference-First Strategy",
        description="Build visibility and collect feedback before journal submission.",
        steps=[
            "Submit extended abstract to a relevant A/A* conference",
            "Present work; collect expert feedback",
            "Expand and revise for full journal paper",
            f"Submit expanded version to {journal_name}",
        ],
        estimated_weeks=40,
        success_probability=0.70,
        risks=["Longer timeline; conference version may need significant expansion"],
        rewards=["Peer feedback before journal; stronger network; citation head start"],
        recommended=False,
    )


def _build_oa_first(fits: list[JournalFitScore]) -> StrategicOption:
    oa_fits = [f for f in fits if f.journal.open_access]
    top_oa = oa_fits[0].journal.name if oa_fits else "PLOS ONE"
    return StrategicOption(
        strategy_type=StrategyType.OPEN_ACCESS_FIRST,
        title="Open-Access First Strategy",
        description="Prioritise open-access journals for maximum discoverability and citation impact.",
        steps=[
            f"Submit to {top_oa} (open-access journal)",
            "Leverage preprint server (arXiv/bioRxiv) for immediate visibility",
            "Promote via ResearchGate and social media after acceptance",
            "Track citation metrics to demonstrate impact",
        ],
        estimated_weeks=16,
        success_probability=round(oa_fits[0].acceptance_probability if oa_fits else 0.60, 3),
        risks=["APCs may be required; lower IF compared to subscription journals"],
        rewards=["Maximum readership; faster citations; compliant with many funder mandates"],
        recommended=False,
    )


def _build_multi_paper(manuscript_title: str) -> StrategicOption:
    return StrategicOption(
        strategy_type=StrategyType.MULTI_PAPER,
        title="Multi-Paper Strategy",
        description="Split research into a paper series for sustained publication output.",
        steps=[
            f"Paper 1: Theory/Methods from '{manuscript_title}' → target fast journal",
            "Paper 2: Empirical results → target high-impact journal",
            "Paper 3: Implications/Applications → target practitioner journal",
            "Cross-cite across the series to boost visibility and citation counts",
        ],
        estimated_weeks=52,
        success_probability=0.80,
        risks=["Risk of 'salami slicing' — check journal policies; requires sustained effort"],
        rewards=["Multiple publications; sustained citation growth; broader audience reach"],
        recommended=False,
    )


def build_publication_strategy(
    manuscript_title: str,
    text: str,
    discipline: str,
    manuscript_quality: float,
) -> PublicationStrategy:
    fits = analyze_journal_fit(text, discipline, manuscript_quality)
    top_fits = fits[:6] if fits else []

    tiered = _build_tiered_strategy(top_fits)
    parallel = _build_parallel_strategy(top_fits)
    conf_first = _build_conference_first(top_fits[0].journal.name if top_fits else "top journal")
    oa_first = _build_oa_first(top_fits)
    multi = _build_multi_paper(manuscript_title)

    options = [tiered, parallel, conf_first, oa_first, multi]

    backup_journals = [f.journal.name for f in top_fits[1:4]]

    q = manuscript_quality / 100.0
    citation_strategy = (
        "Share a preprint on arXiv or bioRxiv before final submission. "
        "Post in ResearchGate and LinkedIn for early engagement. "
        "Email key colleagues in the field once accepted."
        if q >= 0.6
        else "Build manuscript quality before focusing on citation strategy."
    )

    return PublicationStrategy(
        manuscript_title=manuscript_title,
        options=options,
        recommended_option=tiered,
        backup_journals=backup_journals,
        citation_strategy=citation_strategy,
        career_alignment=(
            "Target Q1/Q2 journals to build your academic profile. "
            "Balance prestige vs acceptance risk based on your current career stage."
        ),
        timeline_summary=(
            f"Tiered strategy: ~30 weeks to acceptance. "
            f"Conference-first: ~40 weeks. "
            f"Open-access fast-track: ~16 weeks."
        ),
    )
