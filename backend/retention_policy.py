"""Retention schedule — the single source of truth for how long Synaptiq keeps
each category of stored data, and how that limit is enforced.

Every period here either restates a decision already made and published
(Privacy Policy "How long we keep data") or reuses an existing operational
period from the code. Nothing here is a legal conclusion: rows marked
``legal_review=True`` must be confirmed by counsel before commercial launch.

A row whose ``days`` is ``None`` has NO automatic deletion yet. Its period
can be switched on without a code change by setting the environment variable
named in ``env`` (a whole number of days) once a period is decided.

Enforcement:
  * ``ttl``      — the document carries ``expires_at`` and a MongoDB TTL index
                   deletes it (index created at startup).
  * ``purge``    — services/cleanup_service.py deletes documents older than
                   the period, daily.
  * ``account``  — kept while the account exists; handled at account
                   deletion by services/account_lifecycle.py.
  * ``none``     — no automatic deletion (see ``note``).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass(frozen=True)
class Rule:
    key: str
    collection: str
    description: str
    days: Optional[int]
    enforcement: str          # ttl | purge | account | none
    basis: str                # where the period comes from
    legal_review: bool = False
    env: Optional[str] = None
    date_field: str = "created_at"
    query: Optional[dict] = None   # extra filter for purge rules
    note: str = ""

    @property
    def effective_days(self) -> Optional[int]:
        if self.env:
            raw = os.environ.get(self.env, "").strip()
            if raw.isdigit() and int(raw) > 0:
                return int(raw)
        return self.days


RULES: tuple[Rule, ...] = (
    # ── Sign-in and security ────────────────────────────────────────────────
    Rule("refresh_tokens", "refresh_tokens", "Sign-in sessions", None, "ttl",
         "Token expiry (14 days, or the browser session)", date_field="expires_at"),
    Rule("email_verifications", "email_verifications", "Email verification links", None, "ttl",
         "Link expiry (24 hours)", date_field="expires_at"),
    Rule("password_resets", "password_resets", "Password reset links", None, "ttl",
         "Link expiry (30 minutes)", date_field="expires_at"),
    Rule("security_events", "security_events", "Security event logs (failed sign-ins, suspicious activity)",
         365, "ttl", "Published in the Privacy Policy (1 year)", legal_review=True, date_field="expires_at"),

    # ── Audit trail ─────────────────────────────────────────────────────────
    Rule("audit_admin", "audit_log", "Records of administrative and account actions",
         90, "ttl", "Existing audit-log period (AUTH-011)", legal_review=True, date_field="expires_at",
         note="Must not contain the email address of a deleted account."),
    Rule("audit_data_access", "audit_log", "Automatic data-access trail written by the database layer",
         90, "purge", "Same period as the audit log (AUTH-011)", legal_review=True,
         date_field="_ts", query={"_source": "shim"}),
    Rule("audit_billing", "audit_log", "Billing, credit and subscription audit records",
         None, "none", "Romanian tax and accounting law", legal_review=True,
         env="RETENTION_AUDIT_BILLING_DAYS", query={"entity_kind": {"$exists": True}},
         note="LEGAL REVIEW REQUIRED: period set by accounting obligations."),

    # ── Consent and contact ─────────────────────────────────────────────────
    Rule("consent_anonymous", "consent_records", "Cookie-consent records not linked to an account",
         730, "purge", "Existing cleanup period (2 years)", legal_review=True,
         query={"user_id": None}),
    Rule("consent_account", "consent_records", "Cookie-consent records linked to an account",
         None, "account", "Proof of consent while the account exists", legal_review=True,
         env="RETENTION_CONSENT_ACCOUNT_DAYS", query={"user_id": {"$ne": None}},
         note="Deleted with the account."),
    Rule("contact_inquiries", "contact_inquiries", "Messages sent through the contact form",
         None, "none", "Kept while needed to answer and follow up", legal_review=True,
         env="RETENTION_CONTACT_INQUIRIES_DAYS",
         note="LEGAL REVIEW REQUIRED: no period decided. Deleted on request."),

    # ── Operational ─────────────────────────────────────────────────────────
    Rule("email_log", "email_log", "Delivery log of emails sent (recipient, subject, status)",
         90, "purge", "Same period as the audit log (AUTH-011)", legal_review=True,
         env="RETENTION_EMAIL_LOG_DAYS"),
    Rule("notifications_read", "notifications", "Read in-app notifications",
         90, "purge", "Existing cleanup period", query={"read": True}),
    Rule("obs_logs", "obs_logs", "Application warning and error logs", 7, "purge",
         "Observability log period (7 days)", date_field="timestamp",
         note="Also covered by a TTL index once the observability TTL ships."),

    # ── Content (kept while the account exists) ─────────────────────────────
    Rule("account", "users", "Account and profile", None, "account",
         "While the account exists; anonymised at deletion"),
    Rule("ai_conversations", "ai_conversations", "AI conversations and results", None, "account",
         "Until the member or the account deletes them"),
    Rule("billing", "billing_history", "Invoices, payments and subscriptions", None, "none",
         "Romanian tax and accounting law", legal_review=True, env="RETENTION_BILLING_DAYS",
         note="Kept after account deletion, linked only to the anonymised account."),
)

BY_KEY = {r.key: r for r in RULES}


def expires_at(key: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """The ``expires_at`` value for a new document under rule ``key``,
    or None when the rule has no period."""
    days = BY_KEY[key].effective_days
    if not days:
        return None
    return (now or datetime.now(timezone.utc)) + timedelta(days=days)


def purge_rules() -> list[Rule]:
    """Rules enforced by the daily purge that currently have a period."""
    return [r for r in RULES
            if r.effective_days and (r.enforcement == "purge" or (r.enforcement == "none" and r.env))]


def schedule() -> list[dict]:
    """Human-readable schedule (internal docs, admin views, tests)."""
    return [{
        "key": r.key, "collection": r.collection, "data": r.description,
        "days": r.effective_days, "enforcement": r.enforcement, "basis": r.basis,
        "legal_review": r.legal_review, "note": r.note,
    } for r in RULES]
