"""AcademicIntelligenceEngine — the permanent reasoning layer behind every academic feature.

Flow in AIEngine.generate():
  1. _academic_enrich(request)  → injects structured system guidance (pre-processing)
  2. LLM call (unchanged)
  3. _academic_post_process(request, response) → validation + quality + memory (post)

The engine is non-blocking: any exception falls through silently.
No existing endpoint or LLM call is disrupted.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from services.academic.knowledge_graph.graph import AcademicKnowledgeGraph
from services.academic.memory.academic_memory import AcademicMemory
from services.academic.models import (
    AcademicAnalysis, AcademicContext, AcademicDomain, AcademicUserProfile,
    ConfidenceLevel, MethodologyType, QualityScore, ResearchDesign,
    ValidationResult,
)
from services.academic.ontology import (
    ACADEMIC_FEATURES, get_quality_threshold, get_reasoning_framework,
)
from services.academic.reasoning.detector import AcademicWeaknessDetector
from services.academic.strategy.strategy_engine import AcademicStrategyEngine
from services.academic.telemetry import AcademicIntelligenceTelemetry, get_academic_telemetry
from services.academic.validation.validator import AcademicQualityEngine, AcademicValidator

logger = logging.getLogger("synaptiq.academic.engine")

# Maximum characters to analyze for context building (avoids processing very large documents twice)
_MAX_ANALYSIS_CHARS = 8000
# Minimum content length to trigger academic enrichment
_MIN_CONTENT_LENGTH = 30


class AcademicIntelligenceEngine:
    """The academic intelligence layer — enriches, validates, and learns from every AI request."""

    def __init__(self, db: Any) -> None:
        self._db = db
        self._detector = AcademicWeaknessDetector()
        self._validator = AcademicValidator()
        self._quality = AcademicQualityEngine()
        self._strategy = AcademicStrategyEngine()
        self._memory = AcademicMemory(db)
        self._graph = AcademicKnowledgeGraph(db)
        self._telemetry = get_academic_telemetry()

        logger.info("AcademicIntelligenceEngine initialized")

    # ── Pre-processing ─────────────────────────────────────────────────────────

    async def enrich_request(self, request: Any) -> Any:
        """Inject academic reasoning context into the request system prompt (best-effort)."""
        if not hasattr(request, "feature") or request.feature not in ACADEMIC_FEATURES:
            return request
        try:
            content = self._extract_content(request)
            if len(content) < _MIN_CONTENT_LENGTH:
                return request

            context = await self._build_context(
                feature=request.feature,
                content=content,
                user_id=request.user_id or "",
            )

            guidance = self._build_system_guidance(context)
            if guidance:
                request.system = (
                    (request.system + "\n\n" + guidance) if request.system else guidance
                )

            self._telemetry.record_enrichment(
                feature=request.feature,
                domain=context.domain.value,
                weakness_count=len(context.detected_weaknesses),
                confidence=context.domain_confidence,
            )
            for w in context.detected_weaknesses:
                self._telemetry.record_weakness(w.type.value)

        except Exception as exc:
            logger.debug("Academic enrichment failed (non-blocking): %s", exc)
        return request

    # ── Post-processing ────────────────────────────────────────────────────────

    async def post_process(self, request: Any, response: Any) -> Any:
        """Validate and quality-score the LLM response, then update memory (best-effort)."""
        if not hasattr(request, "feature") or request.feature not in ACADEMIC_FEATURES:
            return response
        try:
            text = getattr(response, "text", "") or ""
            if not text:
                return response

            # Rebuild minimal context for post-processing (lightweight)
            ctx = AcademicContext(feature=request.feature, user_id=request.user_id or "")

            validation = self._validator.validate(text, ctx)
            self._telemetry.record_validation(validation.is_valid)

            quality = self._quality.score(text, request.feature, ctx)
            self._telemetry.record_quality(quality.overall_score, quality.needs_improvement)

            # Store academic metadata on response if possible
            if hasattr(response, "__dict__"):
                response.__dict__["academic_quality_score"] = quality.overall_score
                response.__dict__["academic_validation_ok"] = validation.is_valid

            # Update memory (fire and forget)
            asyncio.create_task(self._memory.record_interaction(
                user_id=request.user_id or "",
                feature=request.feature,
                quality_score=quality.overall_score,
            ))

        except Exception as exc:
            logger.debug("Academic post-process failed (non-blocking): %s", exc)
        return response

    # ── Full analysis (called directly, not via AIEngine) ─────────────────────

    async def analyze(
        self,
        text: str,
        feature: str,
        user_id: str = "",
    ) -> AcademicAnalysis:
        """Comprehensive academic analysis of text — used by dedicated endpoints."""
        t0 = time.monotonic()
        context = await self._build_context(feature=feature, content=text, user_id=user_id)

        validation = self._validator.validate(text, context)
        quality = self._quality.score(text, feature, context)

        profile = await self._memory.get_user_profile(user_id) if user_id else AcademicUserProfile(user_id="")
        strategy = self._strategy.generate(profile, context)

        confidence_score = self._compute_confidence(context, quality)

        processing_ms = int((time.monotonic() - t0) * 1000)
        guidance = self._build_system_guidance(context)

        return AcademicAnalysis(
            context=context,
            quality=quality,
            validation=validation,
            strategy=strategy,
            confidence=ConfidenceLevel.from_score(confidence_score),
            overall_confidence_score=round(confidence_score, 3),
            enriched_system_guidance=guidance,
            processing_time_ms=processing_ms,
        )

    # ── Strategy ──────────────────────────────────────────────────────────────

    async def get_strategy(self, user_id: str) -> list[dict]:
        """Return strategic recommendations for the user."""
        profile = await self._memory.get_user_profile(user_id)
        recommendations = self._strategy.generate(profile)
        return [r.to_dict() for r in recommendations]

    # ── Admin/stats methods ────────────────────────────────────────────────────

    def get_telemetry_stats(self) -> dict:
        return self._telemetry.get_stats()

    async def get_memory_stats(self) -> dict:
        return await self._memory.get_stats()

    async def get_graph_stats(self) -> dict:
        return await self._graph.get_stats()

    async def get_user_memory(self, user_id: str) -> dict:
        return await self._memory.get_memory_summary(user_id)

    async def clear_user_memory(self, user_id: str) -> int:
        return await self._memory.clear_memory(user_id)

    def reset_telemetry(self) -> None:
        self._telemetry.reset()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _extract_content(self, request: Any) -> str:
        """Extract the primary text content from an AIRequest for analysis."""
        messages = getattr(request, "messages", [])
        # Take the last user message (most recent = most relevant for analysis)
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                return str(msg.get("content", ""))[:_MAX_ANALYSIS_CHARS]
        return ""

    async def _build_context(
        self,
        feature: str,
        content: str,
        user_id: str,
    ) -> AcademicContext:
        """Build a complete AcademicContext from content and user history."""
        # Domain and methodology detection
        domain, domain_confidence = self._detector.detect_domain(content)
        methodology, design = self._detector.detect_methodology(content)
        sections = self._detector.detect_sections(content)
        flags = self._detector.build_structure_flags(content)
        citation_count = self._detector.count_citations(content)
        word_count = len(content.split())

        # Weakness detection
        weaknesses = self._detector.detect(
            content, feature=feature, domain=domain, methodology=methodology
        )

        # User memory context (best-effort)
        preferences: dict = {}
        recent_topics: list[str] = []
        preferred_methodology: str = ""
        interaction_count: int = 0
        if user_id:
            try:
                profile = await self._memory.get_user_profile(user_id)
                preferences = {"primary_domain": profile.primary_domain}
                recent_topics = profile.active_research_topics[:5]
                preferred_methodology = profile.preferred_methodology
                interaction_count = profile.interaction_count
            except Exception:
                pass

        # Knowledge graph topics (best-effort)
        related_topics: list[str] = []
        if user_id:
            try:
                related_topics = await self._graph.get_user_research_topics(user_id, limit=5)
            except Exception:
                pass

        reasoning_framework = get_reasoning_framework(feature)
        threshold = get_quality_threshold(feature)

        return AcademicContext(
            feature=feature,
            user_id=user_id,
            domain=domain,
            domain_confidence=domain_confidence,
            methodology_type=methodology,
            research_design=design,
            detected_sections=sections,
            word_count=word_count,
            citation_count=citation_count,
            detected_weaknesses=weaknesses,
            user_preferences=preferences,
            recent_topics=recent_topics,
            preferred_methodology=preferred_methodology,
            interaction_count=interaction_count,
            expected_quality_threshold=threshold,
            reasoning_framework=reasoning_framework,
            related_topics=related_topics,
            **flags,
        )

    def _build_system_guidance(self, context: AcademicContext) -> str:
        """Serialize AcademicContext into a system prompt injection string."""
        parts: list[str] = []

        parts.append("═══ ACADEMIC INTELLIGENCE CONTEXT ═══")

        if context.domain != AcademicDomain.UNKNOWN:
            parts.append(
                f"Domain: {context.domain.value.replace('_', ' ').title()} "
                f"(confidence: {context.domain_confidence:.0%})"
            )
        if context.methodology_type != MethodologyType.UNKNOWN:
            parts.append(f"Methodology: {context.methodology_type.value.replace('_', ' ').title()}")
        if context.research_design != ResearchDesign.UNKNOWN:
            parts.append(f"Research Design: {context.research_design.value.replace('_', ' ').title()}")

        if context.reasoning_framework:
            parts.append("")
            parts.append("REASONING FRAMEWORK:")
            parts.append(context.reasoning_framework)

        if context.detected_weaknesses:
            parts.append("")
            parts.append("DETECTED ISSUES TO ADDRESS:")
            for w in context.detected_weaknesses[:8]:
                severity_icon = {"low": "ℹ", "medium": "⚠", "high": "⚠⚠", "critical": "❌"}.get(
                    w.severity.value, "⚠"
                )
                parts.append(f"{severity_icon} [{w.severity.value.upper()}] {w.description}")
                parts.append(f"   → {w.suggestion}")

        quality_criteria = _QUALITY_CRITERIA.get(context.feature, [])
        if quality_criteria:
            parts.append("")
            parts.append("QUALITY CRITERIA FOR THIS RESPONSE:")
            for criterion in quality_criteria:
                parts.append(f"• {criterion}")

        if context.recent_topics:
            parts.append("")
            parts.append(f"USER RESEARCH CONTEXT: {', '.join(context.recent_topics[:3])}")

        if context.user_preferences.get("primary_domain"):
            parts.append(f"USER DOMAIN FOCUS: {context.user_preferences['primary_domain']}")

        parts.append("═══════════════════════════════════")
        return "\n".join(parts)

    def _compute_confidence(
        self, context: AcademicContext, quality: QualityScore
    ) -> float:
        score = 0.50
        score += context.domain_confidence * 0.20
        score += quality.overall_score * 0.25
        if context.citation_count >= 5:
            score += 0.10
        if context.has_methodology:
            score += 0.05
        if context.has_hypothesis:
            score += 0.05
        critical = context.get_critical_weaknesses()
        score -= min(0.20, len(critical) * 0.05)
        return round(min(1.0, max(0.0, score)), 3)


# ── Quality criteria per feature (injected into prompt) ───────────────────────

_QUALITY_CRITERIA: dict[str, list[str]] = {
    "manuscript_review": [
        "Evaluate hypothesis clarity and testability",
        "Check methodology rigor and validity",
        "Assess statistical analysis appropriateness",
        "Verify conclusions are supported by results",
        "Identify missing ethical compliance elements",
    ],
    "literature_review": [
        "Synthesize findings, do not just list papers",
        "Identify contradictions and gaps",
        "Assess temporal coverage (classic + recent)",
        "Suggest clear research directions",
    ],
    "research_gap_finder": [
        "Identify specific, actionable research gaps",
        "Categorize gaps by type (methodological, population, temporal, theoretical)",
        "Prioritize gaps by potential impact",
        "Suggest concrete research designs to fill each gap",
    ],
    "statistical_review": [
        "Check test appropriateness for data type",
        "Flag missing effect sizes and confidence intervals",
        "Evaluate sample size adequacy",
        "Check assumption testing",
    ],
    "abstract_generator": [
        "Include: background, objective, methods, key results, conclusion",
        "Keep to 150-250 words",
        "Include 4-6 keywords at the end",
        "Avoid citations and abbreviations",
    ],
    "grant_gap_detection": [
        "Check for clear problem statement",
        "Verify measurable objectives and milestones",
        "Assess team capacity and timeline feasibility",
        "Identify missing budget justification elements",
    ],
}


# ── Singleton ──────────────────────────────────────────────────────────────────

_engine: AcademicIntelligenceEngine | None = None
_engine_lock = threading.Lock()


async def get_academic_engine() -> AcademicIntelligenceEngine:
    """Return or create the process-level singleton."""
    global _engine
    if _engine is not None:
        return _engine
    from db import get_db
    from repo.shim import make_db_proxy
    db = make_db_proxy(get_db(), system=True)
    with _engine_lock:
        if _engine is None:
            _engine = AcademicIntelligenceEngine(db)
    return _engine


def reset_academic_engine() -> None:
    global _engine
    with _engine_lock:
        _engine = None
