"""
Event Registry / Catalog — centralized documentation of all domain events.

Every event type is documented with:
  - Purpose (what it means)
  - Producer (which service/module emits it)
  - Consumers (which modules subscribe)
  - Payload schema (field names + types)
  - Version (current schema version)
  - Lifecycle (stable / deprecated / experimental)

This catalog is exposed via the admin API so teams can discover events
without reading source code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .models import (
    PUBLICATION_CREATED, PUBLICATION_UPDATED, PUBLICATION_DELETED,
    PUBLICATION_SUBMITTED, PUBLICATION_PUBLISHED,
    CITATION_ADDED, CITATION_REMOVED,
    PROJECT_CREATED, PROJECT_ARCHIVED,
    WORKSPACE_CREATED, WORKSPACE_SHARED,
    MISSION_CREATED, MISSION_STARTED, MISSION_COMPLETED, MISSION_FAILED,
    MISSION_APPROVAL_NEEDED, AGENT_FINISHED,
    RECOMMENDATION_GENERATED, TWIN_UPDATED, TWIN_GOAL_REACHED,
    KNOWLEDGE_GRAPH_UPDATED, KG_NODE_ADDED, KG_EDGE_ADDED,
    ORCID_SYNCED, USER_VERIFIED, PROFILE_COMPLETED,
    GRANT_DISCOVERED, GRANT_SUBMITTED, GRANT_AWARDED,
    INSTITUTION_UPDATED, INSTITUTION_MEMBER_ADDED, INSTITUTION_MEMBER_REMOVED,
    TEACHING_ACTIVITY_CREATED, MARKETPLACE_ORDER_CREATED,
    RESEARCH_GOAL_REACHED, COLLABORATION_STARTED,
)


Lifecycle = Literal["stable", "experimental", "deprecated"]


@dataclass
class PayloadField:
    name:        str
    type:        str
    required:    bool = True
    description: str  = ""


@dataclass
class EventCatalogEntry:
    event_type:   str
    version:      int
    lifecycle:    Lifecycle
    purpose:      str
    producer:     str
    consumers:    list[str]
    payload:      list[PayloadField]   = field(default_factory=list)
    dependencies: list[str]            = field(default_factory=list)  # other event types

    def to_dict(self) -> dict:
        return {
            "event_type":   self.event_type,
            "version":      self.version,
            "lifecycle":    self.lifecycle,
            "purpose":      self.purpose,
            "producer":     self.producer,
            "consumers":    self.consumers,
            "payload":      [
                {"name": f.name, "type": f.type, "required": f.required, "description": f.description}
                for f in self.payload
            ],
            "dependencies": self.dependencies,
        }


class EventRegistry:
    """Centralized catalog of all domain events."""

    def __init__(self) -> None:
        self._entries: dict[str, EventCatalogEntry] = {}

    def register(self, entry: EventCatalogEntry) -> None:
        self._entries[entry.event_type] = entry

    def get(self, event_type: str) -> EventCatalogEntry | None:
        return self._entries.get(event_type)

    def all(self) -> list[dict]:
        return [e.to_dict() for e in self._entries.values()]

    def by_producer(self, producer: str) -> list[dict]:
        return [e.to_dict() for e in self._entries.values() if e.producer == producer]

    def by_consumer(self, consumer: str) -> list[dict]:
        return [e.to_dict() for e in self._entries.values() if consumer in e.consumers]

    def stable(self) -> list[dict]:
        return [e.to_dict() for e in self._entries.values() if e.lifecycle == "stable"]


# ── Build the catalog ─────────────────────────────────────────────────────────

def _build_catalog() -> EventRegistry:
    reg = EventRegistry()

    # ── Publications ──────────────────────────────────────────────────────────
    for etype, purpose in [
        (PUBLICATION_CREATED,   "A new publication record has been added to the system"),
        (PUBLICATION_UPDATED,   "An existing publication has been modified"),
        (PUBLICATION_DELETED,   "A publication has been soft-deleted"),
        (PUBLICATION_SUBMITTED, "A manuscript has been submitted for external review"),
        (PUBLICATION_PUBLISHED, "A paper has been formally published (DOI assigned)"),
    ]:
        reg.register(EventCatalogEntry(
            event_type=etype, version=1, lifecycle="stable",
            purpose=purpose, producer="publications_service",
            consumers=["knowledge_graph", "twin", "recommendations", "notifications",
                       "reputation", "institution_intelligence"],
            payload=[
                PayloadField("title", "str"),
                PayloadField("status", "str"),
                PayloadField("journal", "str", required=False),
                PayloadField("doi", "str", required=False),
            ],
        ))

    # ── Citations ─────────────────────────────────────────────────────────────
    for etype, purpose in [
        (CITATION_ADDED,   "A citation to a publication was recorded"),
        (CITATION_REMOVED, "A citation was removed or corrected"),
    ]:
        reg.register(EventCatalogEntry(
            event_type=etype, version=1, lifecycle="stable",
            purpose=purpose, producer="citations_service",
            consumers=["reputation", "knowledge_graph", "analytics", "twin"],
            payload=[
                PayloadField("publication_id", "str"),
                PayloadField("citing_paper", "str"),
                PayloadField("citation_count", "int"),
            ],
        ))

    # ── Workspaces / Projects ─────────────────────────────────────────────────
    for etype, producer, consumers, purpose in [
        (PROJECT_CREATED,   "projects_service",   ["knowledge_graph", "twin"], "New research project created"),
        (PROJECT_ARCHIVED,  "projects_service",   ["knowledge_graph", "twin"], "Research project archived"),
        (WORKSPACE_CREATED, "workspaces_service", ["knowledge_graph"],         "Research workspace created"),
        (WORKSPACE_SHARED,  "workspaces_service", ["notifications"],           "Workspace shared with collaborator"),
    ]:
        reg.register(EventCatalogEntry(
            event_type=etype, version=1, lifecycle="stable",
            purpose=purpose, producer=producer, consumers=consumers,
            payload=[PayloadField("name", "str"), PayloadField("description", "str", required=False)],
        ))

    # ── Missions ──────────────────────────────────────────────────────────────
    for etype, purpose in [
        (MISSION_CREATED,         "Autonomous research mission was created"),
        (MISSION_STARTED,         "Mission execution began"),
        (MISSION_COMPLETED,       "All mission steps completed successfully"),
        (MISSION_FAILED,          "Mission execution failed after retries exhausted"),
        (MISSION_APPROVAL_NEEDED, "Mission reached a human approval gate"),
    ]:
        reg.register(EventCatalogEntry(
            event_type=etype, version=1, lifecycle="stable",
            purpose=purpose, producer="ara_service",
            consumers=["notifications", "twin", "recommendations", "dashboard", "analytics"],
            payload=[
                PayloadField("mission_id", "str"),
                PayloadField("title", "str"),
                PayloadField("agent_types", "list[str]"),
            ],
        ))

    reg.register(EventCatalogEntry(
        event_type=AGENT_FINISHED, version=1, lifecycle="stable",
        purpose="An individual agent completed its assigned step",
        producer="ara_service",
        consumers=["analytics", "twin"],
        payload=[
            PayloadField("agent_type", "str"),
            PayloadField("step_id", "str"),
            PayloadField("output_summary", "str", required=False),
        ],
    ))

    # ── AI / Recommendations ──────────────────────────────────────────────────
    reg.register(EventCatalogEntry(
        event_type=RECOMMENDATION_GENERATED, version=1, lifecycle="stable",
        purpose="Proactive recommendation was generated for a user",
        producer="recommendation_engine",
        consumers=["notifications", "dashboard"],
        payload=[
            PayloadField("category", "str"),
            PayloadField("confidence", "str"),
            PayloadField("evidence_count", "int"),
        ],
    ))

    # ── Twin ──────────────────────────────────────────────────────────────────
    for etype, purpose in [
        (TWIN_UPDATED,     "Digital research twin profile was updated with new activity"),
        (TWIN_GOAL_REACHED,"A research goal defined in the twin has been achieved"),
    ]:
        reg.register(EventCatalogEntry(
            event_type=etype, version=1, lifecycle="stable",
            purpose=purpose, producer="twin_service",
            consumers=["recommendations", "notifications", "dashboard"],
            payload=[PayloadField("updated_dimensions", "list[str]", required=False)],
        ))

    # ── Knowledge Graph ───────────────────────────────────────────────────────
    for etype, purpose in [
        (KNOWLEDGE_GRAPH_UPDATED, "Knowledge graph was updated with new nodes or edges"),
        (KG_NODE_ADDED,           "A new node was added to the knowledge graph"),
        (KG_EDGE_ADDED,           "A new relationship was added to the knowledge graph"),
    ]:
        reg.register(EventCatalogEntry(
            event_type=etype, version=1, lifecycle="stable",
            purpose=purpose, producer="lkg_service",
            consumers=["twin", "recommendations", "analytics"],
            payload=[
                PayloadField("node_type", "str", required=False),
                PayloadField("label", "str", required=False),
            ],
        ))

    # ── Identity ──────────────────────────────────────────────────────────────
    for etype, purpose in [
        (ORCID_SYNCED,      "ORCID profile was synced for a researcher"),
        (USER_VERIFIED,     "Researcher identity was verified"),
        (PROFILE_COMPLETED, "User profile reached 100% completion"),
    ]:
        reg.register(EventCatalogEntry(
            event_type=etype, version=1, lifecycle="stable",
            purpose=purpose, producer="identity_service",
            consumers=["reputation", "notifications", "knowledge_graph", "twin"],
            payload=[PayloadField("verification_level", "str", required=False)],
        ))

    # ── Grants ────────────────────────────────────────────────────────────────
    for etype, purpose in [
        (GRANT_DISCOVERED, "A new relevant grant opportunity was discovered"),
        (GRANT_SUBMITTED,  "A grant application was submitted"),
        (GRANT_AWARDED,    "A grant was formally awarded"),
    ]:
        reg.register(EventCatalogEntry(
            event_type=etype, version=1, lifecycle="stable",
            purpose=purpose, producer="grant_service",
            consumers=["notifications", "twin", "reputation", "institution_intelligence"],
            payload=[
                PayloadField("grant_title", "str"),
                PayloadField("funder", "str", required=False),
                PayloadField("amount", "float", required=False),
            ],
        ))

    # ── Institution ───────────────────────────────────────────────────────────
    for etype, purpose in [
        (INSTITUTION_UPDATED,        "Institution profile or metadata was updated"),
        (INSTITUTION_MEMBER_ADDED,   "A researcher joined an institution"),
        (INSTITUTION_MEMBER_REMOVED, "A researcher left an institution"),
    ]:
        reg.register(EventCatalogEntry(
            event_type=etype, version=1, lifecycle="stable",
            purpose=purpose, producer="institution_service",
            consumers=["institution_intelligence", "analytics"],
            payload=[PayloadField("institution_name", "str")],
        ))

    # ── Teaching ──────────────────────────────────────────────────────────────
    reg.register(EventCatalogEntry(
        event_type=TEACHING_ACTIVITY_CREATED, version=1, lifecycle="stable",
        purpose="A teaching activity (lecture, tutorial, workshop) was recorded",
        producer="teaching_service",
        consumers=["reputation", "twin", "analytics"],
        payload=[
            PayloadField("activity_type", "str"),
            PayloadField("title", "str"),
        ],
    ))

    # ── Marketplace ───────────────────────────────────────────────────────────
    reg.register(EventCatalogEntry(
        event_type=MARKETPLACE_ORDER_CREATED, version=1, lifecycle="stable",
        purpose="An order for academic services was placed in the marketplace",
        producer="marketplace_service",
        consumers=["notifications", "billing", "analytics"],
        payload=[
            PayloadField("service_type", "str"),
            PayloadField("amount", "float"),
        ],
    ))

    # ── Research ──────────────────────────────────────────────────────────────
    for etype, purpose, consumers in [
        (RESEARCH_GOAL_REACHED,  "A defined research goal was reached",  ["notifications", "twin", "reputation"]),
        (COLLABORATION_STARTED,  "A research collaboration was initiated", ["notifications", "knowledge_graph"]),
    ]:
        reg.register(EventCatalogEntry(
            event_type=etype, version=1, lifecycle="stable",
            purpose=purpose, producer="research_service", consumers=consumers,
            payload=[PayloadField("goal_type", "str", required=False)],
        ))

    return reg


# Module-level singleton
catalog: EventRegistry = _build_catalog()
