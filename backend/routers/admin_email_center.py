"""Admin email center — templates, campaigns, individual and bulk send.

H1: Bulk send now enforces email_marketing_consent (GDPR/CAN-SPAM).
    Only users with email_marketing_consent != False receive bulk emails.
    Each bulk email includes a signed unsubscribe link.

H2: send_individual and send_bulk accept template_id to use stored templates.
    Body {{variable}} placeholders are replaced before sending.
"""
from __future__ import annotations
import base64
import hmac
import hashlib
import os
import re
import secrets
from datetime import datetime, timezone
from typing import Optional

import asyncio

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request
from worker import enqueue_job
from worker.models import Job, Priority
from pydantic import BaseModel

from db import get_db
from services.admin_audit import log_event, request_meta
from services.permissions import require_super_admin
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/admin", tags=["admin"])

VALID_SEGMENTS = {"all", "free", "paid", "unverified", "consented"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_oid(oid_str: str) -> ObjectId:
    try:
        return ObjectId(oid_str)
    except (InvalidId, Exception):
        raise HTTPException(status_code=400, detail="Invalid ID")


# ---------------------------------------------------------------------------
# Unsubscribe token helpers (HMAC-signed, user_id based)
# ---------------------------------------------------------------------------

def _unsub_secret() -> bytes:
    return os.environ.get("JWT_SECRET", "dev_fallback_secret").encode()


def make_unsubscribe_token(user_id: str) -> str:
    sig = hmac.new(_unsub_secret(), user_id.encode(), hashlib.sha256).hexdigest()
    raw = f"{user_id}.{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def verify_unsubscribe_token(token: str) -> Optional[str]:
    """Returns user_id if the token is valid, None otherwise."""
    try:
        padded = token + "=" * (4 - len(token) % 4)
        raw = base64.urlsafe_b64decode(padded).decode()
        user_id, sig = raw.rsplit(".", 1)
        expected_sig = hmac.new(_unsub_secret(), user_id.encode(), hashlib.sha256).hexdigest()
        if secrets.compare_digest(sig, expected_sig):
            return user_id
    except Exception:
        pass
    return None


def _unsubscribe_url(user_id: str) -> str:
    # Link directly to the backend API endpoint — it processes the token and
    # redirects to {FRONTEND_BASE_URL}/unsubscribed on success.
    backend = os.environ.get("BACKEND_BASE_URL", "").rstrip("/")
    token = make_unsubscribe_token(user_id)
    return f"{backend}/api/unsubscribe?token={token}"


def _add_unsubscribe_footer(html: str, user_id: str) -> str:
    url = _unsubscribe_url(user_id)
    footer = (
        '<hr style="border:none;border-top:1px solid #eee;margin:30px 0;">'
        '<p style="color:#999;font-size:12px;text-align:center;">'
        'You received this email because you are a SYNAPTIQ member.<br>'
        f'<a href="{url}" style="color:#999;">Unsubscribe</a>'
        "</p>"
    )
    return html + footer


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

def _render_template(body_html: str, variables: dict) -> str:
    """Replace {{variable}} placeholders with values from the variables dict."""
    def replacer(match: re.Match) -> str:
        key = match.group(1).strip()
        return str(variables.get(key, match.group(0)))
    return re.sub(r"\{\{(\w+)\}\}", replacer, body_html)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class TemplateCreate(BaseModel):
    name: str
    subject: str
    body_html: str
    description: str = ""


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    description: Optional[str] = None


class SendIndividualRequest(BaseModel):
    user_id: str
    subject: str = ""
    body_html: str = ""
    template_id: Optional[str] = None
    variables: dict = {}


class SendBulkRequest(BaseModel):
    segment: str
    subject: str = ""
    body_html: str = ""
    template_id: Optional[str] = None
    variables: dict = {}


# ---------------------------------------------------------------------------
# Email log
# ---------------------------------------------------------------------------

@router.get("/email/log", dependencies=[Depends(require_super_admin)])
async def email_log(limit: int = 50, admin: dict = Depends(require_super_admin)):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cursor = db.email_log.find({}).sort("created_at", -1).limit(limit)
    items = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        items.append(doc)
    return items


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

@router.get("/email/templates")
async def list_templates(admin: dict = Depends(require_super_admin)):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cursor = db.email_templates.find({}).sort("created_at", -1)
    items = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        items.append(doc)
    return items


@router.post("/email/templates")
async def create_template(body: TemplateCreate, request: Request, admin: dict = Depends(require_super_admin)):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    existing = await db.email_templates.find_one({"name": body.name})
    if existing:
        raise HTTPException(status_code=400, detail="A template with that name already exists")
    doc = {
        "name": body.name,
        "subject": body.subject,
        "body_html": body.body_html,
        "description": body.description,
        "created_by": admin.get("email"),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    result = await db.email_templates.insert_one(doc)
    await log_event("admin.email.template.create", actor_id=admin["id"], actor_email=admin.get("email"),
                    ip=request_meta(request)["ip"], extra={"name": body.name})
    return {"id": str(result.inserted_id), **doc}


@router.put("/email/templates/{tid}")
async def update_template(tid: str, body: TemplateUpdate, request: Request, admin: dict = Depends(require_super_admin)):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(tid)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = _now_iso()
    result = await db.email_templates.update_one({"_id": oid}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    await log_event("admin.email.template.update", actor_id=admin["id"], actor_email=admin.get("email"),
                    target_id=tid, ip=request_meta(request)["ip"])
    return {"ok": True}


@router.delete("/email/templates/{tid}")
async def delete_template(tid: str, request: Request, admin: dict = Depends(require_super_admin)):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(tid)
    result = await db.email_templates.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    await log_event("admin.email.template.delete", actor_id=admin["id"], actor_email=admin.get("email"),
                    target_id=tid, ip=request_meta(request)["ip"])
    return {"ok": True}


@router.post("/email/templates/{tid}/preview")
async def preview_template(tid: str, body: dict, admin: dict = Depends(require_super_admin)):
    """Render a template with provided variables and return the HTML preview."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(tid)
    tmpl = await db.email_templates.find_one({"_id": oid})
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    variables = body.get("variables", {})
    rendered = _render_template(tmpl["body_html"], variables)
    return {
        "subject": _render_template(tmpl["subject"], variables),
        "body_html": rendered,
    }


# ---------------------------------------------------------------------------
# Send individual
# H2: accepts template_id — loads template from DB and substitutes variables
# ---------------------------------------------------------------------------

@router.post("/email/send-individual")
async def send_individual(body: SendIndividualRequest, request: Request, admin: dict = Depends(require_super_admin)):
    if not body.template_id and not body.body_html:
        raise HTTPException(status_code=400, detail="Provide either body_html or template_id")

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        user = await db.users.find_one({"_id": ObjectId(body.user_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Resolve template or use raw body
    resolved_subject = body.subject
    resolved_html = body.body_html

    if body.template_id:
        tmpl = await db.email_templates.find_one({"_id": _parse_oid(body.template_id)})
        if not tmpl:
            raise HTTPException(status_code=404, detail="Email template not found")
        variables = {
            "user_name": user.get("full_name") or user.get("email", ""),
            "user_email": user.get("email", ""),
            **body.variables,
        }
        resolved_subject = body.subject or _render_template(tmpl["subject"], variables)
        resolved_html = _render_template(tmpl["body_html"], variables)

    to_email = user.get("email", "")
    status = "failed"
    provider_id = None
    try:
        from services.email_service import send_email
        result = await send_email(to=to_email, subject=resolved_subject, html=resolved_html,
                                  event_kind="admin_individual")
        status = "sent" if result.get("ok") else "failed"
        provider_id = result.get("id")
    except Exception:
        status = "failed"

    await log_event("admin.email.send_individual", actor_id=admin["id"], actor_email=admin.get("email"),
                    target_id=body.user_id, target_email=to_email, ip=request_meta(request)["ip"],
                    extra={"subject": resolved_subject, "status": status,
                           "template_id": body.template_id, "provider_id": provider_id})
    if status == "failed":
        raise HTTPException(status_code=502, detail="Email delivery failed")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Send bulk
# H1: filter by email_marketing_consent — only consented users receive marketing email
# H2: template_id resolves stored template, variables substituted per-user
# ---------------------------------------------------------------------------

async def _run_bulk_send(
    campaign_id: str,
    query: dict,
    base_subject: str,
    base_html: Optional[str],
    tmpl: Optional[dict],
    body_variables: dict,
) -> None:
    """Background task: iterate recipients and send with retry + exponential backoff.

    Progress is written to email_campaigns every 50 sends so the admin UI
    can poll for real-time progress. Max throughput: ~10 emails/second to
    respect Resend rate limits.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    sent_count = 0
    failed_count = 0
    skipped_count = 0
    _MAX_RETRIES = 3

    try:
        from services.email_service import send_email

        cursor = db.users.find(query, {"_id": 1, "email": 1, "full_name": 1, "first_name": 1})
        async for user in cursor:
            email = user.get("email", "")
            if not email:
                skipped_count += 1
                continue

            user_id_str = str(user["_id"])
            user_vars = {
                "user_name": user.get("full_name") or user.get("first_name") or email,
                "user_email": email,
                **body_variables,
            }

            if tmpl:
                resolved_subject = base_subject or _render_template(tmpl["subject"], user_vars)
                final_html = _render_template(tmpl["body_html"], user_vars)
            else:
                resolved_subject = base_subject
                final_html = _render_template(base_html or "", user_vars)

            final_html = _add_unsubscribe_footer(final_html, user_id_str)

            # Retry with exponential backoff: 1 s, 2 s, 4 s
            success = False
            for attempt in range(_MAX_RETRIES):
                try:
                    result = await send_email(
                        to=email, subject=resolved_subject, html=final_html,
                        event_kind="admin_bulk",
                    )
                    if result.get("ok"):
                        sent_count += 1
                        success = True
                        break
                except Exception:
                    if attempt < _MAX_RETRIES - 1:
                        await asyncio.sleep(2 ** attempt)
            if not success:
                failed_count += 1

            # Write progress to DB every 50 sends
            if (sent_count + failed_count) % 50 == 0:
                await db.email_campaigns.update_one(
                    {"_id": ObjectId(campaign_id)},
                    {"$set": {
                        "sent_count": sent_count,
                        "failed_count": failed_count,
                        "skipped_count": skipped_count,
                        "status": "sending",
                    }},
                )

            # Rate limit: max ~10 emails/second
            await asyncio.sleep(0.1)

    except Exception as exc:
        await db.email_campaigns.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": {
                "status": "failed",
                "error": str(exc)[:500],
                "sent_count": sent_count,
                "failed_count": failed_count,
                "skipped_count": skipped_count,
                "completed_at": _now_iso(),
            }},
        )
        return

    await db.email_campaigns.update_one(
        {"_id": ObjectId(campaign_id)},
        {"$set": {
            "status": "completed",
            "sent_count": sent_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "completed_at": _now_iso(),
        }},
    )


@router.post("/email/send-bulk")
async def send_bulk(
    body: SendBulkRequest,
    request: Request,
    admin: dict = Depends(require_super_admin),
):
    if body.segment not in VALID_SEGMENTS:
        raise HTTPException(status_code=400, detail=f"Invalid segment. Must be one of: {', '.join(sorted(VALID_SEGMENTS))}")
    if not body.template_id and not body.body_html:
        raise HTTPException(status_code=400, detail="Provide either body_html or template_id")

    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    # H2: resolve template if provided
    base_html = body.body_html
    base_subject = body.subject
    tmpl = None
    if body.template_id:
        tmpl = await db.email_templates.find_one({"_id": _parse_oid(body.template_id)})
        if not tmpl:
            raise HTTPException(status_code=404, detail="Email template not found")

    # H1: ALWAYS filter out unsubscribed users in bulk sends
    consent_filter = {"email_marketing_consent": {"$ne": False}}
    if body.segment == "all":
        query: dict = consent_filter
    elif body.segment == "free":
        query = {**consent_filter, "plan_code": "free"}
    elif body.segment == "paid":
        query = {**consent_filter, "plan_code": {"$in": ["researcher", "pro_researcher", "institution"]}}
    elif body.segment == "unverified":
        query = {**consent_filter, "email_verified": False}
    elif body.segment == "consented":
        query = {"email_marketing_consent": True}
    else:
        query = consent_filter

    # Create campaign record immediately — HTTP response returns campaign_id at once
    campaign_doc = {
        "segment": body.segment,
        "subject": base_subject,
        "template_id": body.template_id,
        "sent_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "status": "queued",
        "sent_by": admin.get("email"),
        "created_at": _now_iso(),
    }
    result = await db.email_campaigns.insert_one(campaign_doc)
    campaign_id = str(result.inserted_id)

    # Queue actual delivery — runs after HTTP response is returned
    _bulk_job = Job(
        job_type="email.bulk_campaign",
        payload={
            "campaign_id":    campaign_id,
            "query":          query,
            "base_subject":   base_subject or "",
            "base_html":      base_html,
            "tmpl":           tmpl,
            "body_variables": body.variables,
        },
        priority=Priority.NORMAL,
    )
    await enqueue_job(_bulk_job, db)

    await log_event(
        "admin.email.bulk_queued",
        actor_id=admin["id"],
        actor_email=admin.get("email"),
        ip=request_meta(request)["ip"],
        extra={"segment": body.segment, "template_id": body.template_id, "campaign_id": campaign_id},
    )

    return {
        "ok": True,
        "campaign_id": campaign_id,
        "status": "queued",
        "message": "Campaign queued. Poll GET /api/admin/email/campaigns for progress.",
    }


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------

@router.get("/email/campaigns")
async def list_campaigns(admin: dict = Depends(require_super_admin)):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cursor = db.email_campaigns.find({}).sort("created_at", -1).limit(100)
    items = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        items.append(doc)
    return items
