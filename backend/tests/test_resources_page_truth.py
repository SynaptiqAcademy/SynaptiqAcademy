"""/resources: an honest research library. No invented counts, articles,
downloads, newsletter or popularity; content comes from one model with an
explicit publication state."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.test_landing_commercial_truth import STALE, FABRICATION, UNSAFE, GENERIC, _visible_text

ROOT = Path(__file__).resolve().parents[2] / "frontend" / "src"
INDEX = (ROOT / "pages" / "resources" / "Resources.jsx").read_text()
ARTICLE = (ROOT / "pages" / "resources" / "ResourceArticle.jsx").read_text()
MODEL = (ROOT / "content" / "resources" / "index.js").read_text()
TEXT = _visible_text(INDEX + ARTICLE)

BANNED = [r"\d+\+? (case studies|articles|guides|resources)", r"[Uu]pdated weekly", r"[Mm]ost read", r"[Tt]rending",
          r"[Pp]opular", r"[Nn]ewsletter", r"[Ss]ubscribe", r"[Dd]ownload", r"[Ww]hite ?paper", r"[Ee]book",
          r"[Ww]ebinar", r"[Tt]emplate", r"[Tt]oolkit", r"Dr\.", r"Head of", r"Everything you need",
          r"[Cc]ustomer [Ss]tories", r"universities.*worldwide", r"Start Free", r"€"]


@pytest.mark.parametrize("pattern", STALE + FABRICATION + UNSAFE + GENERIC + BANNED)
def test_no_invented_or_promotional_claims(pattern):
    assert not re.search(pattern, TEXT), pattern


def test_single_content_source_with_publication_state():
    assert 'status === "published"' in MODEL and "isPublishable" in MODEL
    assert "publishedResources()" in INDEX and "findPublished(slug)" in ARTICLE
    assert "export const RESOURCES = [];" in MODEL          # nothing published until it passes review


def test_reading_time_is_calculated_not_typed():
    assert "readingMinutes" in MODEL and not re.search(r"readTime|\d+ min read", INDEX + MODEL)


def test_unknown_guides_are_noindex_and_kinds_are_labelled():
    assert 'm.content = "noindex"' in ARTICLE
    for kind in ("Product help", "Editorial", "Product updates"):
        assert kind in INDEX


def test_search_tracks_no_query_text():
    for call in re.findall(r"track\(([^)]*)\)", INDEX + ARTICLE):
        assert not re.search(r"\bq\b|needle|value", call), call
