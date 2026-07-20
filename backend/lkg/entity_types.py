"""
Unified Academic Entity & Relationship Registry — Sprint 1.4

Single canonical list of all entity types and relationship types used across
every graph implementation. Every graph operation imports from here.

Replaces:
  • lkg/models.py::NODE_TYPES, EDGE_TYPES
  • services/akg/entity_registry.py::ENTITY_TYPES
  • services/knowledge_graph/models.py::NodeType, RelType
"""
from __future__ import annotations

# ── Entity types (40 canonical types) ────────────────────────────────────────
# Superset of all three legacy implementations.

ENTITY_TYPES: dict[str, dict] = {
    # People
    "researcher":         {"label": "Researcher",           "color": "#3B82F6", "group": "people"},
    "student":            {"label": "Student",              "color": "#06B6D4", "group": "people"},
    "educator":           {"label": "Educator",             "color": "#8B5CF6", "group": "people"},
    "reviewer":           {"label": "Reviewer",             "color": "#F59E0B", "group": "people"},
    "editor":             {"label": "Editor",               "color": "#EF4444", "group": "people"},
    "supervisor":         {"label": "Supervisor",           "color": "#7C3AED", "group": "people"},

    # Institutions
    "institution":        {"label": "Institution",          "color": "#10B981", "group": "institutions"},
    "university":         {"label": "University",           "color": "#059669", "group": "institutions"},
    "department":         {"label": "Department",           "color": "#34D399", "group": "institutions"},
    "laboratory":         {"label": "Laboratory",           "color": "#059669", "group": "institutions"},
    "research_group":     {"label": "Research Group",       "color": "#6EE7B7", "group": "institutions"},
    "funding_agency":     {"label": "Funding Agency",       "color": "#D97706", "group": "institutions"},
    "research_center":    {"label": "Research Center",      "color": "#22C55E", "group": "institutions"},

    # Research outputs
    "publication":        {"label": "Publication",          "color": "#EF4444", "group": "research"},
    "manuscript":         {"label": "Manuscript",           "color": "#F87171", "group": "research"},
    "dataset":            {"label": "Dataset",              "color": "#DC2626", "group": "research"},
    "repository":         {"label": "Repository",           "color": "#B91C1C", "group": "research"},
    "patent":             {"label": "Patent",               "color": "#991B1B", "group": "research"},
    "project":            {"label": "Project",              "color": "#E07B23", "group": "research"},

    # Funding
    "grant":              {"label": "Grant",                "color": "#F59E0B", "group": "funding"},
    "grant_application":  {"label": "Grant Application",    "color": "#D97706", "group": "funding"},
    "funding_program":    {"label": "Funding Program",      "color": "#B45309", "group": "funding"},

    # Venues
    "conference":         {"label": "Conference",           "color": "#6366F1", "group": "venues"},
    "journal":            {"label": "Journal",              "color": "#818CF8", "group": "venues"},
    "publisher":          {"label": "Publisher",            "color": "#A78BFA", "group": "venues"},

    # Knowledge
    "keyword":            {"label": "Keyword",              "color": "#64748B", "group": "knowledge"},
    "topic":              {"label": "Topic",                "color": "#475569", "group": "knowledge"},
    "research_area":      {"label": "Research Area",        "color": "#334155", "group": "knowledge"},
    "method":             {"label": "Method",               "color": "#1E293B", "group": "knowledge"},
    "technique":          {"label": "Technique",            "color": "#0F172A", "group": "knowledge"},
    "concept":            {"label": "Concept",              "color": "#312E81", "group": "knowledge"},
    "hypothesis":         {"label": "Hypothesis",           "color": "#3730A3", "group": "knowledge"},

    # Technology
    "software":           {"label": "Software",             "color": "#0EA5E9", "group": "technology"},
    "programming_lang":   {"label": "Programming Language", "color": "#38BDF8", "group": "technology"},
    "statistical_method": {"label": "Statistical Method",   "color": "#7DD3FC", "group": "technology"},
    "ai_model":           {"label": "AI Model",             "color": "#BAE6FD", "group": "technology"},

    # Teaching
    "course":             {"label": "Course",               "color": "#84CC16", "group": "teaching"},
    "teaching_resource":  {"label": "Teaching Resource",    "color": "#BEF264", "group": "teaching"},

    # Geography & Policy
    "country":            {"label": "Country",              "color": "#22C55E", "group": "geo"},
    "organization":       {"label": "Organization",         "color": "#86EFAC", "group": "geo"},
    "policy":             {"label": "Policy",               "color": "#BBF7D0", "group": "geo"},

    # Platform
    "marketplace_service":{"label": "Marketplace Service",  "color": "#FB7185", "group": "platform"},
}

# ── Relationship types (26 canonical types) ───────────────────────────────────
# Superset of all three legacy implementations.
# Uppercase by convention (graph DB standard).

RELATIONSHIP_TYPES: dict[str, dict] = {
    "AUTHORED":           {"label": "Authored",        "group": "creation"},
    "CO_AUTHORED":        {"label": "Co-authored",     "group": "creation"},
    "CITED":              {"label": "Cited",           "group": "citation"},
    "REFERENCES":         {"label": "References",      "group": "citation"},
    "COLLABORATES_WITH":  {"label": "Collaborates",    "group": "social"},
    "MENTORS":            {"label": "Mentors",         "group": "social"},
    "SUPERVISES":         {"label": "Supervises",      "group": "social"},
    "REVIEWS":            {"label": "Reviews",         "group": "review"},
    "EDITS":              {"label": "Edits",           "group": "review"},
    "FUNDED_BY":          {"label": "Funded by",       "group": "funding"},
    "AFFILIATED_WITH":    {"label": "Affiliated with", "group": "membership"},
    "BELONGS_TO":         {"label": "Belongs to",      "group": "membership"},
    "PART_OF":            {"label": "Part of",         "group": "membership"},
    "MEMBER_OF":          {"label": "Member of",       "group": "membership"},
    "RELATED_TO":         {"label": "Related to",      "group": "semantic"},
    "BELONGS_TO_TOPIC":   {"label": "In topic",        "group": "semantic"},
    "USES_METHOD":        {"label": "Uses method",     "group": "methodology"},
    "USES_DATASET":       {"label": "Uses dataset",    "group": "methodology"},
    "SUPPORTS":           {"label": "Supports",        "group": "evidence"},
    "CONTRADICTS":        {"label": "Contradicts",     "group": "evidence"},
    "VALIDATES":          {"label": "Validates",       "group": "evidence"},
    "EXTENDS":            {"label": "Extends",         "group": "lineage"},
    "PRECEDES":           {"label": "Precedes",        "group": "lineage"},
    "CONNECTED_TO":       {"label": "Connected to",    "group": "general"},
    "PUBLISHED_IN":       {"label": "Published in",    "group": "venue"},
    "WORKS_AT":           {"label": "Works at",        "group": "employment"},
}

# ── Convenience sets ──────────────────────────────────────────────────────────

ALL_ENTITY_TYPES:       set[str] = set(ENTITY_TYPES)
ALL_RELATIONSHIP_TYPES: set[str] = set(RELATIONSHIP_TYPES)

# Legacy aliases so old code that imports from models.py still works
NODE_TYPES = list(ENTITY_TYPES)
EDGE_TYPES = list(RELATIONSHIP_TYPES)


def validate_entity_type(t: str) -> str:
    """Normalise entity type; raise ValueError if unknown."""
    t = t.lower().strip()
    if t in ENTITY_TYPES:
        return t
    raise ValueError(f"Unknown entity type '{t}'. Valid: {sorted(ENTITY_TYPES)}")


def validate_rel_type(t: str) -> str:
    """Normalise relationship type (upper); raise ValueError if unknown."""
    t = t.upper().strip()
    if t in RELATIONSHIP_TYPES:
        return t
    raise ValueError(f"Unknown relationship type '{t}'. Valid: {sorted(RELATIONSHIP_TYPES)}")
