"""Workspace Invitation — migrated to the component system."""
from __future__ import annotations

from html import escape
from typing import Tuple

from ..categories import EmailCategory
from ..components import component_hero, component_body_text, component_button_row, component_link_fallback
from ..layout import render_email
from ..plaintext import text_heading, text_paragraph, text_button, render_text_email

CATEGORY = EmailCategory.TRANSACTIONAL


def workspace_invitation_email(*, recipient_name: str, workspace_name: str, role: str,
                               inviter_name: str, accept_url: str) -> Tuple[str, str, str]:
    # The workspace name can reveal a research topic, so it stays in the app:
    # emails pass through our email provider and mailbox providers, and the
    # subject is kept in our delivery log.
    inviter = escape(inviter_name or "A Synaptiq member")
    role_txt = escape(role or "member")
    subject = "You've been invited to a workspace on Synaptiq"
    body = (
        f"<p><strong>{inviter}</strong> has invited you to collaborate in a workspace on Synaptiq.</p>"
        f"<p>You will join as <strong>{role_txt}</strong>. Open the invitation to see the workspace.</p>"
    )
    note = "If you do not recognize the inviter, you can safely ignore this message."

    html = render_email(
        preheader="You've been invited to a workspace",
        sections=[
            component_hero("Workspace invitation", "You've been invited to a workspace"),
            component_body_text(body),
            component_button_row(("Review invitation", accept_url)),
            component_link_fallback(accept_url),
            component_body_text(f"<p style='font-size:12.5px;color:#64748B;'>{note}</p>"),
        ],
    )
    text = render_text_email(sections=[
        text_heading("Workspace invitation", "You've been invited to a workspace"),
        text_paragraph(f"{inviter_name or 'A Synaptiq member'} has invited you to collaborate in a workspace on Synaptiq. "
                       f"You will join as {role or 'member'}. Open the invitation to see the workspace."),
        text_button("Review invitation", accept_url),
        note,
    ])
    return subject, html, text
