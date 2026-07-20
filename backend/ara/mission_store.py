"""
MongoDB persistence for the Autonomous Research Agent system.

Collections:
  ara_missions   — mission documents
  ara_steps      — steps per mission
  ara_approvals  — approval requests
  ara_logs       — append-only audit log
  ara_schedules  — recurring schedule templates
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId

logger = logging.getLogger("ara.store")

_M  = "ara_missions"
_S  = "ara_steps"
_A  = "ara_approvals"
_L  = "ara_logs"
_SC = "ara_schedules"
_CK = "ara_checkpoints"
_EV = "ara_events"
_TL = "ara_timeline"
_LK = "ara_locks"


# ── Indexes ───────────────────────────────────────────────────────────────────

async def ensure_indexes(db) -> None:
    await db[_M].create_index("user_id")
    await db[_M].create_index([("user_id", 1), ("status", 1)])
    await db[_M].create_index([("status", 1), ("heartbeat", 1)])   # recovery queries
    await db[_M].create_index([("status", 1), ("queued_at", 1)])   # stuck-queued queries
    await db[_S].create_index("mission_id")
    await db[_A].create_index("mission_id")
    await db[_A].create_index([("user_id", 1), ("status", 1)])
    await db[_L].create_index("mission_id")
    await db[_L].create_index([("mission_id", 1), ("created_at", -1)])
    await db[_SC].create_index("user_id")
    await db[_SC].create_index([("active", 1), ("next_run_at", 1)])  # scheduler
    await db[_CK].create_index([("mission_id", 1), ("step_id", 1)], unique=True)
    await db[_EV].create_index("mission_id")
    await db[_EV].create_index([("type", 1), ("timestamp", -1)])
    await db[_TL].create_index("mission_id")
    await db[_LK].create_index("mission_id", unique=True)
    await db[_LK].create_index("expires_at", expireAfterSeconds=0)  # MongoDB TTL


# ── Missions ──────────────────────────────────────────────────────────────────

async def create_mission(db, user_id: str, title: str, description: str,
                         autonomy_level: int, mission_type: str = "general",
                         params: dict | None = None) -> str:
    now    = datetime.now(timezone.utc)
    doc    = {
        # Core fields (unchanged)
        "user_id":        user_id,
        "title":          title,
        "description":    description,
        "mission_type":   mission_type,
        "autonomy_level": autonomy_level,
        "params":         params or {},
        "status":         "draft",
        "plan":           [],
        "agents_used":    [],
        "total_steps":    0,
        "completed_steps": 0,
        "created_at":     now,
        "updated_at":     now,
        "started_at":     None,
        "completed_at":   None,
        "error":          None,
        "result_summary": None,
        "report":         None,
        "validation":     None,
        "estimated_credits": 0,
        "used_credits":   0,
        # Enterprise execution fields (Phase XXXV.2)
        "priority":           5,      # MissionPriority.NORMAL
        "worker_id":          None,   # ID of the worker currently executing
        "execution_token":    None,   # UUID for this execution attempt
        "heartbeat":          None,   # last heartbeat from running worker
        "retry_count":        0,      # number of retries attempted
        "max_retries":        3,
        "last_error":         None,
        "checkpoint_step":    None,   # last successfully checkpointed step_id
        "queued_at":          None,   # when the mission entered the queue
        "execution_history":  [],     # immutable log of execution attempts
        "scheduler_id":       None,   # which schedule created this mission
        "run_after":          None,   # earliest execution time (for delayed missions)
    }
    result = await db[_M].insert_one(doc)
    return str(result.inserted_id)


async def get_mission(db, mission_id: str, user_id: str | None = None) -> dict | None:
    q: dict = {"_id": ObjectId(mission_id)}
    if user_id:
        q["user_id"] = user_id
    doc = await db[_M].find_one(q, {"_id": 1, **{k: 1 for k in [
        "user_id", "title", "description", "mission_type", "autonomy_level",
        "params", "status", "plan", "agents_used", "total_steps",
        "completed_steps", "created_at", "updated_at", "started_at",
        "completed_at", "error", "result_summary", "report", "validation",
        "estimated_credits", "used_credits",
    ]}})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def list_missions(db, user_id: str, status: str | None = None,
                        limit: int = 20) -> list[dict]:
    q: dict = {"user_id": user_id}
    if status:
        q["status"] = status
    docs = await db[_M].find(q, {"_id": 1, "title": 1, "status": 1, "mission_type": 1,
                                  "autonomy_level": 1, "total_steps": 1, "completed_steps": 1,
                                  "created_at": 1, "started_at": 1, "completed_at": 1,
                                  "result_summary": 1, "error": 1,
                                  }).sort("created_at", -1).limit(limit).to_list(limit)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


async def update_mission(db, mission_id: str, updates: dict) -> None:
    updates["updated_at"] = datetime.now(timezone.utc)
    await db[_M].update_one({"_id": ObjectId(mission_id)}, {"$set": updates})


async def set_plan(db, mission_id: str, plan: list[dict], estimated_credits: int) -> None:
    await update_mission(db, mission_id, {
        "plan":              plan,
        "total_steps":       len(plan),
        "estimated_credits": estimated_credits,
        "status":            "plan_review",
    })


async def delete_mission(db, mission_id: str, user_id: str) -> bool:
    result = await db[_M].delete_one({"_id": ObjectId(mission_id), "user_id": user_id})
    return result.deleted_count > 0


# ── Enterprise execution lifecycle functions ────────────────────────────────────

async def mark_queued(db, mission_id: str) -> None:
    """Transition mission to queued state (entered execution queue)."""
    now = datetime.now(timezone.utc)
    await db[_M].update_one(
        {"_id": ObjectId(mission_id)},
        {"$set": {"status": "queued", "queued_at": now, "updated_at": now}},
    )


async def mark_running(db, mission_id: str, worker_id: str, execution_token: str) -> None:
    """Transition mission to running state (worker acquired lock and started)."""
    now = datetime.now(timezone.utc)
    history_entry = {
        "token":      execution_token,
        "worker_id":  worker_id,
        "started_at": now.isoformat(),
    }
    await db[_M].update_one(
        {"_id": ObjectId(mission_id)},
        {
            "$set": {
                "status":          "running",
                "worker_id":       worker_id,
                "execution_token": execution_token,
                "heartbeat":       now,
                "started_at":      now,
                "updated_at":      now,
            },
            "$push": {"execution_history": history_entry},
        },
    )


async def update_heartbeat(db, mission_id: str) -> None:
    """Update heartbeat timestamp (called by worker every ~10s)."""
    now = datetime.now(timezone.utc)
    await db[_M].update_one(
        {"_id": ObjectId(mission_id)},
        {"$set": {"heartbeat": now, "updated_at": now}},
    )


async def increment_retry(db, mission_id: str, error: str) -> None:
    """Increment retry counter and record last error."""
    now = datetime.now(timezone.utc)
    await db[_M].update_one(
        {"_id": ObjectId(mission_id)},
        {
            "$inc": {"retry_count": 1},
            "$set": {
                "status":     "retrying",
                "last_error": error[:500],
                "worker_id":  None,
                "heartbeat":  None,
                "updated_at": now,
            },
        },
    )


async def archive_mission(db, mission_id: str, user_id: str) -> bool:
    """Move a completed/failed/cancelled mission to archived state."""
    result = await db[_M].update_one(
        {"_id": ObjectId(mission_id), "user_id": user_id,
         "status": {"$in": ["completed", "failed", "cancelled"]}},
        {"$set": {"status": "archived", "updated_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count > 0


async def get_missions_by_status(db, status: str | list, limit: int = 50) -> list[dict]:
    """Return missions with given status (or list of statuses). No user filter."""
    q: dict = {"status": {"$in": status} if isinstance(status, list) else status}
    docs = await db[_M].find(
        q,
        {"_id": 1, "user_id": 1, "title": 1, "status": 1, "worker_id": 1,
         "heartbeat": 1, "retry_count": 1, "queued_at": 1, "started_at": 1},
    ).limit(limit).to_list(limit)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


# ── Steps ──────────────────────────────────────────────────────────────────────

async def upsert_step(db, step: dict) -> None:
    await db[_S].update_one(
        {"mission_id": step["mission_id"], "step_id": step["step_id"]},
        {"$set": step},
        upsert=True,
    )


async def get_steps(db, mission_id: str) -> list[dict]:
    return await db[_S].find({"mission_id": mission_id}, {"_id": 0}).to_list(50)


async def update_step(db, mission_id: str, step_id: str, updates: dict) -> None:
    await db[_S].update_one(
        {"mission_id": mission_id, "step_id": step_id},
        {"$set": updates},
    )


# ── Approvals ──────────────────────────────────────────────────────────────────

async def create_approval(db, approval: dict) -> str:
    result = await db[_A].insert_one({**approval, "created_at": datetime.now(timezone.utc)})
    return str(result.inserted_id)


async def get_approval(db, approval_id: str, user_id: str | None = None) -> dict | None:
    q: dict = {"_id": ObjectId(approval_id)}
    if user_id:
        q["user_id"] = user_id
    doc = await db[_A].find_one(q, {"_id": 1, **{k: 1 for k in [
        "mission_id", "step_id", "user_id", "action", "description",
        "proposed_by", "data", "evidence", "status", "created_at",
        "resolved_at", "resolved_by", "reject_reason",
    ]}})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def list_pending_approvals(db, user_id: str) -> list[dict]:
    docs = await db[_A].find(
        {"user_id": user_id, "status": "pending"},
        {"_id": 1, "mission_id": 1, "action": 1, "description": 1, "proposed_by": 1, "data": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(20)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


async def resolve_approval(db, approval_id: str, status: str,
                           resolved_by: str, reject_reason: str | None = None) -> None:
    await db[_A].update_one(
        {"_id": ObjectId(approval_id)},
        {"$set": {
            "status":       status,
            "resolved_at":  datetime.now(timezone.utc),
            "resolved_by":  resolved_by,
            "reject_reason": reject_reason,
        }},
    )


async def get_mission_approvals(db, mission_id: str) -> list[dict]:
    docs = await db[_A].find({"mission_id": mission_id}, {"_id": 1, "action": 1, "status": 1,
                                                            "created_at": 1, "resolved_at": 1}).to_list(20)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


# ── Logs ───────────────────────────────────────────────────────────────────────

async def append_log(db, mission_id: str, agent: str, event: str,
                     detail: str, data: dict | None = None) -> None:
    await db[_L].insert_one({
        "mission_id": mission_id,
        "agent":      agent,
        "event":      event,
        "detail":     detail,
        "data":       data or {},
        "created_at": datetime.now(timezone.utc),
    })


async def get_logs(db, mission_id: str, limit: int = 50) -> list[dict]:
    docs = await db[_L].find(
        {"mission_id": mission_id}, {"_id": 0}
    ).sort("created_at", 1).limit(limit).to_list(limit)
    return docs


# ── Schedules ─────────────────────────────────────────────────────────────────

async def create_schedule(db, user_id: str, schedule: dict) -> str:
    schedule["user_id"]   = user_id
    schedule["created_at"] = datetime.now(timezone.utc)
    schedule["active"]     = True
    schedule["last_run"]   = None
    result = await db[_SC].insert_one(schedule)
    return str(result.inserted_id)


async def list_schedules(db, user_id: str) -> list[dict]:
    docs = await db[_SC].find({"user_id": user_id}, {"_id": 1, "title": 1, "mission_type": 1,
                                                       "cron_expression": 1, "active": 1, "last_run": 1}).to_list(20)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


async def delete_schedule(db, schedule_id: str, user_id: str) -> bool:
    result = await db[_SC].delete_one({"_id": ObjectId(schedule_id), "user_id": user_id})
    return result.deleted_count > 0
