"""Research Gap Intelligence Engine — main orchestrator for Phase VIII.

Pipeline:
  1. Resolve inputs (text + optional lit session)
  2. Rule-based detection (always; fast)
  3. Corpus analysis (if papers available)
  4. AI detection (primary intelligence layer)
  5. Merge & de-duplicate gaps
  6. Score all gaps (10-dimension opportunity scoring)
  7. Enrich gaps with research questions
  8. Build competitive landscape
  9. Build visualizations
  10. Persist and return
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from db import get_db

from .models import (
    GapAnalysisResult, GapIntelligenceRequest, DetectedGap,
    AnalysisDepth, ExportFormat, GapType, CompetitiveLandscape,
    ResearchQuestion,
)
from .source_resolver import resolve_inputs
from .rule_detector import detect_from_text, detect_from_corpus, extract_corpus_insights
from .corpus_analyzer import analyze_corpus
from .ai_detector import detect_gaps_with_ai
from .opportunity_scorer import score_all, compute_field_metrics
from .competitive_landscape import build_landscape_from_corpus, build_landscape_from_ai
from .question_generator import enrich_gap_with_questions
from .viz_builder import build_all_visualizations
from .export_engine import export_result
from .telemetry import GapIntelligenceTelemetry, get_gap_telemetry
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.research_gap.engine")


class GapIntelligenceEngine:
    """Orchestrates all phases of Research Gap Intelligence analysis."""

    def __init__(self, telemetry: GapIntelligenceTelemetry) -> None:
        self._telemetry = telemetry

    async def analyze(self, request: GapIntelligenceRequest) -> GapAnalysisResult:
        """Run the complete gap intelligence pipeline."""
        started = time.monotonic()
        db = get_db()

        db = DBProxy(db, SecurityContext.system())

        # ── 1. Resolve inputs ──────────────────────────────────────────────────
        resolved = await resolve_inputs(request, db)

        # ── 2. Rule-based detection ────────────────────────────────────────────
        rule_gaps: list[DetectedGap] = []
        rule_gaps.extend(detect_from_text(
            resolved.text, request.topic, request.focus_gap_types or None
        ))
        if resolved.papers:
            rule_gaps.extend(detect_from_corpus(
                resolved.papers, resolved.analyses, request.topic
            ))

        # ── 3. Corpus analysis ─────────────────────────────────────────────────
        corpus_insights = None
        corpus_cd = None
        if resolved.papers or resolved.analyses:
            corpus_insights = extract_corpus_insights(resolved.papers, resolved.analyses)
            corpus_cd = analyze_corpus(resolved.papers, resolved.analyses, request.topic)

        # ── 4. AI detection ────────────────────────────────────────────────────
        (
            ai_gaps, topic_overview,
            consensus, disagreements, evolution,
            missing_variables, saturation_map, roadmap_raw,
        ) = await detect_gaps_with_ai(
            request,
            resolved.text,
            corpus_insights,
            rule_gaps,
        )

        # ── 5. Merge gaps (AI primary, rules fill remaining types) ─────────────
        merged = _merge_gaps(ai_gaps, rule_gaps)

        # ── 6. Score ───────────────────────────────────────────────────────────
        scored = score_all(merged)

        # ── 7. Enrich with research questions ──────────────────────────────────
        enriched = [enrich_gap_with_questions(g, request.topic) for g in scored]

        # ── 8. Competitive landscape ───────────────────────────────────────────
        ai_landscape = topic_overview.get("competitive_landscape", {}) if isinstance(topic_overview, dict) else {}
        landscape = build_landscape_from_corpus(
            resolved.papers, resolved.analyses, request.topic, ai_landscape
        )

        # ── 9. Priority research questions (cross-gap, top-5) ──────────────────
        priority_rqs = _collect_priority_rqs(enriched, n=5)

        # ── 10. Add corpus insights to consensus/disagreements ─────────────────
        if corpus_cd:
            consensus = (corpus_cd.consensus_areas + consensus)[:8]
            disagreements = (corpus_cd.disagreement_areas + disagreements)[:8]
            evolution = (corpus_cd.knowledge_evolution + evolution)[:6]
            missing_variables = (missing_variables + corpus_cd.missing_variables)[:10]
            landscape.emerging_topics = list(dict.fromkeys(
                corpus_cd.research_topics_emerging + landscape.emerging_topics
            ))[:8]
            landscape.declining_topics = list(dict.fromkeys(
                corpus_cd.research_topics_declining + landscape.declining_topics
            ))[:5]

        # ── 11. Visualizations ─────────────────────────────────────────────────
        vizs = build_all_visualizations(
            enriched, landscape, resolved.papers, saturation_map
        )

        # ── 12. Field-level metrics ────────────────────────────────────────────
        novelty_idx, opp_score = compute_field_metrics(enriched)

        # ── 13. Clean up topic_overview ────────────────────────────────────────
        if isinstance(topic_overview, dict):
            topic_overview.pop("competitive_landscape", None)

        result = GapAnalysisResult(
            user_id=request.user_id,
            topic=request.topic,
            analysis_depth=request.analysis_depth,
            input_sources=[s.value for s in request.input_sources],
            corpus_size=resolved.corpus_size,
            lit_session_id=request.lit_session_id,
            detected_gaps=enriched,
            total_gaps=len(enriched),
            topic_overview=topic_overview,
            research_consensus=consensus,
            research_disagreements=disagreements,
            knowledge_evolution=evolution,
            saturation_map=saturation_map,
            missing_variables=missing_variables,
            field_novelty_index=novelty_idx,
            field_opportunity_score=opp_score,
            competitive_landscape=landscape,
            priority_research_questions=priority_rqs,
            research_roadmap=_normalise_roadmap(roadmap_raw),
            visualizations=vizs,
            analysis_duration_ms=int((time.monotonic() - started) * 1000),
        )

        # ── 14. Persist ────────────────────────────────────────────────────────
        await self._persist(result, db)

        # ── 15. Telemetry ──────────────────────────────────────────────────────
        self._telemetry.record_analysis(
            depth=request.analysis_depth.value,
            gap_count=len(enriched),
            avg_opp_score=opp_score,
            latency_ms=result.analysis_duration_ms,
            sources=[s.value for s in request.input_sources],
        )
        self._telemetry.record_gap_types([g.gap_type.value for g in enriched])

        return result

    async def get_result(
        self, result_id: str, user_id: str
    ) -> Optional[GapAnalysisResult]:
        """Fetch a stored analysis result by ID."""
        db = get_db()
        db = DBProxy(db, SecurityContext.system())

        doc = await db.gap_intelligence_results.find_one({"result_id": result_id})
        if not doc:
            return None
        if doc.get("user_id") != user_id:
            return None
        return _doc_to_result(doc)

    async def list_results(self, user_id: str, limit: int = 50) -> list[dict]:
        """List user's analyses (summary only — no heavy fields)."""
        db = get_db()
        db = DBProxy(db, SecurityContext.system())

        docs = await db.gap_intelligence_results.find(
            {"user_id": user_id},
            {
                "result_id": 1, "topic": 1, "analysis_depth": 1,
                "total_gaps": 1, "field_opportunity_score": 1,
                "field_novelty_index": 1, "corpus_size": 1,
                "credits_used": 1, "created_at": 1,
            },
        ).sort("created_at", -1).to_list(limit)
        return [
            {
                "result_id": d.get("result_id", str(d.get("_id", ""))),
                "topic": d.get("topic", ""),
                "analysis_depth": d.get("analysis_depth", "standard"),
                "total_gaps": d.get("total_gaps", 0),
                "field_opportunity_score": d.get("field_opportunity_score", 0.0),
                "field_novelty_index": d.get("field_novelty_index", 0.0),
                "corpus_size": d.get("corpus_size", 0),
                "credits_used": d.get("credits_used", 0),
                "created_at": d.get("created_at", ""),
            }
            for d in docs
        ]

    async def export(self, result_id: str, user_id: str, fmt: ExportFormat) -> tuple[str, str, str]:
        """Export a result in the given format. Returns (content, filename, content_type)."""
        result = await self.get_result(result_id, user_id)
        if not result:
            return "", "", ""
        content, filename, ct = export_result(result, fmt)
        self._telemetry.record_export(fmt.value)
        return content, filename, ct

    async def admin_list_results(self, limit: int = 50) -> list[dict]:
        """Admin: list all analyses across users."""
        db = get_db()
        db = DBProxy(db, SecurityContext.system())

        docs = await db.gap_intelligence_results.find(
            {}, {"result_id": 1, "user_id": 1, "topic": 1, "total_gaps": 1,
                 "analysis_depth": 1, "created_at": 1}
        ).sort("created_at", -1).to_list(limit)
        return [
            {
                "result_id": d.get("result_id", ""),
                "user_id": d.get("user_id", ""),
                "topic": d.get("topic", ""),
                "total_gaps": d.get("total_gaps", 0),
                "analysis_depth": d.get("analysis_depth", ""),
                "created_at": d.get("created_at", ""),
            }
            for d in docs
        ]

    def get_telemetry_stats(self) -> dict:
        return self._telemetry.get_stats()

    async def _persist(self, result: GapAnalysisResult, db) -> None:
        try:
            doc = result.to_dict()
            await db.gap_intelligence_results.update_one(
                {"result_id": result.result_id},
                {"$set": doc},
                upsert=True,
            )
        except Exception as exc:
            log.error("Failed to persist gap analysis result: %s", exc)


# ── Gap merging ────────────────────────────────────────────────────────────────

def _merge_gaps(
    ai_gaps: list[DetectedGap],
    rule_gaps: list[DetectedGap],
) -> list[DetectedGap]:
    """AI gaps take priority; rule gaps fill in gap types not covered by AI."""
    merged = list(ai_gaps)
    ai_types = {g.gap_type for g in ai_gaps}

    for rg in rule_gaps:
        if rg.gap_type not in ai_types:
            # Rule gap for a type AI missed
            merged.append(rg)
            ai_types.add(rg.gap_type)
        else:
            # Upgrade AI gap with rule-based evidence if it exists
            for ag in merged:
                if ag.gap_type == rg.gap_type:
                    ag.supporting_evidence = list(dict.fromkeys(
                        ag.supporting_evidence + rg.supporting_evidence
                    ))
                    ag.detected_by = "hybrid"
                    break

    return merged


# ── Priority RQs ──────────────────────────────────────────────────────────────

def _collect_priority_rqs(gaps: list[DetectedGap], n: int = 5) -> list[ResearchQuestion]:
    """Collect the top n research questions across all gaps, by publication_potential."""
    all_rqs: list[tuple[float, ResearchQuestion]] = []
    potential_map = {"high": 1.0, "medium": 0.65, "low": 0.30}

    for g in gaps:
        for rq in g.research_questions:
            score = potential_map.get(rq.publication_potential, 0.5)
            # Weight by gap opportunity score
            weighted = score * g.opportunity_score.overall_score
            all_rqs.append((weighted, rq))

    all_rqs.sort(key=lambda x: -x[0])
    seen = set()
    top: list[ResearchQuestion] = []
    for _, rq in all_rqs:
        key = rq.question[:60].lower()
        if key not in seen:
            seen.add(key)
            top.append(rq)
        if len(top) >= n:
            break
    return top


def _normalise_roadmap(raw: list) -> list[dict]:
    if not raw:
        return []
    result = []
    for phase in raw:
        if not isinstance(phase, dict):
            continue
        result.append({
            "phase": int(phase.get("phase", len(result) + 1)),
            "title": str(phase.get("title", "")),
            "description": str(phase.get("description", "")),
            "duration": str(phase.get("duration", "")),
            "outputs": [str(o) for o in phase.get("outputs", [])],
            "gap_types_addressed": [str(g) for g in phase.get("gap_types_addressed", [])],
            "dependencies": [str(d) for d in phase.get("dependencies", [])],
        })
    return result[:5]


def _doc_to_result(doc: dict) -> GapAnalysisResult:
    """Deserialise a MongoDB document into a GapAnalysisResult."""
    result = GapAnalysisResult(
        result_id=doc.get("result_id", ""),
        user_id=doc.get("user_id", ""),
        topic=doc.get("topic", ""),
        input_sources=doc.get("input_sources", []),
        corpus_size=doc.get("corpus_size", 0),
        lit_session_id=doc.get("lit_session_id", ""),
        total_gaps=doc.get("total_gaps", 0),
        topic_overview=doc.get("topic_overview", {}),
        research_consensus=doc.get("research_consensus", []),
        research_disagreements=doc.get("research_disagreements", []),
        knowledge_evolution=doc.get("knowledge_evolution", []),
        saturation_map=doc.get("saturation_map", {}),
        missing_variables=doc.get("missing_variables", []),
        field_novelty_index=doc.get("field_novelty_index", 0.0),
        field_opportunity_score=doc.get("field_opportunity_score", 0.0),
        research_roadmap=doc.get("research_roadmap", []),
        visualizations=doc.get("visualizations", {}),
        analysis_duration_ms=doc.get("analysis_duration_ms", 0),
        credits_used=doc.get("credits_used", 0),
        created_at=doc.get("created_at", ""),
    )
    try:
        result.analysis_depth = AnalysisDepth(doc.get("analysis_depth", "standard"))
    except ValueError:
        result.analysis_depth = AnalysisDepth.STANDARD

    # Gaps are stored as dicts; convert back
    result.detected_gaps = []  # Full gaps are in the dict; heavy deserialization optional
    result.competitive_landscape = _doc_to_landscape(doc.get("competitive_landscape", {}))
    result.priority_research_questions = [
        _doc_to_rq(q) for q in doc.get("priority_research_questions", [])
        if isinstance(q, dict)
    ]
    return result


def _doc_to_landscape(d: dict) -> CompetitiveLandscape:
    from .models import PublicationDensity, ResearchMaturity
    cl = CompetitiveLandscape(
        active_researchers=d.get("active_researchers", []),
        leading_institutions=d.get("leading_institutions", []),
        leading_journals=d.get("leading_journals", []),
        leading_conferences=d.get("leading_conferences", []),
        emerging_topics=d.get("emerging_topics", []),
        declining_topics=d.get("declining_topics", []),
        competition_hotspots=d.get("competition_hotspots", []),
        opportunity_whitespace=d.get("opportunity_whitespace", []),
        field_growth_rate=d.get("field_growth_rate", ""),
        interdisciplinary_links=d.get("interdisciplinary_links", []),
    )
    try:
        cl.publication_density = PublicationDensity(d.get("publication_density", "moderate"))
    except ValueError:
        pass
    try:
        cl.research_maturity = ResearchMaturity(d.get("research_maturity", "developing"))
    except ValueError:
        pass
    return cl


def _doc_to_rq(d: dict) -> ResearchQuestion:
    return ResearchQuestion(
        question=d.get("question", ""),
        rationale=d.get("rationale", ""),
        novelty_statement=d.get("novelty_statement", ""),
        suggested_methodology=d.get("suggested_methodology", ""),
        expected_contribution=d.get("expected_contribution", ""),
        publication_potential=d.get("publication_potential", "medium"),
        target_journal_type=d.get("target_journal_type", ""),
        hypotheses=d.get("hypotheses", []),
        research_objectives=d.get("research_objectives", []),
        research_aims=d.get("research_aims", []),
        alternative_paths=d.get("alternative_paths", []),
    )


# ── Singleton ──────────────────────────────────────────────────────────────────

_engine_instance: Optional[GapIntelligenceEngine] = None


async def get_gap_engine() -> GapIntelligenceEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = GapIntelligenceEngine(telemetry=get_gap_telemetry())
    return _engine_instance


def reset_gap_engine() -> None:
    global _engine_instance
    _engine_instance = None
