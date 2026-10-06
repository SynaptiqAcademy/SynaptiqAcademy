"""Collaboration Invitation / Application Update — migrated to the component system."""
from __future__ import annotations

from html import escape
from typing import Tuple

from ..categories import EmailCategory
from ..components import component_hero, component_body_text, component_button_row, component_link_fallback
from ..layout import render_email
from ..plaintext import text_heading, text_paragraph, text_button, render_text_email

CATEGORY = EmailCategory.TRANSACTIONAL


def collaboration_invitation_email(*, recipient_name: str, collaboration_title: str,
                                   inviter_name: str, kind: str, action_url: str,
                                   message: str = "") -> Tuple[str, str, str]:
    """`kind` is 'application' (someone applied to your collab) or 'decision' (your application was decided).

    The collaboration title and the applicant's message stay in the app: they
    can reveal research topics, and emails pass through our email provider.
    """
    who = escape(inviter_name or "A Synaptiq member")
    if kind == "application":
        overline = "New application"
        heading = "Someone applied to your collaboration"
        body = f"<p><strong>{who}</strong> applied to one of your collaborations.</p>"
        cta = "Review application"
        text_body = f"{inviter_name or 'A Synaptiq member'} applied to one of your collaborations."
    else:
        overline = "Application update"
        heading = "Your collaboration application was updated"
        body = (
            f"<p>The status of one of your collaboration applications was updated by <strong>{who}</strong>.</p>"
        )
        cta = "Open collaboration"
        text_body = f"The status of one of your collaboration applications was updated by {inviter_name or 'a Synaptiq member'}."

    msg_block = "<p>Open Synaptiq to read the details.</p>"
    subject = f"SYNAPTIQ: {heading}"

    html = render_email(
        preheader=heading,
        sections=[
            component_hero(overline, heading),
            component_body_text(body + msg_block),
            component_button_row((cta, action_url)),
            component_link_fallback(action_url),
        ],
    )
    text = render_text_email(sections=[
        text_heading(overline, heading),
        text_paragraph(text_body + " Open Synaptiq to read the details."),
        text_button(cta, action_url),
    ])
    return subject, html, text
