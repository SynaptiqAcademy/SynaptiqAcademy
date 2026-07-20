"""AI-powered research gap detection — the primary intelligence layer.

Uses the Academic Intelligence Engine for context enrichment and calls the LLM
with a comprehensive structured prompt covering all 18 gap types.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from .models import (
    DetectedGap, GapType, GapSeverity, OpportunityScore,
    MethodologyRecommendation, ResearchQuestion, CorpusInsights,
    GapIntelligenceRequest,
)
from .taxonomy import GAP_METADATA, score_to_severity

log = logging.getLogger("synaptiq.research_gap.ai")

_SYSTEM = """\
You are a world-class research strategist and systematic review expert specialising in
identifying publishable research gaps. You reason like a senior professor conducting a
pre-study literature assessment before designing a research programme.

CORE TASK: Identify specific, fundable, publishable research opportunities — not generic
"more research is needed" statements.

ACCURACY RULES (strictly enforced):
1. Do not invent specific paper titles, author names, journal volumes, or DOIs.
2. Draw only on genuine knowledge from training data. If uncertain, qualify your statements.
3. Name real methodologies, theoretical traditions, geographic regions, and population groups.
4. Explain WHY each gap exists — not just that it exists.
5. Publication potential scores must reflect realistic academic publishing conditions.
6. Distinguish gaps that are underexplored by choice versus those avoided for practical reasons.
7. Every gap must have supporting evidence and at least one concrete research question.

Return ONLY a single valid JSON object — no markdown fences, no preamble.\
"""

_PROMPT = """\
Conduct a comprehensive Research Gap Intelligence analysis for the following topic.
Identify the most compelling and genuinely publishable research opportunities.

═══════════════════════════════════════════════════════════
ANALYSIS BRIEF
═══════════════════════════════════════════════════════════
TOPIC:               {topic}
DISCIPLINE:          {discipline}
METHODOLOGY PREF:    {methodology_preference}
YEAR RANGE:          {year_range}
TARGET JOURNAL:      {target_journal_type}
ADDITIONAL CONTEXT:  {additional_context}

FOCUS GAP TYPES:     {focus_types}

═══════════════════════════════════════════════════════════
AVAILABLE EVIDENCE
═══════════════════════════════════════════════════════════
{evidence_block}

═══════════════════════════════════════════════════════════
CORPUS INTELLIGENCE (from systematic analysis)
═══════════════════════════════════════════════════════════
{corpus_block}

═══════════════════════════════════════════════════════════
REQUIRED OUTPUT FORMAT
═══════════════════════════════════════════════════════════
Return a JSON object matching this exact schema:

{{
  "topic_overview": {{
    "summary": "<2-4 sentences characterising the field and its research landscape>",
    "maturity_level": "nascent|developing|established|mature",
    "publication_density": "sparse|moderate|dense|saturated",
    "key_disciplines_involved": ["<discipline>"],
    "knowledge_basis_note": "<honest note on how well this topic is known>",
    "missing_variables": ["<variable missing from current literature>"],
    "saturation_map": {{"<subtopic>": "saturated|dense|moderate|sparse"}}
  }},
  "research_consensus": ["<specific area of strong agreement>"],
  "research_disagreements": ["<specific area of active debate or contradiction>"],
  "knowledge_evolution": ["<how the field has evolved over time>"],
  "detected_gaps": [
    {{
      "gap_type": "<one of: theoretical|methodological|empirical|practical|technological|regional|population|industry|temporal|policy|educational|healthcare|digital_transformation|sustainability|innovation|ai_gap|interdisciplinary|future_research>",
      "title": "<specific, actionable gap title — not generic>",
      "description": "<2-3 sentences describing the gap and why it matters>",
      "why_gap_exists": "<specific explanation of WHY this gap has not been filled — historical, institutional, technical, or practical reasons>",
      "supporting_evidence": ["<specific piece of evidence — from text or general knowledge>"],
      "supporting_publications": ["<any real authors/research groups known to work in adjacent areas>"],
      "contradicting_evidence": ["<evidence that might challenge this gap claim>"],
      "confidence_score": <0.0-1.0>,
      "severity": "critical|high|medium|low",
      "opportunity_score": {{
        "novelty_score": <0.0-1.0>,
        "feasibility_score": <0.0-1.0>,
        "publication_probability": <0.0-1.0>,
        "funding_potential": <0.0-1.0>,
        "implementation_difficulty": <0.0-1.0>,
        "research_impact": <0.0-1.0>,
        "citation_potential": <0.0-1.0>,
        "interdisciplinary_potential": <0.0-1.0>,
        "commercialization_potential": <0.0-1.0>,
        "novelty_rationale": "<why this specific novelty score>",
        "feasibility_rationale": "<why this feasibility estimate>",
        "publication_rationale": "<realistic publication assessment>",
        "funding_rationale": "<why this funding potential score>",
        "impact_rationale": "<expected research impact reasoning>"
      }},
      "alternative_interpretations": ["<alternative way to interpret this gap>"],
      "potential_risks": ["<practical or scientific risk in pursuing this>"],
      "expected_contribution": "<what knowledge would be created if addressed>",
      "recommended_next_steps": ["<concrete action step>"],
      "competition_level": "low|medium|high|very_high",
      "active_researchers_estimate": "<estimate of active researcher count in this gap area>",
      "leading_venues": ["<journal or conference relevant to this gap>"],
      "research_questions": [
        {{
          "question": "<specific, answerable research question>",
          "rationale": "<why this question is currently unanswered>",
          "novelty_statement": "<precisely what is novel>",
          "suggested_methodology": "<most appropriate method>",
          "expected_contribution": "<what this would add to knowledge>",
          "publication_potential": "high|medium|low",
          "target_journal_type": "<type of journal>",
          "hypotheses": ["<testable hypothesis if applicable>"],
          "research_objectives": ["<specific research objective>"],
          "research_aims": ["<overarching research aim>"],
          "alternative_paths": ["<alternative research direction from same starting point>"]
        }}
      ],
      "methodology_recommendation": {{
        "research_design": "<recommended primary design>",
        "sampling_strategy": "<sampling approach>",
        "data_collection": ["<data collection method>"],
        "analysis_methods": ["<analysis technique>"],
        "statistical_techniques": ["<statistical test or model>"],
        "qualitative_techniques": ["<qualitative approach if applicable>"],
        "mixed_methods_approach": "<integration strategy if mixed>",
        "ai_approaches": ["<AI/ML technique if applicable>"],
        "survey_design": "<survey details if applicable>",
        "case_study_notes": "<case study guidance if applicable>",
        "experimental_design": "<experimental details if applicable>",
        "rationale": "<why this methodology is most appropriate>"
      }}
    }}
  ],
  "competitive_landscape": {{
    "active_researchers": ["<researcher name or group known in this field>"],
    "leading_institutions": ["<institution active in this research area>"],
    "leading_journals": ["<journal where work in this area is typically published>"],
    "leading_conferences": ["<conference relevant to this field>"],
    "emerging_topics": ["<topic gaining traction>"],
    "declining_topics": ["<topic losing research attention>"],
    "publication_density": "sparse|moderate|dense|saturated",
    "research_maturity": "nascent|developing|established|mature",
    "competition_hotspots": ["<subarea with highest researcher competition>"],
    "opportunity_whitespace": ["<undercompeted area with high potential>"],
    "field_growth_rate": "<characterisation of how fast this field is growing>",
    "interdisciplinary_links": ["<adjacent discipline that could contribute>"]
  }},
  "priority_research_questions": [
    {{
      "question": "<top-priority research question>",
      "rationale": "<why this is the most important question to pursue>",
      "novelty_statement": "<what makes this uniquely valuable>",
      "suggested_methodology": "<best approach>",
      "expected_contribution": "<knowledge created>",
      "publication_potential": "high|medium|low",
      "target_journal_type": "<journal type>",
      "hypotheses": ["<testable hypothesis>"],
      "research_objectives": ["<specific objective>"],
      "research_aims": ["<overarching aim>"],
      "alternative_paths": ["<alternative>"]
    }}
  ],
  "research_roadmap": [
    {{
      "phase": <integer starting at 1>,
      "title": "<phase title>",
      "description": "<what to do in this phase>",
      "duration": "<estimated duration>",
      "outputs": ["<expected research output>"],
      "gap_types_addressed": ["<gap type>"],
      "dependencies": ["<prerequisite from previous phase>"]
    }}
  ]
}}

The detected_gaps array must contain between {min_gaps} and {max_gaps} gaps,
ordered from highest to lowest opportunity score.
The priority_research_questions array must contain exactly 5 items.
The research_roadmap must contain 3-5 phases.\
"""


async def detect_gaps_with_ai(
    request: GapIntelligenceRequest,
    content_text: str,
    corpus_insights: Optional[object] = None,
    existing_rule_gaps: Optional[list] = None,
) -> tuple[list[DetectedGap], dict, list, list, list, list, dict, list]:
    """
    Main AI detection pass. Returns:
    (gaps, topic_overview, consensus, disagreements, evolution, missing_variables,
     saturation_map, research_roadmap)
    """
    evidence_block = _build_evidence_block(content_text, request)
    corpus_block = _build_corpus_block(corpus_insights, existing_rule_gaps)
    focus_types = (
        ", ".join(t.value for t in request.focus_gap_types)
        if request.focus_gap_types
        else "all gap types"
    )
    year_range = _format_year_range(request.year_from, request.year_to)

    min_gaps = 5 if request.analysis_depth.value == "quick" else 8
    max_gaps = 10 if request.analysis_depth.value == "quick" else 18

    prompt = _PROMPT.format(
        topic=request.topic or "Not specified",
        discipline=request.discipline or "Not specified",
        methodology_preference=request.methodology_preference or "No preference",
        year_range=year_range,
        target_journal_type=request.target_journal_type or "Not specified",
        additional_context=request.additional_context or "None",
        focus_types=focus_types,
        evidence_block=evidence_block,
        corpus_block=corpus_block,
        min_gaps=min_gaps,
        max_gaps=max_gaps,
    )

    try:
        from services.ai.llm import call_llm
        raw = await call_llm(
            system=_SYSTEM,
            user_msg=prompt,
            feature="research_gap.finder",
            max_tokens=8000,
        )
        data = _parse_json(raw)
        return _extract_results(data)
    except Exception as exc:
        log.error("AI gap detection failed: %s", exc)
        return [], {}, [], [], [], [], {}, []


def _build_evidence_block(text: str, request: GapIntelligenceRequest) -> str:
    if not text:
        return "No documents provided — analysis based on field knowledge only."
    # Truncate to avoid token overflow; 4000 chars ≈ 1000 tokens
    truncated = text[:4000]
    if len(text) > 4000:
        truncated += f"\n\n[... {len(text) - 4000} additional characters truncated ...]"
    return truncated


def _build_corpus_block(corpus_insights, existing_gaps: Optional[list]) -> str:
    parts: list[str] = []

    if corpus_insights is not None:
        ci = corpus_insights
        if getattr(ci, "paper_count", 0) > 0:
            parts.append(f"Papers analysed: {ci.paper_count}")
        if getattr(ci, "year_range", ""):
            parts.append(f"Publication span: {ci.year_range}")
        if getattr(ci, "dominant_methodologies", []):
            parts.append(f"Dominant methodologies: {', '.join(ci.dominant_methodologies[:4])}")
        if getattr(ci, "consensus_areas", []):
            parts.append(f"Rule-based consensus: {'; '.join(ci.consensus_areas[:3])}")
        if getattr(ci, "contradictions", []):
            parts.append(f"Contradictions detected: {'; '.join(ci.contradictions[:2])}")
        if getattr(ci, "missing_methodologies", []):
            parts.append(f"Missing methodologies: {', '.join(ci.missing_methodologies)}")
        if getattr(ci, "missing_geographies", []):
            parts.append(f"Missing geographies: {', '.join(ci.missing_geographies[:4])}")
        if getattr(ci, "common_limitations", []):
            parts.append(f"Common limitations: {'; '.join(ci.common_limitations[:3])}")

    if existing_gaps:
        gap_titles = [g.title for g in existing_gaps[:5] if hasattr(g, "title")]
        if gap_titles:
            parts.append(f"Rule-engine pre-detected: {'; '.join(gap_titles)}")

    return "\n".join(parts) if parts else "No corpus available — rely on field knowledge."


def _format_year_range(year_from, year_to) -> str:
    if year_from and year_to:
        return f"{year_from}–{year_to}"
    if year_from:
        return f"{year_from} onwards"
    if year_to:
        return f"up to {year_to}"
    return "Not specified"


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```", 2)
        inner = parts[1] if len(parts) >= 2 else text
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.split("```")[0].strip()
    return json.loads(text)


def _extract_results(
    data: dict,
) -> tuple[list[DetectedGap], dict, list, list, list, list, dict, list]:
    """Parse raw AI JSON into typed domain objects."""
    topic_overview = data.get("topic_overview", {})
    consensus = data.get("research_consensus", [])
    disagreements = data.get("research_disagreements", [])
    evolution = data.get("knowledge_evolution", [])
    missing_variables = topic_overview.get("missing_variables", [])
    saturation_map = topic_overview.get("saturation_map", {})
    research_roadmap = data.get("research_roadmap", [])

    gaps: list[DetectedGap] = []
    for raw_gap in data.get("detected_gaps", []):
        if not isinstance(raw_gap, dict):
            continue
        gap = _parse_gap(raw_gap)
        if gap:
            gaps.append(gap)

    # Inject priority_research_questions as top-level (gap-agnostic)
    priority_rqs_raw = data.get("priority_research_questions", [])
    priority_rqs = [_parse_research_question(q) for q in priority_rqs_raw if isinstance(q, dict)]

    return (
        gaps, topic_overview, consensus, disagreements, evolution,
        missing_variables, saturation_map, research_roadmap,
    )


def _parse_gap(d: dict) -> Optional[DetectedGap]:
    try:
        gap_type_str = str(d.get("gap_type", "theoretical")).lower().replace(" ", "_")
        try:
            gap_type = GapType(gap_type_str)
        except ValueError:
            gap_type = GapType.FUTURE_RESEARCH

        severity_str = str(d.get("severity", "medium")).lower()
        try:
            severity = GapSeverity(severity_str)
        except ValueError:
            severity = GapSeverity.MEDIUM

        opp_raw = d.get("opportunity_score", {})
        opportunity_score = OpportunityScore(
            novelty_score=_clamp(opp_raw.get("novelty_score", 0.60)),
            feasibility_score=_clamp(opp_raw.get("feasibility_score", 0.55)),
            publication_probability=_clamp(opp_raw.get("publication_probability", 0.60)),
            funding_potential=_clamp(opp_raw.get("funding_potential", 0.50)),
            implementation_difficulty=_clamp(opp_raw.get("implementation_difficulty", 0.45)),
            research_impact=_clamp(opp_raw.get("research_impact", 0.60)),
            citation_potential=_clamp(opp_raw.get("citation_potential", 0.55)),
            interdisciplinary_potential=_clamp(opp_raw.get("interdisciplinary_potential", 0.40)),
            commercialization_potential=_clamp(opp_raw.get("commercialization_potential", 0.30)),
            novelty_rationale=str(opp_raw.get("novelty_rationale", "")),
            feasibility_rationale=str(opp_raw.get("feasibility_rationale", "")),
            publication_rationale=str(opp_raw.get("publication_rationale", "")),
            funding_rationale=str(opp_raw.get("funding_rationale", "")),
            impact_rationale=str(opp_raw.get("impact_rationale", "")),
        )

        meth_raw = d.get("methodology_recommendation", {})
        methodology = MethodologyRecommendation(
            research_design=str(meth_raw.get("research_design", "")),
            sampling_strategy=str(meth_raw.get("sampling_strategy", "")),
            data_collection=_to_str_list(meth_raw.get("data_collection", [])),
            analysis_methods=_to_str_list(meth_raw.get("analysis_methods", [])),
            statistical_techniques=_to_str_list(meth_raw.get("statistical_techniques", [])),
            qualitative_techniques=_to_str_list(meth_raw.get("qualitative_techniques", [])),
            mixed_methods_approach=str(meth_raw.get("mixed_methods_approach", "")),
            ai_approaches=_to_str_list(meth_raw.get("ai_approaches", [])),
            survey_design=str(meth_raw.get("survey_design", "")),
            case_study_notes=str(meth_raw.get("case_study_notes", "")),
            experimental_design=str(meth_raw.get("experimental_design", "")),
            rationale=str(meth_raw.get("rationale", "")),
        )

        research_questions = [
            _parse_research_question(q)
            for q in d.get("research_questions", [])
            if isinstance(q, dict)
        ]

        from .models import CompetitionLevel
        competition_str = str(d.get("competition_level", "medium")).lower()
        try:
            competition = CompetitionLevel(competition_str)
        except ValueError:
            competition = CompetitionLevel.MEDIUM

        return DetectedGap(
            gap_type=gap_type,
            title=str(d.get("title", f"{gap_type.value} gap")),
            description=str(d.get("description", "")),
            why_gap_exists=str(d.get("why_gap_exists", "")),
            supporting_evidence=_to_str_list(d.get("supporting_evidence", [])),
            supporting_publications=_to_str_list(d.get("supporting_publications", [])),
            contradicting_evidence=_to_str_list(d.get("contradicting_evidence", [])),
            confidence_score=_clamp(float(d.get("confidence_score", 0.65))),
            severity=severity,
            opportunity_score=opportunity_score,
            methodology_recommendation=methodology,
            research_questions=research_questions,
            alternative_interpretations=_to_str_list(d.get("alternative_interpretations", [])),
            potential_risks=_to_str_list(d.get("potential_risks", [])),
            expected_contribution=str(d.get("expected_contribution", "")),
            recommended_next_steps=_to_str_list(d.get("recommended_next_steps", [])),
            competition_level=competition,
            active_researchers_estimate=str(d.get("active_researchers_estimate", "")),
            leading_venues=_to_str_list(d.get("leading_venues", [])),
            detected_by="ai",
        )
    except Exception as exc:
        log.warning("Gap parse error: %s — raw=%s", exc, str(d)[:200])
        return None


def _parse_research_question(d: dict) -> ResearchQuestion:
    return ResearchQuestion(
        question=str(d.get("question", "")),
        rationale=str(d.get("rationale", "")),
        novelty_statement=str(d.get("novelty_statement", "")),
        suggested_methodology=str(d.get("suggested_methodology", "")),
        expected_contribution=str(d.get("expected_contribution", "")),
        publication_potential=str(d.get("publication_potential", "medium")),
        target_journal_type=str(d.get("target_journal_type", "")),
        hypotheses=_to_str_list(d.get("hypotheses", [])),
        research_objectives=_to_str_list(d.get("research_objectives", [])),
        research_aims=_to_str_list(d.get("research_aims", [])),
        alternative_paths=_to_str_list(d.get("alternative_paths", [])),
    )


def _clamp(v, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return 0.5


def _to_str_list(v) -> list[str]:
    if not v:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x]
    return [str(v)]
