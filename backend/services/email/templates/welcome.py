"""Welcome Email — sent once, immediately after successful registration.

Idempotency lives at the call site (routers/auth.py atomically flips
`welcome_email_sent` before enqueuing) — this module is a pure renderer.
"""
from __future__ import annotations

from typing import Tuple

from ..categories import EmailCategory
from ..components import (
    component_hero, component_body_text, component_feature_grid,
    component_step_list, component_info_card, component_button_row, component_divider,
)
from ..layout import render_email
from ..plaintext import (
    text_heading, text_paragraph, text_feature_list, text_step_list,
    text_button, text_divider, render_text_email,
)
from ..i18n import t

CATEGORY = EmailCategory.TRANSACTIONAL

_WHO_FOR = "Researchers, PhD Candidates, Educators, Universities, and Research Teams"

_FEATURES = [
    ("🪪", "Academic Passport", "Your verified academic identity"),
    ("🤝", "Collaborations", "Find and work with researchers worldwide"),
    ("🧪", "Research Workspaces", "Organize projects and teams"),
    ("✨", "AI Research Tools", "Draft, summarize, and analyze faster"),
    ("📚", "Publishing", "Track and manage your publications"),
    ("🎤", "Conferences", "Discover and track academic events"),
    ("💰", "Grants", "Find funding opportunities"),
]

_STEPS = [
    ("Complete Academic Passport", "Add your institution, role, and research areas"),
    ("Verify Email", "Confirm your email address to unlock full access"),
    ("Connect ORCID", "Sync your publications and identifiers automatically"),
    ("Discover Researchers", "Find collaborators in your field"),
    ("Create First Workspace", "Start organizing your research"),
]


def welcome_email(*, recipient_name: str, profile_setup_url: str, app_url: str,
                  locale: str = "en") -> Tuple[str, str, str]:
    first_name = recipient_name or "researcher"
    subject = t("welcome.subject", locale)

    html = render_email(
        preheader=t("welcome.subheading", locale),
        sections=[
            component_hero(
                t("welcome.overline", locale),
                t("welcome.heading", locale, first_name=first_name),
                t("welcome.subheading", locale),
            ),
            component_body_text(
                f"<p>{t('welcome.intro', locale)}</p>"
                f"<p><strong>Built for:</strong> {_WHO_FOR}.</p>"
            ),
            component_divider(),
            component_body_text(f"<strong>{t('welcome.features_heading', locale)}</strong>"),
            component_feature_grid(_FEATURES),
            component_divider(),
            component_body_text(f"<strong>{t('welcome.quickstart_heading', locale)}</strong>"),
            component_step_list(_STEPS),
            component_info_card(
                t("welcome.credits_heading", locale),
                f"<p>{t('welcome.credits_body', locale)}</p>",
            ),
            component_button_row(
                (t("welcome.cta_primary", locale), profile_setup_url),
                (t("welcome.cta_secondary", locale), app_url),
            ),
        ],
    )

    text = render_text_email(
        sections=[
            text_heading(t("welcome.overline", locale), t("welcome.heading", locale, first_name=first_name), t("welcome.subheading", locale)),
            text_paragraph(t("welcome.intro", locale)),
            f"Built for: {_WHO_FOR}.",
            text_divider(),
            t("welcome.features_heading", locale) + ":\n" + text_feature_list(_FEATURES),
            text_divider(),
            t("welcome.quickstart_heading", locale) + ":\n" + text_step_list(_STEPS),
            t("welcome.credits_heading", locale) + ": " + t("welcome.credits_body", locale),
            text_button(t("welcome.cta_primary", locale), profile_setup_url),
            text_button(t("welcome.cta_secondary", locale), app_url),
        ],
    )

    return subject, html, text
