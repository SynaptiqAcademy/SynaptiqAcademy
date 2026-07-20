"""Statistical Intelligence 2.0 — Orchestration Engine (Phase X).

14-step pipeline:
  1.  Parse input data
  2.  Analyse research design
  3.  Review sampling
  4.  Review data quality
  5.  Review statistical methods
  6.  Check assumptions
  7.  Interpret results
  8.  Review validity
  9.  AI comprehensive advisory
  10. Merge dimensions (AI primary, rules fill)
  11. Build publication readiness
  12. Build revision roadmap
  13. Build all visualizations
  14. Persist → MongoDB + telemetry

Backward-compatible: does NOT touch statistical_reviews collection.
New collection: statistical_intelligence_results.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from .models import (
    AnalysisDepth, AnalysisMethod, DimensionScore, ExportFormat,
    IssueSeverity, Priority, PublicationReadiness, RecommendedAnalysis,
    ResearchDesign, RevisionPhase, ReviewerCriticism, StatisticalAnalysisRequest,
    StatisticalIntelligenceResult, StatisticalIssue, StudyType, VerdictLevel,
    _score_to_grade,
)
from .data_parser import parse_input
from .design_analyzer import analyze_design
from .sampling_reviewer import review_sampling
from .data_quality_reviewer import review_data_quality
from .method_reviewer import review_methods
from .assumption_checker import check_assumptions
from .result_interpreter import interpret_results
from .validity_reviewer import review_validity
from .ai_advisor import review_with_ai
from .viz_builder import build_all_visualizations
from .export_engine import export_result
from .telemetry import get_statistical_telemetry
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.statistical.engine")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Dimension merging ─────────────────────────────────────────────────────────

def _merge_dimensions(
    rule_dims: "StatisticalDimensions",
    ai_dims: dict,
) -> "StatisticalDimensions":
    """AI dimensions take priority; rule-based fills any missing."""
    for attr, key in [
        ("methodological_rigor", "methodological_rigor"),
        ("sample_adequacy",      "sample_adequacy"),
        ("data_quality",         "data_quality"),
        ("result_validity",      "result_validity"),
        ("construct_validity",   "construct_validity"),
        ("reporting_quality",    "reporting_quality"),
    ]:
        ai_dim = ai_dims.get(key, {})
        if ai_dim and ai_dim.get("score", 0) > 0:
            dim = getattr(rule_dims, attr)
            dim.score = float(ai_dim.get("score", dim.score))
            dim.grade = ai_dim.get("grade", _score_to_grade(dim.score))
            dim.rationale = ai_dim.get("rationale", dim.rationale)
            # Blend strengths/weaknesses (AI first, dedup, cap 5)
            rule_s = dim.strengths
            rule_w = dim.weaknesses
            ai_s = ai_dim.get("strengths", [])
            ai_w = ai_dim.get("weaknesses", [])
            seen = set()
            merged_s, merged_w = [], []
            for s in ai_s + rule_s:
                if s not in seen:
                    seen.add(s)
                    merged_s.append(s)
            seen = set()
            for w in ai_w + rule_w:
                if w not in seen:
                    seen.add(w)
                    merged_w.append(w)
            dim.strengths = merged_s[:5]
            dim.weaknesses = merged_w[:5]
    return rule_dims


# ── Publication readiness ─────────────────────────────────────────────────────

def _build_publication_readiness(
    overall_score: float,
    critical_count: int,
    major_count: int,
    ai_pr: dict,
) -> PublicationReadiness:
    if ai_pr and ai_pr.get("overall_score", 0) > 0:
        try:
            return PublicationReadiness(
                overall_score=float(ai_pr["overall_score"]),
                acceptance_probability=float(ai_pr.get("acceptance_probability", 0.0)),
                desk_rejection_risk=float(ai_pr.get("desk_rejection_risk", 0.0)),
                verdict=VerdictLevel(ai_pr.get("verdict", "insufficient")),
                strongest_element=str(ai_pr.get("strongest_element", "")),
                critical_barrier=str(ai_pr.get("critical_barrier", "")),
                assessment=str(ai_pr.get("assessment", "")),
            )
        except (KeyError, ValueError):
            pass

    # Rule-based fallback
    if critical_count >= 3 or overall_score < 40:
        acceptance = 0.05
        desk_rej = 0.80
        verdict = VerdictLevel.INSUFFICIENT
    elif critical_count >= 1 or overall_score < 55:
        acceptance = 0.10
        desk_rej = 0.50
        verdict = VerdictLevel.WEAK
    elif major_count >= 3 or overall_score < 65:
        acceptance = 0.20
        desk_rej = 0.30
        verdict = VerdictLevel.WEAK
    elif major_count >= 1 or overall_score < 75:
        acceptance = 0.35
        desk_rej = 0.15
        verdict = VerdictLevel.ADEQUATE
    elif overall_score < 85:
        acceptance = 0.55
        desk_rej = 0.05
        verdict = VerdictLevel.ADEQUATE
    else:
        acceptance = 0.70
        desk_rej = 0.02
        verdict = VerdictLevel.STRONG

    return PublicationReadiness(
        overall_score=overall_score,
        acceptance_probability=acceptance,
        desk_rejection_risk=desk_rej,
        verdict=verdict,
        strongest_element="",
        critical_barrier="See critical issues above.",
        assessment=f"Statistical quality score of {overall_score:.1f}/100.",
    )


# ── Verdict mapping ───────────────────────────────────────────────────────────

def _map_verdict(verdict_str: str, overall_score: float) -> VerdictLevel:
    mapping = {
        "strong": VerdictLevel.STRONG,
        "adequate": VerdictLevel.ADEQUATE,
        "weak": VerdictLevel.WEAK,
        "insufficient": VerdictLevel.INSUFFICIENT,
    }
    if verdict_str.lower() in mapping:
        return mapping[verdict_str.lower()]
    # Rule fallback
    if overall_score >= 80: return VerdictLevel.STRONG
    if overall_score >= 65: return VerdictLevel.ADEQUATE
    if overall_score >= 45: return VerdictLevel.WEAK
    return VerdictLevel.INSUFFICIENT


# ── Revision roadmap ──────────────────────────────────────────────────────────

def _build_revision_roadmap(
    critical: list[StatisticalIssue],
    major: list[StatisticalIssue],
    moderate: list[StatisticalIssue],
    minor: list[StatisticalIssue],
    recommended: list[RecommendedAnalysis],
    ai_roadmap: list,
) -> list[RevisionPhase]:
    # Prefer AI roadmap if available and non-empty
    if ai_roadmap:
        phases = []
        for p in ai_roadmap[:6]:
            phases.append(RevisionPhase(
                phase=int(p.get("phase", len(phases) + 1)),
                title=str(p.get("title", "Revision Phase")),
                priority=str(p.get("priority", "medium")),
                estimated_effort=str(p.get("estimated_effort", "1-2 weeks")),
                actions=list(p.get("actions", [])),
            ))
        return phases

    # Rule-based roadmap
    phases: list[RevisionPhase] = []

    if critical:
        phases.append(RevisionPhase(
            phase=1,
            title="Critical Statistical Corrections",
            priority="high",
            estimated_effort="1-2 weeks",
            actions=[f"Fix: {i.recommendation}" for i in critical[:5]],
            issue_count=len(critical),
        ))

    if major:
        phases.append(RevisionPhase(
            phase=len(phases) + 1,
            title="Major Statistical Revisions",
            priority="high",
            estimated_effort="2-4 weeks",
            actions=[f"Address: {i.recommendation}" for i in major[:5]],
            issue_count=len(major),
        ))

    assumption_issues = [i for i in moderate if i.category == "assumptions"]
    if assumption_issues:
        phases.append(RevisionPhase(
            phase=len(phases) + 1,
            title="Assumption Testing & Verification",
            priority="medium",
            estimated_effort="1-2 weeks",
            actions=[f"Test: {i.recommendation}" for i in assumption_issues[:5]],
            issue_count=len(assumption_issues),
        ))

    essential = [r for r in recommended if r.priority == Priority.ESSENTIAL]
    if essential:
        phases.append(RevisionPhase(
            phase=len(phases) + 1,
            title="Additional Essential Analyses",
            priority="medium",
            estimated_effort="1-2 weeks",
            actions=[f"{r.analysis}: {r.rationale}" for r in essential[:4]],
            issue_count=len(essential),
        ))

    reporting_issues = [i for i in moderate + minor if i.category == "reporting"]
    if reporting_issues:
        phases.append(RevisionPhase(
            phase=len(phases) + 1,
            title="Reporting & Documentation",
            priority="low",
            estimated_effort="3-5 days",
            actions=[f"Report: {i.recommendation}" for i in reporting_issues[:5]],
            issue_count=len(reporting_issues),
        ))

    phases.append(RevisionPhase(
        phase=len(phases) + 1,
        title="Final Review",
        priority="low",
        estimated_effort="1-2 days",
        actions=[
            "Proofread all statistical tables and figures",
            "Verify APA 7th edition format for all statistics",
            "Cross-check in-text statistics with tables",
            "Confirm all assumptions are documented",
        ],
        issue_count=0,
    ))

    return phases


# ── Engine ────────────────────────────────────────────────────────────────────

class StatisticalIntelligenceEngine:
    def __init__(self) -> None:
        self._telemetry = get_statistical_telemetry()

    async def analyse(
        self, request: StatisticalAnalysisRequest
    ) -> StatisticalIntelligenceResult:
        started = time.monotonic()
        result = StatisticalIntelligenceResult(
            user_id=request.user_id,
            topic=request.topic,
            research_question=request.research_question,
            analysis_depth=request.analysis_depth,
            input_format=request.input_format,
            created_at=_now(),
        )
        all_issues: list[StatisticalIssue] = []

        try:
            # ── 1. Parse input ────────────────────────────────────────────────
            text = request.content if isinstance(request.content, str) else ""
            if not isinstance(request.content, str):
                parsed = parse_input(request.content, request.input_format)
                text = parsed.raw_text
            else:
                from .data_parser import parse_text
                parsed = parse_text(request.content)

            # Enrich text with request context
            full_context = "\n\n".join(filter(None, [
                f"Topic: {request.topic}",
                f"Research question: {request.research_question}",
                f"Methodology: {request.methodology}",
                f"Hypotheses: {request.hypotheses}",
                text,
            ]))

            # ── 2. Analyse design ─────────────────────────────────────────────
            design = analyze_design(full_context, parsed)
            result.research_design = design

            # ── 3. Review sampling ────────────────────────────────────────────
            sampling, sampling_issues = review_sampling(full_context, design)
            result.sampling_analysis = sampling
            all_issues.extend(sampling_issues)

            # ── 4. Data quality ───────────────────────────────────────────────
            dq, dq_issues = review_data_quality(full_context, parsed)
            result.data_quality = dq
            all_issues.extend(dq_issues)

            # ── 5. Method review ──────────────────────────────────────────────
            method_evals, method_issues = review_methods(full_context, design)
            result.method_evaluations = method_evals
            all_issues.extend(method_issues)

            # ── 6. Assumption checking ────────────────────────────────────────
            assumption_checks, assumption_issues = check_assumptions(full_context, design)
            result.assumption_checks = assumption_checks
            all_issues.extend(assumption_issues)

            # ── 7. Result interpretation ──────────────────────────────────────
            interp, interp_issues = interpret_results(full_context)
            result.results_interpretation = interp
            all_issues.extend(interp_issues)

            # ── 8. Validity review ────────────────────────────────────────────
            validity, validity_issues = review_validity(full_context, design)
            result.validity_analysis = validity
            all_issues.extend(validity_issues)

            # ── 9. AI advisor (QUICK: AI only, STANDARD/DEEP: full) ───────────
            ai_result = {}
            if request.analysis_depth != AnalysisDepth.QUICK or not all_issues:
                ai_result = await review_with_ai(
                    content=full_context,
                    topic=request.topic,
                    research_question=request.research_question,
                    methodology=request.methodology,
                    hypotheses=request.hypotheses,
                    discipline=design.discipline,
                    detected_methods=[m.value for m in design.detected_methods if m != AnalysisMethod.UNKNOWN],
                    study_type=design.study_type.value,
                    sample_size=design.sample_size,
                    critical_issue_count=sum(1 for i in all_issues if i.severity == IssueSeverity.CRITICAL),
                    major_issue_count=sum(1 for i in all_issues if i.severity == IssueSeverity.MAJOR),
                )

            result.ai_review = ai_result
            result.executive_summary = ai_result.get("executive_summary", "")
            result.statistical_review_text = ai_result.get("statistical_review_text", "")

            # ── 10. Merge dimensions ──────────────────────────────────────────
            # Populate rule-based dimension scores first
            result.dimensions.methodological_rigor.score = (
                sum(e.appropriateness_score for e in method_evals) / max(len(method_evals), 1)
                if method_evals else 50.0
            )
            result.dimensions.sample_adequacy.score = sampling.score
            result.dimensions.data_quality.score    = dq.score
            result.dimensions.result_validity.score = interp.score
            result.dimensions.construct_validity.score = validity.construct_validity_score
            result.dimensions.reporting_quality.score = interp.score * 0.8

            for attr in ["methodological_rigor", "sample_adequacy", "data_quality",
                         "result_validity", "construct_validity", "reporting_quality"]:
                dim = getattr(result.dimensions, attr)
                if dim.grade == "N/A":
                    dim.grade = _score_to_grade(dim.score)

            result.dimensions = _merge_dimensions(result.dimensions, ai_result.get("dimensions", {}))

            # ── Collect additional AI issues ──────────────────────────────────
            for ai_issue in ai_result.get("additional_critical_issues", []):
                try:
                    all_issues.append(StatisticalIssue(
                        severity=IssueSeverity(ai_issue.get("severity", "moderate")),
                        category=ai_issue.get("category", "general"),
                        title=str(ai_issue.get("title", "")),
                        description=str(ai_issue.get("description", "")),
                        recommendation=str(ai_issue.get("recommendation", "")),
                    ))
                except (ValueError, KeyError):
                    pass

            # ── Collect recommended analyses ──────────────────────────────────
            recommended: list[RecommendedAnalysis] = []
            for rec in ai_result.get("recommended_analyses", []):
                try:
                    recommended.append(RecommendedAnalysis(
                        analysis=str(rec.get("analysis", "")),
                        rationale=str(rec.get("rationale", "")),
                        priority=Priority(rec.get("priority", "recommended")),
                        software_guidance=str(rec.get("software_guidance", "")),
                    ))
                except (ValueError, KeyError):
                    pass
            result.recommended_analyses = recommended

            # ── Collect reviewer criticisms ───────────────────────────────────
            criticisms: list[ReviewerCriticism] = []
            for c in ai_result.get("reviewer_criticisms", []):
                criticisms.append(ReviewerCriticism(
                    comment=str(c.get("comment", "")),
                    severity=str(c.get("severity", "major")),
                    suggested_response=str(c.get("suggested_response", "")),
                ))
            result.reviewer_criticisms = criticisms

            # ── Classify all issues ───────────────────────────────────────────
            for issue in all_issues:
                if issue.severity == IssueSeverity.CRITICAL:
                    result.critical_issues.append(issue)
                elif issue.severity == IssueSeverity.MAJOR:
                    result.major_issues.append(issue)
                elif issue.severity == IssueSeverity.MODERATE:
                    result.moderate_issues.append(issue)
                else:
                    result.minor_issues.append(issue)

            # ── 11. Publication readiness ─────────────────────────────────────
            result.overall_score = result.dimensions.weighted_score()
            result.overall_verdict = _map_verdict(
                ai_result.get("overall_verdict", ""),
                result.overall_score,
            )
            result.publication_readiness = _build_publication_readiness(
                result.overall_score,
                len(result.critical_issues),
                len(result.major_issues),
                ai_result.get("publication_readiness", {}),
            )

            # ── 12. Revision roadmap ──────────────────────────────────────────
            roadmap = _build_revision_roadmap(
                result.critical_issues, result.major_issues,
                result.moderate_issues, result.minor_issues,
                recommended, ai_result.get("revision_roadmap", []),
            )
            result.revision_roadmap = roadmap

            # ── 13. Visualizations ────────────────────────────────────────────
            result.visualizations = build_all_visualizations(
                dims=result.dimensions,
                assumption_checks=result.assumption_checks,
                results_interp=result.results_interpretation,
                data_quality=result.data_quality,
                design=design,
                sampling=sampling,
                validity=validity,
                critical=result.critical_issues,
                major=result.major_issues,
                moderate=result.moderate_issues,
                minor=result.minor_issues,
                publication_readiness=result.publication_readiness,
                roadmap=[p.to_dict() for p in roadmap],
            )

            # ── 14. Persist ───────────────────────────────────────────────────
            await self._persist(result)

        except Exception as exc:
            log.error("Statistical intelligence engine error: %s", exc, exc_info=True)
            self._telemetry.record_error()
            raise

        # ── Telemetry ─────────────────────────────────────────────────────────
        latency_ms = (time.monotonic() - started) * 1000
        self._telemetry.record_review(
            depth=request.analysis_depth.value,
            overall_score=result.overall_score,
            verdict=result.overall_verdict.value,
            latency_ms=latency_ms,
        )
        return result

    async def _persist(self, result: StatisticalIntelligenceResult) -> None:
        try:
            from db import get_db
            db = get_db()
            db = DBProxy(db, SecurityContext.system())

            doc = result.to_dict()
            doc["_id"] = result.result_id
            await db.statistical_intelligence_results.replace_one(
                {"_id": result.result_id}, doc, upsert=True
            )
        except Exception as exc:
            log.warning("Failed to persist statistical intelligence result: %s", exc)

    async def get_result(
        self, result_id: str, user_id: str
    ) -> Optional[StatisticalIntelligenceResult]:
        try:
            from db import get_db
            db = get_db()
            db = DBProxy(db, SecurityContext.system())

            doc = await db.statistical_intelligence_results.find_one(
                {"_id": result_id, "user_id": user_id}
            )
            if not doc:
                return None
            return self._doc_to_result(doc)
        except Exception as exc:
            log.warning("get_result error: %s", exc)
            return None

    async def list_results(self, user_id: str, limit: int = 20) -> list[dict]:
        try:
            from db import get_db
            db = get_db()
            db = DBProxy(db, SecurityContext.system())

            docs = await (
                db.statistical_intelligence_results
                .find({"user_id": user_id}, {"visualizations": 0, "ai_review": 0, "assumption_checks": 0})
                .sort("created_at", -1)
                .to_list(limit)
            )
            return [self._summary_from_doc(d) for d in docs]
        except Exception:
            return []

    async def admin_list_results(self, limit: int = 50) -> list[dict]:
        try:
            from db import get_db
            db = get_db()
            db = DBProxy(db, SecurityContext.system())

            docs = await (
                db.statistical_intelligence_results
                .find({}, {"visualizations": 0, "ai_review": 0})
                .sort("created_at", -1)
                .to_list(limit)
            )
            return [self._summary_from_doc(d) for d in docs]
        except Exception:
            return []

    def get_telemetry_stats(self) -> dict:
        return self._telemetry.get_stats()

    async def export(
        self, result_id: str, user_id: str, fmt: ExportFormat
    ) -> tuple[str, str, str]:
        result = await self.get_result(result_id, user_id)
        if not result:
            return "", "", ""
        content, filename, ct = export_result(result, fmt)
        self._telemetry.record_export(fmt.value)
        return content, filename, ct

    @staticmethod
    def _doc_to_result(doc: dict) -> StatisticalIntelligenceResult:
        r = StatisticalIntelligenceResult(
            result_id=str(doc.get("_id", "")),
            user_id=str(doc.get("user_id", "")),
            topic=str(doc.get("topic", "")),
            research_question=str(doc.get("research_question", "")),
            overall_score=float(doc.get("overall_score", 0)),
            executive_summary=str(doc.get("executive_summary", "")),
            statistical_review_text=str(doc.get("statistical_review_text", "")),
            visualizations=doc.get("visualizations", {}),
            created_at=str(doc.get("created_at", "")),
        )
        try:
            r.analysis_depth = AnalysisDepth(doc.get("analysis_depth", "standard"))
        except ValueError:
            pass
        try:
            r.overall_verdict = VerdictLevel(doc.get("overall_verdict", "insufficient"))
        except ValueError:
            pass
        pr_d = doc.get("publication_readiness", {})
        if pr_d:
            try:
                r.publication_readiness = PublicationReadiness(
                    overall_score=float(pr_d.get("overall_score", 0)),
                    acceptance_probability=float(pr_d.get("acceptance_probability", 0)),
                    desk_rejection_risk=float(pr_d.get("desk_rejection_risk", 0)),
                    verdict=VerdictLevel(pr_d.get("verdict", "insufficient")),
                    strongest_element=str(pr_d.get("strongest_element", "")),
                    critical_barrier=str(pr_d.get("critical_barrier", "")),
                    assessment=str(pr_d.get("assessment", "")),
                )
            except (ValueError, KeyError):
                pass
        return r

    @staticmethod
    def _summary_from_doc(doc: dict) -> dict:
        return {
            "result_id": str(doc.get("_id", "")),
            "topic": doc.get("topic", ""),
            "overall_score": doc.get("overall_score", 0),
            "overall_verdict": doc.get("overall_verdict", ""),
            "analysis_depth": doc.get("analysis_depth", ""),
            "created_at": doc.get("created_at", ""),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_ENGINE: Optional[StatisticalIntelligenceEngine] = None
_ENGINE_LOCK = None


async def get_statistical_engine() -> StatisticalIntelligenceEngine:
    global _ENGINE, _ENGINE_LOCK
    import asyncio
    if _ENGINE_LOCK is None:
        _ENGINE_LOCK = asyncio.Lock()
    async with _ENGINE_LOCK:
        if _ENGINE is None:
            _ENGINE = StatisticalIntelligenceEngine()
    return _ENGINE


def reset_statistical_engine() -> None:
    global _ENGINE
    _ENGINE = None


# ── Public helper exports for engine.py internal functions ────────────────────

def _merge_dimensions_public(rule_dims, ai_dims):
    return _merge_dimensions(rule_dims, ai_dims)


def _build_publication_readiness_public(score, critical, major, ai_pr):
    return _build_publication_readiness(score, critical, major, ai_pr)


def _map_verdict_public(verdict_str, score):
    return _map_verdict(verdict_str, score)
