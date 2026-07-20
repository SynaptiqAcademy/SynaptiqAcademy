"""AI Manuscript Review — full academic peer-review via Claude.

Accepts a PDF or DOCX upload, extracts the full text, and asks Claude to
produce a structured, scored, section-by-section peer-review report.

Endpoints:
  POST /api/manuscript-review          — upload file, run review (costs 20 credits)
  GET  /api/manuscript-review/history  — list caller's past reviews
  GET  /api/manuscript-review/{id}     — fetch one review by id
"""
from __future__ import annotations

import io
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from auth_utils import get_current_user
from db import get_db
from services.ai.llm import call_llm
from services.credits_service import consume_credits, refund_credits
from services.permissions import require_feature
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.manuscript_review")
router = APIRouter(prefix="/api/manuscript-review", tags=["manuscript-review"])

ALLOWED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
MAX_FILE_BYTES = 50 * 1024 * 1024   # 50 MB
MAX_TEXT_CHARS = 60_000              # ~15 k tokens — keeps latency and cost reasonable
MIN_TEXT_CHARS = 200                 # reject trivially short documents


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────── text extraction ────────────────────────────────

def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    pages: list[str] = []
    for page in reader.pages:
        try:
            extracted = page.extract_text()
            if extracted:
                pages.append(extracted)
        except Exception:
            pass
    return "\n".join(pages)


def _extract_docx(data: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(data))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _extract_text(data: bytes, mime: str) -> str:
    if mime == "application/pdf":
        return _extract_pdf(data)
    return _extract_docx(data)


# ────────────────────────────── Claude prompt ────────────────────────────────

_SYSTEM = (
    "You are an expert academic peer reviewer with broad expertise across STEM and social science "
    "disciplines. You apply rigorous, constructive, and fair evaluation standards consistent with "
    "high-impact journal peer review. Return ONLY valid JSON — no markdown fences, no commentary."
)

_PROMPT_TEMPLATE = """\
Review the following manuscript text and produce a structured academic peer-review report.

Every score (0–100) must be derived from the actual content of the manuscript — do not invent or randomise values.

MANUSCRIPT TEXT:
{manuscript_text}

Return a single JSON object with this exact schema:

{{
  "executive_summary": {{
    "overview": "<3-5 sentence holistic assessment>",
    "recommendation": "accept | minor_revision | major_revision | reject",
    "overall_score": <integer 0-100>
  }},
  "sections": {{
    "research_problem": {{
      "score": <integer 0-100>,
      "strengths": ["<string>", ...],
      "weaknesses": ["<string>", ...],
      "recommendations": ["<string>", ...]
    }},
    "literature_foundation": {{
      "score": <integer 0-100>,
      "coverage": "<string>",
      "recency": "<string>",
      "theoretical_grounding": "<string>",
      "recommendations": ["<string>", ...]
    }},
    "methodology": {{
      "score": <integer 0-100>,
      "research_design": "<string>",
      "sampling": "<string>",
      "variables": "<string>",
      "data_collection": "<string>",
      "recommendations": ["<string>", ...]
    }},
    "statistical_validity": {{
      "score": <integer 0-100>,
      "analysis_quality": "<string>",
      "threats_to_validity": ["<string>", ...],
      "recommendations": ["<string>", ...]
    }},
    "writing_quality": {{
      "score": <integer 0-100>,
      "clarity": "<string>",
      "flow": "<string>",
      "argumentation": "<string>",
      "recommendations": ["<string>", ...]
    }},
    "publication_readiness": {{
      "score": <integer 0-100>,
      "publication_probability": "<string>",
      "major_issues": ["<string>", ...],
      "minor_issues": ["<string>", ...]
    }}
  }},
  "revision_checklist": {{
    "high_priority": ["<string>", ...],
    "medium_priority": ["<string>", ...],
    "low_priority": ["<string>", ...]
  }}
}}
"""


async def _run_claude_review(text: str) -> dict:
    truncated = text[:MAX_TEXT_CHARS]
    if len(text) > MAX_TEXT_CHARS:
        truncated += (
            "\n\n[Reviewer note: manuscript truncated at 60,000 characters "
            "due to processing limits. Sections beyond this point were not evaluated.]"
        )

    raw = await call_llm(
        system=_SYSTEM,
        user_msg=_PROMPT_TEMPLATE.format(manuscript_text=truncated),
        feature="manuscript.review",
        max_tokens=4096,
    )

    # Strip any accidental markdown fences Claude might add despite instructions
    text_out = raw.strip()
    if text_out.startswith("```"):
        parts = text_out.split("```", 2)
        if len(parts) >= 3:
            inner = parts[1]
            if inner.startswith("json"):
                inner = inner[4:]
            text_out = inner.strip()
        else:
            text_out = text_out.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text_out)
    except json.JSONDecodeError as exc:
        log.error("Review JSON parse failed: %s | raw[:400]=%s", exc, text_out[:400])
        raise HTTPException(
            502,
            "The review engine returned malformed output. Please try again."
        )


def _weighted_overall(review: dict) -> float:
    """Average the six section scores; fall back to Claude's own overall_score."""
    secs = review.get("sections", {})
    weights = {
        "research_problem":     1.5,
        "literature_foundation": 1.0,
        "methodology":           1.5,
        "statistical_validity":  1.5,
        "writing_quality":       1.0,
        "publication_readiness": 1.5,
    }
    total_w = 0.0
    total_s = 0.0
    for key, w in weights.items():
        s = secs.get(key, {}).get("score")
        if isinstance(s, (int, float)) and 0 <= s <= 100:
            total_s += s * w
            total_w += w
    if total_w == 0:
        return float(review.get("executive_summary", {}).get("overall_score", 0))
    return round(total_s / total_w, 1)


def _ser(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


# ─────────────────────────────── endpoints ──────────────────────────────────

@router.post("")
async def create_review(
    file: UploadFile = File(...),
    manuscript_id: Optional[str] = Form(None),
    user: dict = Depends(require_feature("ai_manuscript_review")),
):
    """Upload a PDF or DOCX and receive a full structured academic review.
    Costs 20 research credits. Credits are refunded if the review fails.
    """
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(415, "Only PDF and DOCX files are accepted.")

    data = await file.read()
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, f"File exceeds {MAX_FILE_BYTES // 1024 // 1024} MB limit.")

    # Extract text before touching credits so a bad upload doesn't consume anything.
    try:
        manuscript_text = _extract_text(data, file.content_type)
    except Exception as exc:
        log.error("Text extraction error: %s", exc)
        raise HTTPException(
            422,
            "Could not extract text. Ensure the file is not password-protected or corrupted."
        )

    if len(manuscript_text.strip()) < MIN_TEXT_CHARS:
        raise HTTPException(
            422,
            "Extracted text is too short. Ensure the document contains readable manuscript content."
        )

    # Consume 20 credits — raises 402 automatically if balance insufficient.
    charged = await consume_credits(
        user["id"], "ai_manuscript_review",
        metadata={"filename": file.filename, "text_length": len(manuscript_text)},
    )
    credits_used = charged.get("consumed", 20)

    # Call Claude — refund on any failure.
    started = time.monotonic()
    try:
        review = await _run_claude_review(manuscript_text)
    except HTTPException:
        await refund_credits(user["id"], "ai_manuscript_review", reason="Review engine error")
        raise
    except Exception as exc:
        await refund_credits(user["id"], "ai_manuscript_review", reason="Unexpected error")
        log.error("Manuscript review generation failed: %s", exc)
        raise HTTPException(503, "Review generation failed. Your credits have been refunded.")
    duration_ms = int((time.monotonic() - started) * 1000)

    overall_score = _weighted_overall(review)

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = {
        "user_id":       user["id"],
        "manuscript_id": manuscript_id,
        "filename":      file.filename or "manuscript",
        "text_length":   len(manuscript_text),
        "review_date":   _now(),
        "overall_score": overall_score,
        "review_json":   review,
        "credits_used":  credits_used,
        "created_at":    _now(),
    }
    result = await db.manuscript_reviews.insert_one(doc)
    doc["_id"] = result.inserted_id

    try:
        await db.ai_requests.insert_one({
            "user_id":     user["id"],
            "feature":     "ai_manuscript_review",
            "credits":     credits_used,
            "duration_ms": duration_ms,
            "success":     True,
            "ref_id":      str(result.inserted_id),
            "created_at":  _now(),
        })
    except Exception:
        pass

    return _ser(doc)


@router.get("/history")
async def list_reviews(user: dict = Depends(get_current_user)):
    """Return the authenticated user's manuscript review history, newest first."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.manuscript_reviews.find(
        {"user_id": user["id"]}
    ).sort("created_at", -1).to_list(50)
    return [_ser(d) for d in docs]


@router.get("/{review_id}")
async def get_review(review_id: str, user: dict = Depends(get_current_user)):
    """Fetch a specific review by ID. Only the owner may access it."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(review_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscript_reviews.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    if doc["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    return _ser(doc)
