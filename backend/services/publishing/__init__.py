"""Academic Publishing Intelligence — Phase XII."""
from .engine import PublishingEngine, get_publishing_engine, reset_publishing_engine
from .models import (
    CoverLetter, ExportFormat, GrantFit, JournalFitScore, JournalProfile,
    MatchType, PublicationDashboard, PublicationRisk, PublicationStrategy,
    ReadinessLevel, RevisionType, RiskLevel, SmartJournalMatch,
    SubmissionReadiness,
)

__all__ = [
    "PublishingEngine", "get_publishing_engine", "reset_publishing_engine",
    "CoverLetter", "ExportFormat", "GrantFit", "JournalFitScore", "JournalProfile",
    "MatchType", "PublicationDashboard", "PublicationRisk", "PublicationStrategy",
    "ReadinessLevel", "RevisionType", "RiskLevel", "SmartJournalMatch",
    "SubmissionReadiness",
]
