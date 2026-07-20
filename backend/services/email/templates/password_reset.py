"""Password Reset — migrated from the legacy single-shell template to the
component system. Same trigger site (routers/auth.py forgot_password()),
same token mechanism — this module only changed how the message renders.
"""
from __future__ import annotations

from typing import Tuple

from ..categories import EmailCategory
from ..components import component_hero, component_body_text, component_button_row, component_link_fallback
from ..layout import render_email
from ..plaintext import text_heading, text_paragraph, text_button, render_text_email

CATEGORY = EmailCategory.SECURITY


def password_reset_email(*, recipient_name: str, reset_url: str, expires_in_minutes: int = 30) -> Tuple[str, str, str]:
    subject = "Reset your SYNAPTIQ password"
    name = recipient_name or "there"
    intro = (
        f"Hi {name}, we received a request to reset the password on your SYNAPTIQ account. "
        f"The link below is valid for <strong>{expires_in_minutes} minutes</strong> and can be used once."
    )
    ignore_note = "If you did not request this, you can ignore this email — your password will not change."

    html = render_email(
        preheader="Reset your password",
        sections=[
            component_hero("Security", "Reset your password"),
            component_body_text(f"<p>{intro}</p>"),
            component_button_row(("Reset password", reset_url)),
            component_link_fallback(reset_url),
            component_body_text(f"<p style='font-size:12.5px;color:#64748B;'>{ignore_note}</p>"),
        ],
    )
    text = render_text_email(sections=[
        text_heading("Security", "Reset your password"),
        text_paragraph(f"Hi {name}, we received a request to reset the password on your SYNAPTIQ account. "
                       f"The link below is valid for {expires_in_minutes} minutes and can be used once."),
        text_button("Reset password", reset_url),
        ignore_note,
    ])
    return subject, html, text
