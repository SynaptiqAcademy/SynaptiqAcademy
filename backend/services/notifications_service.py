"""Notification service abstraction (architecture only — providers are pluggable).

Usage from any router:
    from services.notifications_service import dispatch, NotificationEvent
    await dispatch(NotificationEvent(
        user_id=user_id, kind="message", title="...", body="...", link="/messages/c/123",
        actor_id=sender_id, payload={"conversation_id": ...},
    ))

Always writes an in-app notification (the `notifications` collection). Then fans the
event out to each registered provider — email, push, slack, etc. Providers are async
and may no-op when not configured. Failures are caught per-provider so one broken
channel never breaks the rest.

Adding Resend later (future work):
    1. pip install resend
    2. Create services/providers/resend_provider.py implementing async send(event)
       (call resend.Emails.send with from/to/subject/html templated from event).
    3. In services/notifications_service.register_default_providers(), append
       ResendProvider(os.environ["RESEND_API_KEY"]) when the env var is set.
    4. No call-site changes — every existing dispatch(...) now also emails.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from bson import ObjectId

from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.notifications")


@dataclass
class NotificationEvent:
    user_id: str                       # recipient
    kind: str                          # "message" | "mention" | "application" | ...
    title: str
    body: str = ""
    link: str = ""
    actor_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)


class NotificationProvider:
    """Implement send(event) async. Must be idempotent and silent-on-failure."""
    name: str = "base"

    async def send(self, event: NotificationEvent) -> None:  # pragma: no cover
        raise NotImplementedError


class InAppProvider(NotificationProvider):
    """Persist into the notifications collection so the bell shows it. Also pushed
    to the recipient's user-channel WebSocket so the badge updates live."""
    name = "in-app"

    async def send(self, event: NotificationEvent) -> None:
        db = get_db()
        db = DBProxy(db, SecurityContext.system())

        doc = {
            "user_id": event.user_id,
            "type": event.kind,
            "title": event.title,
            "body": event.body,
            "link": event.link,
            "actor_id": event.actor_id,
            "payload": event.payload,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.notifications.insert_one(doc)
        # Live push to badge consumers
        try:
            from services.realtime import manager
            await manager.broadcast_user(event.user_id, {
                "type": "notification",
                "kind": event.kind,
                "title": event.title,
                "body": event.body,
                "link": event.link,
            })
        except Exception as e:
            logger.debug("WS push failed: %s", e)


class EmailProviderStub(NotificationProvider):
    """Placeholder for the future Resend integration. Logs only.

    When RESEND_API_KEY is set, replace this with a real provider that templates
    the event into an HTML email (see module docstring)."""
    name = "email-stub"

    async def send(self, event: NotificationEvent) -> None:
        if os.environ.get("DISABLE_EMAIL_STUB") == "1":
            return
        logger.info("[email-stub] would email user_id=%s kind=%s title=%s",
                    event.user_id, event.kind, event.title)


_providers: List[NotificationProvider] = []
_hooks: List[Callable[[NotificationEvent], Awaitable[None]]] = []


def register_provider(p: NotificationProvider) -> None:
    _providers.append(p)


def register_hook(hook: Callable[[NotificationEvent], Awaitable[None]]) -> None:
    """Lightweight observer (e.g. analytics) — fired alongside providers."""
    _hooks.append(hook)


def register_default_providers() -> None:
    if _providers:  # idempotent
        return
    register_provider(InAppProvider())
    # ResendProvider is registered by services.email_service.register() during
    # startup so it can read RESEND_API_KEY without circular imports at module load.


async def dispatch(event: NotificationEvent) -> None:
    for p in _providers:
        try:
            await p.send(event)
        except Exception as e:
            logger.exception("[%s] dispatch failed: %s", p.name, e)
    for h in _hooks:
        try:
            await h(event)
        except Exception as e:
            logger.debug("hook failed: %s", e)


def event_dict(event: NotificationEvent) -> dict:
    return asdict(event)
