"""Public website release gate: navigation, product truth and editorial
rules that should not regress. Reads the frontend sources."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"
APP = (SRC / "App.js").read_text()
LAYOUT = (SRC / "components" / "layout" / "MarketingLayout.jsx").read_text()
PUBLIC = ["Landing", "Platform", "ResearchLanding", "AIWorkspaceLanding", "InstitutionsLanding", "Pricing", "About",
          "Contact", "HelpCenter", "Status", "Security"]


def _page(name):
    p = SRC / "pages" / f"{name}.jsx"
    return p.read_text()


def test_header_items_route_to_real_pages():
    for href in re.findall(r'\{ href: "(/[a-z-]+)",\s+label:', LAYOUT):
        assert re.search(r'<Route path="%s" element=\{<(?!Navigate)' % re.escape(href), APP), href


def test_one_primary_signup_label():
    assert "Get Started" not in LAYOUT
    assert LAYOUT.count("Start Free") >= 2          # desktop + mobile


def test_fabricated_pages_are_gone():
    for route, dest in (("/documentation", "/help-center"), ("/developers", "/contact?topic=partnership"),
                        ("/resources/customer-stories", "/resources")):
        assert f'<Route path="{route}" element={{<Navigate to="{dest}" replace />}} />' in APP, route
    for name in ("Documentation", "ApiPortal"):
        assert not (SRC / "pages" / f"{name}.jsx").exists()
    assert '"/documentation"' not in LAYOUT and '"/developers"' not in LAYOUT


def test_status_shows_no_invented_metrics():
    st = _page("Status")
    for bad in ("99.9", "97.2", "< 100 ms", "uptime over", "degradedSeed", "Payments & Billing"):
        assert bad not in st, bad
    assert "/api/status" in st


def test_help_and_contact_make_no_unverified_claims():
    for name in ("HelpCenter", "Contact"):
        text = _page(name)
        for bad in ("@synaptiq.academy", "articles", "Most viewed", "7 years", "within 30 days", "working days",
                    "Book a Demo", "migrate", "No credit card", "personally", "Built on trust", "modernize"):
            assert bad not in text, f"{name}: {bad}"


@pytest.mark.parametrize("name", PUBLIC)
def test_public_pages_avoid_filler_and_internal_language(name):
    text = _page(name)
    for bad in (r"\bempower", r"\bunlock", r"revolutioni[sz]e", r"\bseamless", r"supercharg", r"transform your research",
                r"next-generation", r"cutting-edge", r"world-class", r"future of research", r"Whether you're",
                r"\bendpoint\b", r"MongoDB", r"feature flag", r"GDPR[- ]compliant", r"Join Now", r"Try Synaptiq"):
        assert not re.search(bad, text, re.I), f"{name}: {bad}"


@pytest.mark.parametrize("name,path", [("Contact", "/contact"), ("HelpCenter", "/help-center"), ("Status", "/status"),
                                       ("Security", "/security"), ("LegalCenter", "/legal"), ("AiPolicy", "/ai-policy")])
def test_pages_set_their_own_metadata(name, path):
    text = _page(name)
    assert "setPageSeo" in text and f'path: "{path}"' in text


def test_editorial_body_copy_is_one_shared_rule_with_a_mobile_fallback():
    css = (SRC / "components" / "landing" / "landing.css").read_text()
    block = css[css.index("Editorial body copy"):]
    assert "text-align: justify" in block and "hyphens: auto" in block
    assert "@media (max-width: 700px)" in block and "text-align: left" in block
    assert 'className="lp-prose"' in _page("About")
    assert '<html lang="en">' in (ROOT / "frontend" / "public" / "index.html").read_text()


def test_pricing_matches_the_owner_model():
    pr = _page("Pricing")
    cat = (ROOT / "backend" / "plans_catalogue.py").read_text()
    assert "€9.99" in pr or "9.99" in cat
    assert "Custom" in pr and "Contact Sales" in pr and "299" not in pr


def test_terminology_reference_exists():
    doc = (ROOT / "docs" / "product" / "public-language.md").read_text()
    for term in ("Academic Passport", "Research Need", "Manuscript Copilot", "Impact Dashboard", "Start Free"):
        assert term in doc
