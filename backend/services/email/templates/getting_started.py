"""Getting Started — sent 24h after registration, only to users who are
still not "active" (see worker/handlers.py's email.getting_started_check
handler for the real, DB-verified eligibility check; this module only
renders the message from data it's handed).
"""
from __future__ import annotations

from typing import Sequence, Tuple

from ..categories import EmailCategory
from ..components import (
    component_hero, component_body_text, component_progress_bar,
    component_bullet_list, component_checklist, component_button_row,
)
from ..layout import render_email
from ..plaintext import (
    text_heading, text_paragraph, text_progress, text_bullet_list,
    text_checklist, text_button, render_text_email,
)
from ..i18n import t

CATEGORY = EmailCategory.PRODUCT_UPDATES

_BENEFITS = [
    "Verified profile badge",
    "Better collaboration matches",
    "Higher trust score",
    "Increased research visibility",
    "AI recommendations tailored to your work",
    "Suggested collaborators in your field",
]


def getting_started_email(*, recipient_name: str, completion_pct: int,
                          remaining_tasks: Sequence[tuple[str, bool]],
                          profile_setup_url: str, locale: str = "en") -> Tuple[str, str, str]:
    """`remaining_tasks` is the real, verified checklist — (label, done) pairs
    computed from the user's actual data (see services/profile_completion.py),
    never a hardcoded or estimated list."""
    first_name = recipient_name or "there"
    subject = t("getting_started.subject", locale)

    html = render_email(
        preheader=t("getting_started.intro", locale),
        sections=[
            component_hero(t("getting_started.overline", locale), t("getting_started.heading", locale, first_name=first_name)),
            component_progress_bar(completion_pct, t("getting_started.progress_label", locale)),
            component_body_text(f"<p>{t('getting_started.intro', locale)}</p>"),
            component_body_text(f"<strong>{t('getting_started.benefits_heading', locale)}</strong>"),
            component_bullet_list(_BENEFITS),
            component_body_text(f"<strong>{t('getting_started.tasks_heading', locale)}</strong>"),
            component_checklist(list(remaining_tasks)),
            component_button_row((t("getting_started.cta_primary", locale), profile_setup_url)),
        ],
    )

    text = render_text_email(
        sections=[
            text_heading(t("getting_started.overline", locale), t("getting_started.heading", locale, first_name=first_name)),
            text_progress(completion_pct, t("getting_started.progress_label", locale)),
            text_paragraph(t("getting_started.intro", locale)),
            t("getting_started.benefits_heading", locale) + ":\n" + text_bullet_list(_BENEFITS),
            t("getting_started.tasks_heading", locale) + ":\n" + text_checklist(list(remaining_tasks)),
            text_button(t("getting_started.cta_primary", locale), profile_setup_url),
        ],
    )

    return subject, html, text
