#!/usr/bin/env bash
# SYNAPTIQ — weekly backup integrity check
# Verifies the most recent daily backup: exists, non-zero size, < 25 hours old,
# and SHA-256 checksum matches the stored .sha256 file.
# Called by synaptiq.cron every Sunday at 03:30 UTC.

set -euo pipefail

S3_BUCKET="${S3_BACKUP_BUCKET:?S3_BACKUP_BUCKET must be set}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ALERT_WEBHOOK="${ALERT_WEBHOOK_URL:-}"

log()   { echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*"; }
alert() {
    log "ALERT: $*"
    if [[ -n "${ALERT_WEBHOOK}" ]]; then
        curl -sf -X POST "${ALERT_WEBHOOK}" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"[SYNAPTIQ] ❌ BACKUP INTEGRITY FAIL: $*\"}" || true
    fi
}

WORK_DIR="/tmp/synaptiq_integrity_check_$$"
mkdir -p "${WORK_DIR}"
trap 'rm -rf "${WORK_DIR}"' EXIT

# ── 1. List and validate latest backup exists ─────────────────────────────────
LATEST=$(aws s3 ls "s3://${S3_BUCKET}/daily/" --region "${AWS_REGION}" \
         | grep '\.enc$' | sort | tail -1)

if [[ -z "${LATEST}" ]]; then
    alert "No encrypted backup files found in s3://${S3_BUCKET}/daily/"
    exit 1
fi

FILENAME=$(echo "${LATEST}" | awk '{print $4}')
SIZE=$(echo "${LATEST}"     | awk '{print $3}')

log "Latest backup: ${FILENAME} (${SIZE} bytes)"

# ── 2. Verify minimum size ────────────────────────────────────────────────────
if [[ "${SIZE}" -lt 8192 ]]; then
    alert "Latest backup ${FILENAME} is suspiciously small (${SIZE} bytes — expected > 8 KB)"
    exit 1
fi

# ── 3. Verify age < 25 hours ──────────────────────────────────────────────────
BACKUP_DATE=$(echo "${LATEST}" | awk '{print $1 " " $2}')
# Support both GNU date (-d) and BSD date (-j -f)
BACKUP_EPOCH=$(date -d "${BACKUP_DATE}" +%s 2>/dev/null \
               || date -j -f "%Y-%m-%d %H:%M:%S" "${BACKUP_DATE}" +%s 2>/dev/null \
               || echo 0)
NOW_EPOCH=$(date +%s)
AGE_HOURS=$(( (NOW_EPOCH - BACKUP_EPOCH) / 3600 ))

if [[ "${AGE_HOURS}" -gt 25 ]]; then
    alert "Latest backup is ${AGE_HOURS}h old (${FILENAME}) — backup job may have failed"
    exit 1
fi

log "Backup age: ${AGE_HOURS}h (within 25h window)"

# ── 4. Verify SHA-256 checksum ────────────────────────────────────────────────
CHECKSUM_FILE="${FILENAME}.sha256"

if aws s3 ls "s3://${S3_BUCKET}/daily/${CHECKSUM_FILE}" --region "${AWS_REGION}" &>/dev/null; then
    log "Downloading checksum file for verification…"
    aws s3 cp "s3://${S3_BUCKET}/daily/${CHECKSUM_FILE}" \
              "${WORK_DIR}/expected.sha256" \
              --region "${AWS_REGION}" --quiet

    log "Downloading archive for checksum verification (this may take a moment)…"
    aws s3 cp "s3://${S3_BUCKET}/daily/${FILENAME}" \
              "${WORK_DIR}/${FILENAME}" \
              --region "${AWS_REGION}" --quiet

    EXPECTED=$(cat "${WORK_DIR}/expected.sha256")
    ACTUAL=$(sha256sum "${WORK_DIR}/${FILENAME}" | awk '{print $1}')

    if [[ "${EXPECTED}" != "${ACTUAL}" ]]; then
        alert "SHA-256 MISMATCH for ${FILENAME}! Expected=${EXPECTED} Actual=${ACTUAL}"
        exit 1
    fi
    log "Checksum OK: ${ACTUAL}"
else
    log "WARNING: No .sha256 file found for ${FILENAME} — legacy backup, skipping checksum verification"
fi

# ── 5. Report success ─────────────────────────────────────────────────────────
SUMMARY="Weekly backup check PASSED — ${FILENAME} (${SIZE} bytes, ${AGE_HOURS}h old)"
log "OK — ${SUMMARY}"

if [[ -n "${ALERT_WEBHOOK}" ]]; then
    curl -sf -X POST "${ALERT_WEBHOOK}" \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"[SYNAPTIQ] ✅ ${SUMMARY}\"}" || true
fi
