"""Workspace Invitation — migrated to the component system."""
from __future__ import annotations

from typing import Tuple

from ..categories import EmailCategory
from ..components import component_hero, component_body_text, component_button_row, component_link_fallback
from ..layout import render_email
from ..plaintext import text_heading, text_paragraph, text_button, render_text_email

CATEGORY = EmailCategory.TRANSACTIONAL


def workspace_invitation_email(*, recipient_name: str, workspace_name: str, role: str,
                               inviter_name: str, accept_url: str) -> Tuple[str, str, str]:
    subject = f"{inviter_name} invited you to '{workspace_name}' on SYNAPTIQ"
    body = (
        f"<p><strong>{inviter_name}</strong> has invited you to collaborate in the workspace "
        f"<strong>{workspace_name}</strong> on SYNAPTIQ.</p>"
        f"<p>You will join as <strong>{role}</strong>.</p>"
    )
    note = "If you do not recognize the inviter, you can safely ignore this message."

    html = render_email(
        preheader=f"Join {workspace_name}",
        sections=[
            component_hero("Workspace invitation", f"Join {workspace_name}"),
            component_body_text(body),
            component_button_row(("Review invitation", accept_url)),
            component_link_fallback(accept_url),
            component_body_text(f"<p style='font-size:12.5px;color:#64748B;'>{note}</p>"),
        ],
    )
    text = render_text_email(sections=[
        text_heading("Workspace invitation", f"Join {workspace_name}"),
        text_paragraph(f"{inviter_name} has invited you to collaborate in the workspace {workspace_name} on SYNAPTIQ. "
                       f"You will join as {role}."),
        text_button("Review invitation", accept_url),
        note,
    ])
    return subject, html, text
