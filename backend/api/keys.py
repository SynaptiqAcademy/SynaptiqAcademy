"""Enterprise API Key management — Phase XXXV.7.

Keys are in the form  sk-syn-<24-char hex>.
Only the SHA-256 hash is stored; the raw key is returned once at creation.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_KEY_PREFIX  = "sk-syn-"
_SUFFIX_BITS = 96      # 24 hex chars
_COLLECTION  = "api_keys"

SCOPE_READ   = "read"
SCOPE_WRITE  = "write"
SCOPE_ADMIN  = "admin"
ALL_SCOPES   = (SCOPE_READ, SCOPE_WRITE, SCOPE_ADMIN)


# ── Models ────────────────────────────────────────────────────────────────────

@dataclass
class ApiKeyRecord:
    key_id:      str
    key_hash:    str
    prefix:      str           # first 12 chars for display (sk-syn-XXXXXX)
    name:        str
    user_id:     str
    scopes:      list[str]
    created_at:  str
    expires_at:  str | None    = None
    last_used:   str | None    = None
    revoked:     bool          = False
    revoked_at:  str | None    = None
    usage_count: int           = 0
    workspace_id: str | None   = None
    metadata:    dict          = field(default_factory=dict)

    def to_dict(self, *, include_hash: bool = False) -> dict:
        d = {
            "key_id":      self.key_id,
            "prefix":      self.prefix,
            "name":        self.name,
            "user_id":     self.user_id,
            "scopes":      self.scopes,
            "created_at":  self.created_at,
            "expires_at":  self.expires_at,
            "last_used":   self.last_used,
            "revoked":     self.revoked,
            "usage_count": self.usage_count,
        }
        if include_hash:
            d["key_hash"] = self.key_hash
        return d


# ── Manager ───────────────────────────────────────────────────────────────────

class ApiKeyManager:

    def __init__(self, db: Any) -> None:
        self._db  = db
        self._col = db[_COLLECTION]

    async def ensure_indexes(self) -> None:
        try:
            await self._col.create_index("key_hash", unique=True)
            await self._col.create_index("key_id",   unique=True)
            await self._col.create_index("user_id")
        except Exception as exc:
            logger.debug("ApiKey index creation: %s", exc)

    # ── Create ────────────────────────────────────────────────────────────────

    def _generate(self) -> tuple[str, str, str]:
        """Returns (raw_key, key_hash, prefix)."""
        suffix   = secrets.token_hex(_SUFFIX_BITS // 8)
        raw_key  = _KEY_PREFIX + suffix
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix   = raw_key[:16]           # sk-syn-XXXXXXXX (16 chars visible)
        return raw_key, key_hash, prefix

    async def create(
        self,
        name:         str,
        user_id:      str,
        scopes:       list[str],
        expires_at:   str | None  = None,
        workspace_id: str | None  = None,
        metadata:     dict | None = None,
    ) -> tuple[str, dict]:
        """
        Create a new API key.

        Returns (raw_key, record_dict).
        raw_key is returned exactly once — it cannot be recovered later.
        """
        raw_key, key_hash, prefix = self._generate()
        now    = datetime.now(timezone.utc).isoformat()
        key_id = "key_" + secrets.token_hex(8)

        doc = {
            "key_id":      key_id,
            "key_hash":    key_hash,
            "prefix":      prefix,
            "name":        name,
            "user_id":     user_id,
            "scopes":      scopes,
            "created_at":  now,
            "expires_at":  expires_at,
            "last_used":   None,
            "revoked":     False,
            "revoked_at":  None,
            "usage_count": 0,
            "workspace_id": workspace_id,
            "metadata":    metadata or {},
        }
        await self._col.insert_one(doc)
        return raw_key, {k: v for k, v in doc.items() if k not in ("_id", "key_hash")}

    # ── Validate ──────────────────────────────────────────────────────────────

    async def validate(self, raw_key: str) -> dict | None:
        """
        Validate a raw API key.

        Returns the record dict (without hash) if valid, None otherwise.
        Also bumps usage_count and last_used.
        """
        if not raw_key.startswith(_KEY_PREFIX):
            return None
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        doc = await self._col.find_one({"key_hash": key_hash})
        if not doc:
            return None
        if doc.get("revoked"):
            return None
        if doc.get("expires_at"):
            if datetime.fromisoformat(doc["expires_at"]) < datetime.now(timezone.utc):
                return None
        now = datetime.now(timezone.utc).isoformat()
        await self._col.update_one(
            {"key_hash": key_hash},
            {"$inc": {"usage_count": 1}, "$set": {"last_used": now}},
        )
        doc.pop("_id", None)
        doc.pop("key_hash", None)
        return doc

    # ── Revoke ────────────────────────────────────────────────────────────────

    async def revoke(self, key_id: str, user_id: str) -> bool:
        now    = datetime.now(timezone.utc).isoformat()
        result = await self._col.update_one(
            {"key_id": key_id, "user_id": user_id},
            {"$set": {"revoked": True, "revoked_at": now}},
        )
        return result.modified_count > 0

    # ── Rotate ────────────────────────────────────────────────────────────────

    async def rotate(self, key_id: str, user_id: str) -> tuple[str, dict] | tuple[None, None]:
        """Revoke an existing key and issue a new one with the same attributes."""
        doc = await self._col.find_one({"key_id": key_id, "user_id": user_id})
        if not doc:
            return None, None
        await self.revoke(key_id, user_id)
        return await self.create(
            name         = doc["name"],
            user_id      = user_id,
            scopes       = doc["scopes"],
            expires_at   = doc.get("expires_at"),
            workspace_id = doc.get("workspace_id"),
            metadata     = doc.get("metadata", {}),
        )

    # ── List / Get ────────────────────────────────────────────────────────────

    async def list_for_user(self, user_id: str) -> list[dict]:
        docs = []
        async for doc in self._col.find({"user_id": user_id}).sort("created_at", -1):
            doc.pop("_id", None)
            doc.pop("key_hash", None)
            docs.append(doc)
        return docs

    async def get(self, key_id: str) -> dict | None:
        doc = await self._col.find_one({"key_id": key_id})
        if not doc:
            return None
        doc.pop("_id", None)
        doc.pop("key_hash", None)
        return doc

    async def admin_list(self, limit: int = 100, skip: int = 0) -> list[dict]:
        docs = []
        async for doc in self._col.find({}).sort("created_at", -1).skip(skip).limit(limit):
            doc.pop("_id", None)
            doc.pop("key_hash", None)
            docs.append(doc)
        return docs


# ── Singleton ─────────────────────────────────────────────────────────────────

_manager: ApiKeyManager | None = None


def init_key_manager(db: Any) -> None:
    global _manager
    _manager = ApiKeyManager(db)


def get_key_manager() -> ApiKeyManager:
    if _manager is None:
        raise RuntimeError("ApiKeyManager not initialised — call init_key_manager(db) first")
    return _manager
