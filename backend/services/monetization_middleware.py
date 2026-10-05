"""Monetization middleware (pure ASGI) — two jobs on every /api request:

1. Route access policy. Most routers predate the tier model and carry no
   plan gate, so FREE restrictions (identity only — no network, messaging,
   collaboration, projects, workspaces, discovery, teaching) are enforced
   here from one auditable table, rather than by editing 100+ routers. The
   rules are prefix-based and server-side; the client cannot influence them.
   Reads (GET) of a user's OWN data areas stay allowed so a downgrade never
   hides research data — it becomes read-only.
   Workspace writes are also blocked when the workspace is locked because
   its owner is above their plan's workspace limit (after a downgrade).

2. AI credit request context. Opens the per-request context that
   services/credits_service.py records reservations in, reads the client's
   Idempotency-Key header, and when the request ends finalizes every
   reservation: COMPLETED if the response status is < 400, otherwise
   RELEASED (refunded) — so a failed AI request is never charged, whatever
   the endpoint's own error handling does.

AI usage itself is gated at the credit chokepoint (consume_credits rejects
FREE / lapsed plans), which covers every credit-billed AI endpoint.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from fastapi import HTTPException
from starlette.requests import Request

logger = logging.getLogger("synaptiq.monetization")

READ = frozenset({"GET", "HEAD"})
WRITE = frozenset({"POST", "PUT", "PATCH", "DELETE"})
ALL = READ | WRITE


@dataclass(frozen=True)
class Rule:
    pattern: re.Pattern
    methods: frozenset
    capability: str


def _r(regex: str, methods: frozenset, capability: str) -> Rule:
    return Rule(re.compile(regex), methods, capability)


# First match wins — specific rules before general ones.
RULES: tuple[Rule, ...] = (
    # Collaboration: Free may READ invitations sent to them (and see the
    # "Upgrade to Pro to respond" prompt) but not send or respond.
    _r(r"^/api/collaboration-requests/?$", frozenset({"POST"}), "can_send_collaboration_request"),
    _r(r"^/api/collaboration-requests/[^/]+/?$", frozenset({"PATCH", "PUT"}), "can_accept_collaboration"),
    _r(r"^/api/workspaces/invitations/[^/]+/respond/?$", WRITE, "can_join_collaboration_workflows"),
    _r(r"^/api/teaching/workspace-invitations/", WRITE, "can_join_collaboration_workflows"),
    _r(r"^/api/collaborations(/|$)", ALL, "can_join_collaboration_workflows"),
    _r(r"^/api/(grant-hub|conference-teams|team-builder|meetings)(/|$)", ALL, "can_join_collaboration_workflows"),
    # Messaging: history stays readable after a downgrade; sending is Pro.
    _r(r"^/api/(conversations|uploads)(/|$)", WRITE, "can_message_researchers"),
    # Research network, researcher discovery and matching.
    _r(r"^/api/(network|researchers|discover|research-need|expertise|reviewer-marketplace|marketplace|acad-market)(/|$)",
       ALL, "can_use_research_network"),
    # Journal / conference / grant discovery.
    _r(r"^/api/journals(/|$)", ALL, "can_use_journal_discovery"),
    _r(r"^/api/conferences(/|$)", ALL, "can_use_conference_discovery"),
    _r(r"^/api/(grants|funding)(/|$)", ALL, "can_use_grant_discovery"),
    # Projects / workspaces and the research data inside them: read-only on Free.
    _r(r"^/api/projects(/|$)", WRITE, "can_create_project"),
    _r(r"^/api/(manuscripts|grant-applications|repository)(/|$)", WRITE, "can_create_project"),
    _r(r"^/api/workspaces(/|$)", WRITE, "can_create_workspace"),
    _r(r"^/api/items(/|$)", WRITE, "can_create_workspace"),
    # Teaching Hub.
    _r(r"^/api/teaching-analytics(/|$)", ALL, "can_use_teaching_hub"),
    _r(r"^/api/teaching(/|$)", WRITE, "can_use_teaching_hub"),
    # Analytics and Pro Advanced intelligence surfaces.
    _r(r"^/api/analytics(/|$)", ALL, "can_view_research_analytics"),
    _r(r"^/api/impact/users/", READ, "can_use_research_network"),
    _r(r"^/api/impact(/|$)", ALL, "can_view_impact_dashboard"),
    _r(r"^/api/research-impact(/|$)", ALL, "can_view_impact_dashboard"),
    _r(r"^/api/citation-monitoring(/|$)", ALL, "can_use_citation_monitoring"),
    _r(r"^/api/(collaboration-intelligence|collab-intelligence)(/|$)", ALL, "can_use_collaboration_intelligence"),
    _r(r"^/api/publication-hub(/|$)", WRITE, "can_use_publication_tracking"),
    # Buying credits is for paid plans only.
    _r(r"^/api/billing/credit-pack-checkout/?$", frozenset({"POST"}), "can_purchase_ai_credits"),
)

# Always allowed, whatever the plan: deleting or leaving your own project or
# workspace (so a downgraded user can tidy up and free a slot).
_ALWAYS_ALLOWED: tuple[tuple[str, re.Pattern], ...] = (
    ("DELETE", re.compile(r"^/api/(workspaces|projects)/[0-9a-f]{24}/?$")),
    ("POST", re.compile(r"^/api/workspaces/[0-9a-f]{24}/leave/?$")),
)

# Workspace-scoped write paths whose workspace can be locked after a downgrade.
_WORKSPACE_WRITE = re.compile(r"^/api/workspaces/([0-9a-f]{24})(/.*)?$")
# Writes that must stay possible on a locked workspace so the owner can free a slot.
_LOCK_EXEMPT = re.compile(r"^/api/workspaces/[0-9a-f]{24}/?(leave/?)?$")

_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9_.:\-]{8,128}$")


def match_rule(method: str, path: str) -> Rule | None:
    for m, pattern in _ALWAYS_ALLOWED:
        if method == m and pattern.match(path):
            return None
    for rule in RULES:
        if method in rule.methods and rule.pattern.search(path):
            return rule
    return None


async def _json_response(send, status: int, detail: dict) -> None:
    body = json.dumps({"detail": detail}).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})


async def _authenticated_user(scope, receive) -> dict | None:
    from auth_utils import get_current_user
    try:
        user = await get_current_user(Request(scope, receive))
    except HTTPException:
        return None   # let the endpoint produce its own 401/403
    user = dict(user)
    user.setdefault("id", str(user.get("_id")))
    return user


async def _workspace_lock_error(user: dict, workspace_id: str) -> dict | None:
    from bson import ObjectId
    from db import get_db
    from repo.shim import DBProxy
    from repo.security_context import SecurityContext
    from services.entitlements import get_entitlements, locked_workspace_ids

    db = DBProxy(get_db(), SecurityContext.system())
    ws = await db.workspaces.find_one({"_id": ObjectId(workspace_id)}, {"owner_id": 1})
    if not ws:
        return None
    owner = user
    if ws.get("owner_id") != user["id"]:
        owner = await db.users.find_one({"_id": ObjectId(ws["owner_id"])}) if ws.get("owner_id") else None
        if not owner:
            return None
        owner = dict(owner, id=str(owner["_id"]))
    if workspace_id not in await locked_workspace_ids(owner, db):
        return None
    limit = get_entitlements(owner)["workspace_limit"]
    own = owner is user
    return {
        "code": "workspace_locked",
        "message": (
            (f"This workspace is read-only: your plan includes {limit} workspace{'s' if limit != 1 else ''}. "
             "Upgrade, or delete a workspace you no longer need, to unlock it.") if own else
            "This workspace is read-only because its owner's plan no longer covers it."
        ),
        "workspace_id": workspace_id,
        "workspace_limit": limit,
        "upgrade_url": "/pricing",
    }


class MonetizationMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith("/api/"):
            return await self.app(scope, receive, send)

        method = scope.get("method", "GET")
        path = scope["path"]

        rule = match_rule(method, path)
        ws_match = _WORKSPACE_WRITE.match(path) if method in WRITE else None
        if rule or (ws_match and not _LOCK_EXEMPT.match(path)):
            user = await _authenticated_user(scope, receive)
            if user is not None:
                from services.entitlements import has_capability, capability_denied
                from services.permissions import is_super_admin
                if not is_super_admin(user):
                    if rule and not has_capability(user, rule.capability):
                        exc = capability_denied(rule.capability, user)
                        await _track_denied(user, rule.capability, path)
                        return await _json_response(send, exc.status_code, exc.detail)
                    if ws_match and not _LOCK_EXEMPT.match(path):
                        lock = await _workspace_lock_error(user, ws_match.group(1))
                        if lock:
                            return await _json_response(send, 402, lock)

        # AI credit request context.
        from services.credits_service import (
            close_request_context, finalize_request_reservations, open_request_context,
        )
        key = None
        for name, value in scope.get("headers") or []:
            if name == b"idempotency-key":
                candidate = value.decode("latin-1").strip()
                if _IDEMPOTENCY_KEY.match(candidate):
                    key = candidate
                break
        token = open_request_context(key)
        status_holder = {"status": 500}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        from services.credits_service import current_request_context
        ctx = current_request_context()
        try:
            await self.app(scope, receive, send_wrapper)
        except BaseException:
            if ctx and ctx["reservations"]:
                await finalize_request_reservations(ctx, success=False, reason="unhandled_exception")
            raise
        else:
            if ctx and ctx["reservations"]:
                ok = status_holder["status"] < 400
                await finalize_request_reservations(
                    ctx, success=ok, reason="" if ok else f"http_{status_holder['status']}")
        finally:
            close_request_context(token)


async def _track_denied(user: dict, capability: str, path: str) -> None:
    try:
        from services.product_analytics import track_server_event
        await track_server_event(user["id"], "paid_feature_attempted",
                                 {"feature": capability, "path": path,
                                  "plan_code": user.get("plan_code") or "free"})
    except Exception:
        pass
