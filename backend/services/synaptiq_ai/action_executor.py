"""Action Executor — execute platform actions on behalf of the user via AI suggestions."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from bson import ObjectId

logger = logging.getLogger("synaptiq.ai.action_executor")

AVAILABLE_ACTIONS: dict[str, dict] = {
    "create_project": {
        "label": "Create Project",
        "description": "Create a new research project",
        "required_fields": ["title"],
        "optional_fields": ["description", "visibility"],
    },
    "create_collaboration": {
        "label": "Create Collaboration",
        "description": "Create a new collaboration opportunity",
        "required_fields": ["title"],
        "optional_fields": ["collab_type", "research_area", "skills_needed"],
    },
    "create_manuscript": {
        "label": "Create Manuscript",
        "description": "Start a new manuscript",
        "required_fields": ["title"],
        "optional_fields": ["manuscript_type"],
    },
    "save_memory": {
        "label": "Save to Memory",
        "description": "Save this to your AI memory",
        "required_fields": ["memory_type", "content"],
        "optional_fields": [],
    },
    "generate_task_list": {
        "label": "Generate Task List",
        "description": "Generate a structured task list from this plan",
        "required_fields": ["plan_text"],
        "optional_fields": [],
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def execute_action(
    user_id: str,
    action_type: str,
    params: dict,
    db,
) -> dict:
    """
    Execute a platform action on behalf of the user.

    Returns:
    {
      "success": bool,
      "action_type": str,
      "result": dict,
      "message": str,
    }
    """
    if action_type not in AVAILABLE_ACTIONS:
        return {
            "success": False,
            "action_type": action_type,
            "result": {},
            "message": f"Unknown action type: {action_type!r}",
        }

    try:
        if action_type == "create_project":
            return await _create_project(user_id, params, db)
        if action_type == "create_collaboration":
            return await _create_collaboration(user_id, params, db)
        if action_type == "create_manuscript":
            return await _create_manuscript(user_id, params, db)
        if action_type == "save_memory":
            return await _save_memory_action(user_id, params, db)
        if action_type == "generate_task_list":
            return await _generate_task_list(user_id, params, db)
    except Exception as exc:
        logger.error("execute_action failed user=%s action=%s err=%s", user_id, action_type, exc)
        return {
            "success": False,
            "action_type": action_type,
            "result": {},
            "message": f"Action failed: {str(exc)[:200]}",
        }

    return {
        "success": False,
        "action_type": action_type,
        "result": {},
        "message": "Action not implemented",
    }


async def _create_project(user_id: str, params: dict, db) -> dict:
    title = (params.get("title") or "").strip()
    if not title:
        return {
            "success": False,
            "action_type": "create_project",
            "result": {},
            "message": "Project title is required.",
        }

    now = _now_iso()
    doc = {
        "title": title,
        "description": (params.get("description") or "").strip(),
        "visibility": params.get("visibility") or "private",
        "owner_id": user_id,
        "members": [user_id],
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "created_by_ai": True,
    }
    result = await db.projects.insert_one(doc)
    project_id = str(result.inserted_id)

    return {
        "success": True,
        "action_type": "create_project",
        "result": {"id": project_id, "title": title},
        "message": f"Project \"{title}\" created successfully.",
    }


async def _create_collaboration(user_id: str, params: dict, db) -> dict:
    title = (params.get("title") or "").strip()
    if not title:
        return {
            "success": False,
            "action_type": "create_collaboration",
            "result": {},
            "message": "Collaboration title is required.",
        }

    skills_needed = params.get("skills_needed")
    if isinstance(skills_needed, str):
        skills_needed = [s.strip() for s in skills_needed.split(",") if s.strip()]
    elif not isinstance(skills_needed, list):
        skills_needed = []

    now = _now_iso()
    doc = {
        "title": title,
        "collab_type": params.get("collab_type") or "research",
        "research_area": (params.get("research_area") or "").strip(),
        "skills_needed": skills_needed,
        "creator_id": user_id,
        "members": [user_id],
        "status": "open",
        "created_at": now,
        "updated_at": now,
        "created_by_ai": True,
    }
    result = await db.collaborations.insert_one(doc)
    collab_id = str(result.inserted_id)

    return {
        "success": True,
        "action_type": "create_collaboration",
        "result": {"id": collab_id, "title": title},
        "message": f"Collaboration \"{title}\" created successfully.",
    }


async def _create_manuscript(user_id: str, params: dict, db) -> dict:
    title = (params.get("title") or "").strip()
    if not title:
        return {
            "success": False,
            "action_type": "create_manuscript",
            "result": {},
            "message": "Manuscript title is required.",
        }

    now = _now_iso()
    doc = {
        "title": title,
        "manuscript_type": params.get("manuscript_type") or "article",
        "lead_author_id": user_id,
        "authors": [user_id],
        "status": "draft",
        "sections": {
            "title": title,
            "abstract": "",
            "introduction": "",
            "literature_review": "",
            "methodology": "",
            "results": "",
            "discussion": "",
            "conclusion": "",
            "references": "",
        },
        "keywords": [],
        "created_at": now,
        "updated_at": now,
        "created_by_ai": True,
    }
    result = await db.manuscripts.insert_one(doc)
    manuscript_id = str(result.inserted_id)

    return {
        "success": True,
        "action_type": "create_manuscript",
        "result": {"id": manuscript_id, "title": title},
        "message": f"Manuscript \"{title}\" created successfully as a draft.",
    }


async def _save_memory_action(user_id: str, params: dict, db) -> dict:
    memory_type = (params.get("memory_type") or "general").strip()
    content = (params.get("content") or "").strip()
    if not content:
        return {
            "success": False,
            "action_type": "save_memory",
            "result": {},
            "message": "Memory content is required.",
        }

    from services.synaptiq_ai.memory_service import save_memory, VALID_MEMORY_TYPES
    if memory_type not in VALID_MEMORY_TYPES:
        memory_type = "general"

    saved = await save_memory(user_id, memory_type, content, db)
    if "error" in saved:
        return {
            "success": False,
            "action_type": "save_memory",
            "result": {},
            "message": f"Failed to save memory: {saved['error']}",
        }

    return {
        "success": True,
        "action_type": "save_memory",
        "result": saved,
        "message": "Memory item saved successfully.",
    }


async def _generate_task_list(user_id: str, params: dict, db) -> dict:
    plan_text = (params.get("plan_text") or "").strip()
    if not plan_text:
        return {
            "success": False,
            "action_type": "generate_task_list",
            "result": {},
            "message": "Plan text is required to generate a task list.",
        }

    # Parse lines containing task-like content: bullets, numbered items, action verbs
    import re
    task_patterns = [
        re.compile(r"^\s*[\-\*\•]\s+(.+)"),         # bullet point
        re.compile(r"^\s*\d+[\.\)]\s+(.+)"),         # numbered
        re.compile(r"^\s*\[[\s\-]\]\s+(.+)"),        # checkbox
    ]

    tasks: list[dict] = []
    for line in plan_text.splitlines():
        line = line.strip()
        if not line:
            continue
        for pat in task_patterns:
            m = pat.match(line)
            if m:
                task_text = m.group(1).strip()
                if len(task_text) > 3:
                    tasks.append({
                        "title": task_text[:200],
                        "status": "pending",
                        "created_by_ai": True,
                    })
                break

    # If no structured items found, split by sentences
    if not tasks:
        sentences = re.split(r"(?<=[.!?])\s+", plan_text)
        for sent in sentences[:10]:
            sent = sent.strip()
            if len(sent) > 10:
                tasks.append({
                    "title": sent[:200],
                    "status": "pending",
                    "created_by_ai": True,
                })

    now = _now_iso()
    task_list_doc = {
        "user_id": user_id,
        "tasks": tasks,
        "source": "ai_generated",
        "created_at": now,
    }
    result = await db.ai_task_lists.insert_one(task_list_doc)
    task_list_id = str(result.inserted_id)

    return {
        "success": True,
        "action_type": "generate_task_list",
        "result": {
            "id": task_list_id,
            "task_count": len(tasks),
            "tasks": tasks,
        },
        "message": f"Generated {len(tasks)} tasks from your plan.",
    }


async def log_action(
    user_id: str,
    conv_id: str,
    action_type: str,
    params: dict,
    result: dict,
    db,
) -> str:
    """Log action to ai_actions collection. Returns action_id."""
    try:
        doc = {
            "user_id": user_id,
            "conv_id": conv_id,
            "action_type": action_type,
            "params": params,
            "result": result,
            "success": result.get("success", False),
            "created_at": _now_iso(),
        }
        insert_result = await db.ai_actions.insert_one(doc)
        return str(insert_result.inserted_id)
    except Exception as exc:
        logger.error("log_action failed user=%s action=%s err=%s", user_id, action_type, exc)
        return ""
