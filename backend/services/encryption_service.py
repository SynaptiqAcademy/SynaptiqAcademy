"""AES-256-GCM field-level encryption for sensitive values stored in MongoDB (AUTH-012).

Usage:
    from services.encryption_service import encrypt_field, decrypt_field

    doc["orcid"]["access_token"] = encrypt_field(raw_token)
    raw_token = decrypt_field(doc["orcid"]["access_token"])

Key management:
    ENCRYPTION_KEY env var must be 32 bytes base64-encoded.
    Generate: python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"

Backward-compatible: decrypt_field() handles both encrypted dicts and legacy plaintext strings.
"""
from __future__ import annotations

import base64
import logging
import os
from typing import Union

logger = logging.getLogger("synaptiq.encryption")

_UNSET = object()
_key_cache = _UNSET


def _get_key() -> bytes | None:
    global _key_cache
    if _key_cache is not _UNSET:
        return _key_cache
    raw = os.environ.get("ENCRYPTION_KEY", "").strip()
    if not raw:
        logger.warning("ENCRYPTION_KEY not set — field encryption disabled (AUTH-012 not active)")
        _key_cache = None
        return None
    try:
        key = base64.b64decode(raw)
        if len(key) != 32:
            raise ValueError(f"Key must be exactly 32 bytes; got {len(key)}")
        _key_cache = key
        return key
    except Exception as e:
        logger.error("Invalid ENCRYPTION_KEY: %s — disabling encryption", e)
        _key_cache = None
        return None


def encrypt_field(plaintext: str) -> dict:
    """Encrypt a string. Returns an encrypted envelope dict, or a plaintext fallback."""
    key = _get_key()
    if not key or not plaintext:
        return {"encrypted": False, "value": plaintext or ""}
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = os.urandom(12)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return {
            "encrypted": True,
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "nonce": base64.b64encode(nonce).decode(),
        }
    except Exception as e:
        logger.error("Encryption failed (storing plaintext as fallback): %s", e)
        return {"encrypted": False, "value": plaintext}


def decrypt_field(data: Union[dict, str, None]) -> str:
    """Decrypt a field value. Transparent for legacy plaintext strings."""
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    if not isinstance(data, dict):
        return str(data)
    if not data.get("encrypted"):
        return data.get("value", "")
    key = _get_key()
    if not key:
        logger.warning("Cannot decrypt: ENCRYPTION_KEY not set")
        return ""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = base64.b64decode(data["nonce"])
        ciphertext = base64.b64decode(data["ciphertext"])
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception as e:
        logger.error("Decryption failed: %s", e)
        return ""


def is_encryption_configured() -> bool:
    return _get_key() is not None
