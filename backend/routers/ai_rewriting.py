"""AI Rewriting — rewrite academic text via Claude.

Gate: researcher+ plan (require_feature("ai_rewriting")).
Cost: 2 credits per request. Refunded automatically on LLM failure.

Endpoints:
  POST /api/ai/rewrite          — rewrite text
  GET  /api/ai/rewrite/history  — caller's past requests (newest first)
  GET  /api/ai/rewrite/{id}     — fetch one by id (owner only)
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

log = logging.getLogger("synaptiq.ai_rewriting")
router = APIRouter(prefix="/api/ai/rewrite", tags=["ai-rewriting"])


# ─────────────────────────────── request model ───────────────────────────────

class RewriteRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000,
                      description="Text to rewrite (up to ~2000 chars recommended)")
    style: str = Field("academic", pattern=r"^(academic|concise|formal|engaging)$")
    instruction: Optional[str] = Field(None, max_length=500,
                                       description="Optional custom instruction for the rewrite")


async def _run_rewrite(
    req: RewriteRequest,
    *,
    user_id: str | None = None,
    db=None,
) -> dict:
    raw = await call_llm(
        prompt_id="manuscript.rewriting",
        variables={
            "style":       req.style,
            "instruction": req.instruction or "None — follow the style guidance above.",
            "text":        req.text,
        },
        feature="manuscript.rewriting",
        user_id=user_id,
        db=db,
        max_tokens=2000,
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
        log.error("Rewriting JSON parse failed: %s | raw[:300]=%s", exc, text[:300])
        raise HTTPException(502, "Rewriting engine returned malformed output. Please try again.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ser(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


# ─────────────────────────────── endpoints ───────────────────────────────────

@router.post("")
async def rewrite_text(
    body: RewriteRequest,
    user: dict = Depends(require_feature("ai_rewriting")),
):
    """Rewrite text in the specified academic style. Costs 2 research credits.
    Credits are refunded automatically if the rewrite fails.
    """
    charged = await consume_credits(
        user["id"], "ai_rewriting",
        metadata={"style": body.style, "text_len": len(body.text)},
    )
    credits_used = charged.get("consumed", 2)

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    started = time.monotonic()
    try:
        result = await _run_rewrite(body, user_id=user["id"], db=db)
    except HTTPException:
        await refund_credits(user["id"], "ai_rewriting", reason="Rewriting engine error")
        raise
    except Exception as exc:
        await refund_credits(user["id"], "ai_rewriting", reason="Unexpected error")
        log.error("Rewriting failed: %s", exc)
        raise HTTPException(503, "Rewriting failed. Your credits have been refunded.")
    duration_ms = int((time.monotonic() - started) * 1000)

    doc = {
        "user_id":     user["id"],
        "original":    body.text,
        "style":       body.style,
        "instruction": body.instruction,
        "result":      result,
        "credits_used": credits_used,
        "created_at":  _now(),
    }
    ins = await db.rewriting_requests.insert_one(doc)
    doc["_id"] = ins.inserted_id

    try:
        await db.ai_requests.insert_one({
            "user_id":     user["id"],
            "feature":     "ai_rewriting",
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
async def list_rewrites(user: dict = Depends(get_current_user)):
    """Return the authenticated user's rewriting history, newest first."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.rewriting_requests.find(
        {"user_id": user["id"]},
        {"original": 0, "result": 0},
    ).sort("created_at", -1).to_list(50)
    return [_ser(d) for d in docs]


@router.get("/{req_id}")
async def get_rewrite(req_id: str, user: dict = Depends(get_current_user)):
    """Fetch a specific rewriting request by ID. Only the owner may access it."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(req_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.rewriting_requests.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    if doc["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    return _ser(doc)
