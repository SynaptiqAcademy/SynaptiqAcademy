"""Corpus-level analysis for Research Gap Intelligence.

Compares publications simultaneously to identify consensus, disagreements,
saturation, fragmentation, missing variables and knowledge evolution.
Operates on Paper + PaperAnalysis objects from the Literature Intelligence Engine.
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field

log = logging.getLogger("synaptiq.research_gap.corpus")


@dataclass
class ConsensusDisagreement:
    consensus_areas: list[str] = field(default_factory=list)
    disagreement_areas: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    missing_variables: list[str] = field(default_factory=list)
    missing_methodologies: list[str] = field(default_factory=list)
    underexplored_populations: list[str] = field(default_factory=list)
    missing_geographies: list[str] = field(default_factory=list)
    missing_datasets: list[str] = field(default_factory=list)
    saturation_signals: list[str] = field(default_factory=list)
    fragmentation_signals: list[str] = field(default_factory=list)
    knowledge_evolution: list[str] = field(default_factory=list)
    research_topics_emerging: list[str] = field(default_factory=list)
    research_topics_declining: list[str] = field(default_factory=list)


def analyze_corpus(
    papers: list,
    analyses: list,
    topic: str = "",
) -> ConsensusDisagreement:
    """Full corpus analysis returning consensus, disagreements, and evolution."""
    result = ConsensusDisagreement()

    if not papers and not analyses:
        return result

    # 1. Methodological consensus / disagreement
    _analyze_methodological_diversity(analyses, result)

    # 2. Findings consensus / contradictions
    _analyze_finding_consensus(analyses, result)

    # 3. Missing variables (cited limitations patterns)
    _analyze_missing_variables(analyses, result)

    # 4. Geographic coverage
    _analyze_geographic_coverage(papers, result)

    # 5. Population coverage
    _analyze_population_coverage(analyses, result)

    # 6. Research evolution (temporal trends)
    _analyze_knowledge_evolution(papers, analyses, result)

    # 7. Saturation vs. fragmentation
    _analyze_saturation(papers, analyses, result)

    return result


def _analyze_methodological_diversity(analyses: list, result: ConsensusDisagreement) -> None:
    if not analyses:
        return

    designs = Counter(
        (a.research_design or "").lower() for a in analyses
        if getattr(a, "research_design", "")
    )
    methodologies = Counter(
        (a.methodology or "").lower() for a in analyses
        if getattr(a, "methodology", "")
    )

    # Consensus: one dominant design
    if designs:
        top_design, top_count = designs.most_common(1)[0]
        if top_count / len(analyses) > 0.60:
            result.consensus_areas.append(
                f"Methodological consensus: {top_design} is the dominant research design "
                f"({top_count}/{len(analyses)} studies)"
            )
        elif len(designs) >= 4:
            result.disagreement_areas.append(
                "Methodological fragmentation: no dominant research design has emerged"
            )

    # Missing methodologies
    all_designs = {"quantitative", "qualitative", "mixed-methods", "experimental", "longitudinal"}
    used = {d for d in designs}
    for absent in all_designs - used:
        if any(keyword in absent for keyword in ["longitudinal", "experimental"]):
            result.missing_methodologies.append(absent)

    # Mixed methods underuse
    quant_count = sum(c for d, c in designs.items() if "quantitat" in d)
    qual_count = sum(c for d, c in designs.items() if "qualitat" in d)
    if quant_count > 0 and qual_count > 0 and "mixed" not in " ".join(designs.keys()):
        result.missing_methodologies.append("mixed-methods integration")


def _analyze_finding_consensus(analyses: list, result: ConsensusDisagreement) -> None:
    if not analyses:
        return

    # Collect result summaries
    results_texts = [
        (a.results or "") for a in analyses if getattr(a, "results", "")
    ]
    if not results_texts:
        return

    # Detect positive vs negative findings
    positive_kw = r"\b(significant|positive|effective|improved|higher|increased|supported)\b"
    negative_kw = r"\b(no significant|not significant|ineffective|no effect|negative|declined)\b"

    positive_count = sum(1 for t in results_texts if re.search(positive_kw, t, re.I))
    negative_count = sum(1 for t in results_texts if re.search(negative_kw, t, re.I))

    total = len(results_texts)
    if total >= 3:
        if positive_count >= total * 0.75:
            result.consensus_areas.append(
                f"Strong positive consensus: {positive_count}/{total} studies report significant positive effects"
            )
        elif negative_count >= total * 0.60:
            result.consensus_areas.append(
                f"Consensus of null results: {negative_count}/{total} studies report non-significant findings"
            )
        elif positive_count >= 2 and negative_count >= 2:
            result.contradictions.append(
                f"Contradictory findings: {positive_count} studies report positive effects "
                f"while {negative_count} report null or negative results — "
                "potential moderating variables unexplored"
            )
            result.disagreement_areas.append(
                "Conflicting findings may indicate boundary conditions or moderating variables not yet identified"
            )

    # Identify shared limitations
    limitations = []
    for a in analyses:
        limitations.extend(getattr(a, "limitations", [])[:3])
    lim_counter = Counter(lim.lower()[:80] for lim in limitations if lim)
    for lim, count in lim_counter.most_common(3):
        if count >= max(2, len(analyses) // 3):
            result.consensus_areas.append(
                f"Shared limitation acknowledged across {count} studies: {lim}"
            )


def _analyze_missing_variables(analyses: list, result: ConsensusDisagreement) -> None:
    if not analyses:
        return

    # Extract variable mentions from analyses
    all_variables: list[str] = []
    for a in analyses:
        variables = getattr(a, "variables", {})
        if isinstance(variables, dict):
            for v_list in variables.values():
                if isinstance(v_list, list):
                    all_variables.extend(str(v) for v in v_list)

    variable_counter = Counter(v.lower() for v in all_variables if len(v) > 3)

    # Variables mentioned only once across corpus = missing systematic study
    once_only = [v for v, c in variable_counter.items() if c == 1]
    if once_only:
        result.missing_variables.extend(once_only[:5])

    # Check for common moderating variables that are typically studied together
    common_moderators = ["culture", "size", "age", "gender", "experience", "sector"]
    for mod in common_moderators:
        if mod not in " ".join(all_variables).lower():
            result.missing_variables.append(f"moderating role of {mod}")


def _analyze_geographic_coverage(papers: list, result: ConsensusDisagreement) -> None:
    if not papers:
        return

    countries = [getattr(p, "country", "") for p in papers if getattr(p, "country", "")]
    if not countries:
        return

    country_counter = Counter(countries)
    covered = set(country_counter.keys())

    major_regions = {
        "Africa": ["Nigeria", "South Africa", "Kenya", "Ethiopia", "Egypt"],
        "Southeast Asia": ["Indonesia", "Vietnam", "Thailand", "Philippines", "Malaysia"],
        "South Asia": ["India", "Pakistan", "Bangladesh"],
        "Middle East": ["Saudi Arabia", "UAE", "Turkey", "Iran"],
        "Latin America": ["Brazil", "Mexico", "Argentina", "Colombia"],
    }

    for region, countries_in_region in major_regions.items():
        if not any(c in covered for c in countries_in_region):
            result.missing_geographies.append(region)


def _analyze_population_coverage(analyses: list, result: ConsensusDisagreement) -> None:
    if not analyses:
        return

    samples_text = " ".join(
        (a.sample or "") for a in analyses if getattr(a, "sample", "")
    ).lower()

    underserved_populations = [
        ("elderly (65+)", ["elderly", "older adult", "senior", "aging"]),
        ("adolescents", ["adolescent", "teenager", "youth", "young people"]),
        ("low-income populations", ["low-income", "poverty", "underserved", "marginalised"]),
        ("rural communities", ["rural", "remote area", "non-urban"]),
        ("ethnic minorities", ["minority", "ethnic", "indigenous", "underrepresented"]),
        ("people with disabilities", ["disability", "disabled", "special needs"]),
    ]

    for pop_label, keywords in underserved_populations:
        if not any(kw in samples_text for kw in keywords):
            result.underexplored_populations.append(pop_label)


def _analyze_knowledge_evolution(papers: list, analyses: list, result: ConsensusDisagreement) -> None:
    if not papers:
        return

    years = sorted(set(p.year for p in papers if getattr(p, "year", None)))
    if len(years) < 2:
        return

    mid = years[len(years) // 2]
    early = [p for p in papers if getattr(p, "year", 0) and p.year <= mid]
    late = [p for p in papers if getattr(p, "year", 0) and p.year > mid]

    def get_keywords(paper_list: list) -> Counter:
        kws: list[str] = []
        for p in paper_list:
            kws.extend([k.lower() for k in getattr(p, "keywords", [])])
        return Counter(kws)

    early_kws = get_keywords(early)
    late_kws = get_keywords(late)

    # Topics growing in late period
    for kw, late_count in late_kws.most_common(10):
        early_count = early_kws.get(kw, 0)
        if late_count > early_count * 1.5 and late_count >= 2:
            result.research_topics_emerging.append(kw)

    # Topics declining
    for kw, early_count in early_kws.most_common(10):
        late_count = late_kws.get(kw, 0)
        if early_count > late_count * 2 and early_count >= 2:
            result.research_topics_declining.append(kw)

    if years:
        result.knowledge_evolution.append(
            f"Research in this area spans {min(years)}–{max(years)} "
            f"({max(years)-min(years)} years of literature)"
        )


def _analyze_saturation(papers: list, analyses: list, result: ConsensusDisagreement) -> None:
    if not papers:
        return

    n = len(papers)
    # Saturation heuristic: >100 papers + dominant design + common keywords
    if n > 100:
        result.saturation_signals.append(
            f"Large corpus ({n} papers) suggests the core topic may be approaching saturation"
        )
    elif n < 15:
        result.fragmentation_signals.append(
            f"Small corpus ({n} papers) indicates an emerging or fragmented field"
        )

    # Topic overlap = saturation signal
    all_keywords: list[str] = []
    for p in papers:
        all_keywords.extend([k.lower() for k in getattr(p, "keywords", [])])
    if all_keywords:
        kw_counter = Counter(all_keywords)
        top_kw, top_count = kw_counter.most_common(1)[0]
        if top_count / n > 0.60:
            result.saturation_signals.append(
                f"Keyword '{top_kw}' appears in {top_count}/{n} papers — "
                "suggesting high research density in this direction"
            )
