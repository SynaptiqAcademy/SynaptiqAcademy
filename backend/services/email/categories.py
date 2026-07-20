"""Email preference categories.

Every email sent through this system declares a category. SECURITY and
TRANSACTIONAL are mandatory — a user can never disable them, matching the
account-safety requirement that a password reset or verification link must
always be deliverable. The other categories check the existing preference
fields on the user document (see routers/email_preferences.py) so this file
is the single gate every future email (billing, newsletters, product
updates...) passes through, rather than each trigger site re-implementing
its own opt-out check.
"""
from __future__ import annotations

from enum import Enum


class EmailCategory(str, Enum):
    SECURITY = "security"                  # verification, password reset, 2FA, new-device alerts — never gated
    TRANSACTIONAL = "transactional"         # welcome, receipts, invitations — core product flow, never gated
    BILLING = "billing"                     # invoices, renewals, payment failed — never gated (legal/financial record)
    PRODUCT_UPDATES = "product_updates"     # getting-started nudges, feature announcements
    RESEARCH_NEWSLETTER = "research_newsletter"
    MARKETING = "marketing"


# Categories a user cannot turn off, regardless of their preference document.
MANDATORY_CATEGORIES = {EmailCategory.SECURITY, EmailCategory.TRANSACTIONAL, EmailCategory.BILLING}


def should_send(user: dict, category: EmailCategory) -> bool:
    """True if this email should be sent given the recipient's preferences.

    `user` is the raw Mongo user document (or any dict with the same keys).
    Missing preference fields default to opted-in, matching
    routers/email_preferences.py's defaults.
    """
    if category in MANDATORY_CATEGORIES:
        return True
    if category == EmailCategory.MARKETING:
        return bool(user.get("email_marketing_consent", True))
    if category in (EmailCategory.PRODUCT_UPDATES, EmailCategory.RESEARCH_NEWSLETTER):
        return bool(user.get("email_notifications_enabled", True))
    return True
