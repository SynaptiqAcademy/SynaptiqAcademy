# Production Checklist

A per-subsystem verification checklist. Status notes marked **[Verified]** reflect direct
testing evidence gathered during this platform's own hardening work (live E2E browser
tests, signed synthetic webhook tests against the real database, isolated recovery
simulations — not assumptions). Items marked **[Verify]** have supporting code but no
fresh test evidence in hand — re-run them before go-live rather than trusting this
checklist blindly; re-verification is cheap, a false assumption in production is not.

## Authentication

- [ ] **[Verified]** Register → login → logout round-trip works end-to-end
- [ ] **[Verified]** Failed-login lockout (soft 15 min, hard 24h) triggers correctly
- [ ] **[Verified]** Refresh token rotation + revocation works; "sign out everywhere" revokes all sessions
- [ ] **[Verified]** Google OAuth: config/routes/callback/error-handling/state-validation all correct in code
- [ ] **[Verify]** Google OAuth: full live round-trip (requires production redirect URI to be live and reachable — see [ORCID_SETUP.md](ORCID_SETUP.md)/Google console config)
- [ ] **[Verified]** ORCID OAuth: config/routes/callback/error-handling/state-validation all correct in code, including the previously-missing error-toast on the settings page
- [ ] Microsoft OAuth is **not implemented** — UI correctly shows "coming soon", this is expected, not a bug
- [ ] MFA (TOTP) enrollment and challenge flow, if used for any admin accounts

## Registration

- [ ] **[Verified]** Registration creates a user with correct default plan/credits sourced from `plans_catalogue.py` (not hardcoded) — covers direct registration, Google OAuth, and ORCID OAuth signup paths
- [ ] **[Verified]** Registration never blocks on email delivery (async job queue)
- [ ] **[Verify]** Duplicate-email registration returns a clear, correct error

## Email Verification

- [ ] **[Verified]** Verification email is enqueued (not sent inline) on registration
- [ ] **[Verified]** `VerifyEmailPending` page shows the correct email address (route-state based, not stale auth-context state)
- [ ] **[Verify]** Verification link redemption is single-use (token marked used in DB)
- [ ] Confirm `EMAIL_VERIFICATION_REQUIRED` is set to the intended value for launch (`1` recommended for production)

## Transactional Emails

- [ ] **[Verified]** Welcome, verification, and getting-started emails all render correctly and share the component-based design system
- [ ] **[Verify]** Resend domain is verified (SPF/DKIM/DMARC — see [RESEND_SETUP.md](RESEND_SETUP.md)) before launch, or emails will land in spam
- [ ] Confirm `EMAIL_DRY_RUN` is unset/`0` in production
- [ ] Confirm mandatory categories (security/transactional/billing) cannot be disabled by users, and gated categories respect preferences

## Profile Completion

- [ ] **[Verified]** Save-and-continue on the profile wizard works (this was the root of a bug found and fixed earlier in this platform's hardening — the systemic double-`/api/` prefix issue)
- [ ] **[Verify]** All wizard steps persist correctly and resuming mid-wizard restores state

## Payments

- [ ] **[Verified]** Stripe webhook signature verification, idempotency (duplicate delivery), and plan-sync logic (upgrade AND downgrade) all confirmed correct via signed synthetic webhook events against the real database
- [ ] **Blocked externally** — `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET` and every plan's Stripe Price ID are unset; see [STRIPE_SETUP.md](STRIPE_SETUP.md) for exactly what to fill in
- [ ] **[Verify]** Once configured: one real test-mode purchase end-to-end using Stripe's test card, before flipping to live keys
- [ ] **[Verify]** `stripe` Python package is actually installed in the production image (found missing in at least one environment during this platform's own verification — declared in `requirements.txt` but not installed)

## Subscriptions

- [ ] **[Verified]** Subscription upgrade/downgrade correctly updates `users.plan_code`, credits, and `subscription_status` together (previously a real, verified bug — subscription success didn't actually upgrade the user; now fixed and tested)
- [ ] **[Verified]** Cancellation reverts the user to the free plan
- [ ] **[Verify]** Billing portal session creation (requires a real Stripe customer — depends on Payments above)

## Credits

- [ ] **[Verified]** Single source of truth — every registration path (direct, Google, ORCID) and the Stripe webhook all read monthly allowance from `plans_catalogue.get_plan()`, no hardcoded numbers remain
- [ ] **[Verified]** Dual-balance model (monthly resets, pack never expires) consumes monthly first
- [ ] **[Verify]** Credit-pack purchase grants correctly (code path unchanged/already correct, but exercise it once real Stripe keys are live)

## Messages / Inbox / Meetings

- [ ] **[Verify]** Send/receive, read receipts, typing indicators, reactions — all backed by the WebSocket layer verified below
- [ ] **[Verify]** Notifications/Inbox unread counts update in real time across tabs
- [ ] **[Verify]** Meeting scheduling, calendar view, and reminders

## Repository / Uploads / Downloads / AWS S3

- [ ] **[Verify]** Upload → S3 `put_object` → retrieval round-trip
- [ ] Confirm `S3_BUCKET_NAME`/`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_REGION` are set — without them, `init_storage()` logs a non-fatal warning at startup but uploads will fail at request time (see [AWS_S3_SETUP.md](AWS_S3_SETUP.md))
- [ ] **[Verify]** File size limits and allowed content types are enforced as expected

## MongoDB

- [ ] **[Verified]** Circuit breaker fails fast (not slow-hangs) during an outage; auto-recovers with no manual restart once Atlas is reachable again
- [ ] **[Verify]** Atlas Network Access allowlist includes the production host's IP
- [ ] **[Verify]** Indexes created cleanly on first boot against a fresh cluster (watch startup logs for anything beyond the expected benign `IndexKeySpecsConflict` warnings)

## Redis

- [ ] **[Verified]** Cold-start and mid-session reconnect both work with no manual restart (isolated recovery test + a live regression found and fixed during this platform's own hardening — a blocking-DNS-call-on-every-check regression)
- [ ] **[Verify]** `REDIS_PASSWORD` set and matches between `.env` and `docker-compose.prod.yml` substitution

## WebSockets

- [ ] **[Verified]** Connection, auth (cookie JWT), membership check, disconnect cleanup (`finally` blocks, no leaked references), multi-tab (independent connections per tab, both correctly fan out), reconnect with exponential backoff — all code-reviewed with no defects found
- [ ] **[Verify]** Live soak test across a real network blip (offline → online) and a long-duration multi-tab session, beyond what a sandboxed code review can prove

## Notifications

- [ ] **[Verify]** In-app notification delivery via `/api/ws/user`
- [ ] **[Verify]** Notification preferences correctly gate non-mandatory categories

## Security

- [ ] **[Verified]** CSRF double-submit enforced on all mutating requests
- [ ] **[Verified]** CORS allowlist is explicit (no wildcard-with-credentials)
- [ ] **[Verified]** Real CSP header emitted with an explicit `connect-src` allowlist
- [ ] Confirm `COOKIE_SECURE=1`, `APP_ENV=production`, `EXPOSE_RESET_TOKEN` unset, for the production environment specifically (see [SECURITY.md](SECURITY.md))
- [ ] Rotate any secrets that may have been used during development/testing before go-live

## API

- [ ] **[Verify]** Decide whether `/docs`/`/redoc`/`/openapi.json` should be public in production (see [API.md](API.md))
- [ ] **[Verify]** Rate limits (nginx + application-level) behave as expected under load

## Monitoring

- [ ] Uptime monitor configured against `/api/health` (see [MONITORING.md](MONITORING.md))
- [ ] `SENTRY_DSN` configured
- [ ] `ALERT_WEBHOOK_URL` configured for backup/disk/DR-validation cron alerts

## Error logging

- [ ] **[Verified]** Global exception handler never leaks stack traces to clients; MongoDB-specific errors return a clean `503`
- [ ] Confirm `LOG_LEVEL` and `APP_ENV=production` (JSON logs) are set correctly for your log aggregator

## Missing Production Requirements (platform-wide, consolidated)

See each linked document's own "Missing Production Requirements" section for full
detail. The highest-priority items across the whole platform:

1. Stripe Price IDs unset — blocks all live payments (§Payments)
2. No `.env`/secrets backup — a host loss loses config alongside data (see [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md))
3. No frontend CI job (see [CI_CD.md](CI_CD.md))
4. No dependency/vulnerability scanning in CI (see [SECURITY.md](SECURITY.md))
5. No CDN in front of static assets or S3 uploads (see [ARCHITECTURE.md](ARCHITECTURE.md), [AWS_S3_SETUP.md](AWS_S3_SETUP.md))
