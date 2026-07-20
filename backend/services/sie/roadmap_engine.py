"""
SIE Roadmap Engine — generates complete 18-stage research roadmaps.
No LLM required: rule-based roadmap generation from topic, questions, and timeline.
"""
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from typing import Optional

_STAGES = [
    ("topic_definition",       "Research Topic Definition",        14,  "Define the precise research topic, scope, and research questions."),
    ("literature_search",      "Literature Search",                21,  "Conduct systematic database search across Scopus, PubMed, Web of Science."),
    ("literature_review",      "Literature Review",                28,  "Synthesise existing knowledge and identify theoretical frameworks."),
    ("gap_identification",     "Research Gap Identification",      14,  "Identify specific knowledge gaps that this research will address."),
    ("methodology_design",     "Methodology Design",               21,  "Define research design, methods, instruments, and ethical approvals."),
    ("data_collection",        "Data Collection",                  30,  "Collect primary or secondary data according to the methodology."),
    ("data_analysis",          "Data Analysis",                    21,  "Apply statistical/qualitative analysis methods to the dataset."),
    ("results_interpretation", "Results & Interpretation",         14,  "Interpret findings in context of the research questions and literature."),
    ("manuscript_draft",       "Manuscript Draft",                 28,  "Write the full manuscript following target journal guidelines."),
    ("internal_review",        "Internal Review",                  14,  "Seek feedback from co-authors, mentors, and departmental colleagues."),
    ("revision_pre_submit",    "Pre-Submission Revision",          14,  "Revise manuscript based on internal feedback."),
    ("journal_selection",      "Journal Selection",                 7,  "Select target journal and 2 backup journals using Synaptiq Publishing Intelligence."),
    ("submission",             "Manuscript Submission",             3,  "Submit manuscript to the target journal via online submission system."),
    ("peer_review_wait",       "Peer Review Period",               60,  "Await peer review outcome (typically 6-12 weeks)."),
    ("revision_post_review",   "Post-Review Revision",             21,  "Address reviewer comments systematically using Synaptiq AI tools."),
    ("resubmission",           "Resubmission",                      3,  "Resubmit revised manuscript with a detailed response letter."),
    ("acceptance_proofing",    "Acceptance & Proofing",            14,  "Proof-read galley proofs and complete copyright transfer."),
    ("post_publication",       "Post-Publication Monitoring",      90,  "Monitor citations, promote via networks, and plan follow-up research."),
]


def _ser(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id", ""))
    for k, v in doc.items():
        if hasattr(v, "isoformat"):
            doc[k] = v.isoformat()
    return doc


def _build_stages(start_date: datetime, journal: str = "") -> list:
    stages = []
    current = start_date
    for key, name, days, description in _STAGES:
        end = current + timedelta(days=days)
        stages.append({
            "key": key,
            "name": name,
            "description": description,
            "estimated_days": days,
            "start_date": current.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "status": "pending",
            "completion": 0,
            "tasks": _stage_tasks(key, journal),
        })
        current = end
    return stages


def _stage_tasks(key: str, journal: str) -> list:
    task_map = {
        "literature_review": ["Search Scopus/PubMed/WoS", "Import references to Synaptiq", "Write synthesis notes"],
        "gap_identification": ["Use Synaptiq Research Gap Finder", "Map identified gaps", "Select primary gap to address"],
        "methodology_design": ["Select research design type", "Design data collection instruments", "Submit ethics application"],
        "manuscript_draft": ["Write Introduction", "Write Methods", "Write Results", "Write Discussion", "Write Abstract"],
        "journal_selection": [f"Primary target: {journal or 'TBD'}", "Select 2 backup journals", "Review submission guidelines"],
        "submission": ["Final formatting check", "Prepare cover letter", "Complete submission form"],
        "revision_post_review": ["Categorise reviewer comments", "Draft point-by-point response", "Revise manuscript"],
    }
    return task_map.get(key, [])


async def generate_roadmap(user_id: str, data: dict, db) -> dict:
    title = data.get("title", "Research Roadmap")
    topic = data.get("topic", "")
    research_questions = data.get("research_questions", [])
    journal = data.get("target_journal", "")
    start = datetime.now(timezone.utc)

    stages = _build_stages(start, journal)
    total_days = sum(s["estimated_days"] for s in stages)
    estimated_end = start + timedelta(days=total_days)

    doc = {
        "user_id": user_id,
        "title": title,
        "topic": topic,
        "research_questions": research_questions,
        "target_journal": journal,
        "backup_journals": data.get("backup_journals", []),
        "stages": stages,
        "current_stage": "topic_definition",
        "total_duration_days": total_days,
        "start_date": start.strftime("%Y-%m-%d"),
        "estimated_end_date": estimated_end.strftime("%Y-%m-%d"),
        "overall_completion": 0,
        "status": "active",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    result = await db.sie_roadmaps.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


async def get_roadmaps(user_id: str, db) -> list:
    cursor = db.sie_roadmaps.find({"user_id": user_id}).sort("created_at", -1)
    docs = await cursor.to_list(50)
    return [_ser(d) for d in docs]


async def get_roadmap(user_id: str, roadmap_id: str, db) -> Optional[dict]:
    try:
        doc = await db.sie_roadmaps.find_one({"_id": ObjectId(roadmap_id), "user_id": user_id})
    except Exception:
        return None
    return _ser(doc) if doc else None


async def advance_stage(user_id: str, roadmap_id: str, stage_key: str, completion: int, db) -> Optional[dict]:
    try:
        doc = await db.sie_roadmaps.find_one({"_id": ObjectId(roadmap_id), "user_id": user_id})
    except Exception:
        return None
    if not doc:
        return None
    stages = doc.get("stages", [])
    for s in stages:
        if s["key"] == stage_key:
            s["completion"] = max(0, min(100, completion))
            s["status"] = "completed" if completion >= 100 else ("in_progress" if completion > 0 else "pending")
    completed_stages = sum(1 for s in stages if s["status"] == "completed")
    overall = round((completed_stages / len(stages)) * 100) if stages else 0
    next_stage = next((s["key"] for s in stages if s["status"] == "pending"), stages[-1]["key"] if stages else "")
    await db.sie_roadmaps.update_one(
        {"_id": ObjectId(roadmap_id)},
        {"$set": {"stages": stages, "overall_completion": overall, "current_stage": next_stage, "updated_at": datetime.now(timezone.utc)}},
    )
    doc = await db.sie_roadmaps.find_one({"_id": ObjectId(roadmap_id)})
    return _ser(doc) if doc else None
