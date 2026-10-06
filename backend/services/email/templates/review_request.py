"""Manuscript Review Request — migrated to the component system."""
from __future__ import annotations

from html import escape
from typing import Tuple

from ..categories import EmailCategory
from ..components import component_hero, component_body_text, component_button_row, component_link_fallback
from ..layout import render_email
from ..plaintext import text_heading, text_paragraph, text_button, render_text_email

CATEGORY = EmailCategory.TRANSACTIONAL


def review_request_email(*, recipient_name: str, manuscript_title: str, requester_name: str,
                         section: str, note: str, review_url: str) -> Tuple[str, str, str]:
    # The manuscript title, section and note stay in the app: they reveal
    # unpublished research, and emails pass through our email provider.
    name = escape(recipient_name or "there")
    requester = escape(requester_name or "A Synaptiq member")
    subject = "You've been asked to review a manuscript on Synaptiq"
    body = (
        f"<p>Hi {name},</p>"
        f"<p><strong>{requester}</strong> has asked you to review a manuscript.</p>"
        f"<p>Open the review to see the manuscript and any note, accept it, and submit a verdict when ready.</p>"
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
    text = render_text_email(sections=[
        text_heading("Manuscript review", "You've been asked to review a manuscript"),
        text_paragraph(f"Hi {recipient_name or 'there'}, {requester_name or 'a Synaptiq member'} has asked you to review a manuscript. "
                       f"Open the review to see the manuscript and any note, accept it, and submit a verdict when ready."),
        text_button("Open review", review_url),
        decline_note,
    ])
    return subject, html, text
