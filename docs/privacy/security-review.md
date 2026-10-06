# Security review (Phase 2): findings and fixes

A code and configuration review with light, non-destructive checks against production (headers, CORS preflight, public config endpoints) and in-process probes against a **local** database. **This is not a penetration test** and must not be described as one.

## Fixed in this phase

| Sev. | Finding | Fix | Test |
|---|---|---|---|
| P0 | **Admin surface open to members.** 40 `/api/admin/*` endpoints only required a signed-in user, including the self-improvement audit log, AI action and conversation telemetry, the notification broadcast, sync-queue processing and automation installs. The Zero Trust middleware's skip list contained `"/api/"`, so it never inspected any API path. | Deny-by-default gate for all of `/api/admin` in `zt/middleware.py`, run before the skip list: requires moderator or platform admin; routes keep their stricter checks. Local probe: members now reach 0 admin endpoints and allow-listed super admins are not blocked. | `tests/test_admin_surface_gate.py` |
| P0 | **ORCID sign-in created accounts silently**: no 18+/Terms acceptance, and it ignored "sign-ups closed". | New accounts need open registration and a signed proof of 18+/Terms acceptance in the OAuth state; acceptance versions recorded. Unknown ORCID on sign-in goes to Register with an explanation. | `tests/test_oauth_signup_gating.py` |
| P1 | Google sign-in created accounts without Terms acceptance; the button showed though Google isn't configured. | Same gating; buttons shown only for providers whose `/config` says `configured: true`; Microsoft "coming soon" button removed. | same |
| P1 | ORCID OAuth state never expired. | 15-minute expiry. | same |
| P1 | **About 12% of OAuth sign-ins failed.** State decoding split at the last "." byte, but the 32-byte HMAC can contain one. Affected ORCID and Google. | Split at the fixed signature length. | `test_state_round_trips_even_when_signature_contains_a_dot` |
| P1 | Self-service deletion needed no re-authentication, left all private content in place, and logged the deleted person's email. | Deletion matrix, password or recent sign-in, no email in audit records. | `tests/test_account_lifecycle.py` |
| P1 | A deleted account's 15-minute access token kept working. | `get_current_user` rejects `status: deleted`. | covered by lifecycle |
| P1 | Email templates put manuscript titles, review notes, collaboration titles and messages, workspace names and notification text into emails, **unescaped** (HTML injection in emails). Subjects were also stored in `email_log`. | Generic subjects and bodies; content stays in the app; names HTML-escaped. | `test_notification_emails_do_not_reveal_research_topics` |
| P1 | Deleting a file left its bytes in object storage. | `storage_service.delete_object` on delete. | lifecycle test |
| P1 | Frontend sent no clickjacking or nosniff headers: only HSTS. `frame-ancestors` in a `<meta>` CSP is ignored by browsers. | `frontend/vercel.json` adds CSP `frame-ancestors 'self'`, X-Frame-Options, nosniff, Referrer-Policy and Permissions-Policy. | production header check |
| P2 | Fonts loaded from Google (IP addresses sent to Google). | Self-hosted; CSP tightened on frontend and API. | `test_fonts_are_self_hosted` |
| — | **SECRET ROTATION REQUIRED**: a production-cluster Atlas credential in `backend/test_atlas_connection.py` (in git history since 20 July 2026). Not the credential production uses now. | Removed from the file; **rotate or delete the Atlas user**. | — |

## Reviewed, no change needed

- **Auth tokens:** HttpOnly cookies (`access_token` 15 min, `refresh_token` 14 days), `COOKIE_SECURE=1` in production, CSRF double-submit token. No tokens in `localStorage`.
- **CORS:** a preflight from a foreign origin is refused (400); the production origin gets credentials.
- **API security headers:** CSP, HSTS with preload, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy.
- **Mass assignment:** `ProfileUpdate` and `OnboardingComplete` expose no privileged fields (role, plan, credits, status, email, verification); Pydantic ignores extra fields.
- **Bundle secrets:** no key patterns in the production build.
- **XSS:** `dangerouslySetInnerHTML` appears only with static strings (style tags, static labels). The deleted Security page was one of those uses.
- **Demo accounts:** never seeded when `APP_ENV=production` (it is).
- **Email verification:** required in production (`EMAIL_VERIFICATION_REQUIRED=1`).

## Not yet reviewed in depth (next phase)

- Per-route IDOR review across all member routes; only the admin prefix was probed systematically.
- Rate-limit coverage beyond authentication, now that Redis is unreachable and limits fall back to in-process.
- Other prefixes that may assume admin-only access without checking, e.g. `/api/institution-*`, `/api/zt/*`.
- File upload validation (moot while object storage is unconfigured).

## Security page: safe and unsafe claims

The former public `/security` "Security Center" made many unverifiable claims. It is removed; `/security` now redirects to the Privacy Policy's security section. **Don't build `/security` until each claim below is verified.**

**Safe to say (verified in code or production):**
- HTTPS everywhere; HSTS on site and API.
- Passwords hashed with bcrypt.
- Short-lived sessions in HttpOnly, Secure cookies, with CSRF protection.
- Sign-in lockout after repeated failures; security events logged and kept 1 year.
- Admin actions logged (90 days).
- Admin API deny-by-default.
- Analytics only with consent; no session recording.
- Fonts self-hosted.
- Self-service export and deletion.
- Emails don't include research content.

**Unsafe (unverified or false). Don't publish:**
- "HTTP rejected, not redirected": Vercel redirects.
- TLS 1.3 only; "encrypted between internal services".
- "AES-256 at rest for databases, backups and uploaded files": object storage isn't even configured; Atlas encryption must be confirmed.
- "Daily backups", "14-day point-in-time recovery", "backup isolation", "recovery testing".
- "Multi-availability-zone": Railway runs 1 replica in `sfo`.
- "EU data residency available".
- "Audit log retained 3 years"; "security events 12 months after deletion"; "server logs 30 days".
- "Deletion within 30 days".
- "GDPR compliant"; "SCCs applied for all US transfers".
- "Anthropic enterprise terms"; "no retention by Anthropic".
- "Every endpoint enforces role checks": false before this phase.
- "Row-level ownership on every read".
- `security@synaptiq.academy`; "acknowledge reports within 48 hours".
- Bug-bounty-style public credit.
- Any certification (ISO 27001, SOC 2).
