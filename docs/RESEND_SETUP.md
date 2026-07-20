# Resend Setup

Resend is the transactional email provider (`backend/services/email/`). Full email
architecture: [EMAIL_SYSTEM.md](EMAIL_SYSTEM.md). This document covers only the
third-party account setup.

## 1. Create account and API key

1. Sign up at resend.com.
2. Dashboard → API Keys → create a key scoped to **Sending access** only (not full
   account access) for the production environment.
3. Set:
   ```
   RESEND_API_KEY=re_...
   ```

## 2. Verify your sending domain

Resend requires domain verification before it will send mail claiming to be from that
domain (otherwise you're limited to Resend's own test domain / low volume).

1. Dashboard → Domains → **Add Domain** → `synaptiq.academy`.
2. Resend shows you DNS records to create: an **SPF** `TXT` record (or a shared `MX`
   record depending on Resend's current setup flow), one or more **DKIM** `TXT`/`CNAME`
   records, and recommends a **DMARC** `TXT` record. Create all of them at your DNS
   provider — see [DNS_CONFIGURATION.md](DNS_CONFIGURATION.md) for where these slot in
   alongside your existing `A` records.
3. Wait for Resend to show the domain as **Verified** (DNS propagation — can take minutes
   to a few hours).

## 3. From address

```
EMAIL_FROM=Synaptiq <noreply@synaptiq.academy>
```

Must use the now-verified domain, or Resend will reject/queue-fail sends.

## 4. Webhook (delivery/open/click tracking)

The backend exposes `POST /api/email/webhook/resend` (`routers/email.py`) with Svix-style
HMAC signature verification.

1. Resend Dashboard → Webhooks → **Add Endpoint**:
   `https://api.synaptiq.academy/api/email/webhook/resend`
2. Subscribe to at least: `email.delivered`, `email.bounced`, `email.complained`,
   `email.opened`, `email.clicked`.
3. Copy the signing secret shown → set:
   ```
   RESEND_WEBHOOK_SECRET=whsec_...
   ```
4. Without this secret set, the webhook endpoint should be treated as non-functional for
   signature-verified delivery — do not skip this step in production.

## 5. Dev/CI safety switches — must be OFF in production

| Variable | Behavior when set | Production value |
|---|---|---|
| `EMAIL_DRY_RUN` | Logs the email instead of sending it via Resend | unset or `0` |
| `DISABLE_EMAIL_STUB` | Related dev/mock path toggle | verify `1` in prod so the real Resend path is used, not a stub |

Both switches exist so CI and local dev never send real email — a real Resend account
key should be considered production-only, and these flags are the guard rail. Confirm
their state before go-live (see [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)).

## 6. Sending limits / reputation

- New Resend accounts/domains start with sending limits and build reputation over time —
  do not launch a large announcement email blast on day one of domain verification.
- Bounce/complaint rates affect deliverability platform-wide for your domain — the
  webhook subscriptions in step 4 exist specifically so the platform can react to bounces
  (e.g., suppress repeatedly-bouncing addresses) rather than blindly re-sending.

## 7. Verification

```bash
# From the backend, using the admin email-test endpoint (if enabled) or by triggering
# a real registration in a non-production environment with EMAIL_DRY_RUN unset:
curl -X POST https://api.synaptiq.academy/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Test User","email":"you@yourdomain.com","password":"..."}'
# Check your inbox for the verification email, and Resend's dashboard → Logs for the send record.
```

## Missing Production Requirements

- No automated bounce-suppression list was found wired to the webhook handlers beyond
  logging — verify `routers/email.py`'s webhook handler actually acts on
  `email.bounced`/`email.complained` events (e.g., marking the user's email preferences)
  before relying on it to protect sender reputation automatically.
