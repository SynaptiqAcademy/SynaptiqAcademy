"""Manuscript Review Request — migrated to the component system."""
from __future__ import annotations

from typing import Tuple

from ..categories import EmailCategory
from ..components import component_hero, component_body_text, component_button_row, component_link_fallback
from ..layout import render_email
from ..plaintext import text_heading, text_paragraph, text_button, render_text_email

CATEGORY = EmailCategory.TRANSACTIONAL


def review_request_email(*, recipient_name: str, manuscript_title: str, requester_name: str,
                         section: str, note: str, review_url: str) -> Tuple[str, str, str]:
    name = recipient_name or "there"
    section_line = f"<p><strong>Section:</strong> {section}</p>" if section else ""
    note_block = (
        f"<blockquote style='margin:16px 0;padding:8px 14px;border-left:3px solid #0F2847;color:#475569;'>{note}</blockquote>"
        if note else ""
    )
    subject = f"Review requested: {manuscript_title[:60]}"
    body = (
        f"<p>Hi {name},</p>"
        f"<p><strong>{requester_name}</strong> has requested your review on the manuscript "
        f"<em>{manuscript_title}</em>.</p>"
        f"{section_line}{note_block}"
        f"<p>Accept the review to access the manuscript and submit a verdict when ready.</p>"
    )
    decline_note = "You can decline the review without consequence."

    html = render_email(
        preheader="You've been asked to review a manuscript",
        sections=[
            component_hero("Manuscript review", "You've been asked to review a manuscript"),
            component_body_text(body),
            component_button_row(("Open review", review_url)),
            component_link_fallback(review_url),
            component_body_text(f"<p style='font-size:12.5px;color:#64748B;'>{decline_note}</p>"),
        ],
    )
    text_note = f"Section: {section}\n" if section else ""
    text_quote = f'"{note}"\n' if note else ""
    text = render_text_email(sections=[
        text_heading("Manuscript review", "You've been asked to review a manuscript"),
        text_paragraph(f"Hi {name}, {requester_name} has requested your review on the manuscript "
                       f"\"{manuscript_title}\".\n{text_note}{text_quote}"
                       f"Accept the review to access the manuscript and submit a verdict when ready."),
        text_button("Open review", review_url),
        decline_note,
    ])
    return subject, html, text
