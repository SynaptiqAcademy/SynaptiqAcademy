"""Node types, edge types, and dataclass definitions for the Living Knowledge Graph."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Optional

# ── Entity types ───────────────────────────────────────────────────────────────
# Every distinct "thing" in the academic ecosystem becomes a first-class node.

NODE_TYPES: list[str] = [
    "researcher", "institution", "department", "project", "publication",
    "manuscript", "dataset", "funding_program", "grant_application",
    "conference", "journal", "publisher", "reviewer", "editor",
    "university", "research_group", "topic", "keyword", "method",
    "technique", "disease", "technology", "software", "language",
    "country", "organization", "teaching_resource", "course",
    "lesson", "service", "repository", "patent", "policy",
]

# ── Relationship types ─────────────────────────────────────────────────────────

EDGE_TYPES: list[str] = [
    "AUTHORED", "CITED", "CO_AUTHORED", "AFFILIATED_WITH", "FUNDED_BY",
    "COLLABORATES_WITH", "REVIEWS", "EDITS", "SUPERVISES", "MENTORS",
    "USES_METHOD", "USES_DATASET", "BELONGS_TO_TOPIC", "RELATED_TO",
    "PRECEDES", "EXTENDS", "CONTRADICTS", "SUPPORTS", "VALIDATES",
    "REFERENCES", "PART_OF", "CONNECTED_TO",
]

# ── Status labels — users must always distinguish these ───────────────────────
EdgeStatus = Literal["verified", "inferred", "predicted", "observed"]

# ── Node ID helpers ───────────────────────────────────────────────────────────

def make_node_id(node_type: str, source: str, identifier: str) -> str:
    """Build a stable, globally unique node identifier.

    Format: {type}:{source}:{identifier}
    Examples:
      researcher:platform:507f1f77bcf86cd799439011
      publication:doi:10.1038/s41586-021-03819-2
      institution:ror:03vek6s52
      topic:keyword:machine-learning
    """
    safe_id = identifier.lower().strip().replace(" ", "-")[:120]
    return f"{node_type}:{source}:{safe_id}"


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class LKGNode:
    node_id:      str
    type:         str
    label:        str
    metadata:     dict = field(default_factory=dict)
    source:       str  = "synaptiq_platform"
    confidence:   Literal["high", "medium", "low"] = "medium"
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version:      int  = 1

    def to_doc(self) -> dict:
        return {
            "node_id":      self.node_id,
            "type":         self.type,
            "label":        self.label,
            "metadata":     self.metadata,
            "source":       self.source,
            "confidence":   self.confidence,
            "last_updated": self.last_updated,
            "version":      self.version,
        }


@dataclass
class LKGEdge:
    from_id:        str
    to_id:          str
    type:           str
    source:         str   = "synaptiq_platform"
    confidence:     Literal["high", "medium", "low"] = "medium"
    weight:         float = 1.0
    evidence:       dict  = field(default_factory=dict)
    status:         EdgeStatus = "verified"
    created_at:     datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    temporal_start: Optional[datetime] = None
    temporal_end:   Optional[datetime] = None

    def to_doc(self) -> dict:
        return {
            "from_id":        self.from_id,
            "to_id":          self.to_id,
            "type":           self.type,
            "source":         self.source,
            "confidence":     self.confidence,
            "weight":         self.weight,
            "evidence":       self.evidence,
            "status":         self.status,
            "created_at":     self.created_at,
            "temporal_start": self.temporal_start,
            "temporal_end":   self.temporal_end,
        }


# ── Node type display metadata ─────────────────────────────────────────────────

NODE_META: dict[str, dict] = {
    "researcher":        {"color": "#1D4ED8", "bg": "#EFF6FF",  "radius": 22},
    "institution":       {"color": "#0F2847", "bg": "#F0F4FF",  "radius": 20},
    "publication":       {"color": "#7C3AED", "bg": "#F5F3FF",  "radius": 16},
    "manuscript":        {"color": "#6D28D9", "bg": "#F5F3FF",  "radius": 16},
    "journal":           {"color": "#DB2777", "bg": "#FDF2F8",  "radius": 15},
    "grant_application": {"color": "#D97706", "bg": "#FFFBEB",  "radius": 14},
    "funding_program":   {"color": "#B45309", "bg": "#FFFBEB",  "radius": 14},
    "topic":             {"color": "#047857", "bg": "#F0FDF4",  "radius": 14},
    "keyword":           {"color": "#059669", "bg": "#ECFDF5",  "radius": 12},
    "conference":        {"color": "#0891B2", "bg": "#ECFEFF",  "radius": 14},
    "dataset":           {"color": "#DC2626", "bg": "#FEF2F2",  "radius": 13},
    "project":           {"color": "#475569", "bg": "#F8FAFC",  "radius": 15},
    "method":            {"color": "#374151", "bg": "#F9FAFB",  "radius": 12},
    "technology":        {"color": "#0284C7", "bg": "#F0F9FF",  "radius": 13},
    "department":        {"color": "#4338CA", "bg": "#EEF2FF",  "radius": 14},
    "default":           {"color": "#64748B", "bg": "#F8FAFC",  "radius": 12},
}

EDGE_COLORS: dict[str, str] = {
    "AUTHORED":          "#1D4ED8",
    "CITED":             "#7C3AED",
    "CO_AUTHORED":       "#047857",
    "AFFILIATED_WITH":   "#0F2847",
    "FUNDED_BY":         "#D97706",
    "COLLABORATES_WITH": "#0891B2",
    "REVIEWS":           "#6D28D9",
    "BELONGS_TO_TOPIC":  "#059669",
    "RELATED_TO":        "#94A3B8",
    "default":           "#CBD5E1",
}
