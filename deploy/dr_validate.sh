#!/usr/bin/env bash
# SYNAPTIQ — Disaster Recovery Validation Script
#
# Validates all critical infrastructure components before and after
# a disaster recovery event. Run this after a restore or deployment.
#
# Usage:
#   source backend/.env && ./deploy/dr_validate.sh
#   or: ./deploy/dr_validate.sh --host https://api.synaptiq.academy
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more critical checks failed

set -uo pipefail

BACKEND_HOST="${1:-https://api.synaptiq.academy}"
# Strip trailing slash
BACKEND_HOST="${BACKEND_HOST%/}"

PASS=0
FAIL=0
WARN=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*"; }
pass() { echo -e "${GREEN}  ✅ PASS${NC}  $*"; (( PASS++ )) || true; }
fail() { echo -e "${RED}  ❌ FAIL${NC}  $*"; (( FAIL++ )) || true; }
warn() { echo -e "${YELLOW}  ⚠️  WARN${NC}  $*"; (( WARN++ )) || true; }

log "========================================================"
log "SYNAPTIQ Disaster Recovery Validation"
log "Target: ${BACKEND_HOST}"
log "========================================================"

# ── 1. Required environment variables ────────────────────────────────────────
log ""
log "[ 1 / 8 ] Environment variables"

check_env() {
    local var="$1"
    local level="${2:-error}"
    local val="${!var:-}"
    if [[ -n "${val}" ]]; then
        pass "${var} is set"
    elif [[ "${level}" == "warn" ]]; then
        warn "${var} is not set (optional)"
    else
        fail "${var} is not set (REQUIRED)"
    fi
}

check_env "MONGODB_URI"
check_env "MONGODB_DB_NAME" warn
check_env "JWT_SECRET"
check_env "REDIS_URL"
check_env "REDIS_PASSWORD"
check_env "ENCRYPTION_KEY"
check_env "RESEND_API_KEY"
check_env "S3_BACKUP_BUCKET" warn
check_env "AWS_ACCESS_KEY_ID" warn
check_env "AWS_SECRET_ACCESS_KEY" warn
check_env "BACKUP_ENCRYPTION_PASSPHRASE" warn
check_env "ALERT_WEBHOOK_URL" warn

# ── 2. MongoDB connectivity ───────────────────────────────────────────────────
log ""
log "[ 2 / 8 ] MongoDB connectivity"

if command -v mongosh &>/dev/null; then
    DB_NAME="${MONGODB_DB_NAME:-${DB_NAME:-synaptiq}}"
    if mongosh "${MONGODB_URI:-${MONGO_URL:-}}" \
            --eval "db.getSiblingDB('${DB_NAME}').runCommand({ping:1})" \
            --quiet --norc 2>/dev/null | grep -q '"ok" : 1\|"ok":1\|ok: 1'; then
        COLL_COUNT=$(mongosh "${MONGODB_URI:-${MONGO_URL:-}}" \
            --eval "db.getSiblingDB('${DB_NAME}').getCollectionNames().length" \
            --quiet --norc 2>/dev/null || echo "unknown")
        USER_COUNT=$(mongosh "${MONGODB_URI:-${MONGO_URL:-}}" \
            --eval "db.getSiblingDB('${DB_NAME}').users.countDocuments({})" \
            --quiet --norc 2>/dev/null || echo "unknown")
        pass "MongoDB reachable — ${COLL_COUNT} collections, ${USER_COUNT} users"
    else
        fail "MongoDB ping failed — check MONGODB_URI and Atlas Network Access"
    fi
else
    warn "mongosh not installed — skipping direct MongoDB check (using /api/health instead)"
fi

# ── 3. Redis connectivity ─────────────────────────────────────────────────────
log ""
log "[ 3 / 8 ] Redis connectivity"

if command -v redis-cli &>/dev/null && [[ -n "${REDIS_URL:-}" ]]; then
    REDIS_HOST=$(echo "${REDIS_URL}" | sed 's|redis://[^@]*@\([^:]*\).*|\1|;s|redis://\([^:]*\).*|\1|')
    REDIS_PORT=$(echo "${REDIS_URL}" | sed 's|.*:\([0-9]*\)/.*|\1|' | grep -E '^[0-9]+$' || echo "6379")
    PW="${REDIS_PASSWORD:-}"
    AUTH_ARGS=()
    [[ -n "${PW}" ]] && AUTH_ARGS=(-a "${PW}" --no-auth-warning)
    if redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" "${AUTH_ARGS[@]}" ping 2>/dev/null | grep -q PONG; then
        REDIS_VERSION=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" "${AUTH_ARGS[@]}" \
            info server 2>/dev/null | grep redis_version | cut -d: -f2 | tr -d '\r' || echo "unknown")
        pass "Redis reachable — version ${REDIS_VERSION}"
    else
        fail "Redis ping failed — check REDIS_URL and REDIS_PASSWORD"
    fi
else
    warn "redis-cli not installed or REDIS_URL not set — skipping direct Redis check"
fi

# ── 4. Application health endpoint ───────────────────────────────────────────
log ""
log "[ 4 / 8 ] Application health endpoints"

if command -v curl &>/dev/null; then
    HTTP_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
        "${BACKEND_HOST}/api/health" --max-time 10 2>/dev/null || echo "000")
    if [[ "${HTTP_STATUS}" == "200" ]]; then
        HEALTH_BODY=$(curl -sf "${BACKEND_HOST}/api/health" --max-time 10 2>/dev/null || echo "{}")
        MONGO_STATUS=$(echo "${HEALTH_BODY}" | grep -o '"mongodb":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
        REDIS_STATUS=$(echo "${HEALTH_BODY}" | grep -o '"redis":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
        pass "/api/health → 200 (mongodb=${MONGO_STATUS}, redis=${REDIS_STATUS})"
    else
        fail "/api/health returned HTTP ${HTTP_STATUS} (expected 200)"
    fi

    LIVE_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
        "${BACKEND_HOST}/api/health/live" --max-time 5 2>/dev/null || echo "000")
    if [[ "${LIVE_STATUS}" == "200" ]]; then
        pass "/api/health/live → 200 (liveness probe OK)"
    else
        fail "/api/health/live returned HTTP ${LIVE_STATUS}"
    fi

    READY_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
        "${BACKEND_HOST}/api/health/ready" --max-time 10 2>/dev/null || echo "000")
    if [[ "${READY_STATUS}" == "200" ]]; then
        pass "/api/health/ready → 200 (readiness probe OK)"
    elif [[ "${READY_STATUS}" == "503" ]]; then
        warn "/api/health/ready → 503 (degraded — MongoDB may be unreachable)"
    else
        fail "/api/health/ready returned HTTP ${READY_STATUS}"
    fi
else
    warn "curl not installed — skipping HTTP health checks"
fi

# ── 5. S3 backup availability ─────────────────────────────────────────────────
log ""
log "[ 5 / 8 ] S3 backup availability"

if [[ -n "${S3_BACKUP_BUCKET:-}" ]] && command -v aws &>/dev/null && \
   [[ -n "${AWS_ACCESS_KEY_ID:-}" ]] && [[ -n "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
    LATEST_BACKUP=$(aws s3 ls "s3://${S3_BACKUP_BUCKET}/daily/" \
        --region "${AWS_REGION:-us-east-1}" 2>/dev/null \
        | grep '\.enc$' | sort | tail -1 || echo "")
    if [[ -n "${LATEST_BACKUP}" ]]; then
        BFILE=$(echo "${LATEST_BACKUP}" | awk '{print $4}')
        BSIZE=$(echo "${LATEST_BACKUP}" | awk '{print $3}')
        BDATE=$(echo "${LATEST_BACKUP}" | awk '{print $1}')
        pass "Latest backup: ${BFILE} (${BSIZE} bytes, ${BDATE})"

        # Check if checksum file exists
        if aws s3 ls "s3://${S3_BACKUP_BUCKET}/daily/${BFILE}.sha256" \
                --region "${AWS_REGION:-us-east-1}" &>/dev/null; then
            pass "Checksum file exists for latest backup"
        else
            warn "No .sha256 file found for latest backup — run check_backup_integrity.sh"
        fi
    else
        fail "No encrypted backups found in s3://${S3_BACKUP_BUCKET}/daily/ — run deploy/backup.sh"
    fi
else
    warn "AWS credentials or S3_BACKUP_BUCKET not set — skipping backup check"
fi

# ── 6. Disk space ─────────────────────────────────────────────────────────────
log ""
log "[ 6 / 8 ] Disk space"

DISK_USAGE=$(df / | awk 'NR==2 {gsub(/%/,""); print $5}')
DISK_AVAIL=$(df -h / | awk 'NR==2 {print $4}')
if [[ "${DISK_USAGE}" -lt 70 ]]; then
    pass "Disk usage: ${DISK_USAGE}% (${DISK_AVAIL} available)"
elif [[ "${DISK_USAGE}" -lt 85 ]]; then
    warn "Disk usage: ${DISK_USAGE}% (${DISK_AVAIL} available) — consider cleanup"
else
    fail "Disk usage: ${DISK_USAGE}% — critically low space (${DISK_AVAIL} available)"
fi

# ── 7. Docker container status ───────────────────────────────────────────────
log ""
log "[ 7 / 8 ] Docker container status"

if command -v docker &>/dev/null; then
    for CONTAINER in synaptiq_backend synaptiq_redis synaptiq_nginx; do
        STATUS=$(docker inspect --format='{{.State.Status}}' "${CONTAINER}" 2>/dev/null || echo "not_found")
        HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}' \
            "${CONTAINER}" 2>/dev/null || echo "not_found")
        if [[ "${STATUS}" == "running" ]]; then
            if [[ "${HEALTH}" == "healthy" ]] || [[ "${HEALTH}" == "no_healthcheck" ]]; then
                pass "${CONTAINER}: running (health: ${HEALTH})"
            else
                warn "${CONTAINER}: running but health=${HEALTH}"
            fi
        else
            fail "${CONTAINER}: status=${STATUS} (expected: running)"
        fi
    done
else
    warn "docker not installed — skipping container status check"
fi

# ── 8. Critical secrets format validation ─────────────────────────────────────
log ""
log "[ 8 / 8 ] Secret format validation"

# JWT_SECRET entropy
JWT="${JWT_SECRET:-}"
if [[ ${#JWT} -ge 32 ]]; then
    pass "JWT_SECRET length: ${#JWT} chars (≥ 32)"
else
    fail "JWT_SECRET too short: ${#JWT} chars (must be ≥ 32)"
fi

# ENCRYPTION_KEY: must be 32-byte base64
ENC="${ENCRYPTION_KEY:-}"
if [[ -n "${ENC}" ]]; then
    ENC_LEN=$(python3 -c "import base64,sys; d=base64.b64decode('${ENC}'); print(len(d))" 2>/dev/null || echo "0")
    if [[ "${ENC_LEN}" == "32" ]]; then
        pass "ENCRYPTION_KEY: valid 32-byte base64"
    else
        fail "ENCRYPTION_KEY: decoded to ${ENC_LEN} bytes (must be 32)"
    fi
else
    fail "ENCRYPTION_KEY is not set"
fi

# MONGODB_URI format
MURI="${MONGODB_URI:-}"
if [[ "${MURI}" == mongodb+srv://* ]]; then
    pass "MONGODB_URI: Atlas SRV format (mongodb+srv://…)"
elif [[ -n "${MURI}" ]]; then
    warn "MONGODB_URI: not Atlas SRV format — OK for dev, not for production"
else
    fail "MONGODB_URI is not set"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
log ""
log "========================================================"
log "DR Validation Summary"
log "  PASS: ${PASS}  WARN: ${WARN}  FAIL: ${FAIL}"
log "========================================================"

if [[ "${FAIL}" -gt 0 ]]; then
    echo -e "${RED}RESULT: NOT READY — ${FAIL} critical check(s) failed${NC}"
    exit 1
elif [[ "${WARN}" -gt 0 ]]; then
    echo -e "${YELLOW}RESULT: READY WITH WARNINGS — ${WARN} non-critical issue(s) found${NC}"
    exit 0
else
    echo -e "${GREEN}RESULT: FULLY READY — all ${PASS} checks passed${NC}"
    exit 0
fi
