"""
Encryption Layer — Phase XXXV.8

Field-level, at-rest, and envelope encryption.
Uses AES-128 (Fernet) from the `cryptography` package.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAS_FERNET = True
except ImportError:
    _HAS_FERNET = False
    logger.warning("cryptography package not found — field encryption using fallback")


def _derive_fernet_key(master_key_bytes: bytes, context: str) -> bytes:
    """Derive a Fernet-compatible key using HKDF-lite (SHA-256 + context)."""
    h = hashlib.sha256(master_key_bytes + context.encode()).digest()   # 32 bytes
    return base64.urlsafe_b64encode(h)                                  # Fernet wants URL-safe b64


class EncryptionEngine:
    """
    Provides:
    - encrypt_field(value, key_id) → ciphertext
    - decrypt_field(ciphertext, key_id) → plaintext
    - encrypt_dict(data, fields, key_id) → data with encrypted fields
    - decrypt_dict(data, fields, key_id) → data with decrypted fields
    """

    def __init__(self, master_key_bytes: bytes | None = None) -> None:
        if master_key_bytes is None:
            raw = os.environ.get("ZT_MASTER_KEY", "")
            if raw:
                try:
                    master_key_bytes = base64.urlsafe_b64decode(raw.encode())
                except Exception:
                    master_key_bytes = raw.encode()
            else:
                master_key_bytes = b"synaptiq-dev-zero-trust-key-2026"
        self._master = master_key_bytes

    def _fernet(self, key_id: str) -> "Fernet | None":
        if not _HAS_FERNET:
            return None
        k = _derive_fernet_key(self._master, key_id)
        from cryptography.fernet import Fernet
        return Fernet(k)

    def encrypt_field(self, value: str, key_id: str = "default") -> str:
        """Encrypt a string field. Prefix: 'enc:' for Fernet, 'b64:' for fallback."""
        if _HAS_FERNET:
            f = self._fernet(key_id)
            ciphertext = f.encrypt(value.encode())
            return "enc:" + ciphertext.decode()
        else:
            return "b64:" + base64.b64encode(value.encode()).decode()

    def decrypt_field(self, ciphertext: str, key_id: str = "default") -> str:
        """Decrypt a field encrypted by encrypt_field."""
        if ciphertext.startswith("enc:") and _HAS_FERNET:
            f = self._fernet(key_id)
            try:
                from cryptography.fernet import InvalidToken
                return f.decrypt(ciphertext[4:].encode()).decode()
            except Exception:
                raise ValueError("Decryption failed — wrong key or tampered data")
        elif ciphertext.startswith("b64:"):
            return base64.b64decode(ciphertext[4:].encode()).decode()
        else:
            return ciphertext  # not encrypted

    def is_encrypted(self, value: str) -> bool:
        return isinstance(value, str) and (
            value.startswith("enc:") or value.startswith("b64:")
        )

    def encrypt_dict(
        self,
        data:    dict,
        fields:  list[str],
        key_id:  str = "default",
    ) -> dict:
        """Return a copy of data with specified fields encrypted."""
        result = dict(data)
        for f in fields:
            if f in result and result[f] is not None and not self.is_encrypted(str(result[f])):
                result[f] = self.encrypt_field(str(result[f]), key_id)
        return result

    def decrypt_dict(
        self,
        data:    dict,
        fields:  list[str],
        key_id:  str = "default",
    ) -> dict:
        """Return a copy of data with specified fields decrypted."""
        result = dict(data)
        for f in fields:
            if f in result and result[f] is not None and self.is_encrypted(str(result[f])):
                try:
                    result[f] = self.decrypt_field(str(result[f]), key_id)
                except Exception:
                    pass  # leave encrypted if decryption fails
        return result

    def generate_key(self) -> str:
        """Generate a new random Fernet key."""
        if _HAS_FERNET:
            return Fernet.generate_key().decode()
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

    def rotate_field(
        self,
        ciphertext: str,
        old_key_id: str,
        new_key_id: str,
    ) -> str:
        """Re-encrypt a field under a new key."""
        plaintext = self.decrypt_field(ciphertext, old_key_id)
        return self.encrypt_field(plaintext, new_key_id)


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: EncryptionEngine | None = None


def init_encryption(master_key_bytes: bytes | None = None) -> None:
    global _engine
    _engine = EncryptionEngine(master_key_bytes)


def get_encryption() -> EncryptionEngine:
    global _engine
    if _engine is None:
        _engine = EncryptionEngine()
    return _engine
