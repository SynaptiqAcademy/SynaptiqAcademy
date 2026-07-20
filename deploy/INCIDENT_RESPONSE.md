# Synaptiq — Incident Response Guide

**Version:** 1.0 | **Updated:** 2026-07-05  
**On-call contact:** contact@synaptiq.academy  
**Status page:** `GET /api/status` (machine-readable) or admin panel → Platform Status

---

## Severity Levels

| Level | Definition | Response Time | Examples |
|-------|-----------|---------------|---------|
| **P1 — Critical** | Complete outage, data loss risk, security breach | 15 min | DB down, auth broken, data leak |
| **P2 — Major** | Core feature unavailable, >25% users affected | 1 hour | AI unavailable, billing broken, login failing |
| **P3 — Minor** | Feature degraded, workaround exists | 4 hours | Email delay, slow queries, one admin endpoint failing |
| **P4 — Informational** | No user impact, monitoring alert | Next business day | Disk >80%, test flake, cert renewal 30d |

---

## On-Call Runbook

### Step 1 — Assess

```bash
# Check platform health
curl https://api.synaptiq.academy/api/health

# Check platform status (public)
curl https://api.synaptiq.academy/api/status

# Check Docker container status
docker ps
docker logs synaptiq_backend --tail=100

# Check Redis
docker exec synaptiq_redis redis-cli -a $REDIS_PASSWORD ping

# Check nginx
nginx -t && systemctl status nginx
```

### Step 2 — Classify severity (P1–P4)

Use the table above. When in doubt, escalate to P2.

### Step 3 — Create an incident

```bash
# Via API (requires super_admin token)
curl -X POST https://api.synaptiq.academy/api/status/incidents \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"API degradation","severity":"major","status":"investigating","affected_components":["api"]}'
```

Or log in to the Admin Control Center → Platform Status → New Incident.

### Step 4 — Resolve

```bash
curl -X PATCH https://api.synaptiq.academy/api/status/incidents/{id} \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"status":"resolved","message":"Issue resolved. Root cause: X. Fix: Y."}'
```

---

## Specific Scenarios

### Database (MongoDB) Outage

**Symptoms:** `/api/health` → `{"checks":{"mongodb":"error:..."}}`; all endpoints return 500.

**Steps:**
1. Check Atlas status: https://status.mongodb.com/
2. Verify network: `mongosh "$MONGODB_URI" --eval "db.runCommand({ping:1})"`
3. Check Atlas Network Access — server IP must be in allowlist
4. If Atlas cluster down: wait (Atlas SLA 99.995%) or activate DR
5. If data corruption: restore from backup (see Restore Guide below)
6. Recovery: platform auto-reconnects when Atlas becomes available

### Redis Outage

**Impact:** Cache misses (slower), rate limiting degraded; sessions still valid (DB-backed fallback)

**Steps:**
1. `docker compose -f deploy/docker-compose.prod.yml restart redis`
2. If volume corrupt: `docker volume rm synaptiq_redis_data` then restart
3. Verify: `docker exec synaptiq_redis redis-cli -a $REDIS_PASSWORD ping`

### AI Provider Outage

**Impact:** AI features return errors; non-AI features unaffected

**Steps:**
1. Check Anthropic status: https://status.anthropic.com/
2. Check OpenAI status: https://status.openai.com/
3. Platform auto-falls back to OpenAI if Anthropic fails
4. If both down: AI features return a user-facing error (no crash)
5. Optionally switch primary via `AI_MATCHING_PROVIDER=openai` env var + restart

### Stripe Outage

**Impact:** New subscriptions/payments fail; existing users unaffected

**Steps:**
1. Monitor https://status.stripe.com/
2. Stripe retries failed webhooks automatically for 72h after recovery
3. Existing subscription status is cached in MongoDB — no action needed for active users
4. If webhook backlog: Stripe dashboard → Webhooks → resend failed events

### Security Incident (Data Breach / Unauthorized Access)

**Steps — IMMEDIATE:**
1. Enable maintenance mode: Admin → Maintenance Mode → Enable
2. Rotate JWT_SECRET (forces all active sessions to expire)
3. Rotate database credentials in Atlas
4. Contact all users via email (Resend bulk)
5. Preserve all logs before any cleanup

**Investigation:**
```bash
# Check audit log
mongosh "$MONGODB_URI/$MONGODB_DB_NAME" --eval "db.obs_audit.find({}).sort({timestamp:-1}).limit(100).pretty()"

# Check auth events
mongosh "$MONGODB_URI/$MONGODB_DB_NAME" --eval "db.audit_log.find({'action':{'\$regex':'login|auth'}}).sort({created_at:-1}).limit(50).pretty()"
```

**Regulatory:**
- GDPR breach notification required within 72 hours to supervisory authority if personal data affected
- NIS2: incident notification to national CSIRT within 24 hours (significant incidents)
- Document: what data, how many users, root cause, remediation

### Payment Failure Spike

**Symptoms:** Multiple `invoice.payment_failed` webhook events; user complaints

**Steps:**
1. Check Stripe Dashboard → Events for patterns
2. Check if `STRIPE_WEBHOOK_SECRET` is correctly set (signature verification failures → events discarded)
3. Check `billing_disputes` collection for dispute spike
4. Common causes: expired cards (monthly), SCA required (European users), Stripe quota issue
5. Users already receive `payment_action_required` notification in-app

### High Disk Usage

**Threshold:** Cron alerts at >80%; `/api/health` warns at >80%, critical at >95%

**Steps:**
1. `df -h /` — check total usage
2. Find largest directories: `du -sh /var/log/synaptiq/* | sort -rh | head`
3. Clear old logs (already handled by cron weekly, but manual purge if urgent)
4. Consider resizing the volume in cloud provider console

---

## Restore Guide

### MongoDB Atlas Restore

**From continuous backup (M10+):**
1. Atlas → Clusters → ... → Restore → Point in Time
2. Select recovery point (RPO: 1 min with continuous backup)
3. Restore to new cluster or same cluster (destructive)
4. Verify: `curl https://api.synaptiq.academy/api/health`

**From mongodump backup (S3):**
```bash
# Download latest backup from S3
aws s3 ls s3://${BACKUP_S3_BUCKET}/${BACKUP_S3_PREFIX}/ | sort | tail -5

# Download
aws s3 cp s3://${BACKUP_S3_BUCKET}/${BACKUP_S3_PREFIX}/<archive>.gz.enc /tmp/

# Decrypt
openssl enc -d -aes-256-cbc -in /tmp/<archive>.gz.enc -out /tmp/<archive>.gz -pass env:BACKUP_ENCRYPTION_KEY

# Restore
mongorestore --uri "$MONGODB_URI" --gzip --archive=/tmp/<archive>.gz --drop
```

**Estimated RTO:** 4 hours (manual), 30 min (Atlas continuous backup)

---

## Communication Templates

### User-facing announcement (major incident)

Subject: Synaptiq Service Alert — [Brief Description]

> We are currently experiencing an issue affecting [feature/all users]. Our team has been alerted and is actively investigating. We will provide updates every [30/60] minutes. We apologize for the disruption.

### Resolution announcement

> The issue affecting [feature] has been resolved as of [time UTC]. All services are now operating normally. If you continue to experience issues, please contact support@synaptiq.academy.

---

## Post-Incident Review

Required for all P1 and P2 incidents within 5 business days:

1. **Timeline** — when detected, when escalated, when resolved
2. **Root cause** — technical and process root causes
3. **Impact** — users affected, data affected, revenue impact
4. **Resolution** — what was done to fix
5. **Prevention** — what changes prevent recurrence
6. **Action items** — specific tasks with owners and deadlines

Document in: Admin → Incidents → Post-Mortem, or as a GitHub issue.

---

## Contact Escalation

| Role | Contact | Availability |
|------|---------|-------------|
| Platform Engineering | contact@synaptiq.academy | Business hours |
| Security | contact@synaptiq.academy | 24/7 for P1 |
| Enterprise Customer Success | contact@synaptiq.academy | Business hours |

*For P1 incidents outside business hours: page via `ALERT_WEBHOOK_URL` (configured in cron)*
