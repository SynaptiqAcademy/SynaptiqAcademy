"""
Digital Research Twin — Phase XXXIII.

A continuously evolving model of a researcher's academic identity, behaviour,
expertise, productivity, goals, and working patterns.

Non-negotiable constraints:
  - Private by default (GDPR-compliant)
  - All derived data traces to verified evidence
  - No fabricated stats, probabilities, or predictions
  - Never replaces researcher judgment
  - User can view, correct, exclude, disable, or delete at any time

MongoDB collections:
  digital_twins   — one document per user (derived intelligence, not raw data)
  twin_goals      — user-defined goals + progress
  twin_events     — incremental event log (what updated the twin)

Extends the existing user model. Does NOT duplicate profile fields.
"""
from . import (
    models,
    twin_store,
    profile_builder,
    working_style,
    goal_tracker,
    health_engine,
    simulation_engine,
    event_processor,
    recommendation_engine,
    temporal_engine,
    explainability,
)

__all__ = [
    "models", "twin_store", "profile_builder", "working_style",
    "goal_tracker", "health_engine", "simulation_engine", "event_processor",
    "recommendation_engine", "temporal_engine", "explainability",
]
