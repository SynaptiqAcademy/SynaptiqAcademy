"""Data models for the Digital Research Twin."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional


# ── Enums ─────────────────────────────────────────────────────────────────────

class CareerStage(str, Enum):
    STUDENT         = "student"
    PHD             = "phd"
    POSTDOC         = "postdoc"
    ASSISTANT_PROF  = "assistant_professor"
    ASSOCIATE_PROF  = "associate_professor"
    FULL_PROF       = "full_professor"
    EMERITUS        = "emeritus"
    INDUSTRY        = "industry_researcher"
    INDEPENDENT     = "independent_researcher"
    UNKNOWN         = "unknown"


class GoalCategory(str, Enum):
    PUBLICATION   = "publication"
    GRANT         = "grant"
    COLLABORATION = "collaboration"
    CAREER        = "career"
    TEACHING      = "teaching"
    CITATION      = "citation"
    NETWORK       = "network"
    OTHER         = "other"


class GoalStatus(str, Enum):
    ACTIVE    = "active"
    COMPLETED = "completed"
    PAUSED    = "paused"
    ABANDONED = "abandoned"


class EvidenceLevel(str, Enum):
    HIGH        = "high"    # 3+ verified data points
    MEDIUM      = "medium"  # 2 verified data points
    LOW         = "low"     # 1 verified data point
    INSUFFICIENT = "insufficient"  # no verified data


# ── Evidence unit ──────────────────────────────────────────────────────────────

@dataclass
class TwinEvidence:
    source:      str           # "Synaptiq manuscripts DB", "ORCID", "OpenAlex", etc.
    detail:      str           # What specifically was observed
    count:       int = 1       # Number of data points from this source
    verified:    bool = True
    observed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "source":      self.source,
            "detail":      self.detail,
            "count":       self.count,
            "verified":    self.verified,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
        }


# ── Derived insight ────────────────────────────────────────────────────────────

@dataclass
class TwinInsight:
    id:               str
    category:         str           # "profile", "working_style", "health", "recommendation"
    title:            str
    text:             str
    evidence:         list[TwinEvidence]
    confidence:       EvidenceLevel
    confidence_basis: str
    data_sources:     list[str]
    generated_at:     datetime
    last_updated:     datetime
    methodology:      str           # How this was derived
    user_correctable: bool = True

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "category":         self.category,
            "title":            self.title,
            "text":             self.text,
            "evidence":         [e.to_dict() for e in self.evidence],
            "confidence":       self.confidence.value,
            "confidence_basis": self.confidence_basis,
            "data_sources":     self.data_sources,
            "generated_at":     self.generated_at.isoformat(),
            "last_updated":     self.last_updated.isoformat(),
            "methodology":      self.methodology,
            "user_correctable": self.user_correctable,
        }


def confidence_from_evidence(evidence: list[TwinEvidence]) -> tuple[EvidenceLevel, str]:
    """Derive confidence from count of verified evidence — no percentages ever."""
    total = sum(e.count for e in evidence if e.verified)
    if total == 0:
        return EvidenceLevel.INSUFFICIENT, "No verified data points available"
    if total == 1:
        return EvidenceLevel.LOW, "Based on 1 verified data point"
    if total == 2:
        return EvidenceLevel.MEDIUM, "Based on 2 verified data points"
    return EvidenceLevel.HIGH, f"Based on {total} verified data points across {len(evidence)} source(s)"


# ── Domain/Interest entry ──────────────────────────────────────────────────────

@dataclass
class ResearchDomainEntry:
    domain:       str
    evidence:     list[TwinEvidence]
    confidence:   EvidenceLevel
    first_seen:   Optional[datetime] = None
    last_active:  Optional[datetime] = None

    def to_dict(self) -> dict:
        c, cb = confidence_from_evidence(self.evidence)
        return {
            "domain":       self.domain,
            "evidence":     [e.to_dict() for e in self.evidence],
            "confidence":   c.value,
            "confidence_basis": cb,
            "first_seen":   self.first_seen.isoformat() if self.first_seen else None,
            "last_active":  self.last_active.isoformat() if self.last_active else None,
        }


# ── Working style observation ──────────────────────────────────────────────────

@dataclass
class WorkingStyleObservation:
    pattern:       str   # e.g., "Publishes manuscripts with quantitative methods"
    observed_count: int  # How many times this was observed
    evidence:      list[TwinEvidence]
    first_observed: Optional[datetime] = None
    last_observed:  Optional[datetime] = None

    def to_dict(self) -> dict:
        c, cb = confidence_from_evidence(self.evidence)
        return {
            "pattern":          self.pattern,
            "observed_count":   self.observed_count,
            "confidence":       c.value,
            "confidence_basis": cb,
            "evidence":         [e.to_dict() for e in self.evidence],
            "first_observed":   self.first_observed.isoformat() if self.first_observed else None,
            "last_observed":    self.last_observed.isoformat() if self.last_observed else None,
        }
