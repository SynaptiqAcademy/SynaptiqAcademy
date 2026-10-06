"""Legal & Trust Phase 2: OAuth must not bypass sign-up rules.

Every way of creating an account must apply the same rules as email sign-up:
sign-ups open, 18+ confirmed and the current Terms accepted, with the
acceptance recorded. ORCID previously created accounts silently on any
callback, and Google created them without Terms acceptance.
"""
from __future__ import annotations

import asyncio
import time
from urllib.parse import parse_qs, urlparse

import pytest

from legal_versions import PRIVACY_VERSION, TERMS_VERSION
from services.orcid import oauth as O
from services import google_oauth as G


class _Users:
    def __init__(self, existing=None):
        self.existing = existing
        self.inserted = []

    async def find_one(self, q, *a, **k):
        return self.existing

    async def insert_one(self, doc):
        self.inserted.append(doc)
        return type("R", (), {"inserted_id": "507f1f77bcf86cd799439011"})()

    async def update_one(self, *a, **k):
        return None


class _DB:
    def __init__(self, users):
        self.users = users


def _state(url: str) -> str:
    return parse_qs(urlparse(url).query)["state"][0]


@pytest.fixture
def orcid_env(monkeypatch):
    import routers.orcid as R
    # Other tests may reload services.orcid.oauth; patch the module object the
    # router actually uses, so state is signed and verified with one secret.
    global O
    O = R.O
    monkeypatch.setattr(O, "ORCID_CLIENT_ID", "test-client")
    monkeypatch.setattr(O, "ORCID_CLIENT_SECRET", "test-secret")
    users = _Users()
    monkeypatch.setattr(R, "get_db", lambda: _DB(users))
    monkeypatch.setattr(R, "DBProxy", lambda db, ctx: db)

    async def _exchange(code):
        return {}
    monkeypatch.setattr(O, "exchange_code", _exchange)
    monkeypatch.setattr(O, "normalize_token", lambda t: {"orcid_id": "0000-0002-1825-0097", "name": "Test Person",
                                                          "access_token": "a", "refresh_token": "r",
                                                          "expires_at": None, "verified_at": None})
    monkeypatch.setattr(R, "_encrypt_orcid_tokens", lambda nt: dict(nt))
    return R, users


def _open(monkeypatch, value: bool):
    async def _is_open(db):
        return value
    monkeypatch.setattr("services.platform_flags.is_registration_open", _is_open)


def _call(R, state):
    return asyncio.run(R.callback(code="c", state=state, error=None, request=None))


def test_orcid_state_carries_terms_only_when_accepted(orcid_env):
    assert O.decode_state(_state(O.authorization_url("signup", accepted_terms=True)))["terms"] == TERMS_VERSION
    assert O.decode_state(_state(O.authorization_url("signup")))["terms"] is None
    assert O.decode_state(_state(O.authorization_url("login")))["terms"] is None


def test_orcid_state_expires(orcid_env):
    stale = O.encode_state({"mode": "login", "uid": None, "ts": int(time.time()) - O.STATE_MAX_AGE_SECS - 5})
    with pytest.raises(ValueError):
        O.decode_state(stale)


def test_orcid_login_with_unknown_orcid_does_not_create_account(orcid_env, monkeypatch):
    R, users = orcid_env
    _open(monkeypatch, True)
    resp = _call(R, _state(O.authorization_url("login")))
    assert users.inserted == []
    assert "/register?orcid_error=terms_required" in resp.headers["location"]


def test_orcid_signup_without_terms_is_refused(orcid_env, monkeypatch):
    R, users = orcid_env
    _open(monkeypatch, True)
    resp = _call(R, _state(O.authorization_url("signup")))
    assert users.inserted == []
    assert "terms_required" in resp.headers["location"]


def test_orcid_signup_refused_when_registration_closed(orcid_env, monkeypatch):
    R, users = orcid_env
    _open(monkeypatch, False)
    resp = _call(R, _state(O.authorization_url("signup", accepted_terms=True)))
    assert users.inserted == []
    assert "registration_closed" in resp.headers["location"]


def test_orcid_signup_with_terms_records_acceptance(orcid_env, monkeypatch):
    R, users = orcid_env
    _open(monkeypatch, True)
    monkeypatch.setattr(R, "_issue_tokens_and_cookies", lambda *a, **k: None, raising=False)
    try:
        _call(R, _state(O.authorization_url("signup", accepted_terms=True)))
    except Exception:
        pass  # token issuance after creation is outside this test
    assert len(users.inserted) == 1
    doc = users.inserted[0]
    assert doc["terms_version"] == TERMS_VERSION
    assert doc["privacy_version_acknowledged"] == PRIVACY_VERSION
    assert doc["terms_accepted_at"] is not None


def test_google_state_carries_terms_only_when_accepted(monkeypatch):
    monkeypatch.setattr(G, "GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setattr(G, "GOOGLE_CLIENT_SECRET", "secret")
    assert G.decode_state(_state(G.authorization_url("signup", accepted_terms=True)))["terms"] == TERMS_VERSION
    assert G.decode_state(_state(G.authorization_url("signup")))["terms"] is None


def test_google_callback_requires_terms_for_new_accounts():
    src = open("routers/google_auth.py", encoding="utf-8").read()
    gate = src.index('payload.get("terms") != TERMS_VERSION')
    create = src.index("# New account via Google")
    assert gate < create
    assert '"terms_version": TERMS_VERSION' in src


def test_state_round_trips_even_when_signature_contains_a_dot(monkeypatch):
    """The HMAC can contain a "." byte (~12% of states). Splitting at the last
    "." made those sign-ins fail with "Invalid state parameter"."""
    from services.orcid import oauth as OO
    monkeypatch.setattr(G, "GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setattr(G, "GOOGLE_CLIENT_SECRET", "secret")
    for i in range(300):
        OO.decode_state(OO.encode_state({"mode": "login", "uid": None, "ts": int(time.time()), "n": i}))
        G.decode_state(G.encode_state("login", f"user-{i}"))
