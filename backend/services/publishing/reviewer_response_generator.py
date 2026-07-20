"""Academic Publishing Intelligence — Reviewer response generator (Phase XII)."""
from __future__ import annotations

from .models import ReviewerComment, ReviewerResponse, RevisionType

_REVISION_INTROS: dict[RevisionType, str] = {
    RevisionType.MAJOR: (
        "We sincerely thank the reviewers for their thorough and constructive feedback. "
        "We have carefully addressed each comment and made substantial revisions to the manuscript. "
        "Below, we provide a point-by-point response to each reviewer."
    ),
    RevisionType.MINOR: (
        "We thank the reviewers for their helpful comments. "
        "We have addressed all points raised and made the appropriate revisions. "
        "Below, we detail our responses to each comment."
    ),
    RevisionType.REJECT_RESUBMIT: (
        "We thank the editor and reviewers for the detailed evaluation. "
        "We have substantially revised the manuscript in response to the reviewers' concerns. "
        "We believe the revised manuscript now addresses the key issues raised."
    ),
    RevisionType.EDITORIAL: (
        "We thank the editorial team for their feedback. "
        "We have made the requested revisions and respond to each point below."
    ),
    RevisionType.ACCEPT: (
        "We thank the reviewers and editors for accepting our manuscript. "
        "We have made the minor revisions requested and provide our responses below."
    ),
}

_COVER_LETTER_TEMPLATES: dict[RevisionType, str] = {
    RevisionType.MAJOR: (
        "Dear {editor_title},\n\n"
        "We are pleased to submit the {revision_type} of our manuscript titled \"{title}\" "
        "(Manuscript ID: {manuscript_id}). We have carefully addressed all reviewer concerns "
        "and provide a detailed point-by-point response document.\n\n"
        "The major changes include: (1) comprehensive revision of the Methods section, "
        "(2) additional analyses addressing Reviewer 2's concerns, and "
        "(3) expanded Discussion linking findings to broader implications.\n\n"
        "We believe the revised manuscript is now substantially stronger and suitable "
        "for publication in {journal}.\n\nYours sincerely,\n{author}"
    ),
    RevisionType.MINOR: (
        "Dear {editor_title},\n\n"
        "We are pleased to resubmit our manuscript \"{title}\" following minor revisions. "
        "All reviewer comments have been addressed as detailed in the attached response document.\n\n"
        "Yours sincerely,\n{author}"
    ),
    RevisionType.REJECT_RESUBMIT: (
        "Dear {editor_title},\n\n"
        "We thank you for the opportunity to resubmit our manuscript \"{title}\". "
        "We have substantially revised the manuscript to address the fundamental concerns raised. "
        "We believe this resubmission represents a significantly improved work.\n\n"
        "Yours sincerely,\n{author}"
    ),
    RevisionType.EDITORIAL: (
        "Dear {editor_title},\n\n"
        "Please find enclosed the revised version of \"{title}\", addressing the editorial "
        "comments received. All requested changes have been made.\n\n"
        "Yours sincerely,\n{author}"
    ),
    RevisionType.ACCEPT: (
        "Dear {editor_title},\n\n"
        "We are delighted to submit the final revised version of \"{title}\". "
        "We have incorporated the minor revisions requested.\n\n"
        "Yours sincerely,\n{author}"
    ),
}

_RESPONSE_TEMPLATE = (
    "**{reviewer_id} — Comment {n}:**\n\n"
    "*Reviewer's comment:*\n> {comment}\n\n"
    "*Response:*\n{response}\n\n"
    "*Action taken:*\n{action}\n\n"
    "---\n"
)


def _generate_response_text(
    comment: str,
    revision_type: RevisionType,
) -> tuple[str, str]:
    """Generate a response and action for a single reviewer comment."""
    comment_lower = comment.lower()

    # Detect comment type and generate appropriate response
    if any(kw in comment_lower for kw in ["sample size", "power", "n=", "participants"]):
        response = (
            "We thank the reviewer for raising this important concern about statistical power. "
            "We have added a post-hoc power analysis (see revised Methods, p. XX) and "
            "explicitly acknowledge this as a limitation in the Discussion."
        )
        action = "Added power analysis; expanded limitations section."

    elif any(kw in comment_lower for kw in ["literature", "citation", "reference", "prior work"]):
        response = (
            "We appreciate this suggestion. We have expanded the literature review to include "
            "the relevant works and have updated our discussion to position our findings "
            "within this broader context. New references have been added on pp. XX–XX."
        )
        action = "Expanded literature review; added new citations."

    elif any(kw in comment_lower for kw in ["methodology", "method", "approach", "validity"]):
        response = (
            "We thank the reviewer for this methodological concern. We have added additional "
            "detail to the Methods section (pp. XX–XX) clarifying our approach and "
            "the validity of our analytical choices."
        )
        action = "Revised and expanded Methods section."

    elif any(kw in comment_lower for kw in ["clarity", "clear", "confusing", "unclear", "explain"]):
        response = (
            "We agree that this section required clarification. We have revised the text "
            "for greater clarity and restructured the argument flow (see revised p. XX)."
        )
        action = "Revised section for clarity; improved language and structure."

    elif any(kw in comment_lower for kw in ["figure", "table", "graph", "visualisation"]):
        response = (
            "We thank the reviewer for this suggestion. We have revised the figure/table "
            "as suggested and updated the caption to be more informative."
        )
        action = "Revised figure/table; updated captions."

    elif any(kw in comment_lower for kw in ["limitation", "weakness", "constraint"]):
        response = (
            "We agree that this limitation should be more explicitly addressed. "
            "We have added a dedicated paragraph discussing this limitation and its implications "
            "for the interpretation of our findings (Discussion, p. XX)."
        )
        action = "Added limitations discussion."

    elif any(kw in comment_lower for kw in ["discussion", "implication", "practical"]):
        response = (
            "We thank the reviewer for this important point. We have expanded the Discussion "
            "to address the theoretical and practical implications of our findings more thoroughly."
        )
        action = "Expanded Discussion section."

    else:
        response = (
            "We thank the reviewer for this comment. We have carefully considered this point "
            "and have made the appropriate revisions to address the concern raised."
        )
        action = "Revised manuscript in response to this comment."

    return response, action


def generate_reviewer_response(
    revision_type: RevisionType,
    manuscript_title: str,
    journal: str,
    reviewer_comments: list[dict],
    metadata: dict | None = None,
) -> ReviewerResponse:
    """Build a full point-by-point reviewer response document."""
    md = metadata or {}
    editor_title = md.get("editor_title", "Editor-in-Chief")
    author = md.get("corresponding_author", "The Corresponding Author")
    manuscript_id = md.get("manuscript_id", "XXXX-XXXX")

    cover = _COVER_LETTER_TEMPLATES.get(revision_type, _COVER_LETTER_TEMPLATES[RevisionType.MAJOR])
    cover_text = cover.format(
        editor_title=editor_title,
        revision_type=revision_type.value.replace("_", " ").title(),
        title=manuscript_title,
        manuscript_id=manuscript_id,
        journal=journal,
        author=author,
    )

    intro = _REVISION_INTROS.get(revision_type, _REVISION_INTROS[RevisionType.MAJOR])
    comments: list[ReviewerComment] = []
    body_parts = [intro, "\n"]

    for i, raw in enumerate(reviewer_comments, 1):
        reviewer_id = raw.get("reviewer_id", f"Reviewer {(i - 1) // 5 + 1}")
        comment_text = raw.get("comment", "")
        response_text, action_text = _generate_response_text(comment_text, revision_type)
        ms_changes = raw.get("manuscript_changes", "See revised manuscript.")

        rc = ReviewerComment(
            reviewer_id=reviewer_id,
            comment_number=i,
            original_comment=comment_text,
            response_text=response_text,
            action_taken=action_text,
            manuscript_changes=ms_changes,
        )
        comments.append(rc)
        body_parts.append(_RESPONSE_TEMPLATE.format(
            reviewer_id=reviewer_id, n=i,
            comment=comment_text[:300] + ("..." if len(comment_text) > 300 else ""),
            response=response_text,
            action=action_text,
        ))

    full_text = cover_text + "\n\n---\n\n# Response to Reviewers\n\n" + "".join(body_parts)

    return ReviewerResponse(
        revision_type=revision_type,
        manuscript_title=manuscript_title,
        journal=journal,
        cover_letter=cover_text,
        comments=comments,
        general_response=intro,
        full_text=full_text,
    )
