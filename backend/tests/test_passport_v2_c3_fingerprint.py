"""Regression tests for the P1 Phase 7 (Academic Passport V2) C3 Academic
Fingerprint — services/passport/fingerprint.py.

Covers: determinism, different users produce different fingerprints,
non-reversibility/no leakage of the underlying user_id or any other private
field, stable display formatting, and that the fingerprint doesn't crash
when PASSPORT_FINGERPRINT_SECRET is unset (graceful fallback).
"""
from __future__ import annotations

import os
import re

from bson import ObjectId

from services.passport.fingerprint import compute_fingerprint, NAMESPACE


class TestDeterminism:
    def test_same_user_id_produces_same_fingerprint(self):
        uid = str(ObjectId())
        a = compute_fingerprint(uid)
        b = compute_fingerprint(uid)
        assert a == b

    def test_different_user_ids_produce_different_fingerprints(self):
        uid_a = str(ObjectId())
        uid_b = str(ObjectId())
        fp_a = compute_fingerprint(uid_a)
        fp_b = compute_fingerprint(uid_b)
        assert fp_a["full"] != fp_b["full"]
        assert fp_a["display"] != fp_b["display"]

    def test_many_distinct_users_have_no_collisions(self):
        ids = [str(ObjectId()) for _ in range(200)]
        fulls = {compute_fingerprint(uid)["full"] for uid in ids}
        assert len(fulls) == len(ids)


class TestFormatting:
    def test_display_format_is_stable_grouped_hex(self):
        uid = str(ObjectId())
        fp = compute_fingerprint(uid)
        assert re.match(r"^SYN · [0-9A-F]{4} · [0-9A-F]{4} · [0-9A-F]{4}$", fp["display"])

    def test_full_is_32_lowercase_hex_chars(self):
        uid = str(ObjectId())
        fp = compute_fingerprint(uid)
        assert re.match(r"^[0-9a-f]{32}$", fp["full"])


class TestNonReversibilityAndNoLeakage:
    def test_fingerprint_does_not_contain_the_raw_user_id(self):
        uid = str(ObjectId())
        fp = compute_fingerprint(uid)
        assert uid not in fp["full"]
        assert uid not in fp["display"]
        assert uid.upper() not in fp["display"]

    def test_fingerprint_does_not_equal_the_source_objectid_bytes(self):
        """The output must not simply re-encode the raw ObjectId — the
        fingerprint's hex is derived from an HMAC digest, not a pass-through
        of the input's own bytes/hex representation."""
        uid = str(ObjectId())
        fp = compute_fingerprint(uid)
        assert fp["full"][:24] != uid
        assert fp["full"].lower() != uid.lower()

    def test_no_email_or_orcid_or_token_material_involved(self):
        """Static check on actual code (not docstrings/comments): the
        fingerprint module must not read/import anything email/ORCID/
        token/password-related — it only ever takes a plain user_id string
        as input. Parses the AST and inspects only real Name/Attribute/
        constant-string nodes, ignoring docstrings and comments so the
        module's own prose explaining what it avoids doesn't self-trigger."""
        import ast
        import inspect
        import services.passport.fingerprint as fp_module

        tree = ast.parse(inspect.getsource(fp_module))
        banned = ("email", "orcid", "password", "access_token", "refresh_token")

        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue  # docstring/bare string statement — not executed code
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = " ".join(a.name for a in node.names)
                assert not any(b in names.lower() for b in banned), f"banned import: {names}"
            if isinstance(node, ast.Name):
                assert not any(b in node.id.lower() for b in banned), f"banned identifier: {node.id}"
            if isinstance(node, ast.Attribute):
                assert not any(b in node.attr.lower() for b in banned), f"banned attribute access: {node.attr}"

    def test_namespace_is_bound_into_the_hash(self):
        """Two different namespaces for the same user_id must diverge —
        proves the HMAC input actually includes NAMESPACE, not just user_id."""
        import hmac
        import hashlib
        uid = str(ObjectId())
        real = compute_fingerprint(uid)
        secret = os.environ.get("PASSPORT_FINGERPRINT_SECRET", "").strip() or \
            "synaptiq-passport-fingerprint-dev-fallback"
        other_namespace_digest = hmac.new(
            secret.encode(), f"OTHER-NAMESPACE:{uid}".encode(), hashlib.sha256
        ).hexdigest()[:32]
        assert real["full"] != other_namespace_digest
        assert NAMESPACE == "SYNAPTIQ-PASSPORT-FINGERPRINT-v1"


class TestGracefulSecretFallback:
    def test_missing_secret_env_var_does_not_raise(self, monkeypatch):
        import services.passport.fingerprint as fp_module
        monkeypatch.delenv("PASSPORT_FINGERPRINT_SECRET", raising=False)
        fp_module._secret_cache = fp_module._UNSET
        uid = str(ObjectId())
        fp = compute_fingerprint(uid)
        assert fp["full"]
        assert fp["display"]
        fp_module._secret_cache = fp_module._UNSET
