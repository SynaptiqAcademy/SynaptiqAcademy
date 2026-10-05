"""/platform: claim safety, no pricing, plan labels that match enforcement."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.test_landing_commercial_truth import STALE, FABRICATION, UNSAFE, GENERIC, _visible_text

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"
FILES = [FRONTEND / "pages" / "Platform.jsx", FRONTEND / "components" / "platform" / "SystemMap.jsx"]
SRC = "\n".join(p.read_text() for p in FILES)
TEXT = _visible_text(SRC)
MIDDLEWARE = (Path(__file__).resolve().parents[1] / "services" / "monetization_middleware.py").read_text()

OLD_CLAIMS = [r"Operating System for Global Research", r"847 papers", r"readiness score", r"8-level trust",
              r"AES-256", r"\bSSO\b", r"\bSAML\b", r"tamper-proof", r"conflict-free", r"Knowledge Graph",
              r"Marketplace", r"H-index", r"altmetrics", r"real time", r"\bmatch score\b(?! )", r"\d+% match",
              r"From idea to impact", r"One-stop", r"Everything you need", r"verified researchers?"]


@pytest.mark.parametrize("pattern", STALE + FABRICATION + UNSAFE + GENERIC + OLD_CLAIMS)
def test_no_unsupported_or_generic_claims(pattern):
    assert not re.search(pattern, TEXT, re.I if pattern in OLD_CLAIMS else 0), pattern


def test_no_pricing_on_platform():
    for bad in ("€", "/month", "AI Credits /", " GB", "Early Access", "checkout"):
        assert bad not in TEXT, bad
    assert 'to="/pricing"' in SRC and "Explore Pricing" in SRC


def test_hero_and_ctas():
    assert "Research starts with a question" not in SRC   # owned by Landing
    assert "You already have the question" not in SRC
    assert 'href="#system"' in SRC and 'id="system"' in SRC and "Explore the system" in SRC
    assert ">Start Free<" in SRC


def test_links_are_real_public_routes():
    app = (FRONTEND / "App.js").read_text()
    for route in set(re.findall(r'(?:to|href): ?"(/[a-z-]+)"|to="(/[a-z-]+)"', SRC)):
        r = next(x for x in route if x)
        assert f'path="{r}"' in app, r


def test_paid_steps_are_gated_where_the_map_says():
    # Map labels Research Need / Team Builder / projects / manuscripts / grants / teaching as Pro.
    for pat in ("research-need", "team-builder", r"\^/api/projects", "manuscripts|grant-applications", r"\^/api/teaching\("):
        assert re.search(pat, MIDDLEWARE), pat


def test_verification_semantics_are_narrow():
    assert "Institutional affiliation only" in SRC
    assert "Not degrees, licences or competence" in SRC
    assert "No match percentages" in SRC


def test_analytics_never_carries_free_text():
    for call in re.findall(r"track\(([^)]*)\)", SRC):
        assert "query" not in call and "question" not in call and "email" not in call, call
