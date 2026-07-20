# SYNAPTIQ — Operational Runbook

**Version:** 2.0 · Last updated: 17 June 2026  
**On-call contact:** contact@synaptiq.academy

---

## Deployment

### First deployment
```bash
# 1. Clone repo, fill secrets
cp backend/.env.example backend/.env
nano backend/.env  # set all REQUIRED fields

# 2. SSL certs
apt install certbot
certbot certonly --standalone -d synaptiq.academy -d www.synaptiq.academy -d api.synaptiq.academy

# 3. Build frontend
cd frontend && npm ci && npm run build

# 4. Start services
docker compose -f deploy/docker-compose.prod.yml up -d

# 5. Verify health
curl https://api.synaptiq.academy/api/health
```

### Rolling update (zero downtime)
```bash
git pull
docker compose -f deploy/docker-compose.prod.yml build backend
docker compose -f deploy/docker-compose.prod.yml up -d --no-deps backend
# nginx keeps serving; backend restarts; Docker health check gates traffic
```

---

## RPO & RTO Targets

| Metric | Target | Mechanism |
|--------|--------|-----------|
| RPO (Recovery Point Objective) | 24 hours | Daily mongodump → S3 |
| RTO (Recovery Time Objective) | 4 hours | Manual restore + verify + restart |

To improve RPO to < 1 hour: migrate to MongoDB Atlas M10+ with continuous cloud backup.

---

## Disaster Recovery Scenarios

### Scenario 1: Database outage (MongoDB unreachable)
**Symptoms:** `/api/health` returns `{"checks":{"mongodb":"error:..."}}`, all API calls fail 500  
**Steps:**
1. Check MongoDB Atlas status: https://status.mongodb.com/
2. Verify `MONGODB_URI` in `.env` is the correct Atlas SRV string (`mongodb+srv://...`)
3. Check Atlas Network Access — add server IP if missing (Atlas → Security → Network Access)
4. If Atlas cluster is down: wait for Atlas recovery (Atlas SLA: 99.995%)
5. If data corruption: restore from backup (see Scenario 5)

### Scenario 2: Redis outage
**Symptoms:** Scheduler warnings in logs; rate limiting and real-time features degraded  
**Impact:** Application continues to serve requests (Redis degrades gracefully — all consumers handle `get_redis() → None`)  
**Steps:**
1. Check Redis container: `docker ps` / `systemctl status synaptiq-redis`
2. Restart: `docker compose -f deploy/docker-compose.prod.yml restart redis`
3. If data volume corrupt: `docker volume rm synaptiq_redis_data` then restart (Redis data is cache — safe to wipe)
4. Confirm recovery: `docker exec synaptiq_redis redis-cli -a $REDIS_PASSWORD ping`

### Scenario 3: Stripe outage
**Symptoms:** Billing endpoints return errors; webhook delivery fails  
**Impact:** New subscriptions and payments fail; existing users unaffected (auth is DB-backed, not Stripe-backed)  
**Steps:**
1. Monitor: https://status.stripe.com/
2. No action required for existing users — their subscription status is cached in MongoDB
3. Once Stripe recovers, Stripe will re-deliver failed webhooks automatically (up to 72h)
4. If webhook re-delivery fails: log into Stripe dashboard → Webhooks → resend failed events manually

### Scenario 4: Resend (email) outage
**Symptoms:** Email verification and password reset emails not delivered  
**Impact:** New user registration blocked (email verification required); existing users unaffected  
**Steps:**
1. Monitor: https://resend.com/status
2. Email delivery will queue and retry automatically once Resend recovers
3. If outage is prolonged (>4h): temporarily set `EMAIL_VERIFICATION_REQUIRED=0` and restart backend (allows registration without email check)
4. Re-enable after Resend recovers: `EMAIL_VERIFICATION_REQUIRED=1` + restart

### Scenario 5: Server crash / host failure
**Symptoms:** All services unreachable; uptime monitor fires alert  
**Steps:**
1. SSH into server (or use cloud provider console)
2. Check disk and memory: `df -h && free -h`
3. Restart Docker: `systemctl restart docker`
4. Restart services: `docker compose -f deploy/docker-compose.prod.yml up -d`
5. Verify: `curl https://api.synaptiq.academy/api/health`
6. If server is unrecoverable: provision new server, restore from backup (Scenario 6)

### Scenario 6: Accidental data deletion / data corruption
**Goal:** Restore MongoDB to the most recent clean state  
**Steps:**
```bash
# 1. Stop backend (prevent further writes to corrupted state)
docker compose -f deploy/docker-compose.prod.yml stop backend

# 2. Run restore (interactive — will prompt for filename)
source backend/.env
./deploy/backup.sh restore

# 3. Verify data integrity
mongosh "$MONGODB_URI" --eval "db.users.countDocuments({})"

# 4. Restart backend
docker compose -f deploy/docker-compose.prod.yml start backend

# 5. Verify health
curl https://api.synaptiq.academy/api/health
```

---

## Monitoring Setup

### Uptime monitoring (configure externally)
- **UptimeRobot** (free) or **BetterStack** (recommended): monitor `https://api.synaptiq.academy/api/health` every 5 minutes
- Set alert: email + SMS to on-call if HTTP status ≠ 200 for 2 consecutive checks
- Set alert: alert if response body `status` ≠ `"ok"` (JSON keyword monitor)

### Error tracking (Sentry)
- Create project at https://sentry.io
- Copy DSN → set `SENTRY_DSN` in `.env` → restart backend
- Set alert rule: notify on new error, on error spike (>10/min)

### Alerting webhook (Slack/Discord)
- Set `ALERT_WEBHOOK_URL` in `.env` to receive:
  - Daily backup success/failure
  - Weekly backup integrity check
  - Disk space > 80%

---

## Credential Rotation

| Credential | How to rotate | Impact |
|------------|---------------|--------|
| `JWT_SECRET` | Change in `.env` + restart | All existing sessions invalidated; users must re-login |
| `ENCRYPTION_KEY` | **Cannot hot-swap** — requires data migration script | Plan maintenance window |
| `ADMIN_PASSWORD` | Change in `.env` + restart; update in DB via admin panel | None if done in order |
| `STRIPE_*` | Rotate in Stripe dashboard → update `.env` → restart | Test with a new subscription first |
| MongoDB Atlas password | Rotate in Atlas → update `MONGODB_URI` in `.env` → restart | < 10s downtime during restart |
| `REDIS_PASSWORD` | Update in `.env` + `docker-compose.prod.yml` env → `docker compose up -d` | Session cache lost (users re-login) |

---

## Business Continuity

### Administrator access recovery
1. Primary admin locked out: use `ADMIN_EMAIL`/`ADMIN_PASSWORD` from `.env` — these are seeded on startup
2. If admin account is corrupted: connect directly to MongoDB Atlas → `db.users.updateOne({email: "admin@synaptiq.academy"}, {$set: {is_super_admin: true}})`
3. All admin actions are logged in `audit_log` collection (90-day TTL)

### Service migration (moving to a new host)
1. Take a backup: `./deploy/backup.sh backup`
2. Provision new server
3. Install Docker, copy `.env`, SSL certs
4. Run restore: `./deploy/backup.sh restore`
5. Update DNS A records to point to new host IP
6. Start services on new host
7. Verify health at new IP before DNS propagates
8. DNS TTL propagation: ~5 minutes (set TTL to 60s before migration)

### GDPR data deletion requests
1. User requests deletion via email (privacy@synaptiq.academy) or Settings
2. Admin deletes account via Admin Control Center → User Management → Delete Account
3. Data removal: profile, content, messages deleted within 30 days
4. Billing records retained 7 years (EU tax law)
5. Log the deletion in `audit_log` with actor=admin, action=gdpr_erasure
