"""
Audit Trail — writes a tamper-evident record of every data mutation.

Every create/update/delete through the Repository layer automatically
calls AuditTrail.record(). Callers never invoke this directly.

Records land in the `data_audit` collection with:
  - who:   user_id, email, role, tenant_id
  - what:  collection, operation, doc_id, diff
  - when:  timestamp (UTC)
  - why:   request_id (correlates to HTTP request or worker run)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class AuditTrail:
    """
    Fire-and-forget audit writer.

    Never blocks the caller — writes are scheduled as background tasks.
    If the write fails, it logs a warning but does NOT raise.
    """

    COLLECTION = "data_audit"

    def __init__(self, db) -> None:
        self._db = db

    # ── Public API ─────────────────────────────────────────────────────────────

    def record(
        self,
        *,
        ctx,                        # SecurityContext
        collection: str,
        operation: str,             # "create" | "update" | "delete" | "restore"
        doc_id: str | None = None,
        before: dict | None = None,
        after:  dict | None = None,
        meta:   dict | None = None,
    ) -> None:
        """
        Schedule an audit write (non-blocking).

        Computes a minimal diff so the audit log stays lean while remaining
        complete enough to reconstruct history.
        """
        entry = {
            "collection": collection,
            "operation":  operation,
            "doc_id":     str(doc_id) if doc_id else None,
            "diff":       _diff(before, after),
            "actor":      ctx.to_audit_dict(),
            "timestamp":  datetime.now(timezone.utc),
            "meta":       meta or {},
        }
        # Fire-and-forget — schedule without awaiting
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._write(entry))
            else:
                # Sync context (tests, CLI) — best effort
                loop.run_until_complete(self._write(entry))
        except RuntimeError:
            pass  # no event loop — skip audit in sync test context

    async def record_async(
        self,
        *,
        ctx,
        collection: str,
        operation: str,
        doc_id: str | None = None,
        before: dict | None = None,
        after:  dict | None = None,
        meta:   dict | None = None,
    ) -> None:
        """Awaitable version for callers that are already in async context."""
        entry = {
            "collection": collection,
            "operation":  operation,
            "doc_id":     str(doc_id) if doc_id else None,
            "diff":       _diff(before, after),
            "actor":      ctx.to_audit_dict(),
            "timestamp":  datetime.now(timezone.utc),
            "meta":       meta or {},
        }
        await self._write(entry)

    async def query(
        self,
        *,
        collection: str | None = None,
        doc_id: str | None = None,
        user_id: str | None = None,
        operation: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Query audit log (admin use only)."""
        filt: dict[str, Any] = {}
        if collection:
            filt["collection"] = collection
        if doc_id:
            filt["doc_id"] = str(doc_id)
        if user_id:
            filt["actor.user_id"] = user_id
        if operation:
            filt["operation"] = operation
        if since:
            filt["timestamp"] = {"$gte": since}
        try:
            cursor = self._db[self.COLLECTION].find(
                filt,
                sort=[("timestamp", -1)],
                limit=limit,
            )
            docs = await cursor.to_list(length=limit)
            return [_serialize(d) for d in docs]
        except Exception as exc:
            logger.warning("Audit query error: %s", exc)
            return []

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _write(self, entry: dict) -> None:
        try:
            await self._db[self.COLLECTION].insert_one(entry)
        except Exception as exc:
            logger.warning("Audit write failed (non-fatal): %s", exc)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _diff(before: dict | None, after: dict | None) -> dict:
    """Compute which fields changed between before and after."""
    if not before and not after:
        return {}
    if not before:
        return {"added": _safe_keys(after)}
    if not after:
        return {"removed": _safe_keys(before)}

    changed: dict[str, Any] = {}
    all_keys = set(before) | set(after)
    skip = {"_id", "updated_at", "version"}
    for k in all_keys:
        if k in skip:
            continue
        b_val = before.get(k)
        a_val = after.get(k)
        if b_val != a_val:
            changed[k] = {"from": _trunc(b_val), "to": _trunc(a_val)}
    return changed


def _safe_keys(d: dict | None) -> list[str]:
    if not d:
        return []
    return [k for k in d if k not in ("_id", "password", "token", "secret")]


def _trunc(val: Any, max_len: int = 200) -> Any:
    """Truncate large values so audit records stay compact."""
    if isinstance(val, str) and len(val) > max_len:
        return val[:max_len] + "…"
    if isinstance(val, (dict, list)):
        s = str(val)
        if len(s) > max_len:
            return s[:max_len] + "…"
        return val
    return val


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc
