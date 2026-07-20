"""Collaboration Invitation / Application Update — migrated to the component system."""
from __future__ import annotations

from typing import Tuple

from ..categories import EmailCategory
from ..components import component_hero, component_body_text, component_button_row, component_link_fallback
from ..layout import render_email
from ..plaintext import text_heading, text_paragraph, text_button, render_text_email

CATEGORY = EmailCategory.TRANSACTIONAL


def collaboration_invitation_email(*, recipient_name: str, collaboration_title: str,
                                   inviter_name: str, kind: str, action_url: str,
                                   message: str = "") -> Tuple[str, str, str]:
    """`kind` is 'application' (someone applied to your collab) or 'decision' (your application was decided)."""
    if kind == "application":
        overline = "New application"
        heading = "Someone applied to your collaboration"
        body = f"<p><strong>{inviter_name}</strong> applied to your collaboration <strong>{collaboration_title}</strong>.</p>"
        cta = "Review application"
        text_body = f"{inviter_name} applied to your collaboration {collaboration_title}."
    else:
        overline = "Application update"
        heading = "Your collaboration application was updated"
        body = (
            f"<p>The status of your application to <strong>{collaboration_title}</strong> "
            f"was updated by <strong>{inviter_name}</strong>.</p>"
        )
        cta = "Open collaboration"
        text_body = f"The status of your application to {collaboration_title} was updated by {inviter_name}."

    msg_block = (
        f"<blockquote style='margin:16px 0;padding:8px 14px;border-left:3px solid #0F2847;color:#475569;'>{message}</blockquote>"
        if message else ""
    )
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
        text_paragraph(text_body + (f'\n"{message}"' if message else "")),
        text_button(cta, action_url),
    ])
    return subject, html, text
