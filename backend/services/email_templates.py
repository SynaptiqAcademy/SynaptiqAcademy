"""Backward-compatible import path.

All template logic now lives in services/email/templates/ (component-based,
HTML + plaintext). This module re-exports the same public names that
services/email_service.py has always imported as `T.<name>(...)`, so no
call site needs to change.

Add new templates in services/email/templates/, not here.
"""
from __future__ import annotations

from services.email.templates import (
    welcome_email,
    verification_email as email_verification_email,
    getting_started_email,
    password_reset_email,
    workspace_invitation_email,
    review_request_email,
    collaboration_invitation_email,
)

__all__ = [
    "welcome_email",
    "email_verification_email",
    "getting_started_email",
    "password_reset_email",
    "workspace_invitation_email",
    "review_request_email",
    "collaboration_invitation_email",
]
