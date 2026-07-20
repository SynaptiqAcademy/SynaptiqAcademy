"""Research gap detection — identifies unanswered questions and methodological voids."""
from __future__ import annotations

import json
import logging
import re
from collections import Counter

from services.literature.models import Paper, PaperAnalysis, ResearchGap

log = logging.getLogger("synaptiq.literature.gaps")

_SYSTEM = """\
You are a research gap analyst. Given structured analyses of academic papers,
identify specific, publishable research gaps — unanswered questions, missing populations,
methodological voids, conflicting evidence, and future opportunities.

RULES:
1. Each gap must be specific and actionable, not generic.
2. Base gaps on evidence from the corpus, not assumptions.
3. Gaps must include a suggested research design to address them.
4. Return ONLY valid JSON — no markdown fences, no preamble.
"""

_PROMPT = """\
Given {n} papers on "{topic}", identify the most important research gaps.

CORPUS SUMMARY:
- Methodologies used: {methodologies}
- Domains covered: {domains}
- Sample types: {samples}
- Year range: {year_range}
- Common limitations: {limitations}

DETAILED ANALYSES (top {detail_count}):
{details}

Return JSON with this schema:
{{
  "gaps": [
    {{
      "type": "methodological|population|geographic|temporal|theoretical|data",
      "title": "<concise gap title>",
      "description": "<2-3 sentences describing the gap and its significance>",
      "evidence": ["<evidence point from corpus>"],
      "severity": "high|medium|low",
      "opportunity_score": <0.0-1.0>,
      "suggested_design": "<recommended research design to address this gap>"
    }}
  ]
}}
"""


async def detect_gaps(
    papers: list[Paper],
    analyses: list[PaperAnalysis],
    topic: str = "",
) -> list[ResearchGap]:
    """Detect research gaps from corpus analyses."""
    # Always run rule-based pass
    rule_gaps = _rule_based_gaps(papers, analyses)

    # AI pass for richer gaps (if analyses have content)
    ai_gaps: list[ResearchGap] = []
    if analyses and any(a.results for a in analyses):
        ai_gaps = await _ai_gap_detection(papers, analyses, topic)

    # Merge: AI gaps take priority; rule gaps fill in
    all_gaps = ai_gaps[:]
    existing_titles = {g.title.lower()[:30] for g in all_gaps}
    for rg in rule_gaps:
        if rg.title.lower()[:30] not in existing_titles:
            all_gaps.append(rg)
            existing_titles.add(rg.title.lower()[:30])

    return sorted(all_gaps, key=lambda g: -g.opportunity_score)[:12]


# ── Rule-based gap detection ───────────────────────────────────────────────────

def _rule_based_gaps(papers: list[Paper], analyses: list[PaperAnalysis]) -> list[ResearchGap]:
    gaps: list[ResearchGap] = []

    if not analyses:
        return gaps

    # 1. Methodological gap: only one type of design used
    designs = [a.research_design.lower() for a in analyses if a.research_design]
    if designs:
        design_counts = Counter(designs)
        if len(design_counts) == 1:
            only_design = list(design_counts.keys())[0]
            gaps.append(_make_gap(
                gap_type="methodological",
                title=f"Lack of {_opposite_design(only_design)} studies",
                description=(
                    f"All corpus papers use {only_design} designs. "
                    "Alternative designs could provide different insights."
                ),
                evidence=[f"{design_counts[only_design]} papers all use {only_design}"],
                severity="high",
                score=0.80,
                design=_opposite_design(only_design),
            ))

    # 2. Temporal gap: studies all from same decade
    years = [p.year for p in papers if p.year]
    if years:
        year_range = max(years) - min(years)
        if year_range < 5 and len(papers) >= 5:
            gaps.append(_make_gap(
                gap_type="temporal",
                title="Limited longitudinal perspective",
                description=(
                    f"All {len(papers)} papers were published within a {year_range}-year window "
                    f"({min(years)}–{max(years)}). Long-term trends are unstudied."
                ),
                evidence=[f"Papers span only {year_range} years"],
                severity="medium",
                score=0.65,
                design="longitudinal cohort study",
            ))

    # 3. Sample gap: all studies from same domain/country
    countries = [p.country for p in papers if p.country]
    if countries:
        country_counts = Counter(countries)
        top_country, count = country_counts.most_common(1)[0]
        if count / len(countries) > 0.80:
            gaps.append(_make_gap(
                gap_type="geographic",
                title=f"Underrepresentation of non-{top_country} contexts",
                description=(
                    f"{count/len(countries):.0%} of papers are from {top_country}. "
                    "Results may not generalise to other cultural or national contexts."
                ),
                evidence=[f"{count}/{len(countries)} papers from {top_country}"],
                severity="medium",
                score=0.70,
                design="cross-national comparative study",
            ))

    # 4. Missing limitations — common limitation = known gap
    all_limitations: list[str] = []
    for a in analyses:
        all_limitations.extend(a.limitations)
    lim_text = " ".join(all_limitations).lower()

    if "small sample" in lim_text or "limited sample" in lim_text:
        gaps.append(_make_gap(
            gap_type="population",
            title="Insufficient sample sizes across corpus",
            description=(
                "Multiple papers acknowledge small or limited samples as a limitation. "
                "Larger-scale studies are needed to confirm findings."
            ),
            evidence=["Recurring limitation: small sample size"],
            severity="high",
            score=0.75,
            design="large-scale randomised or cohort study",
        ))

    # 5. No future_work in most papers
    papers_with_future = sum(1 for a in analyses if a.future_work)
    if papers_with_future < len(analyses) // 2 and len(analyses) >= 4:
        gaps.append(_make_gap(
            gap_type="theoretical",
            title="Underspecified future research agenda",
            description=(
                "Most papers in the corpus do not propose specific future research directions, "
                "indicating a field that may lack theoretical roadmap."
            ),
            evidence=[f"Only {papers_with_future}/{len(analyses)} papers propose future work"],
            severity="low",
            score=0.45,
            design="Delphi study or consensus review",
        ))

    return gaps


def _make_gap(
    gap_type: str,
    title: str,
    description: str,
    evidence: list[str],
    severity: str,
    score: float,
    design: str,
) -> ResearchGap:
    from services.literature.models import ResearchGap
    return ResearchGap(
        type=gap_type,
        title=title,
        description=description,
        evidence=evidence,
        severity=severity,
        opportunity_score=score,
        suggested_design=design,
    )


def _opposite_design(design: str) -> str:
    opposites = {
        "quantitative": "qualitative",
        "qualitative": "quantitative",
        "cross-sectional": "longitudinal cohort",
        "case study": "systematic review",
        "survey": "randomised controlled trial",
        "experimental": "observational",
    }
    for k, v in opposites.items():
        if k in design.lower():
            return v
    return "mixed-methods"


# ── AI gap detection ──────────────────────────────────────────────────────────

async def _ai_gap_detection(
    papers: list[Paper],
    analyses: list[PaperAnalysis],
    topic: str,
) -> list[ResearchGap]:
    # Build compact corpus summary
    methodologies = list(set(a.methodology for a in analyses if a.methodology))[:5]
    domains = list(set(a.domain for a in analyses if a.domain))[:4]
    samples = [a.sample[:80] for a in analyses if a.sample][:5]
    years = [p.year for p in papers if p.year]
    year_range = f"{min(years)}–{max(years)}" if years else "unknown"

    all_limitations: list[str] = []
    for a in analyses:
        all_limitations.extend(a.limitations[:2])
    limitations_str = "; ".join(all_limitations[:8]) or "not specified"

    # Detailed analyses block (top 10)
    details_list = []
    for a in analyses[:10]:
        p = next((p for p in papers if p.paper_id == a.paper_id), None)
        title = (p.title if p else "") or "Unknown"
        details_list.append(
            f"- {title}: design={a.research_design or '?'}, "
            f"sample={a.sample[:60] or '?'}, limitations=[{'; '.join(a.limitations[:2])}]"
        )

    try:
        from services.ai.llm import call_llm
        raw = await call_llm(
            system=_SYSTEM,
            user_msg=_PROMPT.format(
                n=len(papers),
                topic=topic or "the research topic",
                methodologies=", ".join(methodologies) or "mixed",
                domains=", ".join(domains) or "mixed",
                samples="; ".join(samples) or "not specified",
                year_range=year_range,
                limitations=limitations_str,
                detail_count=len(details_list),
                details="\n".join(details_list),
            ),
            feature="literature_review.gap_detection",
            max_tokens=2000,
        )
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.split("```")[0].strip()
        data = json.loads(text)
        return [_parse_ai_gap(g) for g in data.get("gaps", []) if isinstance(g, dict)]
    except Exception as exc:
        log.warning("AI gap detection failed: %s", exc)
        return []


def _parse_ai_gap(d: dict) -> ResearchGap:
    return ResearchGap(
        type=d.get("type", "theoretical"),
        title=str(d.get("title", "Unspecified gap")),
        description=str(d.get("description", "")),
        evidence=[str(e) for e in d.get("evidence", []) if e],
        severity=d.get("severity", "medium"),
        opportunity_score=float(d.get("opportunity_score", 0.5)),
        suggested_design=str(d.get("suggested_design", "")),
    )
