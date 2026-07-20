"""Rule-based research gap detection — fast, deterministic, no LLM.

Detects gaps by applying keyword signals and corpus statistical patterns.
Always runs before the AI layer so the AI has a baseline to refine.
"""
from __future__ import annotations

import re
import logging
from collections import Counter

from .models import (
    DetectedGap, GapType, GapSeverity, OpportunityScore,
    MethodologyRecommendation, CorpusInsights,
)
from .taxonomy import GAP_SIGNALS, GAP_METADATA, score_to_severity

log = logging.getLogger("synaptiq.research_gap.rule")


def detect_from_text(
    text: str,
    topic: str,
    focus_types: list[GapType] | None = None,
) -> list[DetectedGap]:
    """Detect gaps from raw text using keyword signal matching."""
    if not text:
        return []

    text_lower = text.lower()
    gaps: list[DetectedGap] = []
    active_types = focus_types or list(GapType)

    for gap_type in active_types:
        signals = GAP_SIGNALS.get(gap_type, [])
        matched = [s for s in signals if s.lower() in text_lower]
        if not matched:
            continue

        meta = GAP_METADATA[gap_type]
        novelty = meta["base_novelty"]
        impact = meta["base_impact"]
        funding = meta["base_funding"]

        # Signal strength adjusts confidence and severity
        signal_strength = min(len(matched) / len(signals), 1.0) if signals else 0.5
        confidence = 0.40 + (signal_strength * 0.35)

        gap = DetectedGap(
            gap_type=gap_type,
            title=f"{meta['label']} identified in {topic}",
            description=meta["description"],
            why_gap_exists=_infer_why(gap_type, text_lower),
            supporting_evidence=[f"Keyword signals found: {', '.join(matched[:5])}"],
            confidence_score=round(confidence, 2),
            severity=score_to_severity(novelty * 0.5 + impact * 0.5),
            opportunity_score=OpportunityScore(
                novelty_score=novelty,
                research_impact=impact,
                funding_potential=funding,
                feasibility_score=0.60,
                publication_probability=0.55,
                citation_potential=0.50,
                interdisciplinary_potential=0.45 if gap_type == GapType.INTERDISCIPLINARY else 0.30,
                implementation_difficulty=0.45,
                commercialization_potential=0.50 if gap_type in (GapType.TECHNOLOGICAL, GapType.AI_GAP) else 0.25,
            ),
            methodology_recommendation=MethodologyRecommendation(
                research_design=meta["typical_design"],
                rationale=f"Appropriate for addressing {meta['label'].lower()}",
            ),
            detected_by="rule_engine",
        )
        gaps.append(gap)

    return gaps


def detect_from_corpus(
    papers: list,
    analyses: list,
    topic: str,
) -> list[DetectedGap]:
    """Detect corpus-level gaps from structured Paper/PaperAnalysis objects."""
    if not papers and not analyses:
        return []

    gaps: list[DetectedGap] = []

    # 1. Methodological monoculture
    designs = [a.research_design.lower() for a in analyses if getattr(a, "research_design", "")]
    if designs:
        design_counts = Counter(designs)
        top_design, top_count = design_counts.most_common(1)[0]
        if top_count / len(designs) >= 0.80 and len(designs) >= 3:
            gaps.append(_methodological_monoculture_gap(top_design, top_count, len(designs), topic))

    # 2. Temporal concentration
    years = [p.year for p in papers if getattr(p, "year", None)]
    if years and len(years) >= 4:
        year_span = max(years) - min(years)
        if year_span < 5:
            gaps.append(_temporal_concentration_gap(years, topic))

    # 3. Geographic concentration
    countries = [getattr(p, "country", "") for p in papers if getattr(p, "country", "")]
    if countries:
        cc = Counter(countries)
        top, count = cc.most_common(1)[0]
        if count / len(countries) > 0.75 and len(countries) >= 4:
            gaps.append(_geographic_concentration_gap(top, count, len(countries), topic))

    # 4. Recurring sample-size limitation
    all_limitations = []
    for a in analyses:
        all_limitations.extend(getattr(a, "limitations", []))
    lim_text = " ".join(all_limitations).lower()
    if ("small sample" in lim_text or "limited sample" in lim_text) and len(analyses) >= 3:
        gaps.append(_sample_size_gap(topic))

    # 5. Missing future work directions
    with_future = sum(1 for a in analyses if getattr(a, "future_work", ""))
    if len(analyses) >= 4 and with_future < len(analyses) // 2:
        gaps.append(_missing_roadmap_gap(with_future, len(analyses), topic))

    # 6. Missing quantitative designs when only qualitative (or vice versa)
    methodologies = [a.methodology.lower() for a in analyses if getattr(a, "methodology", "")]
    if methodologies:
        has_quant = any("quantitat" in m for m in methodologies)
        has_qual = any("qualitat" in m for m in methodologies)
        if has_qual and not has_quant:
            gaps.append(_missing_quantitative_gap(topic))
        elif has_quant and not has_qual:
            gaps.append(_missing_qualitative_gap(topic))

    # 7. Missing empirical validation (if only reviews or conceptual papers)
    review_count = sum(1 for a in analyses if "review" in (getattr(a, "research_design", "") or "").lower())
    if review_count == len(analyses) and len(analyses) >= 3:
        gaps.append(_missing_empirical_gap(topic))

    return gaps


def extract_corpus_insights(papers: list, analyses: list) -> CorpusInsights:
    """Build a CorpusInsights object from Paper + PaperAnalysis objects."""
    insights = CorpusInsights(paper_count=len(papers))

    if not papers and not analyses:
        return insights

    # Dominant methodologies
    methodologies = [a.methodology for a in analyses if getattr(a, "methodology", "")]
    insights.dominant_methodologies = list(dict.fromkeys(methodologies))[:5]

    # Year range
    years = [p.year for p in papers if getattr(p, "year", None)]
    if years:
        insights.year_range = f"{min(years)}–{max(years)}"

    # Common limitations
    all_lims: list[str] = []
    for a in analyses:
        all_lims.extend(getattr(a, "limitations", [])[:2])
    lim_counter = Counter(lim.lower()[:60] for lim in all_lims)
    insights.common_limitations = [lim for lim, _ in lim_counter.most_common(5)]

    # Missing methodologies (what's NOT present)
    designs = {(a.research_design or "").lower() for a in analyses}
    all_designs = {"quantitative", "qualitative", "mixed-methods", "longitudinal", "experimental"}
    insights.missing_methodologies = [d for d in all_designs if d not in designs and designs][:3]

    # Knowledge evolution from years
    if years and max(years) - min(years) > 5:
        insights.knowledge_evolution_notes.append(
            f"Field has evolved over {max(years) - min(years)} years "
            f"({min(years)}–{max(years)})"
        )

    # Saturation signals
    if len(papers) > 50:
        insights.saturation_signals.append(
            f"Large corpus ({len(papers)} papers) may indicate field maturity"
        )

    return insights


# ── Gap constructors ───────────────────────────────────────────────────────────

def _methodological_monoculture_gap(design: str, count: int, total: int, topic: str) -> DetectedGap:
    opposite = _opposite_design(design)
    return DetectedGap(
        gap_type=GapType.METHODOLOGICAL,
        title=f"Methodological monoculture: all studies use {design}",
        description=(
            f"{count}/{total} papers use {design} designs. "
            f"The absence of {opposite} studies limits the depth of evidence."
        ),
        why_gap_exists=(
            f"{design.capitalize()} designs dominate because they are easier to publish "
            "in mainstream journals in this field, creating a self-reinforcing citation cycle."
        ),
        supporting_evidence=[f"{count}/{total} papers use {design}"],
        confidence_score=0.85,
        severity=GapSeverity.HIGH,
        opportunity_score=OpportunityScore(
            novelty_score=0.75, research_impact=0.72, funding_potential=0.58,
            feasibility_score=0.65, publication_probability=0.70, citation_potential=0.60,
        ),
        methodology_recommendation=MethodologyRecommendation(
            research_design=opposite,
            rationale=f"Addresses the methodological monoculture by introducing {opposite} evidence",
        ),
        detected_by="rule_engine",
    )


def _temporal_concentration_gap(years: list[int], topic: str) -> DetectedGap:
    return DetectedGap(
        gap_type=GapType.TEMPORAL,
        title="Absence of longitudinal perspective",
        description=(
            f"All {len(years)} papers were published within a {max(years)-min(years)}-year window "
            f"({min(years)}–{max(years)}). Long-term trends and temporal dynamics are unstudied."
        ),
        why_gap_exists=(
            "Short-duration studies dominate because they fit within typical grant cycles "
            "(3-5 years) and produce faster outputs, biasing the literature toward cross-sectional snapshots."
        ),
        supporting_evidence=[f"Year range: {min(years)}–{max(years)} ({max(years)-min(years)} years)"],
        confidence_score=0.80,
        severity=GapSeverity.MEDIUM,
        opportunity_score=OpportunityScore(
            novelty_score=0.68, research_impact=0.70, funding_potential=0.55,
            feasibility_score=0.40, publication_probability=0.65, citation_potential=0.62,
        ),
        methodology_recommendation=MethodologyRecommendation(
            research_design="longitudinal cohort study",
            rationale="Captures temporal dynamics absent from cross-sectional corpus",
        ),
        detected_by="rule_engine",
    )


def _geographic_concentration_gap(top_country: str, count: int, total: int, topic: str) -> DetectedGap:
    pct = int(count / total * 100)
    return DetectedGap(
        gap_type=GapType.REGIONAL,
        title=f"Geographic concentration: {pct}% of studies from {top_country}",
        description=(
            f"{count}/{total} papers are from {top_country}. "
            "Cultural and institutional differences may limit generalisability."
        ),
        why_gap_exists=(
            f"Research output from {top_country} dominates due to established grant infrastructure, "
            "publication networks, and English-language journals centred in that region."
        ),
        supporting_evidence=[f"{count}/{total} papers from {top_country}"],
        confidence_score=0.78,
        severity=GapSeverity.MEDIUM,
        opportunity_score=OpportunityScore(
            novelty_score=0.70, research_impact=0.62, funding_potential=0.58,
            feasibility_score=0.60, publication_probability=0.65, citation_potential=0.55,
        ),
        methodology_recommendation=MethodologyRecommendation(
            research_design="cross-national comparative study",
            rationale="Addresses geographic bias by including underrepresented regions",
        ),
        detected_by="rule_engine",
    )


def _sample_size_gap(topic: str) -> DetectedGap:
    return DetectedGap(
        gap_type=GapType.POPULATION,
        title="Insufficient sample sizes across corpus",
        description=(
            "Multiple studies acknowledge small or limited samples as a key limitation. "
            "Statistical power is insufficient to detect moderate effect sizes."
        ),
        why_gap_exists=(
            "Small samples arise from resource constraints, difficulty accessing target populations, "
            "and acceptance of underpowered studies in conference venues."
        ),
        supporting_evidence=["Recurring limitation: small/limited sample size"],
        confidence_score=0.80,
        severity=GapSeverity.HIGH,
        opportunity_score=OpportunityScore(
            novelty_score=0.58, research_impact=0.72, funding_potential=0.65,
            feasibility_score=0.55, publication_probability=0.70, citation_potential=0.65,
        ),
        methodology_recommendation=MethodologyRecommendation(
            research_design="large-scale multi-site survey or randomised trial",
            rationale="Addresses statistical power limitations identified across the corpus",
        ),
        detected_by="rule_engine",
    )


def _missing_roadmap_gap(with_future: int, total: int, topic: str) -> DetectedGap:
    return DetectedGap(
        gap_type=GapType.FUTURE_RESEARCH,
        title="Underspecified future research agenda",
        description=(
            f"Only {with_future}/{total} papers propose concrete future research directions. "
            "The field lacks a shared theoretical roadmap."
        ),
        why_gap_exists=(
            "Authors often omit specific future directions because reviewers do not reward them, "
            "and the field has not reached the consensus needed for a coherent research agenda."
        ),
        supporting_evidence=[f"Only {with_future}/{total} papers specify future research"],
        confidence_score=0.65,
        severity=GapSeverity.LOW,
        opportunity_score=OpportunityScore(
            novelty_score=0.62, research_impact=0.60, funding_potential=0.50,
            feasibility_score=0.70, publication_probability=0.58, citation_potential=0.52,
        ),
        methodology_recommendation=MethodologyRecommendation(
            research_design="Delphi study or systematic research agenda mapping",
            rationale="Establishes shared future research priorities for the field",
        ),
        detected_by="rule_engine",
    )


def _missing_quantitative_gap(topic: str) -> DetectedGap:
    return DetectedGap(
        gap_type=GapType.METHODOLOGICAL,
        title="Absence of quantitative validation",
        description=(
            "The corpus is dominated by qualitative research. "
            "Quantitative validation of identified patterns is absent."
        ),
        why_gap_exists=(
            "Qualitative studies are faster to execute and more acceptable as exploratory work "
            "in emerging fields, delaying the quantitative validation stage."
        ),
        supporting_evidence=["All identified studies use qualitative methods"],
        confidence_score=0.78,
        severity=GapSeverity.HIGH,
        opportunity_score=OpportunityScore(
            novelty_score=0.72, research_impact=0.75, funding_potential=0.62,
            feasibility_score=0.60, publication_probability=0.75, citation_potential=0.68,
        ),
        methodology_recommendation=MethodologyRecommendation(
            research_design="large-scale survey or experimental study",
            rationale="Provides quantitative evidence to complement qualitative foundations",
        ),
        detected_by="rule_engine",
    )


def _missing_qualitative_gap(topic: str) -> DetectedGap:
    return DetectedGap(
        gap_type=GapType.METHODOLOGICAL,
        title="Absence of qualitative depth",
        description=(
            "The corpus relies entirely on quantitative methods. "
            "Underlying mechanisms, experiences, and contextual factors remain unexplored."
        ),
        why_gap_exists=(
            "Quantitative designs dominate because they align with positivist paradigms "
            "favoured by high-impact journals, marginalising interpretive approaches."
        ),
        supporting_evidence=["All identified studies use quantitative methods"],
        confidence_score=0.75,
        severity=GapSeverity.MEDIUM,
        opportunity_score=OpportunityScore(
            novelty_score=0.68, research_impact=0.65, funding_potential=0.52,
            feasibility_score=0.65, publication_probability=0.65, citation_potential=0.58,
        ),
        methodology_recommendation=MethodologyRecommendation(
            research_design="grounded theory or phenomenological qualitative study",
            rationale="Explores mechanisms and lived experiences invisible to quantitative methods",
        ),
        detected_by="rule_engine",
    )


def _missing_empirical_gap(topic: str) -> DetectedGap:
    return DetectedGap(
        gap_type=GapType.EMPIRICAL,
        title="Lack of primary empirical research",
        description=(
            "The corpus consists primarily of reviews or conceptual papers. "
            "Original empirical studies are absent."
        ),
        why_gap_exists=(
            "Review papers are often published first in emerging fields because "
            "primary empirical work takes longer to execute and report."
        ),
        supporting_evidence=["Corpus dominated by review/conceptual papers"],
        confidence_score=0.80,
        severity=GapSeverity.HIGH,
        opportunity_score=OpportunityScore(
            novelty_score=0.78, research_impact=0.80, funding_potential=0.70,
            feasibility_score=0.58, publication_probability=0.80, citation_potential=0.72,
        ),
        methodology_recommendation=MethodologyRecommendation(
            research_design="primary empirical study (survey, experiment, or field study)",
            rationale="Provides original data where only synthesised evidence currently exists",
        ),
        detected_by="rule_engine",
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _infer_why(gap_type: GapType, text_lower: str) -> str:
    """Generate a contextual WHY explanation based on gap type and text signals."""
    whys = {
        GapType.THEORETICAL: (
            "Theoretical frameworks were not developed because the field is still "
            "descriptive and has not advanced to the explanatory stage."
        ),
        GapType.METHODOLOGICAL: (
            "Methodological limitations persist because existing instruments were adapted "
            "from adjacent fields without rigorous validation for this context."
        ),
        GapType.EMPIRICAL: (
            "Empirical gaps exist because conceptual work preceded data collection, "
            "and access to appropriate datasets remains restricted."
        ),
        GapType.REGIONAL: (
            "Geographic gaps arise from publication bias toward English-language journals "
            "and unequal research infrastructure across regions."
        ),
        GapType.POPULATION: (
            "Population gaps result from convenience sampling and ethical difficulties "
            "in accessing vulnerable or specialised groups."
        ),
        GapType.TEMPORAL: (
            "Temporal gaps exist because grant cycles favour short-duration studies, "
            "and longitudinal data infrastructure is rarely funded."
        ),
        GapType.POLICY: (
            "Policy gaps arise because academic researchers and policymakers operate in "
            "separate knowledge ecosystems with limited cross-pollination."
        ),
        GapType.AI_GAP: (
            "AI applications have not been explored because the field predates the "
            "current generation of AI tools, or researchers lack the technical skills."
        ),
        GapType.INTERDISCIPLINARY: (
            "Interdisciplinary approaches are absent because academic incentive structures "
            "reward depth over breadth, discouraging cross-disciplinary collaboration."
        ),
    }
    return whys.get(gap_type, f"This gap exists because {gap_type.value} aspects are underexplored in the field.")


def _opposite_design(design: str) -> str:
    opposites = {
        "quantitative": "qualitative or mixed-methods",
        "qualitative": "quantitative survey or experiment",
        "cross-sectional": "longitudinal cohort",
        "case study": "large-scale survey",
        "survey": "experimental or quasi-experimental",
        "experimental": "observational or qualitative",
        "review": "primary empirical study",
    }
    for k, v in opposites.items():
        if k in design:
            return v
    return "mixed-methods"
