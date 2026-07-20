# Incident Response

> The complete, scenario-by-scenario guide (with copy-paste commands for every scenario)
> lives at [`/deploy/INCIDENT_RESPONSE.md`](../deploy/INCIDENT_RESPONSE.md) and
> [`/deploy/RUNBOOK.md`](../deploy/RUNBOOK.md). This document is the quick-reference
> entry point — read it first, then jump to the detailed scenario in `/deploy` for exact
> commands.

## Severity levels

| Level | Definition | Response time |
|---|---|---|
| P1 — Critical | Complete outage, data loss risk, security breach | 15 min |
| P2 — Major | Core feature unavailable, >25% of users affected | 1 hour |
| P3 — Minor | Feature degraded, workaround exists | 4 hours |
| P4 — Informational | No user impact, monitoring alert only | Next business day |

## Step 1 — How to identify the issue

```bash
curl https://api.synaptiq.academy/api/health     # overall health + per-dependency status
curl https://api.synaptiq.academy/api/status     # public incident/status feed
docker ps                                        # container status
docker logs synaptiq_backend --tail=100          # recent backend logs
docker exec synaptiq_redis redis-cli -a "$REDIS_PASSWORD" ping
nginx -t && systemctl status nginx               # if running nginx outside Docker
```

`/api/health`'s `checks` object tells you immediately whether MongoDB or Redis is the
proximate cause — start there before digging into application logs.

## Step 2 — Where to check logs

See [LOGGING.md](LOGGING.md) for the full reference. Fastest paths:

```bash
docker logs synaptiq_backend --tail=200 -f | jq 'select(.level=="ERROR")'
# or, bare metal:
journalctl -u synaptiq-backend --since "30 min ago" -o json | jq 'select(.level=="ERROR")'
```

Sentry (`SENTRY_DSN`), if configured, is usually faster than grepping raw logs for a new
or spiking error type. The internal observability platform's `GET /api/ops/logs`,
`GET /api/ops/security`, and `GET /api/ops/audit` (super-admin) are worth checking for
anything auth/security-adjacent — see [MONITORING.md](MONITORING.md).

## Step 3 — Classify severity and open an incident

Use the table above; escalate to P2 when unsure. Log the incident so `/api/status`
reflects reality for users:

```bash
curl -X POST https://api.synaptiq.academy/api/status/incidents \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"API degradation","severity":"major","status":"investigating","affected_components":["api"]}'
```

## Step 4 — How to roll back

See [DEPLOYMENT.md](DEPLOYMENT.md)'s "Rollback procedure". Summary:

```bash
docker compose -f deploy/docker-compose.prod.yml stop backend
docker tag synaptiq-backend:<previous-tag> synaptiq-backend:latest
docker compose -f deploy/docker-compose.prod.yml up -d --no-deps backend
curl https://api.synaptiq.academy/api/health
```

Application code changes here are safe to roll back independently of the database in
the common case (migrations in this codebase are additive/idempotent — see
[DATABASE.md](DATABASE.md)); verify the specific release's changelog entry if it
mentions a destructive migration.

## Step 5 — How to restore (data loss / corruption)

See [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md) for the full procedure. Summary:

```bash
docker compose -f deploy/docker-compose.prod.yml stop backend
source backend/.env
./deploy/backup.sh restore
mongosh "$MONGODB_URI" --eval "db.users.countDocuments({})"   # sanity check
docker compose -f deploy/docker-compose.prod.yml start backend
curl https://api.synaptiq.academy/api/health
```

## Step 6 — How to notify users

Templates (from `/deploy/INCIDENT_RESPONSE.md`):

> **Major incident:** "We are currently experiencing an issue affecting [feature/all
> users]. Our team has been alerted and is actively investigating. We will provide
> updates every [30/60] minutes. We apologize for the disruption."
>
> **Resolved:** "The issue affecting [feature] has been resolved as of [time UTC]. All
> services are now operating normally. If you continue to experience issues, please
> contact support@synaptiq.academy."

Post updates to the `/api/status` incident record (`PATCH
/api/status/incidents/{id}`) so the in-app/public status page stays current — this is
the single source of truth users and the admin panel both read from.

## Specific scenarios (quick index — full steps in `/deploy/INCIDENT_RESPONSE.md`)

| Scenario | Impact | First action |
|---|---|---|
| MongoDB Atlas outage | All API calls fail | Check status.mongodb.com, verify Network Access allowlist |
| Redis outage | Degraded (rate limiting/real-time), not down | No urgent action — self-heals; see [REDIS_SETUP.md](REDIS_SETUP.md) |
| AI provider outage | AI features error, rest of app fine | Check status.anthropic.com / status.openai.com; auto-fallback already in place |
| Stripe outage | New payments fail, existing users unaffected | Check status.stripe.com; Stripe re-delivers webhooks for 72h |
| Resend outage | Verification/reset emails not delivered | Check resend.com/status; consider temporary `EMAIL_VERIFICATION_REQUIRED=0` if prolonged |
| Security incident / breach | Varies | Enable maintenance mode, rotate `JWT_SECRET` immediately, preserve logs, see below |
| High disk usage | Risk of full outage if unaddressed | `df -h /`, clear old logs, resize volume |

## Security incident — immediate steps

1. Enable maintenance mode (Admin → Maintenance Mode).
2. Rotate `JWT_SECRET` — this immediately invalidates every active session platform-wide.
3. Rotate MongoDB Atlas credentials.
4. Preserve all logs *before* any cleanup.
5. Notify affected users.
6. GDPR: breach notification to the supervisory authority within 72 hours if personal
   data was affected. NIS2: notify your national CSIRT within 24 hours for significant
   incidents.

## Post-incident review

Required for every P1/P2 within 5 business days: timeline, root cause (technical and
process), impact (users/data/revenue), resolution, prevention, action items with owners
and deadlines. Document in Admin → Incidents → Post-Mortem or as a GitHub issue.

## Contact escalation

| Role | Contact | Availability |
|---|---|---|
| Platform Engineering | contact@synaptiq.academy | Business hours |
| Security | contact@synaptiq.academy | 24/7 for P1 |
| Enterprise Customer Success | contact@synaptiq.academy | Business hours |

## Missing Production Requirements

- No dedicated on-call paging rotation/tool (PagerDuty, Opsgenie) is wired in — today's
  alerting is a Slack/Discord-compatible webhook (`ALERT_WEBHOOK_URL`) from cron jobs
  only, which is not the same as a paging system with acknowledgement/escalation.
- The single listed contact (`contact@synaptiq.academy`) for every role/severity is a
  bottleneck for true 24/7 P1 coverage — define a real on-call rotation before scaling
  past a single-operator team.
