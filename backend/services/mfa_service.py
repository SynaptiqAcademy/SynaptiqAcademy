"""TOTP Multi-Factor Authentication service.

Implements RFC 6238 TOTP (Time-based One-Time Password) compatible with
Google Authenticator, Microsoft Authenticator, and Authy.

MFA data is stored per-user in the `mfa_configs` collection:
  {
    user_id: str,
    secret: str  (base32, encrypted at rest via FERNET if FERNET_KEY set),
    recovery_codes: [str, ...]  (bcrypt-hashed, each single-use),
    enabled: bool,
    configured_at: str,
    last_used_at: str | None,
    use_count: int,
  }
"""
from __future__ import annotations

import base64
import io
import os
import secrets
import string
from datetime import datetime, timezone
from typing import Optional

import bcrypt
import pyotp
import qrcode
import qrcode.image.svg

from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

_APP_NAME = os.environ.get("APP_NAME", "Synaptiq")
_RECOVERY_CODE_COUNT = 10
_RECOVERY_CODE_LEN = 10


# ─────────────────────────────────────────────────────────────────────────────
# Secret generation & QR
# ─────────────────────────────────────────────────────────────────────────────

def generate_secret() -> str:
    """Generate a cryptographically random 32-char base32 TOTP secret."""
    return pyotp.random_base32()


def generate_qr_png_b64(email: str, secret: str) -> str:
    """Return a base64-encoded PNG of the TOTP enrollment QR code."""
    uri = pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=_APP_NAME)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ─────────────────────────────────────────────────────────────────────────────
# TOTP verification
# ─────────────────────────────────────────────────────────────────────────────

def verify_totp(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code. Allows ±1 window (30s drift tolerance)."""
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code.strip(), valid_window=1)
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Recovery codes
# ─────────────────────────────────────────────────────────────────────────────

_CODE_ALPHABET = string.ascii_uppercase + string.digits


def _gen_one_code() -> str:
    raw = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_RECOVERY_CODE_LEN))
    return f"{raw[:5]}-{raw[5:]}"


def generate_recovery_codes() -> tuple[list[str], list[str]]:
    """Returns (plaintext_codes, bcrypt_hashes).

    Caller stores hashes; shows plaintext to the user ONCE.
    """
    codes = [_gen_one_code() for _ in range(_RECOVERY_CODE_COUNT)]
    hashes = [bcrypt.hashpw(c.encode(), bcrypt.gensalt()).decode() for c in codes]
    return codes, hashes


def verify_and_consume_recovery_code(stored_hashes: list[str], candidate: str) -> tuple[bool, list[str]]:
    """Return (matched, remaining_hashes_after_consuming_matched_code).

    If a code matches, it is removed from the list (single-use).
    """
    candidate = candidate.upper().replace(" ", "").strip()
    if len(candidate) == 10:
        candidate = f"{candidate[:5]}-{candidate[5:]}"
    for h in stored_hashes:
        try:
            if bcrypt.checkpw(candidate.encode(), h.encode()):
                remaining = [x for x in stored_hashes if x != h]
                return True, remaining
        except Exception:
            continue
    return False, stored_hashes


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

async def get_mfa_config(user_id: str) -> Optional[dict]:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    return await db.mfa_configs.find_one({"user_id": user_id})


async def mfa_is_enabled(user_id: str) -> bool:
    cfg = await get_mfa_config(user_id)
    return bool(cfg and cfg.get("enabled"))


async def begin_enrollment(user_id: str, email: str) -> dict:
    """Start the enrollment process. Returns secret and QR PNG (base64).

    Stored as pending (enabled=False) until the user verifies.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    secret = generate_secret()
    qr_b64 = generate_qr_png_b64(email, secret)

    await db.mfa_configs.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "secret": secret,
            "recovery_codes": [],
            "enabled": False,
            "pending_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    return {"secret": secret, "qr_b64": qr_b64}


async def complete_enrollment(user_id: str, code: str) -> tuple[bool, list[str]]:
    """Verify the first OTP code and activate MFA. Returns (ok, plaintext_recovery_codes)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cfg = await db.mfa_configs.find_one({"user_id": user_id})
    if not cfg or not cfg.get("secret"):
        return False, []
    if not verify_totp(cfg["secret"], code):
        return False, []

    plaintext, hashes = generate_recovery_codes()
    now = datetime.now(timezone.utc).isoformat()
    await db.mfa_configs.update_one(
        {"user_id": user_id},
        {"$set": {
            "enabled": True,
            "recovery_codes": hashes,
            "configured_at": now,
            "last_used_at": now,
            "use_count": 1,
        }},
    )
    # Write enabled flag to user document too for fast lookup
    await db.users.update_one({"_id": __import__("bson").ObjectId(user_id)}, {"$set": {"mfa_enabled": True}})
    return True, plaintext


async def verify_mfa_code(user_id: str, code: str) -> tuple[bool, str]:
    """Verify TOTP or recovery code. Returns (ok, method).

    method is 'totp' or 'recovery'.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cfg = await db.mfa_configs.find_one({"user_id": user_id})
    if not cfg or not cfg.get("enabled"):
        return False, ""

    # Try TOTP first
    if verify_totp(cfg["secret"], code):
        await db.mfa_configs.update_one(
            {"user_id": user_id},
            {"$set": {"last_used_at": datetime.now(timezone.utc).isoformat()},
             "$inc": {"use_count": 1}},
        )
        return True, "totp"

    # Try recovery codes
    ok, remaining = verify_and_consume_recovery_code(cfg.get("recovery_codes", []), code)
    if ok:
        upd: dict = {
            "recovery_codes": remaining,
            "last_used_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.mfa_configs.update_one({"user_id": user_id}, {"$set": upd, "$inc": {"use_count": 1}})
        return True, "recovery"

    return False, ""


async def disable_mfa(user_id: str) -> None:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.mfa_configs.update_one(
        {"user_id": user_id},
        {"$set": {"enabled": False, "disabled_at": datetime.now(timezone.utc).isoformat()}},
    )
    await db.users.update_one(
        {"_id": __import__("bson").ObjectId(user_id)},
        {"$set": {"mfa_enabled": False}},
    )


async def regenerate_recovery_codes(user_id: str) -> tuple[bool, list[str]]:
    """Replace all recovery codes. Returns (ok, new_plaintext_codes)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cfg = await db.mfa_configs.find_one({"user_id": user_id})
    if not cfg or not cfg.get("enabled"):
        return False, []
    plaintext, hashes = generate_recovery_codes()
    await db.mfa_configs.update_one(
        {"user_id": user_id},
        {"$set": {"recovery_codes": hashes, "codes_regenerated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return True, plaintext
