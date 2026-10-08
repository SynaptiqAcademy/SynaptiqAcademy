# Backup and Recovery

A backup counts only after it has been restored. This page says what protects the
production database, how to prove a restore works without touching production, and what
has and has not been verified.

## Production database

Evidence available in the repository and Railway metadata points to **MongoDB Atlas**:

- `services/prod_validator.py` refuses production start-up unless `MONGODB_URI` is an Atlas
  `mongodb+srv://…mongodb.net` string.
- The developer configuration uses an Atlas cluster.
- The Railway `MongoDB` service in the project (image `mongo:8.0`, volume `/data/db`, ~85 MB)
  shows near-zero CPU and no public traffic.

This is **not confirmed**. Confirm it by looking only at the host part of `MONGODB_URI` in
Railway → service **SynaptiqAcademy** → **Variables**: `*.mongodb.net` means Atlas,
`*.railway.internal` means the Railway service. If the Railway `MongoDB` service is unused,
remove it after confirming nothing connects to it.

## Layers

| Layer | What | Status |
|---|---|---|
| 1. Provider backup (primary) | Atlas Cloud Backup with continuous point-in-time restore (cluster tier M10 or above) | **To enable and record** — Atlas → Cluster → Backup |
| 2. Independent logical copy | Encrypted `mongodump` archive in a separate S3 bucket, daily | Procedure below; schedule it once the backup user and bucket exist |
| 3. Uploaded files | S3 versioning on the uploads bucket, plus a lifecycle rule for old versions | To verify — AWS → S3 → bucket → Properties |
| 4. Configuration and secrets | Copy of every Railway/Vercel variable in a password manager or secrets manager, kept outside Railway | To do |

Targets: **RPO** ≤ 1 hour with Atlas point-in-time restore (24 hours with the logical copy
alone). **RTO** about 1 hour (restore to a new cluster, verify, switch `MONGODB_URI`, redeploy).

## Logical backup (layer 2)

Uses a dedicated Atlas database user with only the `backup` role, never the application user.

```bash
# Inputs (from a secrets manager — never typed into shell history):
#   BACKUP_SOURCE_URI   read-only backup user connection string
#   BACKUP_DB_NAME      e.g. synaptiq
#   BACKUP_PASSPHRASE   encryption passphrase, stored separately from the bucket
STAMP=$(date -u +%Y%m%dT%H%M%SZ); BASE="synaptiq_${BACKUP_DB_NAME}_${STAMP}"
# 1. document counts before the dump (per collection) → before.json   (mongosh countDocuments)
# 2. dump without putting the URI on the command line:
printf 'uri: "%s"\n' "$BACKUP_SOURCE_URI" > dump.yaml && chmod 600 dump.yaml
mongodump --config=dump.yaml --db="$BACKUP_DB_NAME" --archive="$BASE.archive.gz" --gzip
rm dump.yaml
# 3. document counts after the dump → after.json; write $BASE.manifest.json with
#    {"db": ..., "collections": {name: {"before": n, "after": n}}}
# 4. encrypt and checksum
openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -in "$BASE.archive.gz" \
  -out "$BASE.archive.gz.enc" -pass env:BACKUP_PASSPHRASE && rm "$BASE.archive.gz"
shasum -a 256 "$BASE.archive.gz.enc" > "$BASE.archive.gz.enc.sha256"
# 5. upload the three files to the backup bucket (object lock / versioning on)
```

The manifest records counts before and after the dump because a live database keeps
changing while `mongodump` runs; a restored collection must fall between the two.

## Isolated restore verification

`deploy/backup/db_restore_verify.sh` restores a backup into a **separate** server and
compares every collection with the manifest. It refuses to run when:

- the target is not local and `ALLOW_REMOTE_TARGET=1` is not set (for a dedicated restore cluster);
- the target host matches `PRODUCTION_HOST_PATTERN`;
- the restored database name does not contain `restore`;
- the checksum does not match or the passphrase is wrong.

```bash
BACKUP_PASSPHRASE=… BACKUP_SRC=s3://<backup-bucket>/<prefix> \
RESTORE_TARGET_URI=mongodb://127.0.0.1:27018/ \
PRODUCTION_HOST_PATTERN=<production cluster host fragment> \
deploy/backup/db_restore_verify.sh
# → restore_report_<stamp>.json with collections, documents, duration, PASS/FAIL
```

A throwaway target can be a local `mongod --port 27018 --dbpath <temp dir>`, a CI service
container, or a temporary Atlas cluster. Delete the restored data afterwards.

For an Atlas point-in-time restore drill: Atlas → Cluster → **Backup** → **Restore** →
*Point in time* → **restore to a new cluster** (never "this cluster"). Then run the count
comparison against the new cluster, record date, recovery point, duration and counts, and
terminate the new cluster.

## Evidence so far

| Check | Result |
|---|---|
| Local procedure: backup of the local test database → restore into a separate `mongod` | **PASS** — 214 collections, 81,783 documents, every count within range, 15 s |
| Safety refusals (remote target, production host pattern, database name, wrong passphrase, tampered archive) | **PASS** — all five refused |
| Production backup policy (Atlas) | **Not verified** — needs Atlas access |
| Production restore drill | **Not performed** — recovery of production data is **unverified** until it is |

## Restore cadence

Run a restore drill after enabling backups, then monthly, and record the report. A backup
that has never been restored is not evidence of recoverability.
