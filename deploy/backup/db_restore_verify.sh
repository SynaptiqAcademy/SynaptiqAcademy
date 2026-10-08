#!/usr/bin/env bash
# Synaptiq — restore a backup into an ISOLATED database and verify it.
#
# Never restores over production: the target must be a separate server
# (localhost, a CI service container, or a dedicated restore cluster) and the
# restored database name must contain "restore". The script refuses anything
# else.
#
# Required env:
#   BACKUP_PASSPHRASE    the passphrase used by db_backup.sh
#   BACKUP_SRC           s3://bucket/prefix   or   file:///absolute/dir
#   RESTORE_TARGET_URI   connection string of the isolated target server
# Optional env:
#   BACKUP_NAME          base name to restore (default: newest in BACKUP_SRC)
#   RESTORE_DB_NAME      database name on the target (default: <db>_restore_<stamp>)
#   ALLOW_REMOTE_TARGET  set to 1 to allow a non-localhost target (a dedicated
#                        restore cluster). Atlas production hosts are still refused
#                        when PRODUCTION_HOST_PATTERN matches.
#   PRODUCTION_HOST_PATTERN  substring of the production host (refused as target)
#   AWS_REGION
#
# Exit status 0 only when the checksum matches, mongorestore succeeds and every
# collection's document count lies within the manifest's before/after range. Writes a JSON report.
set -euo pipefail

ts()  { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] $*"; }
die() { echo "[$(ts)] RESTORE CHECK FAILED: $*" >&2; exit 1; }

: "${BACKUP_PASSPHRASE:?}"; : "${BACKUP_SRC:?}"; : "${RESTORE_TARGET_URI:?}"

# ── Target safety ────────────────────────────────────────────────────────────
TARGET_HOST=$(printf '%s' "${RESTORE_TARGET_URI}" | sed -E 's#^[a-z+]+://([^@/]*@)?([^/?]+).*#\2#')
case "${TARGET_HOST}" in
  localhost*|127.0.0.1*|mongodb*|mongo:*|"[::1]"*) ;;   # local or CI service container
  *)
    [[ "${ALLOW_REMOTE_TARGET:-0}" == "1" ]] || die "target is not local; set ALLOW_REMOTE_TARGET=1 for a dedicated restore cluster"
    ;;
esac
if [[ -n "${PRODUCTION_HOST_PATTERN:-}" && "${TARGET_HOST}" == *"${PRODUCTION_HOST_PATTERN}"* ]]; then
  die "target matches the production host pattern — refusing"
fi

WORK=$(mktemp -d); trap 'rm -rf "${WORK}"' EXIT

# ── Fetch ────────────────────────────────────────────────────────────────────
fetch() {  # fetch <name>
  case "${BACKUP_SRC}" in
    s3://*) aws s3 cp "${BACKUP_SRC%/}/$1" "${WORK}/$1" --region "${AWS_REGION:-eu-central-1}" --only-show-errors ;;
    file://*) cp "${BACKUP_SRC#file://}/$1" "${WORK}/$1" ;;
  esac
}
if [[ -z "${BACKUP_NAME:-}" ]]; then
  case "${BACKUP_SRC}" in
    s3://*) BACKUP_NAME=$(aws s3 ls "${BACKUP_SRC%/}/" --region "${AWS_REGION:-eu-central-1}" | awk '{print $4}' | grep '\.archive\.gz\.enc$' | sort | tail -1) ;;
    file://*) BACKUP_NAME=$(ls "${BACKUP_SRC#file://}" | grep '\.archive\.gz\.enc$' | sort | tail -1) ;;
  esac
  BACKUP_NAME="${BACKUP_NAME%.archive.gz.enc}"
fi
[[ -n "${BACKUP_NAME}" ]] || die "no backup found"
log "Restoring ${BACKUP_NAME}"
for f in "${BACKUP_NAME}.archive.gz.enc" "${BACKUP_NAME}.archive.gz.enc.sha256" "${BACKUP_NAME}.manifest.json"; do
  fetch "$f" || die "could not fetch $f"
done

# ── Integrity ────────────────────────────────────────────────────────────────
( cd "${WORK}" && shasum -a 256 -c "${BACKUP_NAME}.archive.gz.enc.sha256" >/dev/null ) || die "checksum mismatch"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -in "${WORK}/${BACKUP_NAME}.archive.gz.enc" -out "${WORK}/archive.gz" \
  -pass env:BACKUP_PASSPHRASE || die "decryption failed (wrong passphrase?)"

SRC_DB=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["db"])' "${WORK}/${BACKUP_NAME}.manifest.json")
STAMP=$(date -u +"%Y%m%dT%H%M%SZ")
RESTORE_DB_NAME="${RESTORE_DB_NAME:-${SRC_DB}_restore_${STAMP}}"
[[ "${RESTORE_DB_NAME}" == *restore* ]] || die "restore database name must contain 'restore'"

# ── Restore ──────────────────────────────────────────────────────────────────
START=$(date +%s)
printf 'uri: "%s"\n' "${RESTORE_TARGET_URI}" > "${WORK}/restore.yaml"; chmod 600 "${WORK}/restore.yaml"
mongorestore --config="${WORK}/restore.yaml" --archive="${WORK}/archive.gz" --gzip \
  --nsFrom="${SRC_DB}.*" --nsTo="${RESTORE_DB_NAME}.*" --drop --quiet || die "mongorestore failed"
DURATION=$(( $(date +%s) - START ))

# ── Verify counts against the manifest ───────────────────────────────────────
export RESTORE_TARGET_URI RESTORE_DB_NAME
mongosh --nodb --quiet --norc --eval '
  const d = connect(process.env.RESTORE_TARGET_URI).getSiblingDB(process.env.RESTORE_DB_NAME);
  const out = {};
  for (const c of d.getCollectionNames()) if (!c.startsWith("system.")) out[c] = d.getCollection(c).countDocuments({});
  print(JSON.stringify(out));
' > "${WORK}/restored.json" || die "count query failed"

REPORT="${RESTORE_REPORT:-./restore_report_${STAMP}.json}"
python3 - "${WORK}/${BACKUP_NAME}.manifest.json" "${WORK}/restored.json" "${REPORT}" "${BACKUP_NAME}" "${RESTORE_DB_NAME}" "${DURATION}" <<'PY'
import json, sys
manifest, restored, report, name, target_db, duration = sys.argv[1:7]
m = json.load(open(manifest))["collections"]; r = json.load(open(restored))
# A live source keeps changing during the dump: the restored count must lie
# between the counts taken just before and just after mongodump.
def ok(c):
    lo, hi = sorted((m[c]["before"], m[c]["after"]))
    return lo <= r.get(c, 0) <= hi
mismatch = {c: {"before": m[c]["before"], "after": m[c]["after"], "restored": r.get(c, 0)}
            for c in m if not ok(c)}
out = {"backup": name, "restored_into": target_db, "duration_s": int(duration),
       "collections": len(m), "documents_manifest_after": sum(v["after"] for v in m.values()),
       "documents_restored": sum(r.get(c, 0) for c in m), "mismatches": mismatch,
       "result": "PASS" if not mismatch else "FAIL"}
json.dump(out, open(report, "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "mismatches"}), "mismatches:", len(mismatch))
sys.exit(0 if not mismatch else 1)
PY
log "Restore verification PASSED — report: ${REPORT}"
