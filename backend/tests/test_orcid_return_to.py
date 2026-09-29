"""P1 Phase 7C4.3 §2 — ORCID "Connect directly from Passport" plumbing.

Root cause fixed: GET /orcid/authorize (mode=link) always redirected back to
/settings after a successful/failed connection, even though ResearchIntegrations
(OrcidSettings.jsx) has been the Passport's Research tab since P1 Phase 7C4.1 —
/settings no longer renders any ORCID UI at all, so every "Connect ORCID"
action inside the Passport silently dead-ended on a page with nothing to show
for it. These tests cover the return_to allowlist/sanitizer and its wiring
into authorization_url — the part safely testable without a live ORCID
sandbox exchange.
"""
from __future__ import annotations

from services.orcid.oauth import sanitize_return_to, authorization_url, decode_state


def test_sanitize_return_to_defaults_to_passport():
    assert sanitize_return_to(None) == "/academic-passport"
    assert sanitize_return_to("") == "/academic-passport"


def test_sanitize_return_to_allows_known_bases():
    assert sanitize_return_to("/academic-passport") == "/academic-passport"
    assert sanitize_return_to("/settings") == "/settings"


def test_sanitize_return_to_allows_safe_fragment():
    assert sanitize_return_to("/academic-passport#research_integrations") == "/academic-passport#research_integrations"


def test_sanitize_return_to_rejects_unknown_path():
    assert sanitize_return_to("/unknown-page") == "/academic-passport"


def test_sanitize_return_to_rejects_open_redirect_attempts():
    # Absolute/protocol-relative URLs must never survive — this value round
    # trips through ORCID's own redirect, so it's attacker-influenceable.
    assert sanitize_return_to("https://evil.example.com") == "/academic-passport"
    assert sanitize_return_to("//evil.example.com") == "/academic-passport"


def test_sanitize_return_to_rejects_unsafe_fragment_chars():
    result = sanitize_return_to("/academic-passport#<script>")
    assert result in ("/academic-passport", "/academic-passport#")
    assert "<script>" not in result


def test_authorization_url_link_mode_encodes_sanitized_return_to(monkeypatch):
    monkeypatch.setattr("services.orcid.oauth.ORCID_CLIENT_ID", "test-client")
    monkeypatch.setattr("services.orcid.oauth.ORCID_CLIENT_SECRET", "test-secret")
    url = authorization_url("link", requesting_user_id="u1", return_to="/academic-passport#research_integrations")
    from urllib.parse import urlparse, parse_qs
    state = parse_qs(urlparse(url).query)["state"][0]
    payload = decode_state(state)
    assert payload["return_to"] == "/academic-passport#research_integrations"
    assert payload["mode"] == "link"
    assert payload["uid"] == "u1"


def test_authorization_url_login_mode_has_no_return_to(monkeypatch):
    monkeypatch.setattr("services.orcid.oauth.ORCID_CLIENT_ID", "test-client")
    monkeypatch.setattr("services.orcid.oauth.ORCID_CLIENT_SECRET", "test-secret")
    url = authorization_url("login", return_to="/academic-passport")
    from urllib.parse import urlparse, parse_qs
    state = parse_qs(urlparse(url).query)["state"][0]
    payload = decode_state(state)
    assert payload["return_to"] is None
