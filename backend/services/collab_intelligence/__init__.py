"""Research Collaboration Intelligence Engine — Phase XIV."""
from .engine import CollabIntelligenceEngine, get_collab_engine, reset_collab_engine
from .models import (
    CareerStage, CollabInsight, CollabMatch, CollabOpportunity, CollabPrediction,
    CollabType, CompetencyGraph, OpportunityType, Recommendation,
    ResearcherProfile, ResearchNetwork, SmartIntroduction, TeamComposition,
    TeamSimulation, TeamType, VisualizationData, VisualizationType,
)
from .researcher_profiler import build_researcher_profile

__all__ = [
    "CollabIntelligenceEngine", "get_collab_engine", "reset_collab_engine",
    "build_researcher_profile",
    "CareerStage", "CollabInsight", "CollabMatch", "CollabOpportunity",
    "CollabPrediction", "CollabType", "CompetencyGraph", "OpportunityType",
    "Recommendation", "ResearcherProfile", "ResearchNetwork", "SmartIntroduction",
    "TeamComposition", "TeamSimulation", "TeamType", "VisualizationData",
    "VisualizationType",
]
