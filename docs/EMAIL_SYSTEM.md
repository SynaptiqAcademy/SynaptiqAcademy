# Email System

Third-party account setup: [RESEND_SETUP.md](RESEND_SETUP.md). This document covers the
application-side architecture.

## Architecture

Component-based, not standalone HTML files per email type — `backend/services/email/`:

| File | Responsibility |
|---|---|
| `components.py` | Reusable HTML building blocks — header, footer, CTA button, cards, banners, divider, support block |
| `layout.py` | Wraps components into a full responsive, dark-mode-aware HTML shell matching the platform's design system |
| `plaintext.py` | Generates the plain-text counterpart for every HTML email (never HTML-only) |
| `tokens.py` | Cryptographically secure, single-use token generation (JWT + `jti`, backed by a DB record marking single use) — shared by email verification and password reset |
| `categories.py` | `EmailCategory` enum and the preference-gating rules (see below) |
| `i18n.py` | Localization scaffolding for future multi-language support |
| `templates/` | One file per email type (`welcome.py`, `verification.py`, `getting_started.py`, `password_reset.py`, `workspace_invitation.py`, `review_request.py`, `collaboration_invitation.py`) — each composes `components.py` + `layout.py` |

`services/email_templates.py` is a backward-compatibility re-export shim for older
import paths — new code should import from `services/email/templates/` directly.
`services/email_service.py` is the actual sending entry point: resolves the recipient's
preferences, picks HTML+plaintext, and calls the configured provider (Resend).

## Categories and user preferences

`EmailCategory` (`categories.py`):

| Category | User can disable? |
|---|---|
| `SECURITY` | **No** — always sent (password reset, suspicious login, etc.) |
| `TRANSACTIONAL` | **No** — always sent (email verification, receipts) |
| `BILLING` | **No** — always sent (payment failed, subscription changes) |
| `MARKETING` | Yes |
| `PRODUCT_UPDATES` | Yes |
| `RESEARCH_NEWSLETTER` | Yes |

`_user_doc()`/`_send_to_user()` in `email_service.py` check the recipient's stored
preferences before sending anything in a gated category; mandatory categories bypass
this check entirely by design.

## Delivery is asynchronous — never blocks the request that triggered it

Emails are enqueued as background jobs (`worker/models.py`'s `JOB_EMAIL_SEND`,
`JOB_EMAIL_GETTING_STARTED_CHECK`) rather than sent inline during, e.g., registration.
`worker/handlers.py`'s `handle_email_send` does the actual Resend call, with retry
(visible as `[email:RETRY n/3]` log lines) and a final `[email:FAIL]` log line if all
retries are exhausted — registration itself never blocks on or fails because of an email
delivery problem.

## Current email types

| Email | Trigger | Category |
|---|---|---|
| Email Verification | Registration (if `EMAIL_VERIFICATION_REQUIRED=1`) | `TRANSACTIONAL` |
| Welcome | Registration, guarded to send exactly once per account | `TRANSACTIONAL` |
| Getting Started | ~24h after registration, only if the user hasn't completed key setup steps (re-checked against real account state at send time — not a blind scheduled send) | `PRODUCT_UPDATES` |
| Password Reset | Forgot-password request | `SECURITY` |
| Workspace Invitation | Invited to a workspace | `TRANSACTIONAL` |
| Review Request | Reviewer marketplace/manuscript review assignment | `TRANSACTIONAL` |
| Collaboration Invitation | Collaboration request | `TRANSACTIONAL` |

## Tokens (verification, password reset)

`tokens.py`: JWT carrying a `jti`, paired with a database record marking that `jti` as
unused. On redemption, the record is marked used — a token cannot be replayed even if
the JWT itself hasn't expired yet. `EMAIL_VERIFICATION_TTL_HOURS` controls the
verification link's lifetime.

## Delivery tracking (Resend webhook)

`POST /api/email/webhook/resend` (`routers/email.py`), Svix-style HMAC-verified
(`RESEND_WEBHOOK_SECRET`). Maps Resend event types to fields recorded against the
`email_log` entry: `email.delivered`→`delivered_at`, `email.bounced`→`bounced_at`,
`email.complained`→`complained_at`, `email.opened`/`email.clicked` similarly tracked.
**Note:** these fields are currently recorded for visibility/audit but are not yet read
back anywhere to actively suppress future sends to a bounced/complained address — see
"Missing Production Requirements."

## Preview & test endpoints

`routers/email.py` exposes a `TEMPLATES` dict plus preview/test endpoints (admin-only) —
useful for visually checking a template renders correctly after any component change,
without needing to trigger the real business event.

## Dev/CI safety

`EMAIL_DRY_RUN=1` logs the would-be email instead of calling Resend — always set in CI
and local dev unless you specifically intend to send real mail. Verify this is **unset**
(or `0`) in production; see [RESEND_SETUP.md](RESEND_SETUP.md) §5.

## Design consistency

Every template shares the same header/footer/CTA components and token-based color/type
scale as the rest of the platform (see the platform's own design-system documentation for
the token source) — responsive, dark-mode aware, and checked for basic accessibility
(sufficient contrast, semantic HTML structure) as part of the component library rather
than per-template.

## Missing Production Requirements

- Bounce/complaint tracking is recorded but not enforced — a repeatedly-bouncing address
  will keep receiving send attempts, which risks sender reputation. Wire an active
  suppression check (e.g., skip sending if `bounced_at`/`complained_at` is set) before a
  large-scale launch.
- `i18n.py` is described as "localization readiness" scaffolding — confirm whether any
  email is actually translated today, or whether every email is currently English-only
  in practice, before advertising multi-language support to users.
