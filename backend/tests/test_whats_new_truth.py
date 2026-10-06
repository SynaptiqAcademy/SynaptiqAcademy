"""/whats-new: a curated, verifiable product ledger. No version numbers,
roadmap, metrics or hype; current plan names; public links only; product
claims bound to the code they describe."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.test_landing_commercial_truth import STALE, FABRICATION, UNSAFE, GENERIC, _visible_text

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"
DATA = (SRC / "content" / "whats-new" / "index.js").read_text()
PAGE = (SRC / "pages" / "resources" / "WhatsNew.jsx").read_text()
TEXT = _visible_text(DATA + PAGE)
APP = (SRC / "App.js").read_text()
BACKEND = Path(__file__).resolve().parents[1]

BANNED = [r"\bv?\d+\.\d+(\.\d+)?\b(?! ?(AI|GB|credits))", r"[Cc]oming soon", r"[Rr]oadmap", r"[Uu]p next",
          r"[Tt]hrilled", r"[Ee]xcited", r"[Dd]elighted", r"[Gg]ame[- ]chang", r"[Ss]marter", r"\d+%", r"\d+x faster",
          r"[Nn]ewsletter", r"[Ss]ubscribe", r"[Rr]eal-time", r"[Pp]ro Researcher", r"Institution plan",
          r"[Vv]erified researcher", r"AI matching", r"now available to buy", r"Pro is now available", r"€"]


@pytest.mark.parametrize("pattern", STALE + FABRICATION + UNSAFE + GENERIC + BANNED)
def test_no_unsupported_or_hyped_claims(pattern):
    assert not re.search(pattern, TEXT), pattern


def test_links_are_public_routes():
    for href in re.findall(r'href: "(/[a-z/-]*)"', DATA):
        assert f'path="{href}"' in APP, href


def test_availability_uses_current_plan_names():
    for a in re.findall(r'availability: "([^"]+)"', DATA):
        assert not re.search(r"Researcher|Institution plan|Enterprise", a), a


def test_claims_bound_to_code():
    rn = (BACKEND / "routers" / "research_need.py").read_text()
    assert "zero-credit" in rn and "Deterministic" in rn                 # notes 5/6: matching uses no credits
    assert "use_ai" in rn                                                 # note 5: AI interpretation is optional
    tb = (BACKEND / "routers" / "team_builder.py").read_text()
    assert '"status") == "accepted"' in tb and "human-initiated only" in tb  # note 8
    from routers.assistant import CAPABILITY_DIRECTIVES
    assert "Never create" in CAPABILITY_DIRECTIVES["citation_generation"]  # note 12
    inst = (BACKEND / "routers" / "institutions.py").read_text()
    assert '"admin_invite"' in inst                                       # note 13
    assert "Online purchase isn't open yet." in DATA                      # note 10: no purchase implied


def test_page_has_permalinks_and_machine_readable_dates():
    assert 'id={`note-${n.slug}`}' in PAGE and "dateTime={n.released_at}" in PAGE
    assert "publishedNotes()" in PAGE
