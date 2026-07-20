"""Academic Publishing Intelligence — Cover letter generator (Phase XII)."""
from __future__ import annotations

import asyncio
from .models import CoverLetter

_TEMPLATE = """\
Dear {editor_title},

We are pleased to submit our manuscript entitled "{title}" for consideration for publication in {journal}.

{opening_paragraph}

{significance_paragraph}

{originality_paragraph}

{fit_paragraph}

{confirmations}

We believe this manuscript will be of significant interest to the readership of {journal}. \
The manuscript has not been previously published and is not under consideration elsewhere.

We look forward to receiving your editorial decision.

Yours sincerely,

{corresponding_author}
"""

_CONFIRMATIONS = [
    "All authors have approved this submission.",
    "The research complies with all relevant ethical standards.",
    "All authors declare no competing interests.",
    "Data are available upon reasonable request.",
]


def _build_opening(metadata: dict) -> str:
    discipline = metadata.get("discipline", "the field")
    topic = metadata.get("topic", "this important research area")
    return (
        f"This manuscript presents {topic} within the area of {discipline}. "
        f"The work addresses a significant gap in the current literature and provides "
        f"novel insights with both theoretical and practical implications."
    )


def _build_significance(metadata: dict) -> str:
    key_finding = metadata.get("key_finding", "our core findings")
    return (
        f"The main contribution of this work is {key_finding}. "
        f"Our results extend the existing body of knowledge and have direct implications "
        f"for researchers, practitioners, and policy-makers in this field."
    )


def _build_originality(metadata: dict) -> str:
    method = metadata.get("method", "a rigorous empirical approach")
    return (
        f"To the best of our knowledge, this is one of the first studies to examine "
        f"this question using {method}. The novelty of our approach lies in "
        f"the systematic integration of theory with empirical evidence."
    )


def _build_fit(journal: str, metadata: dict) -> str:
    scope = metadata.get("journal_scope", "the journal's broad scope")
    return (
        f"This manuscript aligns closely with {scope} of {journal}. "
        f"The readership will find it directly relevant to current debates "
        f"and open questions in the field."
    )


async def generate_cover_letter(
    manuscript_title: str,
    journal: str,
    metadata: dict | None = None,
    call_llm=None,
) -> CoverLetter:
    """Generate a structured cover letter, optionally enriched by AI."""
    md = metadata or {}
    editor_title = md.get("editor_title", "Editor-in-Chief")
    author = md.get("corresponding_author", "The Corresponding Author")

    opening = _build_opening(md)
    significance = _build_significance(md)
    originality = _build_originality(md)
    fit = _build_fit(journal, md)
    confirmations = "\n".join(f"• {c}" for c in _CONFIRMATIONS)

    rule_based_text = _TEMPLATE.format(
        editor_title=editor_title,
        title=manuscript_title,
        journal=journal,
        opening_paragraph=opening,
        significance_paragraph=significance,
        originality_paragraph=originality,
        fit_paragraph=fit,
        confirmations=confirmations,
        corresponding_author=author,
    )

    # Optionally enrich with LLM
    final_text = rule_based_text
    if call_llm is not None:
        try:
            prompt = (
                f"You are an expert academic writing coach. "
                f"Improve this cover letter for submission to {journal}. "
                f"Keep the structure but make it more compelling and specific.\n\n"
                f"Manuscript: {manuscript_title}\n\n"
                f"Draft:\n{rule_based_text}\n\n"
                f"Provide only the improved letter text, no commentary."
            )
            ai_result = await call_llm(user_msg=prompt, system="You are an expert academic writing assistant.", feature="publishing.cover_letter")
            if ai_result and len(ai_result) > 200:
                final_text = ai_result
        except Exception:
            pass  # Fall back to rule-based text

    sections = [
        "Salutation", "Introduction", "Significance",
        "Originality", "Journal fit", "Confirmations", "Closing",
    ]

    return CoverLetter(
        journal=journal,
        editor_title=editor_title,
        manuscript_title=manuscript_title,
        text=final_text,
        word_count=len(final_text.split()),
        sections=sections,
    )
