"""Centralized audit logger.

Append-only `audit_log` collection capturing every security-sensitive or
compliance-relevant action: billing, subscription, credit, reward, coupon, and
super-admin operations.

Schema:
  {actor_id, actor_email, actor_role, action, entity_kind, entity_id,
   target_user_id, before, after, metadata, ip, user_agent, created_at}
"""
from __future__ import annotations
from datetime import datetime, timezone

from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext


async def write_audit(
    *, actor: dict | None, action: str, entity_kind: str = "", entity_id: str = "",
    target_user_id: str | None = None, before: dict | None = None,
    after: dict | None = None, metadata: dict | None = None,
    ip: str = "", user_agent: str = "",
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.audit_log.insert_one({
        "actor_id": (actor or {}).get("id"),
        "actor_email": (actor or {}).get("email"),
        "actor_role": (actor or {}).get("role", "user"),
        "action": action,
        "entity_kind": entity_kind,
        "entity_id": entity_id,
        "target_user_id": target_user_id,
        "before": before,
        "after": after,
        "metadata": metadata or {},
        "ip": ip,
        "user_agent": user_agent,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
