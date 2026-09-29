"""Institution email verification — P1 Phase 7C4.4.

Sent when a user submits an institutional email address to prove
affiliation with a claimed institution (Academic Passport → Institution
Verification → Method 1). Token generation/storage/expiry lives in
routers/institutions.py (JWT + single-use `institution_email_verifications`
record), mirroring services/email/templates/verification.py's pattern for
account email verification — this module only renders the message.
"""
from __future__ import annotations

from typing import Tuple

from ..categories import EmailCategory
from ..components import (
    component_hero, component_body_text, component_button_row,
    component_link_fallback, component_alert_banner,
)
from ..layout import render_email
from ..plaintext import text_heading, text_paragraph, text_button, render_text_email

CATEGORY = EmailCategory.SECURITY


def institution_email_verification_email(
    *, recipient_name: str, institution_name: str, verify_url: str,
    expires_in_minutes: int = 30,
) -> Tuple[str, str, str]:
    first_name = recipient_name or "there"
    subject = f"Confirm your affiliation with {institution_name}"
    heading = "Confirm your institutional email"
    overline = "Academic Passport · Institution Verification"

    html = render_email(
        preheader=heading,
        sections=[
            component_hero(overline, heading),
            component_body_text(
                f"<p>Hi {first_name},</p>"
                f"<p>You asked Synaptiq to verify your affiliation with "
                f"<strong>{institution_name}</strong> using this email address. "
                f"Click the button below to confirm it's yours.</p>"
            ),
            component_button_row(("Confirm institutional email", verify_url)),
            component_link_fallback(verify_url),
            component_alert_banner(
                f"This link expires in {expires_in_minutes} minutes and can only be used once.",
                "info",
            ),
            component_body_text(
                "<p style='font-size:12.5px;color:#64748B;'>"
                "If you didn't request this, you can safely ignore this email — "
                "no changes will be made to your account.</p>"
            ),
        ],
    )

    text = render_text_email(
        sections=[
            text_heading(overline, heading),
            text_paragraph(
                f"Hi {first_name}, you asked Synaptiq to verify your affiliation with "
                f"{institution_name} using this email address."
            ),
            text_button("Confirm institutional email", verify_url),
            f"This link expires in {expires_in_minutes} minutes and can only be used once.",
            "If you didn't request this, you can safely ignore this email.",
        ],
    )

    return subject, html, text
