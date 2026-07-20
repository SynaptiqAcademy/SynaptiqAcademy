#!/usr/bin/env bash
# SYNAPTIQ — MongoDB backup to S3
#
# Prerequisites:
#   apt install mongodb-database-tools awscli
#   Set env vars: MONGODB_URI, MONGODB_DB_NAME, S3_BACKUP_BUCKET, AWS_ACCESS_KEY_ID,
#                 AWS_SECRET_ACCESS_KEY, AWS_REGION, BACKUP_ENCRYPTION_PASSPHRASE
#
# Cron (see synaptiq.cron): runs daily at 02:00 UTC, weekly full retained 4 weeks
# RPO target: 24 hours (daily backup)
# RTO target: 4 hours (restore + verify + restart)
#
# To test a restore:
#   RESTORE_DRY_RUN=1 ./backup.sh restore 2024-01-15

set -euo pipefail

# ── Config (override via env or .env) ────────────────────────────────────────
MONGO_URL="${MONGODB_URI:-${MONGO_URL:-}}"
if [[ -z "${MONGO_URL}" ]]; then
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] ERROR: MONGODB_URI (or MONGO_URL) must be set" >&2
    exit 1
fi
DB_NAME="${MONGODB_DB_NAME:-${DB_NAME:-synaptiq}}"
S3_BUCKET="${S3_BACKUP_BUCKET:?S3_BACKUP_BUCKET must be set}"
AWS_REGION="${AWS_REGION:-us-east-1}"
RETENTION_DAILY=7
RETENTION_WEEKLY=4

BACKUP_DIR="/tmp/synaptiq_backup_$$"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H%M%SZ")
DAY_OF_WEEK=$(date -u +"%u")  # 1=Monday … 7=Sunday
ARCHIVE_NAME="synaptiq_${TIMESTAMP}.tar.gz"
ENCRYPTED_NAME="${ARCHIVE_NAME}.enc"
CHECKSUM_NAME="${ENCRYPTED_NAME}.sha256"

log()   { echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*"; }
error() { echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] ERROR: $*" >&2; }

alert_success() {
    local msg="$1"
    log "SUCCESS: ${msg}"
    if [[ -n "${ALERT_WEBHOOK_URL:-}" ]]; then
        curl -sf -X POST "${ALERT_WEBHOOK_URL}" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"[SYNAPTIQ] ✅ ${msg}\"}" || true
    fi
}

alert_failure() {
    local msg="$1"
    error "${msg}"
    if [[ -n "${ALERT_WEBHOOK_URL:-}" ]]; then
        curl -sf -X POST "${ALERT_WEBHOOK_URL}" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"[SYNAPTIQ] ❌ BACKUP FAILURE: ${msg}\"}" || true
    fi
    exit 1
}

# ── BACKUP ────────────────────────────────────────────────────────────────────
backup() {
    # Encryption is mandatory — never upload plaintext backups
    if [[ -z "${BACKUP_ENCRYPTION_PASSPHRASE:-}" ]]; then
        alert_failure "BACKUP_ENCRYPTION_PASSPHRASE must be set. Refusing to upload unencrypted backup."
    fi

    log "Starting backup — DB=${DB_NAME} → s3://${S3_BUCKET}"

    mkdir -p "${BACKUP_DIR}"
    trap 'rm -rf "${BACKUP_DIR}"' EXIT

    log "Running mongodump…"
    mongodump \
        --uri="${MONGO_URL}" \
        --db="${DB_NAME}" \
        --out="${BACKUP_DIR}/dump" \
        --gzip \
        --numParallelCollections=2 \
        || alert_failure "mongodump failed"

    log "Archiving…"
    tar -czf "${BACKUP_DIR}/${ARCHIVE_NAME}" -C "${BACKUP_DIR}" dump \
        || alert_failure "tar archiving failed"

    log "Encrypting archive (AES-256-CBC, PBKDF2, 100k iterations)…"
    openssl enc -aes-256-cbc -pbkdf2 -iter 100000 \
        -pass pass:"${BACKUP_ENCRYPTION_PASSPHRASE}" \
        -in  "${BACKUP_DIR}/${ARCHIVE_NAME}" \
        -out "${BACKUP_DIR}/${ENCRYPTED_NAME}" \
        || alert_failure "openssl encryption failed"

    log "Computing SHA-256 checksum…"
    sha256sum "${BACKUP_DIR}/${ENCRYPTED_NAME}" | awk '{print $1}' \
        > "${BACKUP_DIR}/${CHECKSUM_NAME}"
    CHECKSUM=$(cat "${BACKUP_DIR}/${CHECKSUM_NAME}")
    log "Checksum: ${CHECKSUM}"

    # Upload encrypted archive to S3 (server-side encryption as additional layer)
    S3_KEY_DAILY="daily/${ENCRYPTED_NAME}"
    log "Uploading archive to s3://${S3_BUCKET}/${S3_KEY_DAILY}"
    aws s3 cp "${BACKUP_DIR}/${ENCRYPTED_NAME}" "s3://${S3_BUCKET}/${S3_KEY_DAILY}" \
        --region "${AWS_REGION}" \
        --sse AES256 \
        || alert_failure "S3 upload (archive) failed"

    # Upload checksum alongside archive
    S3_KEY_CHECKSUM="daily/${CHECKSUM_NAME}"
    log "Uploading checksum to s3://${S3_BUCKET}/${S3_KEY_CHECKSUM}"
    aws s3 cp "${BACKUP_DIR}/${CHECKSUM_NAME}" "s3://${S3_BUCKET}/${S3_KEY_CHECKSUM}" \
        --region "${AWS_REGION}" \
        --sse AES256 \
        || alert_failure "S3 upload (checksum) failed"

    # Sunday → also copy to weekly/
    if [[ "${DAY_OF_WEEK}" == "7" ]]; then
        log "Sunday — also copying to weekly/"
        aws s3 cp "s3://${S3_BUCKET}/${S3_KEY_DAILY}" \
                  "s3://${S3_BUCKET}/weekly/${ENCRYPTED_NAME}" \
            --region "${AWS_REGION}" || true
        aws s3 cp "s3://${S3_BUCKET}/${S3_KEY_CHECKSUM}" \
                  "s3://${S3_BUCKET}/weekly/${CHECKSUM_NAME}" \
            --region "${AWS_REGION}" || true
    fi

    # Prune old daily backups (keep RETENTION_DAILY)
    log "Pruning daily archives older than ${RETENTION_DAILY} most-recent…"
    aws s3 ls "s3://${S3_BUCKET}/daily/" --region "${AWS_REGION}" | \
        sort | grep '\.enc$' | head -n -${RETENTION_DAILY} | \
        awk '{print $4}' | \
        while read -r f; do
            [[ -n "${f}" ]] && {
                aws s3 rm "s3://${S3_BUCKET}/daily/${f}"           --region "${AWS_REGION}" || true
                aws s3 rm "s3://${S3_BUCKET}/daily/${f}.sha256"    --region "${AWS_REGION}" || true
            }
        done

    # Prune old weekly backups (keep RETENTION_WEEKLY)
    log "Pruning weekly archives older than ${RETENTION_WEEKLY} most-recent…"
    aws s3 ls "s3://${S3_BUCKET}/weekly/" --region "${AWS_REGION}" | \
        sort | grep '\.enc$' | head -n -${RETENTION_WEEKLY} | \
        awk '{print $4}' | \
        while read -r f; do
            [[ -n "${f}" ]] && {
                aws s3 rm "s3://${S3_BUCKET}/weekly/${f}"          --region "${AWS_REGION}" || true
                aws s3 rm "s3://${S3_BUCKET}/weekly/${f}.sha256"   --region "${AWS_REGION}" || true
            }
        done

    ARCHIVE_SIZE=$(stat -c%s "${BACKUP_DIR}/${ENCRYPTED_NAME}" 2>/dev/null \
                   || stat -f%z "${BACKUP_DIR}/${ENCRYPTED_NAME}" 2>/dev/null || echo "unknown")
    alert_success "Backup complete — ${ENCRYPTED_NAME} (${ARCHIVE_SIZE} bytes) | checksum: ${CHECKSUM}"
}

# ── RESTORE ───────────────────────────────────────────────────────────────────
restore() {
    local DATE_FILTER="${1:-}"
    log "Listing available backups…"
    aws s3 ls "s3://${S3_BUCKET}/daily/" --region "${AWS_REGION}" | \
        grep '\.enc$' | grep "${DATE_FILTER}" || true

    if [[ "${RESTORE_DRY_RUN:-0}" == "1" ]]; then
        log "DRY RUN — no files downloaded or restored."
        exit 0
    fi

    read -rp "Enter exact filename to restore (e.g. synaptiq_2024-01-15T020000Z.tar.gz.enc): " RESTORE_FILE
    [[ -z "${RESTORE_FILE}" ]] && { log "Aborted."; exit 1; }

    mkdir -p "${BACKUP_DIR}"
    trap 'rm -rf "${BACKUP_DIR}"' EXIT

    log "Downloading archive: s3://${S3_BUCKET}/daily/${RESTORE_FILE}"
    aws s3 cp "s3://${S3_BUCKET}/daily/${RESTORE_FILE}" "${BACKUP_DIR}/${RESTORE_FILE}" \
        --region "${AWS_REGION}" || { error "Download failed"; exit 1; }

    # Download and verify SHA256 checksum
    CHECKSUM_FILE="${RESTORE_FILE}.sha256"
    if aws s3 cp "s3://${S3_BUCKET}/daily/${CHECKSUM_FILE}" "${BACKUP_DIR}/${CHECKSUM_FILE}" \
            --region "${AWS_REGION}" 2>/dev/null; then
        log "Verifying SHA-256 checksum…"
        EXPECTED=$(cat "${BACKUP_DIR}/${CHECKSUM_FILE}")
        ACTUAL=$(sha256sum "${BACKUP_DIR}/${RESTORE_FILE}" | awk '{print $1}')
        if [[ "${EXPECTED}" != "${ACTUAL}" ]]; then
            error "CHECKSUM MISMATCH — archive may be corrupted!"
            error "  Expected: ${EXPECTED}"
            error "  Actual:   ${ACTUAL}"
            exit 1
        fi
        log "Checksum OK: ${ACTUAL}"
    else
        log "WARNING: No checksum file found — skipping integrity verification (legacy backup)"
    fi

    # Decrypt
    if [[ "${RESTORE_FILE}" == *.enc ]]; then
        if [[ -z "${BACKUP_ENCRYPTION_PASSPHRASE:-}" ]]; then
            error "BACKUP_ENCRYPTION_PASSPHRASE must be set to decrypt backup"
            exit 1
        fi
        log "Decrypting…"
        DECRYPTED="${RESTORE_FILE%.enc}"
        openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
            -pass pass:"${BACKUP_ENCRYPTION_PASSPHRASE}" \
            -in  "${BACKUP_DIR}/${RESTORE_FILE}" \
            -out "${BACKUP_DIR}/${DECRYPTED}" \
            || { error "Decryption failed — wrong passphrase?"; exit 1; }
        RESTORE_ARCHIVE="${DECRYPTED}"
    else
        RESTORE_ARCHIVE="${RESTORE_FILE}"
    fi

    log "Extracting archive…"
    tar -xzf "${BACKUP_DIR}/${RESTORE_ARCHIVE}" -C "${BACKUP_DIR}" \
        || { error "Extraction failed"; exit 1; }

    # Count collections before restore for comparison
    PRE_COUNT=$(mongosh "${MONGO_URL}" --quiet \
        --eval "db.getSiblingDB('${DB_NAME}').getCollectionNames().length" 2>/dev/null || echo "unknown")
    log "Pre-restore collection count: ${PRE_COUNT}"

    log "Restoring to MongoDB (DB=${DB_NAME}, --drop)…"
    mongorestore \
        --uri="${MONGO_URL}" \
        --db="${DB_NAME}" \
        --drop \
        --gzip \
        "${BACKUP_DIR}/dump/${DB_NAME}" \
        || { error "mongorestore failed"; exit 1; }

    # Verify restore integrity
    log "Verifying restore integrity…"
    POST_COUNT=$(mongosh "${MONGO_URL}" --quiet \
        --eval "db.getSiblingDB('${DB_NAME}').getCollectionNames().length" 2>/dev/null || echo "unknown")
    USER_COUNT=$(mongosh "${MONGO_URL}" --quiet \
        --eval "db.getSiblingDB('${DB_NAME}').users.countDocuments({})" 2>/dev/null || echo "unknown")
    log "Post-restore — collections: ${POST_COUNT}, users: ${USER_COUNT}"

    if [[ "${POST_COUNT}" == "0" ]] || [[ "${POST_COUNT}" == "unknown" ]]; then
        error "WARNING: Post-restore collection count is ${POST_COUNT} — verify manually"
    else
        log "Restore integrity: OK (${POST_COUNT} collections, ${USER_COUNT} users)"
    fi

    log "Restore complete. Next steps:"
    log "  1. Verify application health: curl https://api.synaptiq.academy/api/health"
    log "  2. Restart backend: docker compose -f deploy/docker-compose.prod.yml start backend"
}

# ── ENTRY ─────────────────────────────────────────────────────────────────────
case "${1:-backup}" in
    backup)  backup ;;
    restore) restore "${2:-}" ;;
    *) echo "Usage: $0 [backup|restore [date-filter]]" >&2; exit 1 ;;
esac
