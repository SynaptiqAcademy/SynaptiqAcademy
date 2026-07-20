"""Email Verification — sent immediately after registration and on resend.

Token generation/storage/expiry stays in routers/auth.py (JWT + single-use
`email_verifications` record) — this module only renders the message.
"""
from __future__ import annotations

from typing import Tuple

from ..categories import EmailCategory
from ..components import (
    component_hero, component_body_text, component_bullet_list,
    component_button_row, component_link_fallback, component_alert_banner,
)
from ..layout import render_email
from ..plaintext import text_heading, text_paragraph, text_bullet_list, text_button, render_text_email
from ..i18n import t

CATEGORY = EmailCategory.SECURITY

_WHY_KEYS = [
    "verify.why_security",
    "verify.why_notifications",
    "verify.why_invitations",
    "verify.why_recovery",
]


def verification_email(*, recipient_name: str, verify_url: str, expires_in_hours: int = 24,
                       locale: str = "en") -> Tuple[str, str, str]:
    first_name = recipient_name or "there"
    subject = t("verify.subject", locale)
    why_items = [t(key, locale) for key in _WHY_KEYS]

    html = render_email(
        preheader=t("verify.heading", locale),
        sections=[
            component_hero(t("verify.overline", locale), t("verify.heading", locale)),
            component_body_text(f"<p>{t('verify.thanks', locale, first_name=first_name)}</p>"),
            component_body_text(f"<strong>{t('verify.why_heading', locale)}</strong>"),
            component_bullet_list(why_items),
            component_button_row((t("verify.cta_primary", locale), verify_url)),
            component_link_fallback(verify_url),
            component_alert_banner(t("verify.expires_note", locale, expires_hours=expires_in_hours), "info"),
            component_body_text(f"<p style='font-size:12.5px;color:#64748B;'>{t('verify.ignore_note', locale)}</p>"),
        ],
    )

    text = render_text_email(
        sections=[
            text_heading(t("verify.overline", locale), t("verify.heading", locale)),
            text_paragraph(t("verify.thanks", locale, first_name=first_name)),
            t("verify.why_heading", locale) + ":\n" + text_bullet_list(why_items),
            text_button(t("verify.cta_primary", locale), verify_url),
            t("verify.expires_note", locale, expires_hours=expires_in_hours),
            t("verify.ignore_note", locale),
        ],
    )

    return subject, html, text
