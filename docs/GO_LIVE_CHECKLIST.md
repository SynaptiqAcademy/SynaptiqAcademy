# Go-Live Checklist

The final sign-off gate before opening Synaptiq to real users with real payments. Every
item should be checked by a real action taken (or a real check run), not assumed from
memory or from a prior pass of this checklist. Cross-references point to the document
with full detail — this page is deliberately just the checklist.

## 1. Infrastructure

- [ ] DNS records live and resolving — [DNS_CONFIGURATION.md](DNS_CONFIGURATION.md)
- [ ] SSL certificates issued and auto-renewal cron confirmed active — [DOMAIN_CONFIGURATION.md](DOMAIN_CONFIGURATION.md)
- [ ] MongoDB Atlas cluster provisioned, network access allowlisted, backups enabled — [MONGODB_ATLAS_SETUP.md](MONGODB_ATLAS_SETUP.md)
- [ ] Redis provisioned with a password set — [REDIS_SETUP.md](REDIS_SETUP.md)
- [ ] S3 buckets created (uploads + backups), IAM scoped correctly — [AWS_S3_SETUP.md](AWS_S3_SETUP.md)
- [ ] Docker Compose stack starts cleanly on the production host — [DEPLOYMENT.md](DEPLOYMENT.md)
- [ ] `docker ps` shows all three containers healthy; `curl /api/health` returns `200`

## 2. Environment variables

- [ ] Every **Required** variable in [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)
      is set in production `.env` — go through the table row by row, don't skim
- [ ] `APP_ENV=production`, `COOKIE_SECURE=1` confirmed active (forced by
      `docker-compose.prod.yml`, but confirm the container actually has them)
- [ ] `EXPOSE_RESET_TOKEN` and `EMAIL_DRY_RUN` confirmed **unset/0** — these are dev/CI-only
      switches that must never be on in production
- [ ] A secure, independent backup of `.env` itself exists (see [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md)
      "Missing Production Requirements" — this is not automated, do it manually)

## 3. Third-party services

- [ ] Resend domain verified (SPF/DKIM/DMARC live), webhook configured — [RESEND_SETUP.md](RESEND_SETUP.md)
- [ ] Google OAuth credentials configured, redirect URI matches exactly, tested with a real Google account — [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)
- [ ] ORCID OAuth credentials configured, redirect URI matches exactly, environment (sandbox vs. production) matches your client ID — [ORCID_SETUP.md](ORCID_SETUP.md)
- [ ] Anthropic and/or OpenAI API keys set, at least one live — [OPENAI_ANTHROPIC_SETUP.md](OPENAI_ANTHROPIC_SETUP.md)
- [ ] Stripe: products/prices created, Price IDs filled into `plans_catalogue.py`, live keys set, webhook endpoint registered and `STRIPE_WEBHOOK_SECRET` set, `stripe` package confirmed installed in the deployed environment — [STRIPE_SETUP.md](STRIPE_SETUP.md)
- [ ] One real test-mode Stripe purchase completed successfully before flipping to live keys

## 4. Security

- [ ] Full checklist in [SECURITY.md](SECURITY.md) reviewed
- [ ] `JWT_SECRET`, `ENCRYPTION_KEY`, `ORCID_STATE_SECRET`, `ZT_MASTER_KEY` are all
      freshly generated, high-entropy, and **not** reused from any development/staging
      environment
- [ ] `CORS_ORIGINS` is the exact production domain list — no wildcards, no leftover
      `localhost` entries
- [ ] Decide and confirm whether `/docs`/`/redoc` should be public — [API.md](API.md)
- [ ] MFA enabled on all `super_admin` accounts

## 5. Functional verification

Work through [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) in full — every
subsystem (auth, registration, email, payments, subscriptions, credits, messaging,
uploads, WebSockets, notifications, API, monitoring, error handling). Do not skip items
marked **[Verify]** just because a related item is marked **[Verified]** from prior
testing — configuration or environment can change between then and now.

## 6. Monitoring & observability

- [ ] Uptime monitor watching `https://api.synaptiq.academy/api/health` — [MONITORING.md](MONITORING.md)
- [ ] `SENTRY_DSN` set and confirmed receiving events (trigger a test error, confirm it appears)
- [ ] `ALERT_WEBHOOK_URL` set and confirmed delivering (check for the daily backup success message)
- [ ] Cron jobs installed and running — `crontab -l` shows `deploy/synaptiq.cron`'s entries — [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md)

## 7. Backup & recovery rehearsal

- [ ] At least one full backup has run successfully and uploaded to S3
- [ ] A restore has been tested (`RESTORE_DRY_RUN=1` at minimum; a real restore into a
      scratch environment is stronger evidence) — [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md)
- [ ] Rollback procedure has been rehearsed at least once against this environment —
      [DEPLOYMENT.md](DEPLOYMENT.md)

## 8. Team readiness

- [ ] Everyone on the launch team has read [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md)
      and knows the severity levels and escalation contacts
- [ ] On-call coverage arranged for the first 48–72 hours post-launch, even if informal
- [ ] [RELEASE_PROCESS.md](RELEASE_PROCESS.md)'s hotfix procedure is understood by whoever
      would need to execute it under pressure

## 9. Legal / compliance (confirm with whoever owns this at your organization — not derivable from code alone)

- [ ] Terms of Service and Privacy Policy pages are live and linked from registration
- [ ] GDPR data-deletion request process is staffed (see `deploy/RUNBOOK.md` → "GDPR data
      deletion requests")
- [ ] Billing/tax configuration matches your actual legal entity and jurisdiction (Stripe
      Tax, if enabled — see [STRIPE_SETUP.md](STRIPE_SETUP.md))

## 10. Final go/no-go

Only proceed once every checked box above reflects a real, current verification — this
checklist exists specifically so nothing depends on someone's memory of "I think we
checked that." If any item is unchecked, that is your go-live blocker list; resolve or
explicitly accept the risk (in writing, with an owner) before opening to real users.

## Consolidated "Missing Production Requirements" (from every document in this manual)

| Area | Gap | Document |
|---|---|---|
| Payments | Stripe Price IDs unset — blocks all live checkout | [STRIPE_SETUP.md](STRIPE_SETUP.md) |
| Backup | `.env`/secrets not included in any automated backup | [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md) |
| CI/CD | No frontend build/test job; no automated deploy; no image registry publishing | [CI_CD.md](CI_CD.md) |
| Security | No dependency/vulnerability scanning or secret-scanning in CI; MFA not enforced for super_admin | [SECURITY.md](SECURITY.md) |
| Architecture | No CDN in front of static assets/uploads; no multi-region failover | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Monitoring | No paging/on-call tool wired in beyond a Slack/Discord webhook; `/api/health` doesn't check S3 or AI provider connectivity | [MONITORING.md](MONITORING.md), [AWS_S3_SETUP.md](AWS_S3_SETUP.md), [OPENAI_ANTHROPIC_SETUP.md](OPENAI_ANTHROPIC_SETUP.md) |
| Email | Bounce/complaint tracking recorded but not actively enforced (no suppression) | [EMAIL_SYSTEM.md](EMAIL_SYSTEM.md) |
| Database | No formal migration-tracking mechanism (idempotent-block pattern only) | [DATABASE.md](DATABASE.md) |
| API | `/docs`/`/redoc` public-by-default — confirm this is intentional | [API.md](API.md) |
| Deployment | No blue/green deploy, no staging environment found, no post-deploy automated smoke test | [DEPLOYMENT.md](DEPLOYMENT.md) |

None of these block a careful, monitored launch — they are the specific, named gaps a
production-grade platform would normally close over time. Treat this table as the
starting backlog for the first post-launch engineering cycle, not as launch blockers in
themselves, except where a document above explicitly says otherwise (Stripe Price IDs
are the one genuine hard blocker for revenue-generating features specifically).
