"""Manuscript Intelligence Engine — Phase IX orchestrator.

Pipeline (15 steps):
  1.  Parse document → full text + structural metadata
  2.  Detect sections → 35 section types
  3.  Rule: scientific quality review
  4.  Rule: writing quality review
  5.  Rule: literature coverage review
  6.  Rule: methodology review
  7.  Rule: statistical quality review
  8.  Merge rule issues into severity buckets
  9.  AI comprehensive review (uses rule results as context)
  10. Merge AI + rule dimensions (AI primary, rules fill gaps)
  11. Infer discipline → journal matching
  12. Compute publication readiness scores
  13. Build revision roadmap
  14. Build visualizations
  15. Persist to MongoDB + update telemetry
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from db import get_db

from .models import (
    ManuscriptIntelligenceResult, ManuscriptReviewRequest, ExportFormat,
    ReviewDepth, Recommendation, PublicationReadiness, JournalMatch,
    ReviewDimensions, QualityDimension, SectionScore, ReviewIssue,
    IssueSeverity, WritingMetrics, LiteratureMetrics, StatisticalMetrics,
    _score_to_grade,
)
from .doc_parser import parse_document
from .section_detector import detect_sections
from .scientific_reviewer import review_scientific_quality
from .writing_reviewer import review_writing_quality
from .literature_reviewer import review_literature
from .method_reviewer import review_methodology
from .statistical_reviewer import review_statistical_quality
from .ai_reviewer import review_with_ai
from .journal_matcher import infer_discipline, recommend_journals
from .revision_planner import build_revision_roadmap
from .viz_builder import build_all_visualizations
from .export_engine import export_result
from .telemetry import ManuscriptTelemetry, get_manuscript_telemetry
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.manuscript.engine")


class ManuscriptIntelligenceEngine:
    """Orchestrates all 15 pipeline steps for manuscript intelligence review."""

    def __init__(self, telemetry: ManuscriptTelemetry) -> None:
        self._telemetry = telemetry

    async def review(
        self,
        request: ManuscriptReviewRequest,
    ) -> ManuscriptIntelligenceResult:
        started = time.monotonic()
        db = get_db()

        db = DBProxy(db, SecurityContext.system())

        # ── 1. Parse document ─────────────────────────────────────────────────
        from .doc_parser import InputFormat as IF
        parsed = parse_document(
            data=request.content,
            fmt=request.input_format,
        )

        text = parsed.full_text
        if not text.strip():
            text = request.content if isinstance(request.content, str) else ""

        # ── 2. Detect sections ────────────────────────────────────────────────
        sections = detect_sections(parsed)
        detected_types = [s.section_type.value for s in sections]

        # ── 3. Scientific quality ─────────────────────────────────────────────
        sci_dim, sci_issues = review_scientific_quality(text, sections)

        # ── 4. Writing quality ────────────────────────────────────────────────
        writing_metrics, write_dim, write_issues = review_writing_quality(text)

        # ── 5. Literature coverage ────────────────────────────────────────────
        lit_metrics, lit_dim, lit_issues = review_literature(text, parsed.reference_count)

        # ── 6. Methodology ────────────────────────────────────────────────────
        if request.review_depth != ReviewDepth.QUICK:
            method_dim, method_issues = review_methodology(text)
        else:
            method_dim = QualityDimension("Methodological Soundness", score=65.0, weight=1.5, grade="B-",
                                          rationale="Quick review — detailed methodology check skipped.")
            method_issues = []

        # ── 7. Statistical quality ────────────────────────────────────────────
        if request.review_depth != ReviewDepth.QUICK:
            stat_metrics, stat_dim, stat_issues = review_statistical_quality(text)
        else:
            stat_metrics = StatisticalMetrics()
            stat_dim = QualityDimension("Statistical Validity", score=65.0, weight=1.0, grade="B-",
                                        rationale="Quick review — statistical check skipped.")
            stat_issues = []

        # ── 8. Merge rule issues ──────────────────────────────────────────────
        all_rule_issues: list[ReviewIssue] = (
            sci_issues + write_issues + lit_issues + method_issues + stat_issues
        )

        # ── 9. AI review ──────────────────────────────────────────────────────
        rule_dims = ReviewDimensions(
            scientific_rigor=sci_dim,
            methodological_soundness=method_dim,
            clarity=write_dim,
            literature_coverage=lit_dim,
            statistical_validity=stat_dim,
        )
        ai_result = await review_with_ai(text, all_rule_issues, rule_dims)

        # ── 10. Merge dimensions (AI primary, rules fill) ─────────────────────
        dims = _merge_dimensions(rule_dims, ai_result.get("review_dimensions_ai", {}))

        overall_score = ai_result.get("overall_score") or dims.weighted_score()
        overall_score = max(0.0, min(100.0, overall_score))

        # Merge issues
        ai_extra_issues: list[ReviewIssue] = ai_result.get("additional_issues", [])
        all_issues = all_rule_issues + ai_extra_issues
        critical = [i for i in all_issues if i.severity == IssueSeverity.CRITICAL]
        major = [i for i in all_issues if i.severity == IssueSeverity.MAJOR]
        minor = [i for i in all_issues if i.severity == IssueSeverity.MINOR]
        suggestions = [i for i in all_issues if i.severity == IssueSeverity.SUGGESTION]

        # ── 11. Discipline + Journal matching ─────────────────────────────────
        discipline = infer_discipline(text.lower(), ai_result.get("inferred_discipline", ""))
        ai_journals = ai_result.get("journal_matches", [])
        if request.review_depth == ReviewDepth.DEEP:
            journal_matches = recommend_journals(text, discipline, overall_score, ai_journals)
        else:
            journal_matches = recommend_journals(text, discipline, overall_score, ai_journals[:3])

        # ── 12. Publication readiness ─────────────────────────────────────────
        pub_readiness_dict = ai_result.get("publication_readiness", {})
        pub_readiness = _build_publication_readiness(
            overall_score, len(critical), len(major), pub_readiness_dict
        )

        # Recommendation
        rec_str = ai_result.get("recommendation", "")
        recommendation = _map_recommendation(rec_str, overall_score, len(critical), len(major))

        # ── 13. Revision roadmap ──────────────────────────────────────────────
        roadmap = build_revision_roadmap(critical, major, minor, suggestions, overall_score)

        # ── 14. Section scores ────────────────────────────────────────────────
        section_scores = _build_section_scores(sections, dims)

        # ── 15a. Visualizations ───────────────────────────────────────────────
        vizs = build_all_visualizations(
            dims=dims,
            section_scores=section_scores,
            pr=pub_readiness,
            critical=critical,
            major=major,
            minor=minor,
            suggestions=suggestions,
            roadmap=roadmap,
            detected_types=detected_types,
            writing_metrics=writing_metrics,
            journal_matches=journal_matches,
        )

        result = ManuscriptIntelligenceResult(
            user_id=request.user_id,
            filename=request.filename,
            manuscript_id=request.manuscript_id,
            review_depth=request.review_depth,
            title=parsed.title or "",
            abstract=parsed.abstract or "",
            keywords=parsed.keywords,
            detected_sections=detected_types,
            section_scores=section_scores,
            word_count=parsed.word_count,
            page_count=parsed.page_count,
            figure_count=parsed.figure_count,
            table_count=parsed.table_count,
            reference_count=parsed.reference_count,
            review_dimensions=dims,
            overall_score=round(overall_score, 1),
            recommendation=recommendation,
            executive_summary=ai_result.get("executive_summary", ""),
            critical_issues=critical,
            major_issues=major,
            minor_issues=minor,
            suggestions=suggestions,
            writing_metrics=writing_metrics,
            literature_metrics=lit_metrics,
            statistical_metrics=stat_metrics,
            publication_readiness=pub_readiness,
            journal_matches=journal_matches,
            inferred_discipline=discipline,
            revision_roadmap=roadmap,
            peer_review_text=ai_result.get("peer_review_report", ""),
            editorial_assessment=ai_result.get("editorial_assessment", ""),
            visualizations=vizs,
            analysis_duration_ms=int((time.monotonic() - started) * 1000),
        )

        # ── 15b. Persist ──────────────────────────────────────────────────────
        await self._persist(result, db)

        # ── 15c. Telemetry ────────────────────────────────────────────────────
        self._telemetry.record_review(
            depth=request.review_depth.value,
            overall_score=overall_score,
            recommendation=recommendation.value,
            latency_ms=result.analysis_duration_ms,
        )

        return result

    async def get_result(
        self, result_id: str, user_id: str
    ) -> Optional[ManuscriptIntelligenceResult]:
        db = get_db()
        db = DBProxy(db, SecurityContext.system())

        doc = await db.manuscript_intelligence_results.find_one({"result_id": result_id})
        if not doc or doc.get("user_id") != user_id:
            return None
        return _doc_to_result(doc)

    async def list_results(self, user_id: str, limit: int = 50) -> list[dict]:
        db = get_db()
        db = DBProxy(db, SecurityContext.system())

        docs = await db.manuscript_intelligence_results.find(
            {"user_id": user_id},
            {"result_id": 1, "filename": 1, "title": 1, "overall_score": 1,
             "recommendation": 1, "review_depth": 1, "word_count": 1,
             "credits_used": 1, "created_at": 1},
        ).sort("created_at", -1).to_list(limit)
        return [
            {
                "result_id": d.get("result_id", str(d.get("_id", ""))),
                "filename": d.get("filename", ""),
                "title": d.get("title", ""),
                "overall_score": d.get("overall_score", 0),
                "recommendation": d.get("recommendation", ""),
                "review_depth": d.get("review_depth", "standard"),
                "word_count": d.get("word_count", 0),
                "credits_used": d.get("credits_used", 0),
                "created_at": d.get("created_at", ""),
            }
            for d in docs
        ]

    async def export(
        self, result_id: str, user_id: str, fmt: ExportFormat
    ) -> tuple[str, str, str]:
        result = await self.get_result(result_id, user_id)
        if not result:
            return "", "", ""
        content, filename, ct = export_result(result, fmt)
        self._telemetry.record_export(fmt.value)
        return content, filename, ct

    async def admin_list_results(self, limit: int = 50) -> list[dict]:
        db = get_db()
        db = DBProxy(db, SecurityContext.system())

        docs = await db.manuscript_intelligence_results.find(
            {}, {"result_id": 1, "user_id": 1, "filename": 1, "overall_score": 1,
                 "recommendation": 1, "review_depth": 1, "created_at": 1}
        ).sort("created_at", -1).to_list(limit)
        return [
            {
                "result_id": d.get("result_id", ""),
                "user_id": d.get("user_id", ""),
                "filename": d.get("filename", ""),
                "overall_score": d.get("overall_score", 0),
                "recommendation": d.get("recommendation", ""),
                "review_depth": d.get("review_depth", ""),
                "created_at": d.get("created_at", ""),
            }
            for d in docs
        ]

    def get_telemetry_stats(self) -> dict:
        return self._telemetry.get_stats()

    async def _persist(self, result: ManuscriptIntelligenceResult, db) -> None:
        try:
            doc = result.to_dict()
            await db.manuscript_intelligence_results.update_one(
                {"result_id": result.result_id},
                {"$set": doc},
                upsert=True,
            )
        except Exception as exc:
            log.error("Failed to persist manuscript review: %s", exc)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _merge_dimensions(
    rule_dims: ReviewDimensions,
    ai_dims: dict[str, QualityDimension],
) -> ReviewDimensions:
    """AI dimensions take priority; rule dimensions fill gaps not covered."""
    def _pick(key: str, rule_dim: QualityDimension) -> QualityDimension:
        ai_dim = ai_dims.get(key)
        if ai_dim and ai_dim.score > 0:
            # Blend rationale — keep AI rationale; add rule strengths/weaknesses
            ai_dim.strengths = list(dict.fromkeys(ai_dim.strengths + rule_dim.strengths))[:5]
            ai_dim.weaknesses = list(dict.fromkeys(ai_dim.weaknesses + rule_dim.weaknesses))[:5]
            return ai_dim
        return rule_dim

    return ReviewDimensions(
        scientific_rigor=_pick("scientific_rigor", rule_dims.scientific_rigor),
        originality=_pick("originality", QualityDimension("Originality & Novelty", score=65.0, weight=1.5, grade="B-")),
        methodological_soundness=_pick("methodological_soundness", rule_dims.methodological_soundness),
        clarity=_pick("clarity", rule_dims.clarity),
        literature_coverage=_pick("literature_coverage", rule_dims.literature_coverage),
        contribution=_pick("contribution", QualityDimension("Scientific Contribution", score=65.0, weight=1.5, grade="B-")),
        statistical_validity=_pick("statistical_validity", rule_dims.statistical_validity),
        ethical_compliance=_pick("ethical_compliance", QualityDimension("Ethical Compliance", score=70.0, weight=0.5, grade="B")),
    )


def _build_publication_readiness(
    overall_score: float,
    critical_count: int,
    major_count: int,
    ai_pr: dict,
) -> PublicationReadiness:
    """Build PublicationReadiness from AI estimate + rule-based corrections."""
    if ai_pr:
        pr = PublicationReadiness(
            overall_score=overall_score,
            acceptance_probability=float(ai_pr.get("acceptance_probability", 0.0)),
            desk_rejection_risk=float(ai_pr.get("desk_rejection_risk", 0.2)),
            reviewer_difficulty=str(ai_pr.get("reviewer_difficulty", "moderate")),
            major_revision_probability=float(ai_pr.get("major_revision_probability", 0.5)),
            minor_revision_probability=float(ai_pr.get("minor_revision_probability", 0.2)),
            estimated_revision_effort=str(ai_pr.get("estimated_revision_effort", "2-4 weeks")),
            target_tier=str(ai_pr.get("target_tier", "Q2")),
            strengths=list(ai_pr.get("strengths", [])),
            barriers=list(ai_pr.get("barriers", [])),
        )
    else:
        # Rule-based fallback
        acc = max(0.0, (overall_score - 40) / 60)
        desk_rej = max(0.0, 1.0 - overall_score / 100) * 0.5
        if critical_count >= 2:
            desk_rej = min(0.85, desk_rej + 0.30)
        pr = PublicationReadiness(
            overall_score=overall_score,
            acceptance_probability=round(acc * 0.3, 3),
            desk_rejection_risk=round(desk_rej, 3),
            reviewer_difficulty="high" if major_count >= 5 else "moderate",
            major_revision_probability=round(min(0.8, major_count * 0.12), 3),
            minor_revision_probability=round(max(0.0, 0.4 - major_count * 0.08), 3),
            estimated_revision_effort=(
                ">3 months" if critical_count >= 2 else
                "2–4 weeks" if major_count >= 3 else
                "1–2 weeks"
            ),
            target_tier="Q2" if overall_score >= 70 else "Q3",
        )
    pr.overall_score = overall_score
    return pr


def _map_recommendation(
    rec_str: str,
    score: float,
    critical_count: int,
    major_count: int,
) -> Recommendation:
    mapping = {
        "accept": Recommendation.ACCEPT,
        "minor_revision": Recommendation.MINOR_REVISION,
        "major_revision": Recommendation.MAJOR_REVISION,
        "revise_and_resubmit": Recommendation.REVISE_AND_RESUBMIT,
        "reject": Recommendation.REJECT,
        "reject_with_encouragement": Recommendation.REJECT_WITH_ENCOURAGEMENT,
    }
    if rec_str in mapping:
        return mapping[rec_str]
    # Rule-based fallback
    if critical_count >= 2 or score < 40:
        return Recommendation.REJECT
    if score < 50:
        return Recommendation.REJECT_WITH_ENCOURAGEMENT
    if score < 60 or major_count >= 5:
        return Recommendation.REVISE_AND_RESUBMIT
    if major_count >= 2:
        return Recommendation.MAJOR_REVISION
    if score >= 80:
        return Recommendation.MINOR_REVISION
    return Recommendation.MAJOR_REVISION


def _build_section_scores(sections, dims: ReviewDimensions) -> list[SectionScore]:
    from .models import SectionType
    from .section_detector import section_type_labels

    labels = section_type_labels()
    score_by_type: dict[str, SectionScore] = {}

    for sec in sections:
        st = sec.section_type
        # Assign score based on dimensions + word count heuristic
        base_score = dims.weighted_score()
        wc = sec.word_count
        if wc < 50:
            penalty = 15
        elif wc < 150:
            penalty = 5
        else:
            penalty = 0

        score_by_type[st.value] = SectionScore(
            section_type=st,
            label=labels.get(st.value, st.value.title()),
            score=max(0, min(100, base_score - penalty)),
            grade=_score_to_grade(max(0, base_score - penalty)),
            detected=True,
            word_count=wc,
        )

    # Critical sections that are missing → score 0
    critical_types = [
        SectionType.ABSTRACT, SectionType.INTRODUCTION,
        SectionType.METHODOLOGY, SectionType.RESULTS,
        SectionType.DISCUSSION, SectionType.CONCLUSIONS,
    ]
    for ct in critical_types:
        if ct.value not in score_by_type:
            score_by_type[ct.value] = SectionScore(
                section_type=ct,
                label=labels.get(ct.value, ct.value.title()),
                score=0.0,
                grade="F",
                detected=False,
                word_count=0,
                weaknesses=[f"Section '{ct.value}' not detected"],
                recommendations=[f"Add a dedicated {ct.value.replace('_', ' ').title()} section"],
            )

    return list(score_by_type.values())


def _doc_to_result(doc: dict) -> ManuscriptIntelligenceResult:
    r = ManuscriptIntelligenceResult(
        result_id=doc.get("result_id", ""),
        user_id=doc.get("user_id", ""),
        filename=doc.get("filename", ""),
        manuscript_id=doc.get("manuscript_id", ""),
        title=doc.get("title", ""),
        abstract=doc.get("abstract", ""),
        keywords=doc.get("keywords", []),
        detected_sections=doc.get("detected_sections", []),
        word_count=doc.get("word_count", 0),
        page_count=doc.get("page_count", 0),
        figure_count=doc.get("figure_count", 0),
        table_count=doc.get("table_count", 0),
        reference_count=doc.get("reference_count", 0),
        overall_score=doc.get("overall_score", 0.0),
        executive_summary=doc.get("executive_summary", ""),
        peer_review_text=doc.get("peer_review_text", ""),
        editorial_assessment=doc.get("editorial_assessment", ""),
        inferred_discipline=doc.get("inferred_discipline", ""),
        revision_roadmap=doc.get("revision_roadmap", []),
        visualizations=doc.get("visualizations", {}),
        analysis_duration_ms=doc.get("analysis_duration_ms", 0),
        credits_used=doc.get("credits_used", 0),
        created_at=doc.get("created_at", ""),
    )
    try:
        r.review_depth = ReviewDepth(doc.get("review_depth", "standard"))
    except ValueError:
        r.review_depth = ReviewDepth.STANDARD
    try:
        r.recommendation = Recommendation(doc.get("recommendation", "major_revision"))
    except ValueError:
        r.recommendation = Recommendation.MAJOR_REVISION
    return r


# ── Singleton ──────────────────────────────────────────────────────────────────

_engine_instance: Optional[ManuscriptIntelligenceEngine] = None


async def get_manuscript_engine() -> ManuscriptIntelligenceEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ManuscriptIntelligenceEngine(get_manuscript_telemetry())
    return _engine_instance


def reset_manuscript_engine() -> None:
    global _engine_instance
    _engine_instance = None
