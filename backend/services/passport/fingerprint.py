"""Synaptiq Academic Fingerprint (P1 Phase 7 C3).

A stable, NON-BIOMETRIC per-account identifier for the Academic Passport —
purely a deterministic label, not a real fingerprint. It is NOT derived
from, and does not expose, email, ORCID, password, OAuth tokens, or the raw
MongoDB ObjectId.

Construction
------------
HMAC-SHA256(secret, f"{NAMESPACE}:{user_id}") — the same authenticated-hash
pattern already used in this codebase for per-user tokens (see
routers/admin_email_center.py's unsubscribe-token HMAC, and
services/encryption_service.py's lazy-cached-key / graceful-fallback secret
pattern, which this module follows for secret handling).

- `user_id` is the account's MongoDB ObjectId, used ONLY as HMAC input —
  never displayed, and not recoverable from the output (see below).
- NAMESPACE binds the hash to this specific application + fingerprint
  version, so the same user_id run through a different namespace (or a
  future v2) produces an unrelated value.
- The secret is PASSPORT_FINGERPRINT_SECRET, a dedicated env var — kept
  separate from JWT_SECRET/ENCRYPTION_KEY so rotating or leaking one
  secret doesn't affect the others. If unset, a documented, non-secret
  fallback constant is used instead (same graceful-degradation shape as
  admin_email_center.py's unsubscribe token) — the fingerprint feature
  still works, it's just not secret-hardened until the env var is set in
  production. This must NEVER crash application startup.

Non-reversibility
------------------
HMAC-SHA256 is a one-way function: given only the digest (or its truncated
display form) and no knowledge of the secret, the input user_id cannot be
recovered. This holds even though MongoDB ObjectIds have some predictable
structure (a timestamp prefix), because recovering user_id from the digest
still requires knowing the secret, which is never exposed to any client.

Two representations are returned:
  - `full`   32 hex chars (128 bits) — the full internal representation.
  - `display` a short, grouped, human-readable public form derived from a
    prefix of the same hash, e.g. "SYN · A1B2 · C3D4 · E5F6" (the exact
    digits are always computed from the real hash — never hardcoded).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os

logger = logging.getLogger("synaptiq.passport.fingerprint")

NAMESPACE = "SYNAPTIQ-PASSPORT-FINGERPRINT-v1"

_UNSET = object()
_secret_cache = _UNSET


def _get_secret() -> bytes:
    global _secret_cache
    if _secret_cache is not _UNSET:
        return _secret_cache
    raw = os.environ.get("PASSPORT_FINGERPRINT_SECRET", "").strip()
    if not raw:
        logger.warning(
            "PASSPORT_FINGERPRINT_SECRET not set — Academic Fingerprint is "
            "using a non-secret fallback key. Set this env var in production "
            "so fingerprints can't be recomputed by anyone who knows a "
            "user_id and this fallback string."
        )
        raw = "synaptiq-passport-fingerprint-dev-fallback"
    _secret_cache = raw.encode()
    return _secret_cache


def compute_fingerprint(user_id: str) -> dict:
    """Return {"full": <32-hex>, "display": "SYN · XXXX · XXXX · XXXX"}.

    Deterministic for the same user_id; different user_ids produce
    unrelated values (standard HMAC-SHA256 avalanche/collision resistance —
    128 bits from `full` alone is already far beyond this application's
    scale; `display`'s 12 hex chars, ~48 bits, are for human display only,
    not intended as a collision-resistant machine key — `full` is."""
    digest = hmac.new(_get_secret(), f"{NAMESPACE}:{user_id}".encode(), hashlib.sha256).hexdigest()
    full = digest[:32]
    display_hex = digest[:12].upper()
    display = "SYN · " + " · ".join(display_hex[i:i + 4] for i in range(0, 12, 4))
    return {"full": full, "display": display}
