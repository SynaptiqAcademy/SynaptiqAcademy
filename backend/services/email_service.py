"""SYNAPTIQ email service — Resend transactional email provider.

Modes
-----
- **Dry run** (default, `EMAIL_DRY_RUN=1` or missing API key): emails are logged
  but never sent. Safe for dev + CI.
- **Live**: when `RESEND_API_KEY`, `EMAIL_FROM`, `FRONTEND_BASE_URL` are all set AND
  `EMAIL_DRY_RUN!=1`, emails are sent via Resend. Network errors are retried with
  exponential backoff (3 attempts, 0.5s/1s/2s).
  `FRONTEND_BASE_URL` is canonical; the historical `APP_BASE_URL` name is still
  accepted as a deprecated backward-compatible fallback (see ENVIRONMENT_VARIABLES.md).

The service exposes both:
  1. **Typed helpers** (`send_password_reset`, `send_workspace_invitation`, etc.)
     for direct trigger sites where the call-site has structured arguments.
  2. **Generic `send_email(to, subject, html)`** for one-off cases.

It also plugs into `notifications_service.dispatch(...)` via the `ResendProvider`
class so any existing in-app notification automatically gets a templated email
sent when the event maps to a known kind (e.g. `workspace_invitation`,
`review_request`).
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

from bson import ObjectId

from db import get_db
from services.notifications_service import NotificationProvider, NotificationEvent
from services import email_templates as T
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.email")

# ----------- Module-level config (read on first use, not at import) -----------

def _frontend_base_url() -> str:
    """FRONTEND_BASE_URL is canonical; APP_BASE_URL is a deprecated backward-
    compatible alias (historically the only variable read here)."""
    return os.environ.get("FRONTEND_BASE_URL") or os.environ.get("APP_BASE_URL") or ""


@dataclass
class EmailConfig:
    api_key: Optional[str]
    sender: Optional[str]
    frontend_base_url: Optional[str]
    dry_run: bool
    provider: str  # always "resend"

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.sender and self.frontend_base_url)


def _config() -> EmailConfig:
    return EmailConfig(
        api_key=os.environ.get("RESEND_API_KEY") or None,
        sender=os.environ.get("EMAIL_FROM") or None,
        frontend_base_url=_frontend_base_url() or None,
        dry_run=os.environ.get("EMAIL_DRY_RUN", "1") == "1",
        provider=os.environ.get("EMAIL_PROVIDER", "resend").lower(),
    )


def is_live() -> bool:
    """Convenience flag for /api/health-style introspection."""
    c = _config()
    return c.configured and not c.dry_run


def absolute_url(path: str) -> str:
    """Join a relative path with FRONTEND_BASE_URL — falls back to the path as-is."""
    base = _frontend_base_url()
    if not base:
        return path
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


# --------------------------- Core send (retry-aware) --------------------------
async def _send_via_resend(*, to: str, subject: str, html: str, text: Optional[str] = None) -> Optional[str]:
    """Thin wrapper around the (synchronous) Resend SDK. Returns the email id."""
    import resend  # local import — keeps import-time cheap when not configured

    cfg = _config()
    resend.api_key = cfg.api_key
    params = {"from": cfg.sender, "to": [to], "subject": subject, "html": html}
    if text:
        params["text"] = text
    logger.debug("[resend:REQUEST] from=%s to=%s subject=%r", cfg.sender, to, subject)
    try:
        res = await asyncio.wait_for(
            asyncio.to_thread(resend.Emails.send, params),
            timeout=10.0,
        )
    except asyncio.TimeoutError:
        logger.error("[resend:TIMEOUT] Resend API did not respond within 10s — to=%s", to)
        raise TimeoutError("Resend API did not respond within 10s")
    eid = (res or {}).get("id") if isinstance(res, dict) else None
    logger.debug("[resend:RESPONSE] id=%s", eid)
    return eid


async def send_email(*, to: str, subject: str, html: str, text: Optional[str] = None,
                     event_kind: str = "transactional",
                     max_attempts: int = 3) -> dict:
    """Send (or log) a single email. Always returns a result dict for caller logging.

    Result shape: {"ok": bool, "mode": "live"|"dry_run"|"unconfigured"|"skipped", "id": str|None, "error": str|None}
    """
    cfg = _config()
    logger.debug("[email:CONFIG] api_key_set=%s sender=%s dry_run=%s configured=%s",
                 bool(cfg.api_key), cfg.sender, cfg.dry_run, cfg.configured)
    # Dry-run / unconfigured path
    if not cfg.configured:
        logger.warning("[email:UNCONFIGURED] kind=%s to=%s — RESEND_API_KEY, EMAIL_FROM or FRONTEND_BASE_URL missing",
                       event_kind, to)
        return {"ok": True, "mode": "unconfigured", "id": None, "error": None}
    if cfg.dry_run:
        logger.info("[email:DRY_RUN] kind=%s to=%s subject=%s", event_kind, to, subject)
        return {"ok": True, "mode": "dry_run", "id": None, "error": None}

    # Live send with exponential backoff
    last_err: Optional[str] = None
    delay = 0.5
    for attempt in range(1, max_attempts + 1):
        try:
            eid = await _send_via_resend(to=to, subject=subject, html=html, text=text)
            logger.info("[email:OK] kind=%s to=%s id=%s (attempt %d)", event_kind, to, eid, attempt)
            try:
                await _record_send(to=to, subject=subject, kind=event_kind, eid=eid, status="sent")
            except Exception:
                pass
            return {"ok": True, "mode": "live", "id": eid, "error": None}
        except Exception as e:
            last_err = str(e)
            logger.warning("[email:RETRY %d/%d] kind=%s to=%s err=%s", attempt, max_attempts, event_kind, to, e)
            if attempt < max_attempts:
                await asyncio.sleep(delay)
                delay *= 2

    logger.error("[email:FAIL] kind=%s to=%s err=%s", event_kind, to, last_err)
    try:
        await _record_send(to=to, subject=subject, kind=event_kind, eid=None, status="failed", error=last_err)
    except Exception:
        pass
    return {"ok": False, "mode": "live", "id": None, "error": last_err}


async def _record_send(*, to: str, subject: str, kind: str, eid: Optional[str],
                       status: str, error: Optional[str] = None) -> None:
    from datetime import datetime, timezone
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.email_log.insert_one({
        "to": to, "subject": subject, "kind": kind,
        "provider_id": eid, "status": status, "error": error,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


# ------------------------------ User helper -----------------------------------
async def _user_doc(user_id: str) -> Optional[dict]:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        return await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None


async def _user_email_name(user_id: str) -> Optional[tuple]:
    u = await _user_doc(user_id)
    if not u or not u.get("email"):
        return None
    return u.get("email"), u.get("full_name") or u.get("first_name") or ""


async def _send_to_user(*, user_id: str, category, subject: str, html: str,
                        text: Optional[str], event_kind: str) -> dict:
    """Preference-gated send: fetches the user, checks the category against
    their preferences (mandatory categories always pass), then sends."""
    from services.email.categories import should_send

    u = await _user_doc(user_id)
    if not u or not u.get("email"):
        return {"ok": False, "mode": "skipped", "error": "user not found"}
    if not should_send(u, category):
        logger.info("[email:PREF_SKIP] kind=%s user=%s category=%s", event_kind, user_id, category.value)
        return {"ok": True, "mode": "skipped_preference", "id": None, "error": None}
    return await send_email(to=u["email"], subject=subject, html=html, text=text, event_kind=event_kind)


# ------------------------------ Typed triggers --------------------------------
async def send_welcome_email(*, user_id: str) -> dict:
    from services.email.categories import EmailCategory
    em = await _user_email_name(user_id)
    if not em: return {"ok": False, "mode": "skipped", "error": "user not found"}
    _to, name = em
    subject, html, text = T.welcome_email(
        recipient_name=name,
        profile_setup_url=absolute_url("/profile-setup"),
        app_url=absolute_url("/discover"),
    )
    return await _send_to_user(user_id=user_id, category=EmailCategory.TRANSACTIONAL,
                               subject=subject, html=html, text=text, event_kind="welcome")


async def send_email_verification(*, user_id: str, token: str, expires_in_hours: int = 24) -> dict:
    from services.email.categories import EmailCategory
    em = await _user_email_name(user_id)
    if not em: return {"ok": False, "mode": "skipped", "error": "user not found"}
    _to, name = em
    verify_url = absolute_url(f"/verify-email?token={token}")
    subject, html, text = T.email_verification_email(recipient_name=name, verify_url=verify_url,
                                                      expires_in_hours=expires_in_hours)
    return await _send_to_user(user_id=user_id, category=EmailCategory.SECURITY,
                               subject=subject, html=html, text=text, event_kind="email_verification")


async def send_getting_started_email(*, user_id: str, completion_pct: int,
                                     remaining_tasks: list[tuple[str, bool]]) -> dict:
    from services.email.categories import EmailCategory
    em = await _user_email_name(user_id)
    if not em: return {"ok": False, "mode": "skipped", "error": "user not found"}
    _to, name = em
    subject, html, text = T.getting_started_email(
        recipient_name=name, completion_pct=completion_pct, remaining_tasks=remaining_tasks,
        profile_setup_url=absolute_url("/profile-setup"),
    )
    return await _send_to_user(user_id=user_id, category=EmailCategory.PRODUCT_UPDATES,
                               subject=subject, html=html, text=text, event_kind="getting_started")


async def send_password_reset(*, user_id: str, token: str, expires_in_minutes: int = 30) -> dict:
    from services.email.categories import EmailCategory
    em = await _user_email_name(user_id)
    if not em: return {"ok": False, "mode": "skipped", "error": "user not found"}
    _to, name = em
    reset_url = absolute_url(f"/reset-password?token={token}")
    subject, html, text = T.password_reset_email(recipient_name=name, reset_url=reset_url,
                                                 expires_in_minutes=expires_in_minutes)
    return await _send_to_user(user_id=user_id, category=EmailCategory.SECURITY,
                               subject=subject, html=html, text=text, event_kind="password_reset")


async def send_workspace_invitation(*, recipient_user_id: str, workspace_id: str,
                                    workspace_name: str, role: str, inviter_name: str) -> dict:
    from services.email.categories import EmailCategory
    em = await _user_email_name(recipient_user_id)
    if not em: return {"ok": False, "mode": "skipped", "error": "user not found"}
    _to, name = em
    accept_url = absolute_url(f"/workspaces/{workspace_id}")
    subject, html, text = T.workspace_invitation_email(
        recipient_name=name, workspace_name=workspace_name, role=role,
        inviter_name=inviter_name, accept_url=accept_url,
    )
    return await _send_to_user(user_id=recipient_user_id, category=EmailCategory.TRANSACTIONAL,
                               subject=subject, html=html, text=text, event_kind="workspace_invitation")


async def send_review_request(*, reviewer_user_id: str, manuscript_id: str,
                              manuscript_title: str, requester_name: str,
                              section: str = "", note: str = "") -> dict:
    from services.email.categories import EmailCategory
    em = await _user_email_name(reviewer_user_id)
    if not em: return {"ok": False, "mode": "skipped", "error": "user not found"}
    _to, name = em
    review_url = absolute_url(f"/manuscripts/{manuscript_id}")
    subject, html, text = T.review_request_email(
        recipient_name=name, manuscript_title=manuscript_title,
        requester_name=requester_name, section=section, note=note, review_url=review_url,
    )
    return await _send_to_user(user_id=reviewer_user_id, category=EmailCategory.TRANSACTIONAL,
                               subject=subject, html=html, text=text, event_kind="review_request")


async def send_collaboration_invitation(*, recipient_user_id: str, collaboration_id: str,
                                        collaboration_title: str, inviter_name: str,
                                        kind: str, message: str = "") -> dict:
    from services.email.categories import EmailCategory
    em = await _user_email_name(recipient_user_id)
    if not em: return {"ok": False, "mode": "skipped", "error": "user not found"}
    _to, name = em
    action_url = absolute_url(f"/collaborations/{collaboration_id}")
    subject, html, text = T.collaboration_invitation_email(
        recipient_name=name, collaboration_title=collaboration_title,
        inviter_name=inviter_name, kind=kind, action_url=action_url, message=message,
    )
    return await _send_to_user(user_id=recipient_user_id, category=EmailCategory.TRANSACTIONAL,
                               subject=subject, html=html, text=text, event_kind="collaboration_invitation")


# ---------------- Provider plug-in for notifications_service ------------------
# NOTE: kinds handled by an explicit typed trigger (workspace_invitation,
# review_request, application*) are deliberately EXCLUDED so we don't double-send.
# The bridge only catches future events that don't yet have a typed call-site.
EVENT_KIND_TO_EMAIL: set = set()


class ResendProvider(NotificationProvider):
    """Bridges in-app notifications → branded transactional emails.

    Routes by `event.kind`. Falls back to a generic notification email for any
    unhandled kind so we don't silently drop user-visible events.
    """
    name = "resend"

    async def send(self, event: NotificationEvent) -> None:
        if event.kind not in EVENT_KIND_TO_EMAIL:
            return  # in-app only — keep email volume sane
        em = await _user_email_name(event.user_id)
        if not em: return
        to, _name = em
        # Map kind → template
        actor_name = event.payload.get("actor_name", "")
        if event.kind == "workspace_invitation":
            await send_workspace_invitation(
                recipient_user_id=event.user_id,
                workspace_id=event.payload.get("workspace_id", ""),
                workspace_name=event.payload.get("workspace_name") or event.title.split(":")[-1].strip(),
                role=event.payload.get("role", "Researcher"),
                inviter_name=actor_name or event.body.split(" ")[0],
            )
        elif event.kind == "review_request":
            await send_review_request(
                reviewer_user_id=event.user_id,
                manuscript_id=event.payload.get("manuscript_id", ""),
                manuscript_title=event.payload.get("manuscript_title") or event.title.replace("Review requested: ", ""),
                requester_name=actor_name or event.body.split(" asked")[0],
                section=event.payload.get("section", ""),
                note=event.payload.get("note", ""),
            )
        elif event.kind in {"application", "application_decision"}:
            kind = "application" if event.kind == "application" else "decision"
            await send_collaboration_invitation(
                recipient_user_id=event.user_id,
                collaboration_id=event.payload.get("collaboration_id", ""),
                collaboration_title=event.payload.get("collaboration_title") or event.title.replace("New application", "").strip(),
                inviter_name=actor_name or "",
                kind=kind,
                message=event.payload.get("message", ""),
            )
        # review_response / review_verdict: just fall through to a lightweight notification body
        else:
            await send_email(
                to=to, subject=f"[SYNAPTIQ] {event.title}",
                html=f"<p>{event.body}</p><p><a href='{absolute_url(event.link or '/')}'>Open SYNAPTIQ</a></p>",
                event_kind=event.kind,
            )


def register() -> None:
    """Idempotent — called from server startup once notifications_service exists."""
    from services.notifications_service import register_provider, _providers
    if any(getattr(p, "name", None) == "resend" for p in _providers):
        return
    register_provider(ResendProvider())
    logger.info("ResendProvider registered (live=%s)", is_live())
