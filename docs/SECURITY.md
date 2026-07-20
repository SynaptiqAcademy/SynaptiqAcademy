# Security

## Authentication

- **Password hashing:** bcrypt (`auth_utils.py`), per-password salt, never reversible.
- **Tokens:** JWT, HS256, signed with `JWT_SECRET`.
  - **Access token:** 15-minute TTL (`ACCESS_MIN = 15` in `auth_utils.py`). Sent as an
    HttpOnly cookie. Not individually revocable before expiry (standard short-lived JWT
    tradeoff) — this is why the TTL is kept short.
  - **Refresh token:** 14-day TTL (`REFRESH_DAYS = 14`). Also HttpOnly cookie. **Is**
    individually revocable — every issued refresh token's `jti` (UUID) is recorded in the
    `refresh_tokens` MongoDB collection (`services/token_service.py`) with
    `revoked`/`revoked_at` fields. Correction against older docs: this registry is
    **MongoDB-backed, not Redis-backed** — refresh token revocation works correctly even
    with Redis fully down.
  - **Rotation:** each refresh consumes the old `jti` (marks it revoked) and issues a new
    one, carrying the same `session_id` forward — so the Active Sessions UI shows one
    stable entry per device/login even though the underlying JWT rotates silently.
  - **Logout** revokes the current refresh token's `jti` immediately.
  - **"Revoke all sessions"** (`revoke_all_user_tokens`) marks every non-revoked
    `refresh_tokens` row for that user as revoked in one operation — used for
    security-incident response (see [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md)) and
    user-initiated "sign out everywhere."
- **Account lockout (AUTH-006):** after repeated failed logins, a soft lockout of
  `LOCKOUT_SOFT_MINUTES = 15` applies; a harder `LOCKOUT_HARD_HOURS = 24` lockout applies
  after continued failures (see `routers/auth.py` for exact thresholds).
- **MFA:** TOTP-based (compatible with Google Authenticator, Microsoft Authenticator,
  Authy), optional per-user, strongly recommended for admin/super_admin accounts.
- **OAuth:** Google and ORCID (see their setup docs). "Microsoft login" is shown in the UI
  as "coming soon" — no backend integration exists yet; this is intentional, not a bug.

## CSRF

Double-submit cookie pattern (`middleware/__init__.py`, `CSRFMiddleware`, AUTH-007):
- On login/register/OAuth, the server sets a **non-HttpOnly** `csrf_token` cookie.
- The frontend reads it via JS and echoes it back as the `X-CSRF-Token` header on every
  mutating request (`POST`/`PUT`/`PATCH`/`DELETE`).
- The middleware rejects the request (`403`) if the header is missing or doesn't match
  the cookie.
- `GET`/`HEAD`/`OPTIONS` are exempt (safe methods).
- A small, explicit exemption list covers a few paths where CSRF enforcement isn't
  meaningful (e.g. `/api/auth/logout`, `/api/auth/csrf-token` itself).

## Rate limiting

`rate_limit.py`, backed by `slowapi`, with automatic Redis → in-memory fallback (never
raises a 500 due to Redis being unavailable — see [REDIS_SETUP.md](REDIS_SETUP.md)).
Additionally enforced at the nginx layer (`deploy/nginx.conf`): 60 req/min/IP general,
10 req/min/IP (burst 5) on auth endpoints specifically.

## Secrets and API keys

- All secrets are environment variables — never committed to the repository (verify
  `.gitignore` excludes `.env`; it does in this repo's root `.gitignore`).
- `ENCRYPTION_KEY` (256-bit, base64) is used by `services/encryption_service.py` to
  encrypt sensitive fields at rest — currently applied to ORCID OAuth
  access/refresh tokens before they're written to MongoDB.
- Rotation guidance: see `deploy/RUNBOOK.md` → "Credential Rotation" table (covers
  `JWT_SECRET`, `ENCRYPTION_KEY`, `ADMIN_PASSWORD`, `STRIPE_*`, MongoDB Atlas password,
  `REDIS_PASSWORD` — impact and steps for each).
- The platform's own API keys (Enterprise API Platform, `backend/api/`) are
  independently hashed/stored — not to be confused with third-party provider keys above.

## Permissions & IDOR protection

- **Role hierarchy:** `user` < `admin` < `super_admin` (`services/permissions.py`).
- **Row-level security:** all MongoDB access goes through `repo/shim.py`'s `DBProxy`,
  constructed with a `SecurityContext` (user id, role, institution/tenant scope — see
  `repo/security_context.py`) derived once per request from the authenticated user.
  Application code never queries MongoDB with a raw client — this is the primary IDOR
  defense: a handler can't accidentally return another user's/tenant's document because
  the repository layer scopes queries to the caller's own `SecurityContext`.
  Cross-tenant/cross-user access requires an explicit, audited elevation (e.g.
  `SecurityContext.system()` for background jobs, `SecurityContext.from_user(admin_user)`
  for admin endpoints — both are visible, greppable call sites, not implicit).
- **Zero Trust package** (`backend/zt/`): every API call is checked via `zt_check`
  middleware — device trust, IP allowlisting, and a risk-scoring engine
  (`RISK_BLOCK_THRESHOLD`/`RISK_VERIFY_THRESHOLD`) that can force step-up verification
  on anomalous logins (new device/location).
- **Audit logging:** every admin action and every write against sensitive collections is
  logged to `audit_log` (billing/security actions, `services/audit.py`) and/or
  `obs_audit` (compliance-grade trail, `obs/audit.py`) — see [MONITORING.md](MONITORING.md).

## Headers

Application-level (`middleware/__init__.py`): `X-Content-Type-Options: nosniff`,
`X-Frame-Options: SAMEORIGIN`, `Strict-Transport-Security` (when running over HTTPS,
`max-age=63072000; includeSubDomains; preload`).

nginx-level (`deploy/nginx.conf`, applied to both frontend and API vhosts):
`Strict-Transport-Security`, `X-Frame-Options: DENY` (stricter than the app-level
`SAMEORIGIN` — nginx's header wins since it's added closer to the client),
`X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`,
`Permissions-Policy` (camera/microphone/geolocation denied) on the frontend vhost.

A real `Content-Security-Policy` header is emitted on every response
(`middleware/__init__.py`, `_csp()`, AUTH-004/AUTH-008): `script-src` has no
`'unsafe-inline'`, and `connect-src` is an explicit allowlist (`'self'` plus the specific
third-party origins the app actually talks to from the browser — Stripe's `api.stripe.com`/
`js.stripe.com`/`hooks.stripe.com`, ORCID's sandbox and production API hosts) rather than
a broad `https:` wildcard. `CSP_REPORT_URI` is a configuration point for CSP violation
reporting on top of this.

## Cookies

| Cookie | HttpOnly | Purpose |
|---|---|---|
| `access_token` | Yes | 15-min JWT, sent on every request |
| `refresh_token` | Yes | 14-day JWT, used only against `/api/auth/refresh` |
| `csrf_token` | **No** (must be JS-readable) | Double-submit CSRF defense |

`COOKIE_SECURE=1` (forced in `docker-compose.prod.yml` regardless of `.env`) sets the
`Secure` flag — cookies are never sent over plain HTTP in production.
`COOKIE_SAMESITE` controls the `SameSite` attribute (default `lax`).

## CORS

Explicit origin allowlist only — **no wildcards permitted alongside credentialed
requests** (`server.py` actively warns and refuses to start correctly if
`CORS_ORIGINS` is empty or `*`). CORS middleware is deliberately registered **last** in
the middleware stack so its headers are present even on error responses generated
earlier in the chain (documented in-line in `server.py` — this fixed a real bug where
Mongo-down error responses arrived with no CORS headers, which browsers report as a
generic "Network Error" rather than the real 500, confusing debugging).

## Missing Production Requirements

- No dependency/vulnerability scanning (e.g. `pip-audit`, `npm audit`, Dependabot) was
  found wired into `.github/workflows/ci.yml` — add one.
- No documented secret-scanning pre-commit hook (e.g. gitleaks) — add one to prevent
  accidental secret commits.
- MFA is optional, not enforced, even for `super_admin` accounts — consider requiring it
  for that role specifically before launch.
