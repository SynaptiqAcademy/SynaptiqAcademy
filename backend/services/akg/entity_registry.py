"""Entity type registry and CRUD for the Academic Knowledge Graph."""
from __future__ import annotations
from .graph_adapter import get_adapter
from lkg.unified import get_unified_graph

# 35 entity types with metadata for rendering and grouping
ENTITY_TYPES: dict[str, dict] = {
    # People
    "researcher":         {"label": "Researcher",          "color": "#3B82F6", "group": "people"},
    "student":            {"label": "Student",             "color": "#06B6D4", "group": "people"},
    "educator":           {"label": "Educator",            "color": "#8B5CF6", "group": "people"},
    "reviewer":           {"label": "Reviewer",            "color": "#F59E0B", "group": "people"},
    "editor":             {"label": "Editor",              "color": "#EF4444", "group": "people"},
    # Institutions
    "institution":        {"label": "Institution",         "color": "#10B981", "group": "institutions"},
    "department":         {"label": "Department",          "color": "#34D399", "group": "institutions"},
    "laboratory":         {"label": "Laboratory",          "color": "#059669", "group": "institutions"},
    "research_group":     {"label": "Research Group",      "color": "#6EE7B7", "group": "institutions"},
    "funding_agency":     {"label": "Funding Agency",      "color": "#D97706", "group": "institutions"},
    # Research outputs
    "publication":        {"label": "Publication",         "color": "#EF4444", "group": "research"},
    "dataset":            {"label": "Dataset",             "color": "#F87171", "group": "research"},
    "repository":         {"label": "Repository",          "color": "#DC2626", "group": "research"},
    "patent":             {"label": "Patent",              "color": "#B91C1C", "group": "research"},
    # Funding
    "grant":              {"label": "Grant",               "color": "#F59E0B", "group": "funding"},
    # Events
    "conference":         {"label": "Conference",          "color": "#6366F1", "group": "events"},
    "journal":            {"label": "Journal",             "color": "#818CF8", "group": "events"},
    "award":              {"label": "Award",               "color": "#A78BFA", "group": "events"},
    # Knowledge
    "keyword":            {"label": "Keyword",             "color": "#64748B", "group": "knowledge"},
    "topic":              {"label": "Topic",               "color": "#475569", "group": "knowledge"},
    "research_area":      {"label": "Research Area",       "color": "#334155", "group": "knowledge"},
    "method":             {"label": "Method",              "color": "#1E293B", "group": "knowledge"},
    "software":           {"label": "Software",            "color": "#0F172A", "group": "knowledge"},
    "programming_lang":   {"label": "Programming Language","color": "#312E81", "group": "knowledge"},
    "statistical_method": {"label": "Statistical Method",  "color": "#3730A3", "group": "knowledge"},
    # Teaching
    "course":             {"label": "Course",              "color": "#0EA5E9", "group": "teaching"},
    "teaching_area":      {"label": "Teaching Area",       "color": "#38BDF8", "group": "teaching"},
    # Geography
    "country":            {"label": "Country",             "color": "#84CC16", "group": "geography"},
    "city":               {"label": "City",                "color": "#BEF264", "group": "geography"},
    # Platform
    "community":          {"label": "Community",           "color": "#FB7185", "group": "platform"},
    "marketplace_service":{"label": "Marketplace Service", "color": "#F43F5E", "group": "platform"},
    "ai_agent":           {"label": "AI Agent",            "color": "#E11D48", "group": "platform"},
    "trust_badge":        {"label": "Trust Badge",         "color": "#BE123C", "group": "platform"},
    "academic_passport":  {"label": "Academic Passport",   "color": "#9F1239", "group": "platform"},
    "publisher":          {"label": "Publisher",           "color": "#881337", "group": "platform"},
}


async def create_entity(entity_type: str, label: str, properties: dict, db) -> dict:
    if entity_type not in ENTITY_TYPES:
        return {"error": f"Unknown entity type: {entity_type}"}
    import hashlib
    entity_id = hashlib.md5(f"{entity_type}:{label.lower().strip()}".encode()).hexdigest()
    adapter = get_adapter()
    return await adapter.upsert_entity(entity_id, entity_type, label, properties, db)


async def get_entity(entity_id: str, db) -> dict | None:
    return await get_adapter().get_entity(entity_id, db)


async def delete_entity(entity_id: str, db) -> bool:
    return await get_adapter().delete_entity(entity_id, db)


async def list_entities(entity_type: str | None, page: int, limit: int, db) -> dict:
    return await get_adapter().list_entities(entity_type, page, limit, db)


async def search_entities_by_label(query: str, entity_types: list[str] | None,
                                    db, limit: int = 20) -> list:
    entity_type = entity_types[0] if entity_types and len(entity_types) == 1 else None
    docs = await get_unified_graph().search_entities(db, query, entity_type=entity_type, limit=limit)
    if entity_types and len(entity_types) > 1:
        docs = [d for d in docs if d.get("type") in entity_types or d.get("entity_type") in entity_types]
    for d in docs:
        d.pop("_id", None)
        d.setdefault("id", d.get("node_id", ""))
    return docs


async def get_entity_stats(db) -> dict:
    unified = get_unified_graph()
    by_type = await unified.group_nodes_by_type(db)
    total = sum(by_type.values())
    return {
        "total": total,
        "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
        "entity_types": ENTITY_TYPES,
    }
