"""Minimal string catalog for transactional emails.

English is the only populated locale today. The lookup function and catalog
shape are built so adding a language later is "add a dict," not "rewrite the
templates" — every template pulls copy through `t(key, locale, **kwargs)`
instead of hardcoding strings inline. `**kwargs` are substituted with
`str.format`, so a string can read `"Hi {name},"` in every locale.

Locale resolution is caller-provided (e.g. from the user's stored language
preference) — this module has no opinion on where that comes from.
"""
from __future__ import annotations

DEFAULT_LOCALE = "en"

_CATALOG: dict[str, dict[str, str]] = {
    "en": {
        # Welcome email
        "welcome.subject": "Welcome to Synaptiq — Your Academic Research Platform",
        "welcome.overline": "Welcome",
        "welcome.heading": "Welcome to Synaptiq, {first_name}",
        "welcome.subheading": "Your academic research platform is ready.",
        "welcome.intro": (
            "Synaptiq brings your research, collaborations, and academic identity into one place — "
            "built for researchers, PhD candidates, educators, universities, and research teams."
        ),
        "welcome.features_heading": "What you can do on Synaptiq",
        "welcome.quickstart_heading": "Quick start",
        "welcome.credits_heading": "Subscriptions & AI Credits",
        "welcome.credits_body": (
            "Your plan includes a monthly allowance of AI Credits. Credits are only consumed when you "
            "actively use an AI tool (e.g. drafting, summarizing, or analyzing) — browsing, editing your "
            "profile, and messaging never cost credits."
        ),
        "welcome.cta_primary": "Complete Your Academic Profile",
        "welcome.cta_secondary": "Go to Synaptiq",

        # Email verification
        "verify.subject": "Verify your email address",
        "verify.overline": "Email verification",
        "verify.heading": "Confirm your email address",
        "verify.thanks": "Thank you for creating a Synaptiq account, {first_name}.",
        "verify.why_heading": "Why we verify your email",
        "verify.why_security": "Security — confirms you own this account",
        "verify.why_notifications": "Notifications — so you never miss an update",
        "verify.why_invitations": "Collaboration invitations — colleagues can reach you",
        "verify.why_recovery": "Account recovery — needed if you ever lose access",
        "verify.cta_primary": "Verify Email Address",
        "verify.expires_note": "This link expires in {expires_hours} hours and can only be used once.",
        "verify.ignore_note": "If you did not create a Synaptiq account, you can safely ignore this email.",

        # Getting started
        "getting_started.subject": "Let's complete your academic profile",
        "getting_started.overline": "Getting started",
        "getting_started.heading": "Let's complete your academic profile, {first_name}",
        "getting_started.progress_label": "Profile completion",
        "getting_started.intro": "Complete your profile to unlock the best Synaptiq experience.",
        "getting_started.benefits_heading": "Why complete your profile",
        "getting_started.tasks_heading": "Remaining tasks",
        "getting_started.cta_primary": "Continue Profile Setup",
    }
}


def t(key: str, locale: str = DEFAULT_LOCALE, **kwargs) -> str:
    catalog = _CATALOG.get(locale) or _CATALOG[DEFAULT_LOCALE]
    template = catalog.get(key) or _CATALOG[DEFAULT_LOCALE].get(key, key)
    return template.format(**kwargs) if kwargs else template
