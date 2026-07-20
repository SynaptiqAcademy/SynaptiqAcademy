# Backup and Recovery

Full disaster-recovery scenarios live in `/deploy/INCIDENT_RESPONSE.md` and
`/deploy/RUNBOOK.md` — this document focuses on what's backed up, how, and how to prove
a restore actually works.

## What's backed up

| Data | Mechanism | Frequency | Retention |
|---|---|---|---|
| MongoDB (all collections) | `deploy/backup.sh` — `mongodump` → tar.gz → AES-256-CBC encrypted → uploaded to S3 | Daily, 02:00 UTC (cron) | 7 daily + 4 weekly (`RETENTION_DAILY=7`, `RETENTION_WEEKLY=4` in `backup.sh`) |
| MongoDB (continuous, if on Atlas M10+) | Atlas's own continuous backup | Continuous | Per your Atlas backup policy |
| S3 uploads bucket | Enable S3 versioning (see [AWS_S3_SETUP.md](AWS_S3_SETUP.md)) — not a separate backup job in this codebase | N/A — versioning-based | Per your bucket's lifecycle policy |
| Configuration (`.env`) | **Not automated** — see "Missing Production Requirements" | Manual | — |
| Secrets | **Not automated** — see "Missing Production Requirements" | Manual | — |

## MongoDB backup — how it works

`deploy/backup.sh backup`:
1. `mongodump --uri "$MONGODB_URI" --db "$MONGODB_DB_NAME"` into a temp directory.
2. `tar.gz` the dump.
3. Encrypt with `openssl enc -aes-256-cbc -pass env:BACKUP_ENCRYPTION_PASSPHRASE`.
4. Compute and store a SHA-256 checksum alongside it.
5. Upload both to `s3://$S3_BACKUP_BUCKET/`.
6. Prune backups beyond the daily/weekly retention window.
7. POST a success/failure message to `ALERT_WEBHOOK_URL` if set.

Scheduled via `deploy/synaptiq.cron`:
```cron
0 2 * * * set -a; . /opt/synaptiq/backend/.env; set +a; /opt/synaptiq/deploy/backup.sh backup >> /var/log/synaptiq/backup.log 2>&1
```

**Required environment variables:** `MONGODB_URI`, `MONGODB_DB_NAME`, `S3_BACKUP_BUCKET`,
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `BACKUP_ENCRYPTION_PASSPHRASE`.
**Required tools on the host:** `mongodump` (from `mongodb-database-tools`), `awscli`.

## Restore procedure

```bash
# 1. Stop the backend (prevent writes to a partially-restored DB)
docker compose -f deploy/docker-compose.prod.yml stop backend

# 2. Run the restore (interactive — prompts for which archive to restore)
source backend/.env
./deploy/backup.sh restore

# 3. Verify row counts / spot-check data
mongosh "$MONGODB_URI" --eval "db.users.countDocuments({})"

# 4. Restart backend
docker compose -f deploy/docker-compose.prod.yml start backend

# 5. Verify health
curl https://api.synaptiq.academy/api/health
```

For Atlas continuous backup (M10+) instead: Atlas UI → Clusters → **Restore** → Point in
Time → select recovery point → restore to new or existing cluster.

## Restore testing (dry run)

```bash
RESTORE_DRY_RUN=1 ./deploy/backup.sh restore <date>
```
Exercises the download/decrypt/checksum-verify path without actually running
`mongorestore` against your live database — use this regularly (not just when you
actually need a restore) to catch a broken backup pipeline before it matters.

## Automated integrity checking

`deploy/check_backup_integrity.sh`, run weekly via cron (Sunday 03:30 UTC): downloads the
latest backup, verifies its SHA-256 checksum, and alerts via `ALERT_WEBHOOK_URL` on
failure — this catches silent corruption (truncated upload, bit rot) between backup and
the moment you'd actually need it.

## Disaster recovery validation

`deploy/dr_validate.sh`, run weekly via cron (Sunday 04:00 UTC, after the integrity
check): validates critical infrastructure components end-to-end against a running
instance (`--host http://localhost:8000` by default, or `$TEST_BASE_URL`).

## RPO / RTO targets

| Metric | Target | Mechanism |
|---|---|---|
| RPO | 24 hours | Daily `mongodump` → S3 |
| RPO (upgrade path) | < 1 hour | MongoDB Atlas M10+ continuous backup (point-in-time restore) |
| RTO | 4 hours | Manual restore + verify + restart |
| RTO (Atlas continuous) | ~30 minutes | Atlas point-in-time restore |

## Restore testing cadence

Run a full restore-to-a-scratch-environment test at least quarterly — a backup that has
never been restored is unverified. `RESTORE_DRY_RUN=1` (above) is a lighter-weight partial
check; a true test restore into a separate MongoDB instance (not production) is the real
proof and should be scheduled on the calendar, not left to "we'll find out during an
actual incident."

## Missing Production Requirements

- **Configuration (`.env`) and secrets are not backed up by any automated mechanism in
  this codebase.** Losing the production host without a separate copy of `.env` means
  losing `JWT_SECRET`, `ENCRYPTION_KEY`, all API keys, etc. simultaneously with the data
  they protect. Store an encrypted copy of `.env` in a secrets manager (AWS Secrets
  Manager, 1Password, Vault) independent of the application host, and document the
  recovery procedure for pulling it back.
- No documented backup of Redis data — acceptable since Redis here is a cache/session
  layer (not source-of-truth data; see [REDIS_SETUP.md](REDIS_SETUP.md)), but confirm
  this assumption still holds if Redis's role in the architecture ever expands.
- No S3 lifecycle policy documented for the backups bucket beyond the script's own
  daily/weekly pruning — consider an S3-level lifecycle rule as a second layer of
  retention enforcement independent of the script.
