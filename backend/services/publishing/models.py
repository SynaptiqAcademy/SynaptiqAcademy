"""Academic Publishing Intelligence — Domain models (Phase XII)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ── Enumerations ──────────────────────────────────────────────────────────────

class MatchType(str, Enum):
    BEST           = "best_match"
    SAFE           = "safe_match"
    HIGH_IMPACT    = "high_impact_match"
    FAST_PUB       = "fast_publication_match"
    OPEN_ACCESS    = "open_access_match"
    BUDGET_FRIENDLY = "budget_friendly_match"


class RevisionType(str, Enum):
    MAJOR            = "major_revision"
    MINOR            = "minor_revision"
    REJECT_RESUBMIT  = "reject_and_resubmit"
    EDITORIAL        = "editorial_request"
    ACCEPT           = "accept_with_changes"


class ReadinessLevel(str, Enum):
    READY          = "ready"
    MINOR_ISSUES   = "minor_issues"
    MAJOR_ISSUES   = "major_issues"
    NOT_READY      = "not_ready"


class RiskLevel(str, Enum):
    CRITICAL  = "critical"
    HIGH      = "high"
    MODERATE  = "moderate"
    LOW       = "low"
    MINIMAL   = "minimal"


class ExportFormat(str, Enum):
    SUBMISSION_PACKAGE   = "submission_package"
    COVER_LETTER         = "cover_letter"
    REVIEWER_RESPONSE    = "reviewer_response"
    PUBLICATION_ROADMAP  = "publication_roadmap"
    JOURNAL_COMPARISON   = "journal_comparison"
    GRANT_READINESS      = "grant_readiness"
    MARKDOWN             = "markdown"
    LATEX                = "latex"
    TEXT                 = "text"


class StrategyType(str, Enum):
    JOURNAL_FIRST     = "journal_first"
    CONFERENCE_FIRST  = "conference_first"
    PARALLEL          = "parallel"
    MULTI_PAPER       = "multi_paper"
    OPEN_ACCESS_FIRST = "open_access_first"
    TIERED            = "tiered"


# ── Journal ───────────────────────────────────────────────────────────────────

@dataclass
class JournalProfile:
    name: str = ""
    publisher: str = ""
    issn: str = ""
    quartile: str = "Q3"
    impact_factor: float = 0.0
    cite_score: float = 0.0
    snip: float = 0.0
    sjr: float = 0.0
    acceptance_rate: float = 0.30
    review_duration_weeks: int = 12
    time_to_publication_weeks: int = 20
    open_access: bool = False
    hybrid: bool = False
    apc_usd: int = 0          # Article Processing Charge
    predatory_risk: float = 0.0    # 0.0 = none, 1.0 = confirmed predatory
    tags: list[str] = field(default_factory=list)
    language: str = "English"
    reference_style: str = "APA"
    requires_data_sharing: bool = False
    ethics_statement_required: bool = True
    requires_cover_letter: bool = True
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "publisher": self.publisher,
            "quartile": self.quartile,
            "impact_factor": self.impact_factor,
            "cite_score": self.cite_score,
            "acceptance_rate": self.acceptance_rate,
            "review_duration_weeks": self.review_duration_weeks,
            "time_to_publication_weeks": self.time_to_publication_weeks,
            "open_access": self.open_access,
            "hybrid": self.hybrid,
            "apc_usd": self.apc_usd,
            "predatory_risk": round(self.predatory_risk, 2),
            "tags": self.tags,
            "language": self.language,
            "reference_style": self.reference_style,
        }


@dataclass
class JournalFitScore:
    journal: JournalProfile = field(default_factory=JournalProfile)
    scope_match: float = 0.0         # 0.0–1.0
    acceptance_probability: float = 0.0
    desk_rejection_risk: float = 0.0
    overall_fit: float = 0.0         # weighted composite
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    rationale: str = ""
    submission_notes: str = ""
    match_type: MatchType | None = None

    def to_dict(self) -> dict:
        return {
            "journal": self.journal.to_dict(),
            "scope_match": round(self.scope_match, 3),
            "acceptance_probability": round(self.acceptance_probability, 3),
            "desk_rejection_risk": round(self.desk_rejection_risk, 3),
            "overall_fit": round(self.overall_fit, 3),
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "rationale": self.rationale,
            "submission_notes": self.submission_notes,
            "match_type": self.match_type.value if self.match_type else None,
        }


@dataclass
class SmartJournalMatch:
    match_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    match_type: MatchType = MatchType.BEST
    label: str = ""
    description: str = ""
    fits: list[JournalFitScore] = field(default_factory=list)
    top_pick: JournalFitScore | None = None

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "match_type": self.match_type.value,
            "label": self.label,
            "description": self.description,
            "matches": [f.to_dict() for f in self.fits[:6]],
            "top_pick": self.top_pick.to_dict() if self.top_pick else None,
        }


# ── Conference ────────────────────────────────────────────────────────────────

@dataclass
class ConferenceFit:
    name: str = ""
    acronym: str = ""
    publisher: str = ""
    ranking: str = "B"             # A*, A, B, C
    acceptance_rate: float = 0.30
    topics: list[str] = field(default_factory=list)
    is_indexed: bool = True
    offers_journal_track: bool = False
    registration_fee_usd: int = 400
    submission_deadline: str = ""
    notification_date: str = ""
    event_date: str = ""
    location: str = ""
    presentation_types: list[str] = field(default_factory=list)

    research_fit: float = 0.0
    acceptance_probability: float = 0.0
    networking_value: float = 0.0
    career_value: float = 0.0
    publication_value: float = 0.0
    overall_score: float = 0.0
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "acronym": self.acronym,
            "ranking": self.ranking,
            "acceptance_rate": self.acceptance_rate,
            "topics": self.topics,
            "is_indexed": self.is_indexed,
            "registration_fee_usd": self.registration_fee_usd,
            "submission_deadline": self.submission_deadline,
            "research_fit": round(self.research_fit, 3),
            "acceptance_probability": round(self.acceptance_probability, 3),
            "networking_value": round(self.networking_value, 3),
            "career_value": round(self.career_value, 3),
            "publication_value": round(self.publication_value, 3),
            "overall_score": round(self.overall_score, 3),
            "rationale": self.rationale,
        }


# ── Grant ─────────────────────────────────────────────────────────────────────

@dataclass
class GrantFit:
    title: str = ""
    funder: str = ""
    amount_usd: int = 0
    deadline: str = ""
    eligibility: list[str] = field(default_factory=list)
    required_docs: list[str] = field(default_factory=list)
    evaluation_criteria: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)

    eligibility_score: float = 0.0
    topic_fit: float = 0.0
    competitiveness: float = 0.5   # 0=highly competitive, 1=attainable
    funding_probability: float = 0.0
    proposal_readiness: float = 0.0
    missing_elements: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "funder": self.funder,
            "amount_usd": self.amount_usd,
            "deadline": self.deadline,
            "eligibility_score": round(self.eligibility_score, 3),
            "topic_fit": round(self.topic_fit, 3),
            "competitiveness": round(self.competitiveness, 3),
            "funding_probability": round(self.funding_probability, 3),
            "proposal_readiness": round(self.proposal_readiness, 3),
            "missing_elements": self.missing_elements,
            "strengths": self.strengths,
            "rationale": self.rationale,
        }


# ── Submission readiness ──────────────────────────────────────────────────────

@dataclass
class ReadinessCheck:
    criterion: str = ""
    category: str = ""       # formatting, references, ethics, content, data, language
    passed: bool = False
    severity: str = "minor"  # minor | major | critical
    message: str = ""
    recommendation: str = ""

    def to_dict(self) -> dict:
        return {
            "criterion": self.criterion,
            "category": self.category,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "recommendation": self.recommendation,
        }


@dataclass
class SubmissionReadiness:
    readiness_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    manuscript_title: str = ""
    target_journal: str = ""
    level: ReadinessLevel = ReadinessLevel.MAJOR_ISSUES
    overall_score: float = 0.0
    grade: str = "C"
    checks: list[ReadinessCheck] = field(default_factory=list)
    critical_blockers: list[str] = field(default_factory=list)
    major_issues: list[str] = field(default_factory=list)
    minor_issues: list[str] = field(default_factory=list)
    passed_checks: int = 0
    total_checks: int = 0
    estimated_revision_days: int = 0
    submission_checklist: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "readiness_id": self.readiness_id,
            "manuscript_title": self.manuscript_title,
            "target_journal": self.target_journal,
            "level": self.level.value,
            "overall_score": round(self.overall_score, 1),
            "grade": self.grade,
            "checks": [c.to_dict() for c in self.checks],
            "critical_blockers": self.critical_blockers,
            "major_issues": self.major_issues,
            "minor_issues": self.minor_issues,
            "passed_checks": self.passed_checks,
            "total_checks": self.total_checks,
            "estimated_revision_days": self.estimated_revision_days,
            "submission_checklist": self.submission_checklist,
        }


# ── Cover letter ──────────────────────────────────────────────────────────────

@dataclass
class CoverLetter:
    letter_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    journal: str = ""
    editor_title: str = "Editor-in-Chief"
    manuscript_title: str = ""
    text: str = ""
    word_count: int = 0
    sections: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "letter_id": self.letter_id,
            "journal": self.journal,
            "editor_title": self.editor_title,
            "manuscript_title": self.manuscript_title,
            "text": self.text,
            "word_count": self.word_count,
            "sections": self.sections,
            "generated_at": self.generated_at.isoformat(),
        }


# ── Reviewer response ─────────────────────────────────────────────────────────

@dataclass
class ReviewerComment:
    reviewer_id: str = "Reviewer 1"
    comment_number: int = 1
    original_comment: str = ""
    response_text: str = ""
    action_taken: str = ""
    manuscript_changes: str = ""

    def to_dict(self) -> dict:
        return {
            "reviewer_id": self.reviewer_id,
            "comment_number": self.comment_number,
            "original_comment": self.original_comment[:200] if self.original_comment else "",
            "response_text": self.response_text,
            "action_taken": self.action_taken,
            "manuscript_changes": self.manuscript_changes,
        }


@dataclass
class ReviewerResponse:
    response_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    revision_type: RevisionType = RevisionType.MAJOR
    manuscript_title: str = ""
    journal: str = ""
    cover_letter: str = ""
    comments: list[ReviewerComment] = field(default_factory=list)
    general_response: str = ""
    full_text: str = ""
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "response_id": self.response_id,
            "revision_type": self.revision_type.value,
            "manuscript_title": self.manuscript_title,
            "journal": self.journal,
            "cover_letter": self.cover_letter,
            "comments": [c.to_dict() for c in self.comments],
            "general_response": self.general_response,
            "full_text": self.full_text,
            "generated_at": self.generated_at.isoformat(),
        }


# ── Publication strategy ──────────────────────────────────────────────────────

@dataclass
class StrategicOption:
    option_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    strategy_type: StrategyType = StrategyType.TIERED
    title: str = ""
    description: str = ""
    steps: list[str] = field(default_factory=list)
    estimated_weeks: int = 0
    success_probability: float = 0.5
    risks: list[str] = field(default_factory=list)
    rewards: list[str] = field(default_factory=list)
    recommended: bool = False

    def to_dict(self) -> dict:
        return {
            "option_id": self.option_id,
            "strategy_type": self.strategy_type.value,
            "title": self.title,
            "description": self.description,
            "steps": self.steps,
            "estimated_weeks": self.estimated_weeks,
            "success_probability": round(self.success_probability, 3),
            "risks": self.risks,
            "rewards": self.rewards,
            "recommended": self.recommended,
        }


@dataclass
class PublicationStrategy:
    strategy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    manuscript_title: str = ""
    options: list[StrategicOption] = field(default_factory=list)
    recommended_option: StrategicOption | None = None
    backup_journals: list[str] = field(default_factory=list)
    citation_strategy: str = ""
    career_alignment: str = ""
    timeline_summary: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "manuscript_title": self.manuscript_title,
            "options": [o.to_dict() for o in self.options],
            "recommended_option": self.recommended_option.to_dict() if self.recommended_option else None,
            "backup_journals": self.backup_journals,
            "citation_strategy": self.citation_strategy,
            "career_alignment": self.career_alignment,
            "timeline_summary": self.timeline_summary,
            "created_at": self.created_at.isoformat(),
        }


# ── Risk analysis ─────────────────────────────────────────────────────────────

@dataclass
class RiskDimension:
    dimension: str = ""
    level: RiskLevel = RiskLevel.MODERATE
    score: float = 0.5           # 0=minimal, 1=critical
    description: str = ""
    signals: list[str] = field(default_factory=list)
    mitigations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension,
            "level": self.level.value,
            "score": round(self.score, 3),
            "description": self.description,
            "signals": self.signals,
            "mitigations": self.mitigations,
        }


@dataclass
class PublicationRisk:
    risk_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    manuscript_title: str = ""
    overall_risk_score: float = 0.5
    overall_risk_level: RiskLevel = RiskLevel.MODERATE
    dimensions: list[RiskDimension] = field(default_factory=list)
    top_risks: list[str] = field(default_factory=list)
    mitigation_plan: list[str] = field(default_factory=list)
    estimated_success_probability: float = 0.5
    ai_assessment: str = ""

    def to_dict(self) -> dict:
        return {
            "risk_id": self.risk_id,
            "manuscript_title": self.manuscript_title,
            "overall_risk_score": round(self.overall_risk_score, 3),
            "overall_risk_level": self.overall_risk_level.value,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "top_risks": self.top_risks,
            "mitigation_plan": self.mitigation_plan,
            "estimated_success_probability": round(self.estimated_success_probability, 3),
            "ai_assessment": self.ai_assessment,
        }


# ── Publishing dashboard ──────────────────────────────────────────────────────

@dataclass
class PublicationDashboard:
    user_id: str = ""
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_manuscripts: int = 0
    published_count: int = 0
    under_review_count: int = 0
    revision_required_count: int = 0
    draft_count: int = 0
    manuscripts: list[dict] = field(default_factory=list)
    readiness_summary: list[dict] = field(default_factory=list)
    recommended_journals: list[dict] = field(default_factory=list)
    upcoming_deadlines: list[dict] = field(default_factory=list)
    submission_history: list[dict] = field(default_factory=list)
    citation_growth: list[dict] = field(default_factory=list)
    impact_projections: list[dict] = field(default_factory=list)
    top_recommended_actions: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "generated_at": self.generated_at.isoformat(),
            "total_manuscripts": self.total_manuscripts,
            "published_count": self.published_count,
            "under_review_count": self.under_review_count,
            "revision_required_count": self.revision_required_count,
            "draft_count": self.draft_count,
            "manuscripts": self.manuscripts,
            "readiness_summary": self.readiness_summary,
            "recommended_journals": self.recommended_journals,
            "upcoming_deadlines": self.upcoming_deadlines,
            "submission_history": self.submission_history,
            "citation_growth": self.citation_growth,
            "impact_projections": self.impact_projections,
            "top_recommended_actions": self.top_recommended_actions,
        }


def _score_to_grade(score: float) -> str:
    if score >= 93: return "A+"
    if score >= 88: return "A"
    if score >= 83: return "A-"
    if score >= 78: return "B+"
    if score >= 73: return "B"
    if score >= 68: return "B-"
    if score >= 63: return "C+"
    if score >= 58: return "C"
    if score >= 50: return "C-"
    if score >= 40: return "D"
    return "F"
