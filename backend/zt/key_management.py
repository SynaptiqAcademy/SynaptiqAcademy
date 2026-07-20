"""
Key Management System — Phase XXXV.8

Centralized key registry with rotation, versioning, and revocation.
Only key *metadata* is stored in MongoDB — actual key material is in-memory
(or loaded from environment variables in production).
"""
from __future__ import annotations

import base64
import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_COL = "zt_keys"


class KeyType(str, Enum):
    ENCRYPTION  = "encryption"
    SIGNING     = "signing"
    JWT         = "jwt"
    WEBHOOK     = "webhook"
    API_KEY     = "api_key"
    AI_PROVIDER = "ai_provider"
    FIELD       = "field"


class KeyStatus(str, Enum):
    ACTIVE   = "active"
    ROTATING = "rotating"
    RETIRED  = "retired"
    REVOKED  = "revoked"


@dataclass
class KeyMetadata:
    key_id:      str
    key_type:    KeyType
    version:     int
    status:      KeyStatus
    algorithm:   str          = "AES-256"
    created_at:  str          = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rotated_at:  str | None   = None
    retired_at:  str | None   = None
    description: str          = ""
    key_hash:    str          = ""   # SHA-256 of key material (for audit, not recovery)

    def to_dict(self) -> dict:
        return {
            "key_id":      self.key_id,
            "key_type":    self.key_type,
            "version":     self.version,
            "status":      self.status,
            "algorithm":   self.algorithm,
            "created_at":  self.created_at,
            "rotated_at":  self.rotated_at,
            "retired_at":  self.retired_at,
            "description": self.description,
            "key_hash":    self.key_hash,
        }


class KeyManager:
    """
    Manages key material in-memory with metadata persisted to MongoDB.

    In production: key material should be loaded from a secrets manager
    (AWS Secrets Manager, HashiCorp Vault, GCP KMS) not derived in-process.
    """

    def __init__(self, db: Any, master_secret: bytes | None = None) -> None:
        self._db     = db
        self._col    = db[_COL]
        self._master = master_secret or self._load_master()
        self._keys:  dict[str, bytes] = {}
        self._meta:  dict[str, KeyMetadata] = {}

    def _load_master(self) -> bytes:
        import os
        raw = os.environ.get("ZT_MASTER_KEY", "")
        if raw:
            try:
                return base64.urlsafe_b64decode(raw.encode())
            except Exception:
                return raw.encode()
        return b"synaptiq-dev-zero-trust-key-2026"

    def _derive(self, key_id: str) -> bytes:
        """Derive key material from master + key_id using SHA-256."""
        return hashlib.sha256(self._master + key_id.encode()).digest()

    async def ensure_indexes(self) -> None:
        try:
            await self._col.create_index("key_id", unique=True)
            await self._col.create_index([("key_type", 1), ("status", 1)])
        except Exception as exc:
            logger.debug("Key index: %s", exc)

    async def load_metadata(self) -> None:
        async for doc in self._col.find({}):
            doc.pop("_id", None)
            meta = KeyMetadata(
                key_id      = doc["key_id"],
                key_type    = KeyType(doc["key_type"]),
                version     = doc["version"],
                status      = KeyStatus(doc["status"]),
                algorithm   = doc.get("algorithm", "AES-256"),
                created_at  = doc.get("created_at", ""),
                rotated_at  = doc.get("rotated_at"),
                retired_at  = doc.get("retired_at"),
                description = doc.get("description", ""),
                key_hash    = doc.get("key_hash", ""),
            )
            self._meta[meta.key_id] = meta
            if meta.status == KeyStatus.ACTIVE:
                self._keys[meta.key_id] = self._derive(meta.key_id)

    async def create_key(
        self,
        key_type:    KeyType,
        description: str = "",
        algorithm:   str = "AES-256",
    ) -> KeyMetadata:
        key_id    = f"{key_type.value}_{secrets.token_hex(8)}"
        key_bytes = secrets.token_bytes(32)
        key_hash  = hashlib.sha256(key_bytes).hexdigest()
        # Store derived key in memory
        self._keys[key_id] = key_bytes

        meta = KeyMetadata(
            key_id      = key_id,
            key_type    = key_type,
            version     = 1,
            status      = KeyStatus.ACTIVE,
            algorithm   = algorithm,
            description = description,
            key_hash    = key_hash,
        )
        self._meta[key_id] = meta
        doc = meta.to_dict()
        try:
            await self._col.insert_one(doc)
        except Exception as exc:
            logger.debug("Key metadata persist: %s", exc)
        return meta

    async def rotate_key(self, key_id: str) -> KeyMetadata | None:
        old = self._meta.get(key_id)
        if not old:
            return None
        new_id     = f"{old.key_type.value}_{secrets.token_hex(8)}"
        new_bytes  = secrets.token_bytes(32)
        new_hash   = hashlib.sha256(new_bytes).hexdigest()
        now        = datetime.now(timezone.utc).isoformat()

        self._keys[new_id] = new_bytes
        new_meta = KeyMetadata(
            key_id      = new_id,
            key_type    = old.key_type,
            version     = old.version + 1,
            status      = KeyStatus.ACTIVE,
            algorithm   = old.algorithm,
            description = f"Rotated from {key_id}",
            key_hash    = new_hash,
        )
        self._meta[new_id] = new_meta

        # Retire old key
        old.status     = KeyStatus.RETIRED
        old.retired_at = now
        old.rotated_at = now
        try:
            await self._col.update_one(
                {"key_id": key_id},
                {"$set": {"status": KeyStatus.RETIRED, "retired_at": now, "rotated_at": now}},
            )
            await self._col.insert_one(new_meta.to_dict())
        except Exception as exc:
            logger.debug("Key rotation persist: %s", exc)
        logger.info("Key rotated: %s → %s", key_id, new_id)
        return new_meta

    async def revoke_key(self, key_id: str) -> bool:
        meta = self._meta.get(key_id)
        if not meta:
            return False
        meta.status = KeyStatus.REVOKED
        self._keys.pop(key_id, None)
        try:
            await self._col.update_one(
                {"key_id": key_id},
                {"$set": {"status": KeyStatus.REVOKED}},
            )
        except Exception as exc:
            logger.debug("Key revoke persist: %s", exc)
        logger.warning("Key revoked: %s", key_id)
        return True

    def get_key_bytes(self, key_id: str) -> bytes | None:
        """Get key material. Returns None if key is not active."""
        meta = self._meta.get(key_id)
        if not meta or meta.status != KeyStatus.ACTIVE:
            return None
        if key_id not in self._keys:
            self._keys[key_id] = self._derive(key_id)
        return self._keys[key_id]

    def list_metadata(self, key_type: KeyType | None = None) -> list[dict]:
        result = list(self._meta.values())
        if key_type:
            result = [m for m in result if m.key_type == key_type]
        return [m.to_dict() for m in result]

    def active_key_for_type(self, key_type: KeyType) -> KeyMetadata | None:
        candidates = [
            m for m in self._meta.values()
            if m.key_type == key_type and m.status == KeyStatus.ACTIVE
        ]
        return max(candidates, key=lambda m: m.version) if candidates else None


# ── Singleton ─────────────────────────────────────────────────────────────────

_manager: KeyManager | None = None


def init_key_management(db: Any) -> KeyManager:
    global _manager
    _manager = KeyManager(db)
    return _manager


def get_key_manager() -> KeyManager:
    if _manager is None:
        raise RuntimeError("KeyManager not initialised")
    return _manager
