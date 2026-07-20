"""Research Gap Intelligence Engine — Phase VIII."""
from services.research_gap.engine import GapIntelligenceEngine, get_gap_engine
from services.research_gap.models import (
    GapAnalysisResult, GapIntelligenceRequest, DetectedGap,
    GapType, AnalysisDepth, ExportFormat,
)

__all__ = [
    "GapIntelligenceEngine",
    "get_gap_engine",
    "GapAnalysisResult",
    "GapIntelligenceRequest",
    "DetectedGap",
    "GapType",
    "AnalysisDepth",
    "ExportFormat",
]
