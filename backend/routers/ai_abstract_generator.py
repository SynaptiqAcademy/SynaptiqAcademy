"""AI Abstract Generator — generate publication-quality abstracts via Claude.

Gate: researcher+ plan (require_feature("ai_abstract_generator")).
Cost: 5 credits per generation. Refunded automatically on LLM failure.

Endpoints:
  POST /api/ai/abstract/generate  — generate abstract
  GET  /api/ai/abstract/history   — caller's past generations (newest first)
  GET  /api/ai/abstract/{id}      — fetch one by id (owner only)
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from services.ai.llm import call_llm
from services.credits_service import consume_credits, refund_credits
from services.permissions import require_feature
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.ai_abstract_generator")
router = APIRouter(prefix="/api/ai/abstract", tags=["ai-abstract-generator"])


# ─────────────────────────────── request model ───────────────────────────────

class AbstractGenerateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    content: str = Field(..., min_length=50, max_length=20000,
                         description="Paper text or section content to summarise")
    manuscript_id: Optional[str] = Field(None, max_length=100)
    style: str = Field("academic", pattern=r"^(academic|structured|concise|narrative)$")
    max_words: int = Field(250, ge=100, le=400)


async def _generate_abstract(
    req: AbstractGenerateRequest,
    *,
    user_id: str | None = None,
    db=None,
) -> dict:
    raw = await call_llm(
        prompt_id="manuscript.abstract_generator",
        variables={
            "title":    req.title,
            "style":    req.style,
            "max_words": req.max_words,
            "content":  req.content[:15000],
        },
        feature="manuscript.abstract_generator",
        user_id=user_id,
        db=db,
        max_tokens=1500,
    )

    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```", 2)
        inner = parts[1] if len(parts) >= 2 else text
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.strip()
        if "```" in text:
            text = text.split("```")[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        log.error("Abstract generator JSON parse failed: %s | raw[:300]=%s", exc, text[:300])
        raise HTTPException(502, "Abstract engine returned malformed output. Please try again.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ser(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


# ─────────────────────────────── endpoints ───────────────────────────────────

@router.post("/generate")
async def generate_abstract(
    body: AbstractGenerateRequest,
    user: dict = Depends(require_feature("ai_abstract_generator")),
):
    """Generate a publication-quality abstract. Costs 5 research credits.
    Credits are refunded automatically if generation fails.
    """
    charged = await consume_credits(
        user["id"], "ai_abstract_generator",
        metadata={"title": body.title[:100], "style": body.style},
    )
    credits_used = charged.get("consumed", 5)

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    started = time.monotonic()
    try:
        result = await _generate_abstract(body, user_id=user["id"], db=db)
    except HTTPException:
        await refund_credits(user["id"], "ai_abstract_generator", reason="Abstract engine error")
        raise
    except Exception as exc:
        await refund_credits(user["id"], "ai_abstract_generator", reason="Unexpected error")
        log.error("Abstract generation failed: %s", exc)
        raise HTTPException(503, "Abstract generation failed. Your credits have been refunded.")
    duration_ms = int((time.monotonic() - started) * 1000)

    doc = {
        "user_id":       user["id"],
        "title":         body.title,
        "style":         body.style,
        "max_words":     body.max_words,
        "manuscript_id": body.manuscript_id,
        "result":        result,
        "credits_used":  credits_used,
        "created_at":    _now(),
    }
    ins = await db.abstract_generations.insert_one(doc)
    doc["_id"] = ins.inserted_id

    try:
        await db.ai_requests.insert_one({
            "user_id":     user["id"],
            "feature":     "ai_abstract_generator",
            "credits":     credits_used,
            "duration_ms": duration_ms,
            "success":     True,
            "ref_id":      str(ins.inserted_id),
            "created_at":  _now(),
        })
    except Exception:
        pass

    return _ser(doc)


@router.get("/history")
async def list_abstracts(user: dict = Depends(get_current_user)):
    """Return the authenticated user's abstract generation history, newest first."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.abstract_generations.find(
        {"user_id": user["id"]},
        {"result": 0},
    ).sort("created_at", -1).to_list(50)
    return [_ser(d) for d in docs]


@router.get("/{gen_id}")
async def get_abstract(gen_id: str, user: dict = Depends(get_current_user)):
    """Fetch a specific abstract generation by ID. Only the owner may access it."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(gen_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.abstract_generations.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    if doc["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    return _ser(doc)
