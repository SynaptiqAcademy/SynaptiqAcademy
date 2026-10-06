"""/blog: an honest publication. No invented articles, authors, roles,
statistics, newsletter or popularity; one content model with explicit
publication state; truthful structured data only."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.test_landing_commercial_truth import STALE, FABRICATION, UNSAFE, GENERIC, _visible_text

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
INDEX = (SRC / "pages" / "resources" / "Blog.jsx").read_text()
ARTICLE = (SRC / "pages" / "resources" / "BlogArticle.jsx").read_text()
MODEL = (SRC / "content" / "blog" / "index.js").read_text()
APP = (SRC / "App.js").read_text()
TEXT = _visible_text(INDEX + ARTICLE)

BANNED = [r"Synaptiq Team", r"Head of", r"Director", r"Dr\.", r"Prof\.", r"\d+%", r"\d{1,3},\d{3} papers",
          r"[Nn]ewsletter", r"[Ss]ubscribe", r"[Uu]nsubscribe", r"[Mm]ost read", r"[Tt]rending", r"[Pp]opular",
          r"[Ww]eekly", r"[Pp]eer-reviewed", r"[Ee]ditorial board", r"Insights & Ideas", r"Start Free",
          r"readTime", r"initials", r"ARTICLES = \["]


@pytest.mark.parametrize("pattern", STALE + FABRICATION + UNSAFE + GENERIC + BANNED)
def test_no_invented_content_or_promotion(pattern):
    assert not re.search(pattern, TEXT), pattern


def test_single_model_explicit_state_nothing_published_yet():
    assert 'p.status === "published"' in MODEL and "export const POSTS = [];" in MODEL
    assert "publishedPosts()" in INDEX and "findPost(slug)" in ARTICLE


def test_structured_data_only_from_real_metadata():
    assert '"@type": "BlogPosting"' in ARTICLE and "datePublished: post.published_at" in ARTICLE
    assert "post.updated_at ? { dateModified" in ARTICLE
    assert "aggregateRating" not in ARTICLE and '"Review"' not in ARTICLE


def test_unknown_articles_noindex_and_routes_exist():
    assert 'm.content = "noindex"' in ARTICLE
    assert 'path="/resources/blog/:slug"' in APP and 'path="/blog"' in APP


def test_analytics_carry_no_query_text():
    for call in re.findall(r"track\(([^)]*)\)", INDEX + ARTICLE):
        assert not re.search(r"\bq\b|needle|value", call), call
