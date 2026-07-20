"""Academic Intelligence Engine — the permanent reasoning layer for all academic features."""
from services.academic.engine import AcademicIntelligenceEngine, get_academic_engine
from services.academic.models import AcademicContext, AcademicAnalysis, QualityScore

__all__ = [
    "AcademicIntelligenceEngine",
    "get_academic_engine",
    "AcademicContext",
    "AcademicAnalysis",
    "QualityScore",
]
