# Production readiness — summary

Status of the launch checks for accepting paid subscriptions. Detailed findings are kept
outside the repository. Manual steps are in [LAUNCH_RUNBOOK.md](LAUNCH_RUNBOOK.md).

**Current verdict: NO-GO** until the "Requires dashboard access" items below are done and
their evidence recorded.

## Done in code (verified by tests)

| Area | Change | Evidence |
|---|---|---|
| Scheduling | Scheduled jobs run in exactly one process via a MongoDB lease with automatic takeover; each job (including digest emails) is claimed once per time window. | `tests/test_launch_remediation.py` — lease exclusivity under concurrency, takeover after holder failure, 8 concurrent schedulers → 1 run |
| Rate limits | Limits are stored in shared storage (Redis when configured, otherwise MongoDB), so all workers and replicas enforce one count. | Live two-worker test: 8 sign-in attempts from rotating forwarded headers → 5 allowed, 3 rejected |
| Client address | One trusted helper for every IP-based control, configurable per proxy topology; super-admin diagnostic `GET /api/admin/security/client-ip`. | Unit tests; `test_auth_suite::test_login_rate_limit` |
| Sign-in performance | Password hashing runs on a dedicated thread pool, off the request event loop; unknown accounts take the same time as known ones; the login risk check runs after the response. | Event-loop responsiveness test; local load test at 100 users: p95 1,483 → 75 ms, sign-in p95 7.7 s → 0.46 s, 0 errors; `test_performance` 11/11 |
| Sign-in privacy | Login no longer sends the user's IP address over plain HTTP to an undisclosed geolocation service; external geolocation is off unless an HTTPS provider is configured. | `TestLoginGeolocation` |
| Billing | Stripe events cannot apply out of order: per-subscription event-time guard, ended subscriptions are final, late invoices grant nothing, and subscription state is re-read from Stripe. | `tests/test_stripe_event_ordering.py` (6 tests; 4 fail without the guard) plus 141 existing billing tests |
| Credits | Credits held by requests that never finished (worker restart, timeout) are returned automatically every 10 minutes, exactly once. | Sweeper test with two concurrent sweepers |
| Storage | Plan storage limits hold under parallel uploads; storage calls no longer block the server; calendar imports are size- and count-limited. | 6 parallel uploads against a 10 MB limit → 3 accepted, 3 refused |
| AI spending | Every AI cap derives from one explicit monthly provider budget; background AI has its own capped share; budget alerts at 50/80/100%. | Budget derivation and background-cap tests |
| Alerts | Webhook alerts for failed Stripe processing, failed jobs, released credits and AI budget, de-duplicated across processes. | Code paths covered by the above tests |
| Encryption | Stored third-party tokens are never written in plaintext when encryption is required. | `test_encryption_fails_closed_without_key_in_production` |
| API | Comment creation request body fixed; API schema generates again; interactive API docs are off outside development. | `test_integration` (34/34) |
| Backups | Isolated restore-and-verify procedure with safety refusals. | Local drill: 214 collections, 81,783 documents restored and verified in 15 s; 5 refusal cases |
| Authentication tests | Auth suites repaired and running (they had been skipped or failing for environmental reasons). | `test_auth_security` 27/27, `test_auth_suite` 26/26 against a live local server (rate-limit case on two workers), `test_regression` 20/20 |

## Requires dashboard access (not verified)

| Item | Why it matters |
|---|---|
| Production database backup policy and a restore drill | Recovery is unverified until a production backup has been restored somewhere other than production |
| External uptime monitors, alert webhook, Sentry alert rules | Outages would otherwise go unnoticed |
| API on `api.synaptiq.academy` and a real Safari test | Sessions on Safari depend on the API being same-site with the app |
| Redis and strict production mode | Production currently runs without Redis |
| Client-address check after deploy | Confirms the proxy header cannot be supplied by clients |
| Database credential rotation | Pre-launch credential hygiene |
| Staging environment and staging load test | Production capacity is unverified; local figures only show bottlenecks |
| Stripe live configuration, S3 bucket policy, AI provider spend limits | Configuration that lives only in provider dashboards |
| Public registration flag | Sign-up is currently closed in production |

## Known remaining issues (lower priority)

- Some background loops start in every worker; they claim work atomically, but the
  presence sweep does not start at all (start-up import issue in the application entry point).
- The readiness endpoint returns database error text.
- Analytics endpoints load large result sets into memory.
- Five pre-existing test failures unrelated to this work (matching engine, copilot,
  collaboration prediction, Redis client), plus test-isolation failures that pass when run per file.
