"""Privacy, Terms and Cookies: the documents must match what the code does."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"
SRC = FE / "src"
PAGES = {n: (SRC / "pages" / f"{n}.jsx").read_text() for n in ("Privacy", "Terms", "Cookies")}
ALL = "\n".join(PAGES.values())
META = (SRC / "content" / "legal" / "meta.js").read_text()
INVENTORY = (SRC / "content" / "legal" / "cookies.js").read_text()

BANNED = [r"bulletproof", r"100% (GDPR|secure)", r"GDPR[- ](compliant|certified)", r"SOC ?2", r"ISO ?27001", r"HIPAA",
          r"military", r"bank[- ](level|grade)", r"fully secure", r"[Ww]e never (use|train)", r"within 24 hours",
          r"Synaptiq (SRL|Ltd|Inc|GmbH)", r"hereinafter", r"ABSOLUTE DISCRETION", r"ANY AND ALL", r"non-refundable",
          r"Most Popular", r"Pro Researcher", r"Researcher plan", r"Institution plan", r"€"]


@pytest.mark.parametrize("pattern", BANNED)
def test_no_legal_theatre_or_unsupported_claims(pattern):
    assert not re.search(pattern, ALL), pattern


def test_versions_match_backend():
    from legal_versions import TERMS_VERSION, PRIVACY_VERSION, COOKIES_VERSION
    for key, v in (("terms", TERMS_VERSION), ("privacy", PRIVACY_VERSION), ("cookies", COOKIES_VERSION)):
        assert re.search(rf'{key}:\s*\{{ version: "{v}"', META), key


def test_operator_is_not_invented():
    assert "operator: null" in META            # flip only with the real legal entity
    assert "OPERATOR_PENDING" in PAGES["Privacy"] and "OPERATOR_PENDING" in PAGES["Terms"]


def test_every_browser_storage_key_is_in_the_cookie_inventory():
    names = set(re.findall(r'name: "([^"]+)"', INVENTORY))
    covered = [k.strip() for n in names for k in n.split(",")]
    exact = {k for k in covered if not k.endswith("*")}
    prefixes = [k[:-1] for k in covered if k.endswith("*")]
    keys = set()
    for f in list(SRC.rglob("*.js")) + list(SRC.rglob("*.jsx")):
        s = f.read_text()
        consts = dict(re.findall(r'(?:const\s+)?([A-Z_]+)\s*[:=]\s*"([a-z][a-z0-9_.]+)"', s))
        for m in re.findall(r'(?:localStorage|sessionStorage)\.setItem\(\s*([^,]+),', s):
            m = m.strip()
            if m.startswith('"'):
                keys.add(m.strip('"'))
            elif m.startswith("`"):
                keys.add(re.sub(r"\$\{[^}]+\}.*", "", m.strip("`")))
            elif m in consts:
                keys.add(consts[m])
            elif "." in m and m.split(".")[-1] in consts:
                keys.add(consts[m.split(".")[-1]])
        for m in re.findall(r'usePersistentSet\(\s*"([^"]+)"', s):
            keys.add(m)
    missing = [k for k in keys if k not in exact and not any(k.startswith(p) for p in prefixes)]
    assert not missing, missing
    auth = (ROOT / "backend" / "auth_utils.py").read_text()
    for cookie in re.findall(r'key="([a-z_]+)"', auth):
        assert cookie in exact, cookie


def test_analytics_only_with_consent_and_no_content_capture():
    init = (FE / "public" / "analytics-init.js").read_text()
    assert "if (analyticsAllowed() && !initialized)" in init
    assert "autocapture: false" in init and "disable_session_recording: true" in init
    consent = (SRC / "lib" / "cookieConsent.js").read_text()
    cats = re.findall(r'id: "([a-z]+)"', consent[consent.index("CATEGORY_META"):consent.index("DEFAULT_PREFS")])
    assert cats == ["essential", "analytics"]
    assert "analytics: false" in consent[consent.index("DEFAULT_PREFS"):]   # off by default
    assert "ALL_ACCEPTED_PREFS = { essential: true, analytics: true, marketing: false, preferences: false }" in consent


def test_reject_is_as_prominent_as_accept():
    b = (SRC / "components" / "consent" / "CookieConsentBanner.jsx").read_text()
    rej = re.search(r'className="([^"]+)"\s*data-testid="consent-reject-btn"', b).group(1)
    acc = re.search(r'className="([^"]+)"\s*data-testid="consent-accept-btn"', b).group(1)
    assert rej == acc
    footer = (SRC / "components" / "layout" / "MarketingLayout.jsx").read_text()
    assert "onClick={openPreferences}" in footer and "Cookie settings" in footer


def test_self_service_rights_described_actually_exist():
    users = (ROOT / "backend" / "routers" / "users.py").read_text()
    assert '@router.get("/me/export")' in users and '@router.delete("/me")' in users
    ui = (SRC / "components" / "settings" / "PrivacySection.jsx").read_text()
    assert 'api.get("/users/me/export")' in ui and 'api.delete("/users/me"' in ui
    assert "Export my data" in PAGES["Privacy"] and "Settings → Privacy" in PAGES["Privacy"]
    robots = (FE / "public" / "robots.txt").read_text()
    assert "Disallow: /" in robots and "Allow: /researcher" not in robots   # profile pages not offered to search engines


@pytest.mark.asyncio
async def test_signup_requires_terms_acceptance(monkeypatch):
    from routers import auth
    from models import RegisterIn
    from starlette.requests import Request

    async def _open(db):
        return True
    monkeypatch.setattr(auth, "is_registration_open", _open)
    req = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1), "query_string": b""})
    with pytest.raises(HTTPException) as e:
        await auth.register(req, RegisterIn(email="x@synaptiq-test.io", password="Abcdef12!", full_name="X"), None)
    assert e.value.status_code == 400
    src = (ROOT / "backend" / "routers" / "auth.py").read_text()
    assert '"terms_version": TERMS_VERSION' in src and '"terms_accepted_at"' in src


# ── Phase 2: secondary legal pages, fonts, retention ─────────────────────────
SECONDARY = {n: (SRC / "pages" / f"{n}.jsx").read_text() for n in ("GDPR", "AiPolicy", "LegalCenter")}


@pytest.mark.parametrize("pattern", BANNED + [
    r"7 years", r"3 years", r"30 days rolling", r"14 days \(point-in-time", r"session recording",
    r"enterprise API (terms|tiers)", r"not retained by Anthropic", r"Cookie preferences",
    r"EU data residency", r"security@synaptiq", r"Compliant",
])
def test_secondary_legal_pages_make_no_unverified_claims(pattern):
    for name, text in SECONDARY.items():
        assert not re.search(pattern, text), f"{name}: {pattern}"


def test_security_center_with_unverified_claims_is_not_served():
    app = (SRC / "App.js").read_text()
    assert '<Route path="/security" element={<Navigate to="/privacy#security" replace />} />' in app
    assert not (SRC / "pages" / "Security.jsx").exists()
    assert "/security<" not in (FE / "public" / "sitemap.xml").read_text()


def test_fonts_are_self_hosted():
    offenders = []
    for path in list(SRC.rglob("*.js")) + list(SRC.rglob("*.jsx")) + list(SRC.rglob("*.css")) + [FE / "public" / "index.html"]:
        text = path.read_text(errors="ignore")
        if "fonts.googleapis.com" in text or "fonts.gstatic.com" in text:
            offenders.append(str(path.relative_to(FE)))
    assert offenders == []
    assert "Google Fonts" not in PAGES["Privacy"]
    mw = (ROOT / "backend" / "middleware" / "__init__.py").read_text()
    assert "fonts.gstatic.com" not in mw


def test_published_retention_matches_retention_policy():
    from retention_policy import BY_KEY
    privacy = PAGES["Privacy"]
    assert BY_KEY["security_events"].effective_days == 365 and '"Security event logs", "1 year"' in privacy
    assert BY_KEY["audit_admin"].effective_days == 90
    assert '(for example, that an account was deleted)", "90 days"]' in privacy
    assert BY_KEY["email_log"].effective_days == 90 and BY_KEY["notifications_read"].effective_days == 90
    assert BY_KEY["consent_anonymous"].effective_days == 730
    assert '["Cookie choices not linked to an account", "2 years"]' in privacy


def test_providers_table_matches_production_setup():
    privacy = PAGES["Privacy"]
    assert '["Railway", "Application servers", "United States"]' in privacy


# ── Legal & Trust consolidation: one system for four documents ───────────────
FOUR = {n: (SRC / "pages" / f"{n}.jsx").read_text() for n in ("Privacy", "Terms", "Cookies", "GDPR")}
LAYOUT = (SRC / "components" / "legal" / "LegalLayout.jsx").read_text()


@pytest.mark.parametrize("name,doc", [("Privacy", "privacy"), ("Terms", "terms"), ("Cookies", "cookies"), ("GDPR", "dataProtection")])
def test_every_legal_document_uses_the_shared_system(name, doc):
    src = FOUR[name]
    assert 'from "../components/legal/LegalLayout"' in src
    assert "pages/legal/LegalLayout" not in src and './legal/LegalLayout' not in src   # legacy layout can't return
    assert f'doc="{doc}"' in src
    # Dates and versions come only from content/legal/meta.js
    assert not re.search(r'(lastUpdated|updated|version)=\{?"', src)


def test_legal_registry_lists_the_four_documents():
    for path in ('path: "/privacy"', 'path: "/terms"', 'path: "/cookies"', 'path: "/gdpr"'):
        assert path in META
    assert 'title: "Data Protection"' in META and "dataProtection: { updated:" in META
    assert "LEGAL_DOCS.map" in LAYOUT and 'aria-current="page"' in LAYOUT and "LegalContinue" in LAYOUT


def test_cookie_settings_actions_open_the_real_consent_control():
    assert "onClick={openPreferences}" in FOUR["Cookies"] and 'import { openPreferences } from "../lib/cookieConsent"' in FOUR["Cookies"]
    assert "Manage cookie settings" in FOUR["Cookies"]
    assert "onClick={openPreferences}" in FOUR["GDPR"]
    footer = (SRC / "components" / "layout" / "MarketingLayout.jsx").read_text()
    assert 'data-testid="footer-cookie-settings"' in footer and "onClick={openPreferences}" in footer
    assert '<FL href="/gdpr">Data Protection</FL>' in footer and '["GDPR", "/gdpr"]' not in footer


def test_cookie_inventory_is_rendered_from_the_canonical_list_only():
    src = FOUR["Cookies"]
    assert "STORAGE_INVENTORY" in src and "access_token" not in src and "ph_<project key>" not in src
    assert not re.search(r'category: "(marketing|preferences|advertising)"', INVENTORY)


def test_data_protection_points_to_privacy_instead_of_duplicating_it():
    src = FOUR["GDPR"]
    assert "LegalTable" not in src                      # no second provider/retention table
    for anchor in ("/privacy#providers", "/privacy#transfers", "/privacy#retention", "/privacy#deletion", "/privacy#security"):
        assert anchor in src
    assert "LegalOperator" in src                        # controller from canonical metadata


@pytest.mark.parametrize("pattern", [
    r"GDPR[- ]compliant", r"[Ff]ully compliant", r"(?<!provider is )[Cc]ertified", r"SOC ?2", r"ISO ?27001", r"HIPAA", r"zero[- ]knowledge",
    r"(?<!not )end-to-end encrypted", r"daily backup", r"[Gg]uaranteed", r"48 hours", r"security@", r"Anthropic does not retain",
    r"OpenAI \(optional", r"self-hosted AI", r"3 years", r"Google Fonts", r"military", r"bank[- ]level", r"GDPR Notice",
])
def test_four_documents_and_trust_pages_make_no_unverified_claims(pattern):
    texts = dict(FOUR)
    texts["Contact"] = (SRC / "pages" / "Contact.jsx").read_text()
    texts["LegalCenter"] = (SRC / "pages" / "LegalCenter.jsx").read_text()
    for name, text in texts.items():
        if pattern == r"Google Fonts" and name == "Cookies":
            continue   # Cookies says fonts are NOT loaded from Google Fonts
        assert not re.search(pattern, text), f"{name}: {pattern}"


def test_public_passport_copy_matches_privacy_by_default():
    panel = (SRC / "components" / "passport" / "PublicPortfolioPanel.jsx").read_text()
    assert "never see your email" not in panel and "stay private unless you turn them on" in panel
