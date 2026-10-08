# Launch runbook — paid subscriptions

Ordered steps that need dashboard access. Each step ends with a check; do not move on
until it passes. Never paste secret values into chat, tickets or commits; keep them in a
password manager. Companion pages: [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md),
[MONITORING.md](MONITORING.md), [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md),
[PRODUCTION_READINESS.md](PRODUCTION_READINESS.md).

## A. Before deploying the remediation release

1. **Confirm the production database.** Railway → *Synaptiq Academy* → **SynaptiqAcademy** →
   Variables → `MONGODB_URI`: read only the host. `*.mongodb.net` = Atlas.
2. **Atlas backups.** Atlas → cluster → **Backup**: Cloud Backup on, continuous backup
   (point-in-time) on, snapshot retention ≥ 7 daily / 4 weekly / 3 monthly. The cluster
   must be M10 or above for continuous backup.
   *Check:* a snapshot exists and the point-in-time window is shown.
3. **Restore drill** (never to the production cluster): Backup → Restore → Point in time →
   *new cluster*. Compare collection counts (BACKUP_AND_RECOVERY.md), record date, recovery
   point, duration, counts; terminate the drill cluster.
   *Check:* report saved. Only now is recovery **verified**.
4. **Alert channel.** Create a Slack/Discord/Teams incoming webhook; Railway → Variables →
   `ALERT_WEBHOOK_URL`. Sentry: set `SENTRY_DSN`, add alert rules. Stripe → Webhooks →
   enable failure emails. Atlas → Alerts (connections, disk, CPU, backup failure).
5. **Uptime monitors** as listed in MONITORING.md, alerting at least two people.
6. **Redis.** Railway → project → **+ New** → Database → Redis (same environment). On
   **SynaptiqAcademy** → Variables → add `REDIS_URL` as a reference to the Redis service's
   private URL (it embeds the password). *Check after deploy:* `/api/health` →
   `"redis":"ok"`. (Shared rate limits and scheduling already work through MongoDB without
   Redis; Redis is still required for strict production mode.)
7. **Gunicorn proxy trust.** Variables: make sure `FORWARDED_ALLOW_IPS` is **not** `*`.
8. **AI budget.** Variables: `AI_MONTHLY_BUDGET_USD` (the provider spend you accept per
   month), optionally `AI_SYSTEM_BUDGET_SHARE`, `AI_EXPECTED_COST_PER_CREDIT_USD`. In the
   Anthropic and OpenAI consoles set a hard monthly limit slightly above that budget and
   notification thresholds.

## B. Deploy the remediation release

9. Push the commits listed in PRODUCTION_READINESS.md (Railway and Vercel deploy from `main`).
   *Check:* Railway deployment SUCCESS; `/api/health` 200.
10. **Client-IP check.** Signed in as super admin in a browser, open
    `https://<api host>/api/admin/security/client-ip`. Note `resolved_ip` (should be your
    public IP). Then, from a terminal with your session cookie, request it again with
    `-H "X-Forwarded-For: 1.2.3.4" -H "X-Real-IP: 1.2.3.4"`.
    *Check:* `resolved_ip` is still your real IP. If it shows `1.2.3.4`, set
    `CLIENT_IP_SOURCE=xff` and repeat; if that also follows the header, stop and report.
11. **Scheduler.** If `DISCOVERY_SCHEDULER_ENABLED=1`: logs show exactly one
    "Discovery scheduler started … (lease holder)" across all workers; MongoDB
    `job_runs` gets one document per job per window.

## C. Move the API to api.synaptiq.academy (same site as the app)

Today the app calls `*.up.railway.app`, a different site, so its session cookies are
third-party. In local browser-engine tests, sign-in did **not** persist in WebKit (Safari's
engine) or in Firefox with third-party cookies blocked; with the API on a same-site
subdomain it persisted in every engine tested.

12. Railway → **SynaptiqAcademy** → **Settings** → **Networking** → *Public Networking* →
    **+ Custom Domain** → `api.synaptiq.academy`. Railway shows a CNAME target (and a TXT
    record if it asks for verification).
13. DNS provider for `synaptiq.academy` → add `CNAME api → <target shown by Railway>`
    (and the TXT record if shown). *Check:* Railway shows the domain as active with a
    certificate; `curl https://api.synaptiq.academy/api/health` → 200.
14. Railway → Variables: `CORS_ORIGINS=https://www.synaptiq.academy,https://synaptiq.academy`,
    `COOKIE_SECURE=1`. Keep `COOKIE_SAMESITE=none` for now (works for both hosts during the switch).
15. Vercel → *synaptiq-academy* → Settings → **Environment Variables** →
    `REACT_APP_BACKEND_URL=https://api.synaptiq.academy` for **Production** → redeploy.
    *Check:* the new bundle calls `api.synaptiq.academy` (browser dev tools → Network).
16. OAuth callbacks: if `GOOGLE_REDIRECT_URI` / `ORCID_REDIRECT_URI` point at the Railway
    host, add the `api.synaptiq.academy` URI in Google Cloud Console → Credentials and in
    the ORCID developer tools first, then change the variables.
17. Railway → Variables: `COOKIE_SAMESITE=lax`. Users signed in before the switch sign in once more.
18. **Real browser test (required — the local engine test is not proof):** on macOS Safari,
    iPhone Safari, Chrome and Firefox: sign in, reload, open three pages, close and reopen
    the tab, upgrade page loads, sign out; repeat in a private window.
    *Check:* all pass. Record device and browser versions.
19. Stripe webhook endpoint can stay on the Railway URL (no cookies involved). To move it,
    add a new endpoint for `https://api.synaptiq.academy/api/billing/webhook`, set its
    signing secret as `STRIPE_WEBHOOK_SECRET`, confirm a test event succeeds, then disable
    the old endpoint.

## D. Strict production mode

20. Railway → Variables: `APP_ENV=production`. The validator refuses to start if a required
    setting is missing; the deployment log lists which. Fix and redeploy until it starts.
    *Check:* `/docs` returns 404; `/api/health` 200.

## E. Rotate the production database credentials

Rotate before launch and whenever a credential may have been copied outside Railway.
Rotate without downtime — create, switch, verify, then revoke:

21. Atlas → **Database Access** → **Add New Database User**: new name (e.g. `synaptiq_app_2026q4`),
    strong generated password, role `readWrite` on the production database only.
22. Build the new connection string from the old one (only username and password change).
    Store it in the password manager.
23. List every consumer of the old credentials: Railway `SynaptiqAcademy` (`MONGODB_URI`
    and `MONGO_URL` if set), any other Railway service or environment that references it,
    backup jobs, BI or admin tools, CI secrets. Developer machines must not receive it.
24. Update each consumer's variable to the new string; Railway redeploys.
    *Check per consumer:* `/api/health/ready` → `"mongodb":"ok"`; a sign-in works; logs show
    no authentication errors.
25. Watch for 30–60 minutes. Atlas → cluster → **Metrics** → connections should be stable;
    Atlas **Project Activity Feed** shows no failed authentications.
26. Revoke: Atlas → Database Access → old user → **Delete**. Re-check `/api/health/ready`.
27. Remove the production string from every developer `.env`; local development uses a
    local MongoDB. Optionally restrict Atlas **Network Access** to Railway's static egress
    IPs (Railway Pro feature) instead of `0.0.0.0/0`.

The same create → switch → verify → revoke order applies to AWS access keys (IAM → create
second key → update → verify upload/download → deactivate old → delete), Stripe secret keys
(Developers → API keys → **Roll key** with an expiry window), Resend and AI provider keys.
Rotating `JWT_SECRET` signs everyone out; schedule it.

## F. Staging and load test

28. Railway → project → **Environments** → **New environment** `staging` (fork of production),
    then override every secret: separate Atlas cluster or database, Stripe **test** keys and
    a test webhook endpoint, separate S3 bucket, `EMAIL_DRY_RUN=1`, low-limit AI keys or a
    stub, its own `JWT_SECRET` and `ENCRYPTION_KEY`, `DISCOVERY_SCHEDULER_ENABLED=0`.
    Same resources and `WORKERS` as production.
29. Give staging same-site domains: `staging.synaptiq.academy` (Vercel Preview or a
    separate Vercel project) and `staging-api.synaptiq.academy` (Railway custom domain).
30. Seed test accounts and synthetic data, then run
    `deploy/loadtest/loadtest.py --base https://staging-api.synaptiq.academy --users users.csv`
    at 25 → 50 → 100 → 200 → 400 users, a 30-minute soak, and a 60-second sign-in burst.
    Record Railway CPU/RAM and Atlas metrics. Pass: page-data p95 < 500 ms, sign-in
    p95 < 1 s, error rate < 0.5%, CPU < 70% at the target load, no unindexed slow queries.

## G. Open for paid sign-ups

31. Stripe live mode: webhook endpoint subscribed to `checkout.session.completed`,
    `checkout.session.async_payment_succeeded`, `customer.subscription.created/updated/deleted`,
    `invoice.paid`, `invoice.payment_failed`, `charge.refunded`, `charge.dispute.created`;
    Billing → failed-payment retries and final action set; tax settings if applicable.
32. AWS S3 uploads bucket: Block Public Access on, default encryption on, versioning on;
    IAM key limited to that bucket.
33. Decide on login geolocation: it is now off. To re-enable it, choose an HTTPS provider,
    add it to `docs/privacy/processors-and-transfers.md` and the privacy notice, then set
    `LOGIN_GEOLOCATION_URL`.
34. Admin → Feature Flags → `public_registration` → on. (It is currently **off** in production.)
35. Make one real low-value purchase with a team card, confirm the plan and credits, then
    refund it and confirm the refund is recorded.
