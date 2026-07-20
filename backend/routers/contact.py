"""Public contact-form endpoint.

Receives submissions from the marketing Contact page and forwards them to
admin@synaptiq.academy via the standard email service. Rate-limited to 5
requests per IP per hour to prevent abuse.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Optional

import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator

from services.email_service import send_email

logger = logging.getLogger("synaptiq.contact")

router = APIRouter(prefix="/api/contact", tags=["contact"])


def _admin_email() -> str:
    return os.environ.get("ADMIN_EMAIL", "admin@synaptiq.academy")

_rate_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 5
_RATE_WINDOW = 3600


def _check_rate(ip: str) -> None:
    now = time.monotonic()
    calls = _rate_store[ip]
    _rate_store[ip] = [t for t in calls if now - t < _RATE_WINDOW]
    if len(_rate_store[ip]) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many contact form submissions. Please wait before trying again.")
    _rate_store[ip].append(now)


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    topic: str
    message: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        if len(v) > 120:
            raise ValueError("Name too long")
        return v

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message is required")
        if len(v) > 4000:
            raise ValueError("Message too long (max 4000 characters)")
        return v

    @field_validator("topic")
    @classmethod
    def topic_allowed(cls, v: str) -> str:
        allowed = {"general", "institution", "press", "support"}
        if v not in allowed:
            raise ValueError(f"Topic must be one of: {', '.join(sorted(allowed))}")
        return v


TOPIC_LABELS = {
    "general": "General enquiry",
    "institution": "Institution plan",
    "press": "Press / partnerships",
    "support": "Product support",
}


@router.post("")
async def submit_contact(payload: ContactRequest, request: Request):
    ip = request.client.host if request.client else "unknown"
    _check_rate(ip)

    topic_label = TOPIC_LABELS.get(payload.topic, payload.topic)
    subject = f"[Contact Form] {topic_label} — {payload.name}"
    html = f"""\
<!doctype html>
<html><body style="font-family:sans-serif;color:#0F172A;max-width:600px;margin:32px auto;padding:0 16px;">
  <h2 style="font-family:Georgia,serif;color:#0F2847;">New contact form submission</h2>
  <table style="border-collapse:collapse;width:100%;font-size:14px;">
    <tr><td style="padding:8px 12px;background:#F8FAFC;font-weight:600;width:30%;">Name</td><td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;">{payload.name}</td></tr>
    <tr><td style="padding:8px 12px;background:#F8FAFC;font-weight:600;">Email</td><td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;"><a href="mailto:{payload.email}">{payload.email}</a></td></tr>
    <tr><td style="padding:8px 12px;background:#F8FAFC;font-weight:600;">Topic</td><td style="padding:8px 12px;border-bottom:1px solid #E2E8F0;">{topic_label}</td></tr>
    <tr><td style="padding:8px 12px;background:#F8FAFC;font-weight:600;vertical-align:top;">Message</td><td style="padding:8px 12px;white-space:pre-wrap;">{payload.message}</td></tr>
  </table>
  <p style="margin-top:24px;font-size:12px;color:#64748B;">Submitted via synaptiq.academy contact form · Reply directly to {payload.email}</p>
</body></html>"""

    admin_email = _admin_email()
    result = await send_email(
        to=admin_email,
        subject=subject,
        html=html,
        event_kind="contact_form",
    )

    if not result.get("ok") and result.get("mode") == "live":
        logger.error("Contact form delivery failed: %s", result.get("error"))
        raise HTTPException(
            status_code=502,
            detail=f"Message could not be delivered. Please email {admin_email} directly.",
        )

    return {"ok": True}
