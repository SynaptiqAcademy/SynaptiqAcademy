"""Diagnostic + tracking endpoints for the transactional email layer.

Use cases:
  - Inspect the live configuration (is_live / dry-run / missing vars).
  - Render a template to HTML in the browser without sending anything.
  - Trigger a dry-run send to the logged-in user's own email address (so admins
    can validate templates end-to-end once they paste a real RESEND_API_KEY).
  - Receive Resend's delivery-event webhook (sent/delivered/opened/clicked/
    bounced/complained) and record it against services/email_service.py's
    email_log collection.

All diagnostic endpoints require an authenticated user; mutation endpoints
require admin. The webhook endpoint is unauthenticated (Resend calls it) but
verifies the Svix-style signature Resend signs every payload with.
"""
import hashlib
import hmac
import logging
import time
from base64 import b64decode, b64encode
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from services import email_templates as T
from services.email_service import is_live, send_email, _config, absolute_url
from zt.deps import zt_check

router = APIRouter(prefix="/api/email", tags=["email"])
logger = logging.getLogger("synaptiq.email.webhook")


TEMPLATES = {
    "welcome": lambda: T.welcome_email(
        recipient_name="Researcher", profile_setup_url=absolute_url("/profile-setup"),
        app_url=absolute_url("/discover"),
    ),
    "email_verification": lambda: T.email_verification_email(
        recipient_name="Researcher", verify_url=absolute_url("/verify-email?token=PREVIEW"),
        expires_in_hours=24,
    ),
    "getting_started": lambda: T.getting_started_email(
        recipient_name="Researcher", completion_pct=45,
        remaining_tasks=[
            ("Verify Email", False), ("Connect ORCID", False),
            ("Add Research Interests", False), ("Upload Profile Photo", False),
            ("Create First Workspace", False),
        ],
        profile_setup_url=absolute_url("/profile-setup"),
    ),
    "password_reset": lambda: T.password_reset_email(
        recipient_name="Researcher", reset_url=absolute_url("/reset-password?token=PREVIEW"),
        expires_in_minutes=30,
    ),
    "workspace_invitation": lambda: T.workspace_invitation_email(
        recipient_name="Researcher", workspace_name="Example Workspace", role="Co-Investigator",
        inviter_name="Platform User", accept_url=absolute_url("/workspaces/preview"),
    ),
    "review_request": lambda: T.review_request_email(
        recipient_name="Researcher", manuscript_title="A study on transformer interpretability",
        requester_name="Platform User", section="methodology",
        note="Please focus on the sampling justification.",
        review_url=absolute_url("/reviews"),
    ),
    "collaboration_invitation_application": lambda: T.collaboration_invitation_email(
        recipient_name="Researcher", collaboration_title="Cross-disciplinary study on PLS-SEM adoption",
        inviter_name="Platform User", kind="application",
        action_url=absolute_url("/collaborations/preview"),
        message="I'd love to contribute statistical modelling.",
    ),
    "collaboration_invitation_decision": lambda: T.collaboration_invitation_email(
        recipient_name="Researcher", collaboration_title="Cross-disciplinary study on PLS-SEM adoption",
        inviter_name="Platform User", kind="decision",
        action_url=absolute_url("/collaborations/preview"),
        message="Status: accepted",
    ),
}


@router.get("/config")
async def email_config(user: dict = Depends(get_current_user)):
    """Non-secret introspection — used by ops to verify env setup."""
    c = _config()
    return {
        "live": is_live(),
        "provider": c.provider,
        "dry_run": c.dry_run,
        "configured": c.configured,
        "missing": [k for k, v in {
            "RESEND_API_KEY": c.api_key, "EMAIL_FROM": c.sender, "FRONTEND_BASE_URL": c.frontend_base_url
        }.items() if not v],
        "sender": c.sender or None,
        "domain": "synaptiq.academy",
        "templates": sorted(TEMPLATES.keys()),
        "webhook_configured": bool(_webhook_secret()),
    }


@router.get("/preview/{template}", response_class=HTMLResponse)
async def email_preview(template: str, user: dict = Depends(get_current_user)):
    """Render a template directly to the browser — never sends an email."""
    if template not in TEMPLATES:
        raise HTTPException(status_code=404, detail="Unknown template")
    _subject, html, _text = TEMPLATES[template]()
    return HTMLResponse(content=html)


@router.get("/preview/{template}/text", response_class=HTMLResponse)
async def email_preview_text(template: str, user: dict = Depends(get_current_user)):
    """Render a template's plaintext fallback — for reviewing the text version."""
    if template not in TEMPLATES:
        raise HTTPException(status_code=404, detail="Unknown template")
    _subject, _html, text = TEMPLATES[template]()
    return HTMLResponse(content=f"<pre>{text}</pre>")


@router.post("/test")
async def email_test(template: str = Query(..., description="Template key (see /api/email/config)"),
                     user: dict = Depends(get_current_user)):
    """Send a single email to the calling user. Honours EMAIL_DRY_RUN.
    Admin-only to avoid abuse for traffic generation.
    """
    zt_check(user, "admin", "admin")
    if template not in TEMPLATES:
        raise HTTPException(status_code=404, detail="Unknown template")
    if not user.get("email"):
        raise HTTPException(status_code=400, detail="Calling user has no email")
    subject, html, text = TEMPLATES[template]()
    result = await send_email(to=user["email"], subject=f"[TEST] {subject}",
                              html=html, text=text, event_kind=f"test:{template}")
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Delivery webhook — Resend → email_log
# ═══════════════════════════════════════════════════════════════════════════

def _webhook_secret() -> str | None:
    import os
    return os.environ.get("RESEND_WEBHOOK_SECRET") or None


def _verify_svix_signature(secret: str, msg_id: str, timestamp: str, body: bytes, signature_header: str) -> bool:
    """Resend signs webhooks using the Svix scheme: HMAC-SHA256 over
    "{msg_id}.{timestamp}.{body}", keyed by the base64-encoded secret's
    portion after 'whsec_'. `signature_header` is a space-separated list of
    "v1,<base64-sig>" candidates — any match is accepted (supports secret
    rotation)."""
    key = secret[len("whsec_"):] if secret.startswith("whsec_") else secret
    try:
        secret_bytes = b64decode(key)
    except Exception:
        secret_bytes = key.encode()

    signed_payload = f"{msg_id}.{timestamp}.".encode() + body
    expected = b64encode(hmac.new(secret_bytes, signed_payload, hashlib.sha256).digest()).decode()

    for candidate in signature_header.split():
        parts = candidate.split(",", 1)
        if len(parts) == 2 and hmac.compare_digest(parts[1], expected):
            return True
    return False


_EVENT_FIELD = {
    "email.sent": "sent_at",
    "email.delivered": "delivered_at",
    "email.delivery_delayed": "delayed_at",
    "email.opened": "opened_at",
    "email.clicked": "clicked_at",
    "email.bounced": "bounced_at",
    "email.complained": "complained_at",
}


@router.post("/webhook/resend")
async def resend_webhook(request: Request):
    """Receives Resend delivery events. Configure this URL (your backend origin +
    /api/email/webhook/resend, e.g. BACKEND_BASE_URL) in the Resend dashboard's
    Webhooks page, and
    set RESEND_WEBHOOK_SECRET to the signing secret it gives you — without
    that env var this endpoint rejects every request (fails closed, not
    open), since an unverified webhook would let anyone forge delivery
    events for any email_log row.
    """
    body = await request.body()
    secret = _webhook_secret()
    if not secret:
        logger.warning("[email.webhook] RESEND_WEBHOOK_SECRET not set — rejecting webhook call")
        raise HTTPException(status_code=503, detail="Webhook receiver not configured")

    msg_id = request.headers.get("svix-id", "")
    timestamp = request.headers.get("svix-timestamp", "")
    signature = request.headers.get("svix-signature", "")
    if not (msg_id and timestamp and signature):
        raise HTTPException(status_code=400, detail="Missing signature headers")

    # Reject stale payloads (replay protection) — 5 minute tolerance.
    try:
        if abs(time.time() - int(timestamp)) > 300:
            raise HTTPException(status_code=400, detail="Timestamp outside tolerance")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp")

    if not _verify_svix_signature(secret, msg_id, timestamp, body, signature):
        logger.warning("[email.webhook] signature verification failed (msg_id=%s)", msg_id)
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event_type = payload.get("type", "")
    data = payload.get("data", {}) or {}
    email_id = data.get("email_id") or data.get("id")
    field = _EVENT_FIELD.get(event_type)

    if email_id and field:
        db = get_db()
        db = DBProxy(db, SecurityContext.system())
        await db.email_log.update_one(
            {"provider_id": email_id},
            {"$set": {field: datetime.now(timezone.utc).isoformat(), "last_event": event_type}},
        )
    else:
        logger.debug("[email.webhook] unhandled event type=%s", event_type)

    return JSONResponse({"ok": True})
