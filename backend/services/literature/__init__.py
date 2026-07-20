"""Literature Intelligence Engine — Phase VII academic literature analysis platform."""
from services.literature.engine import LiteratureIntelligenceEngine, get_literature_engine
from services.literature.models import ReviewSession, ReviewType, Paper, PaperSource

__all__ = [
    "LiteratureIntelligenceEngine",
    "get_literature_engine",
    "ReviewSession",
    "ReviewType",
    "Paper",
    "PaperSource",
]
