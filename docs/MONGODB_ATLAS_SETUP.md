# MongoDB Atlas Setup

The application connects exclusively via Motor's async driver to a MongoDB **Atlas** SRV
connection string (`backend/db.py`) — it is not tested against a bare `mongod` in
production (CI uses a plain `mongo:7` container, but that's test-only, see
[CI_CD.md](CI_CD.md)).

## 1. Create the cluster

1. Atlas → **Create a new cluster**. Minimum recommended tier for production: **M10**
   (required for continuous backup / point-in-time restore — see
   [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md)). Lower tiers work for staging/dev.
2. Choose a region close to your application servers.
3. Enable **Atlas Vector Search** on this cluster if you use AI features that rely on
   embeddings (referenced in `deploy/ARCHITECTURE.md` — 1536-dim OpenAI-compatible
   vectors).

## 2. Database user

Atlas → **Database Access** → **Add New Database User**:
- Authentication: username/password
- Built-in role: `readWrite` scoped to the target database (avoid `atlasAdmin` for the
  application's own credential — reserve elevated roles for human operators).

## 3. Network access

Atlas → **Network Access** → **Add IP Address**:
- Add your production server's static egress IP.
- If your host has a dynamic IP (common on some managed platforms — see
  [RAILWAY_SETUP.md](RAILWAY_SETUP.md)'s note on this), you'll need a static-IP add-on or
  a NAT gateway with a fixed IP; `0.0.0.0/0` (allow from anywhere) is not recommended for
  production.

## 4. Connection string

Atlas → **Connect** → **Drivers** → copy the SRV connection string, then set:

```
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority&appName=SYNAPTIQ
MONGODB_DB_NAME=synaptiq
```

(`db.py` also accepts the deprecated backward-compatible alias `MONGO_URL`, plus `DB_NAME`
for the database name — both intentionally kept so older deployments keep working.
Prefer the `MONGODB_*` names for new deployments. As of the 2026-07-19 configuration
consistency pass, the undocumented `DATABASE_URL`/`MONGO_URI` fallbacks that used to
exist in `db.py` — accepted at runtime but never recognized by
`services/prod_validator.py`'s production check, a real inconsistency — have been
removed; `MONGODB_URI`/`MONGO_URL` are now the only two names either the app or the
validator will ever look for.)

## 5. Connection pooling

`db.py` reads `MONGO_MAX_POOL` (default `200`) and
`MONGO_SERVER_SELECTION_TIMEOUT_MS` for pool sizing and failure detection. The default of
200 is generous for a multi-worker Gunicorn deployment — tune down for smaller clusters.

## 6. Indexes

Indexes are created idempotently at application startup (see the many `*_indexes_created`
log lines in `server.py`'s startup sequence — one per feature phase). No manual index
management is required for a fresh Atlas cluster; the app self-provisions on first boot.
A few index-name conflicts are logged as non-fatal warnings on repeated startups (existing
index with the same auto-generated name but different options) — these are safe to
ignore; see [DATABASE.md](DATABASE.md).

## 7. Circuit breaker behavior

`db.py` implements `is_db_down()` / `mark_db_down()` / `mark_db_up()` — if Atlas becomes
unreachable, the app enters a degraded mode (fails fast instead of hanging on every
request) for a cooldown window (`DB_DOWN_COOLDOWN_SECONDS`, default 60s) before retrying.
No manual restart is needed for Atlas to be picked back up once it recovers — the
worker-platform supervisor and this circuit breaker both auto-recover.

## 8. Backups

See [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md). Two independent mechanisms exist:
Atlas's own continuous backup (M10+, configure in Atlas UI) and `deploy/backup.sh`
(`mongodump` → encrypted archive → S3, run daily via cron). Enable Atlas continuous
backup for the best RPO/RTO; keep the `mongodump`/S3 path as an independent, portable
copy that doesn't depend on staying with Atlas.

## Missing Production Requirements

- No documented Atlas alerting configuration (e.g., connection count, disk usage, slow
  query alerts) — set these up in Atlas → Alerts; nothing in the codebase does this for you.
- No explicit Atlas IP-allowlist automation for hosts with dynamic IPs.
