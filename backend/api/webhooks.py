"""Webhook delivery system — Phase XXXV.7.

Webhooks are HMAC-SHA256 signed (X-Synaptiq-Signature header).
Delivery engine retries up to 3 times with exponential back-off.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_COL_HOOKS       = "api_webhooks"
_COL_DELIVERIES  = "api_webhook_deliveries"
_MAX_RETRIES     = 3
_RETRY_DELAYS    = (5, 30, 120)    # seconds between attempts


# ── Event types ───────────────────────────────────────────────────────────────

class WebhookEvent:
    MISSION_STARTED   = "mission.started"
    MISSION_COMPLETED = "mission.completed"
    MISSION_FAILED    = "mission.failed"
    AGENT_ACTION      = "agent.action"
    AI_REQUEST        = "ai.request"
    AI_COMPLETE       = "ai.complete"
    USER_CREATED      = "user.created"
    ALERT_FIRED       = "alert.fired"
    COST_THRESHOLD    = "cost.threshold"
    PUBLICATION_READY = "publication.ready"
    GRANT_MATCH       = "grant.match"
    REVIEW_ASSIGNED   = "review.assigned"

    ALL = (
        MISSION_STARTED, MISSION_COMPLETED, MISSION_FAILED,
        AGENT_ACTION, AI_REQUEST, AI_COMPLETE,
        USER_CREATED, ALERT_FIRED, COST_THRESHOLD,
        PUBLICATION_READY, GRANT_MATCH, REVIEW_ASSIGNED,
    )


# ── Models ────────────────────────────────────────────────────────────────────

@dataclass
class Webhook:
    webhook_id:  str
    user_id:     str
    url:         str
    events:      list[str]
    secret:      str           # HMAC signing secret (stored plain — only user knows it)
    name:        str           = ""
    active:      bool          = True
    created_at:  str           = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata:    dict          = field(default_factory=dict)

    def to_dict(self, *, hide_secret: bool = True) -> dict:
        d = {
            "webhook_id": self.webhook_id,
            "user_id":    self.user_id,
            "url":        self.url,
            "events":     self.events,
            "name":       self.name,
            "active":     self.active,
            "created_at": self.created_at,
        }
        if not hide_secret:
            d["secret"] = self.secret
        return d


@dataclass
class WebhookDelivery:
    delivery_id:  str
    webhook_id:   str
    event:        str
    payload:      dict
    attempt:      int   = 1
    success:      bool  = False
    status_code:  int   = 0
    error:        str   = ""
    delivered_at: str   = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


# ── HMAC signing ──────────────────────────────────────────────────────────────

def sign_payload(secret: str, body: bytes) -> str:
    """Return HMAC-SHA256 signature as 'sha256=<hex>'."""
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    expected = sign_payload(secret, body)
    return hmac.compare_digest(expected, signature)


# ── Delivery engine ───────────────────────────────────────────────────────────

class WebhookEngine:

    def __init__(self, db: Any) -> None:
        self._db      = db
        self._hooks   = db[_COL_HOOKS]
        self._deliv   = db[_COL_DELIVERIES]

    async def ensure_indexes(self) -> None:
        try:
            await self._hooks.create_index("webhook_id", unique=True)
            await self._hooks.create_index("user_id")
            await self._deliv.create_index("webhook_id")
            await self._deliv.create_index("event")
            await self._deliv.create_index("delivered_at")
        except Exception as exc:
            logger.debug("Webhook index creation: %s", exc)

    # ── Registration ──────────────────────────────────────────────────────────

    async def create(
        self,
        user_id: str,
        url:     str,
        events:  list[str],
        name:    str  = "",
        metadata: dict | None = None,
    ) -> dict:
        webhook_id = "wh_" + secrets.token_hex(8)
        secret     = "whsec_" + secrets.token_hex(24)
        hook = Webhook(
            webhook_id = webhook_id,
            user_id    = user_id,
            url        = url,
            events     = events,
            secret     = secret,
            name       = name,
            metadata   = metadata or {},
        )
        doc = hook.__dict__.copy()
        await self._hooks.insert_one(doc)
        result = hook.to_dict(hide_secret=False)   # expose secret once at creation
        return result

    async def update(self, webhook_id: str, user_id: str, **updates) -> bool:
        allowed = {"url", "events", "name", "active", "metadata"}
        update  = {k: v for k, v in updates.items() if k in allowed}
        if not update:
            return False
        result = await self._hooks.update_one(
            {"webhook_id": webhook_id, "user_id": user_id},
            {"$set": update},
        )
        return result.modified_count > 0

    async def delete(self, webhook_id: str, user_id: str) -> bool:
        result = await self._hooks.delete_one({"webhook_id": webhook_id, "user_id": user_id})
        return result.deleted_count > 0

    async def list_for_user(self, user_id: str) -> list[dict]:
        docs = []
        async for doc in self._hooks.find({"user_id": user_id}).sort("created_at", -1):
            doc.pop("_id", None)
            doc.pop("secret", None)
            docs.append(doc)
        return docs

    # ── Dispatch ──────────────────────────────────────────────────────────────

    async def dispatch(self, event: str, payload: dict) -> None:
        """Find all active webhooks subscribed to event and enqueue deliveries."""
        async for doc in self._hooks.find({"active": True, "events": event}):
            asyncio.create_task(self._deliver(doc, event, payload))

    async def _deliver(self, hook: dict, event: str, payload: dict, attempt: int = 1) -> None:
        delivery_id = "dlv_" + secrets.token_hex(8)
        body_dict   = {"event": event, "data": payload, "webhook_id": hook["webhook_id"]}
        body_bytes  = json.dumps(body_dict, default=str).encode()
        signature   = sign_payload(hook["secret"], body_bytes)

        success     = False
        status_code = 0
        error_msg   = ""

        try:
            import httpx  # optional dep; graceful if missing
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    hook["url"],
                    content   = body_bytes,
                    headers   = {
                        "Content-Type":         "application/json",
                        "X-Synaptiq-Signature": signature,
                        "X-Synaptiq-Event":     event,
                        "X-Delivery-ID":        delivery_id,
                    },
                )
                status_code = resp.status_code
                success     = 200 <= resp.status_code < 300
        except ImportError:
            error_msg = "httpx not installed — webhook delivery skipped"
            logger.warning("Webhook delivery skipped: httpx not installed")
        except Exception as exc:
            error_msg = str(exc)
            logger.warning("Webhook delivery attempt %d failed: %s", attempt, exc)

        rec = {
            "delivery_id":  delivery_id,
            "webhook_id":   hook["webhook_id"],
            "event":        event,
            "payload":      body_dict,
            "attempt":      attempt,
            "success":      success,
            "status_code":  status_code,
            "error":        error_msg,
            "delivered_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await self._deliv.insert_one(rec)
        except Exception:
            pass

        if not success and attempt < _MAX_RETRIES and not error_msg.startswith("httpx"):
            delay = _RETRY_DELAYS[attempt - 1]
            await asyncio.sleep(delay)
            await self._deliver(hook, event, payload, attempt + 1)

    async def deliveries(self, webhook_id: str, limit: int = 50) -> list[dict]:
        docs = []
        async for doc in self._deliv.find({"webhook_id": webhook_id}).sort("delivered_at", -1).limit(limit):
            doc.pop("_id", None)
            docs.append(doc)
        return docs


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: WebhookEngine | None = None


def init_webhook_engine(db: Any) -> None:
    global _engine
    _engine = WebhookEngine(db)


def get_webhook_engine() -> WebhookEngine:
    if _engine is None:
        raise RuntimeError("WebhookEngine not initialised")
    return _engine
